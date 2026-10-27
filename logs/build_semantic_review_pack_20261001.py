"""Bounded, timestamped CAM_FRONT previews for five development review cases."""

import csv
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'logs'))
from evaluation_media_audit_20260926 import records

NAMES = ('scene-0158', 'scene-0905', 'scene-0544', 'scene-0997', 'scene-0703')
DEST = ROOT / 'exports/semantic_review_20261001'
REPORT = ROOT / 'HDBSCAN/tables/semantic_review_media_20261001.json'


def record(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    if DEST.exists() or REPORT.exists():
        raise FileExistsError('Dated exports already exist; do not overwrite')
    split_path = ROOT / 'HDBSCAN/tables/evaluation_split_20260924.csv'
    raw_path = ROOT / 'HDBSCAN/tables/scene_features_development_audit700_20260927.csv'
    run_path = ROOT / 'HDBSCAN/tables/parameter_stability_20260930/n30_s1_seed42.csv'
    semantic_path = ROOT / 'HDBSCAN/tables/cluster_semantics_20260930.json'
    rows = {r['scene_name']: r for r in read_csv(split_path) if r['scene_name'] in NAMES}
    if set(rows) != set(NAMES) or any(r['split'] != 'development' for r in rows.values()):
        raise ValueError('Review cases must be frozen development members')
    raw = {r['scene_name']: r for r in read_csv(raw_path) if r['scene_name'] in NAMES}
    run = {r['scene_name']: r for r in read_csv(run_path) if r['scene_name'] in NAMES}
    for name in NAMES:
        if not rows[name]['scene_token'] == raw[name]['scene_token'] == run[name]['scene_token']:
            raise ValueError('Scene token mismatch')
    semantic = json.loads(semantic_path.read_text(encoding='utf-8'))
    missing = []
    for item in semantic['inputs']:
        path = Path(item['path'])
        if not path.exists():
            missing.append(item)
        elif record(path)['sha256'] != item['sha256']:
            raise ValueError('Semantic input changed: ' + str(path))
    meta = ROOT / 'nuScenes/v1.0-trainval'
    sources = [record(p) for p in [split_path, raw_path, run_path, semantic_path, Path(__file__),
               ROOT / 'logs/evaluation_media_audit_20260926.py']]
    sources += [record(meta / n) for n in ['scene.json', 'sample.json', 'sensor.json', 'calibrated_sensor.json']]
    scenes = {r['name']: r for r in json.loads((meta / 'scene.json').read_text(encoding='utf-8')) if r['name'] in NAMES}
    tokens = {s['token']: n for n, s in scenes.items()}
    samples = {s['token']: s for s in json.loads((meta / 'sample.json').read_text(encoding='utf-8')) if s['scene_token'] in tokens}
    sensors = {s['token']: s for s in json.loads((meta / 'sensor.json').read_text(encoding='utf-8'))}
    calibrations = {s['token']: sensors[s['sensor_token']]['channel']
                    for s in json.loads((meta / 'calibrated_sensor.json').read_text(encoding='utf-8'))}
    camera = {n: [] for n in NAMES}
    for count, row in enumerate(records(meta / 'sample_data.json'), 1):
        if count % 500000 == 0:
            print(f'Metadata rows scanned: {count}', flush=True)
        sample = samples.get(row['sample_token'])
        if sample and calibrations[row['calibrated_sensor_token']] == 'CAM_FRONT':
            camera[tokens[sample['scene_token']]].append(row)
    sources.append(record(meta / 'sample_data.json'))
    DEST.mkdir(parents=True)
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 20)
    findings = []
    for name in NAMES:
        scene = scenes[name]
        if scene['token'] != rows[name]['scene_token'] or scene['log_token'] != rows[name]['log_token']:
            raise ValueError('Scene metadata identity mismatch')
        scene_samples = [s for s in samples.values() if s['scene_token'] == scene['token']]
        if len(scene_samples) != scene['nbr_samples']:
            raise ValueError('Incomplete sample metadata')
        start = samples[scene['first_sample_token']]['timestamp']
        last = samples[scene['last_sample_token']]['timestamp']
        all_frames = sorted(camera[name], key=lambda r: r['timestamp'])
        keyframes = [r for r in all_frames if r['is_key_frame']]
        if len(keyframes) != len(scene_samples) or len({r['sample_token'] for r in keyframes}) != len(scene_samples):
            raise ValueError('Incomplete keyframe metadata')
        # Keep sweeps between first and last front keyframes, never bridge scenes.
        all_frames = [r for r in all_frames if keyframes[0]['timestamp'] <= r['timestamp'] <= keyframes[-1]['timestamp']]
        media = []
        for r in all_frames:
            path = (ROOT / 'nuScenes' / r['filename']).resolve()
            path.relative_to((ROOT / 'nuScenes').resolve())
            media.append({'token': r['token'], 'filename': r['filename'], 'timestamp': r['timestamp'],
                          'is_key_frame': r['is_key_frame'], 'exists_nonempty': path.is_file() and path.stat().st_size > 0})
        missing_keys = [m for m in media if m['is_key_frame'] and not m['exists_nonempty']]
        item = {'scene_name': name, 'scene_token': scene['token'], 'log_token': scene['log_token'],
                'description': scene['description'], 'location': rows[name]['log_location'],
                'split': 'development', 'cluster': int(run[name]['cluster']), 'priority_rank': int(run[name]['priority_rank']),
                'risk': float(run[name]['risk']), 'metadata_span_seconds': (last-start)/1e6,
                'keyframes': len(keyframes), 'camera_records_within_keyframe_span': len(all_frames),
                'missing_media_count': sum(not m['exists_nonempty'] for m in media),
                'missing_keyframes': len(missing_keys), 'media': media, 'outputs': [], 'status': 'pending'}
        findings.append(item)
        if missing_keys:
            item['status'] = 'missing_keyframes_no_export'
            print(f'{name}: {len(missing_keys)} missing keyframes; export skipped', flush=True)
            continue
        # Degrade explicitly to 2-Hz keyframes if sweeps are incomplete.
        pool = all_frames if item['missing_media_count'] == 0 else keyframes
        item['sampling_mode'] = 'camera_sweeps_nearest_6hz' if pool is all_frames else 'keyframes_native_2hz'
        if pool is all_frames:
            selected = {}
            tick = pool[0]['timestamp']
            while tick <= pool[-1]['timestamp']:
                nearest = min(pool, key=lambda r: (abs(r['timestamp'] - tick), r['timestamp']))
                selected[nearest['token']] = nearest
                tick += 1e6 / 6
            selected[pool[-1]['token']] = pool[-1]
            chosen = sorted(selected.values(), key=lambda r: r['timestamp'])
        else:
            chosen = pool
        frames, frame_records, durations = [], [], []
        try:
            for i, r in enumerate(chosen):
                path = ROOT / 'nuScenes' / r['filename']
                with Image.open(path) as original:
                    original.load()
                    if original.size != (r['width'], r['height']):
                        raise ValueError('Image dimensions disagree with metadata')
                    frame = ImageOps.contain(original.convert('RGB'), (960, 540), Image.Resampling.LANCZOS)
                canvas = Image.new('RGB', (960, 576), 'black')
                canvas.paste(frame, ((960-frame.width)//2, 36))
                relative = (r['timestamp'] - start)/1e6
                ImageDraw.Draw(canvas).text((12, 7), f'{name} | CAM_FRONT | data t={relative:06.2f}s', font=font, fill='white')
                frames.append(canvas)
                frame_records.append({'index': i, 'token': r['token'], 'filename': r['filename'],
                    'timestamp': r['timestamp'], 'scene_relative_seconds': relative, 'source': record(path)})
                if i < len(chosen)-1:
                    # Accumulated centisecond rounding prevents the old 6.25-fps speed-up.
                    t0 = chosen[0]['timestamp']
                    duration = 10 * (round((chosen[i+1]['timestamp']-t0)/10000) - round((r['timestamp']-t0)/10000))
                else:
                    duration = durations[-1] if durations else 500
                durations.append(max(10, duration))
            gif = DEST / f'{name}_CAM_FRONT_timestamped.gif'
            frames[0].save(gif, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False)
            decoded_durations = []
            with Image.open(gif) as check:
                if check.n_frames != len(frames):
                    raise ValueError('Unexpected merged GIF frames')
                for i in range(check.n_frames):
                    check.seek(i)
                    check.load()
                    decoded_durations.append(check.info['duration'])
            if decoded_durations != durations:
                raise ValueError('GIF timing mismatch')
            contact = Image.new('RGB', (960, 576), 'white')
            indices = sorted({round(i*(len(frames)-1)/5) for i in range(6)})
            for k, i in enumerate(indices):
                contact.paste(frames[i].resize((320, 288), Image.Resampling.LANCZOS), ((k%3)*320, (k//3)*288))
            contact_path = DEST / f'{name}_contact.jpg'
            contact.save(contact_path, quality=90)
            item.update(status='exported_verified', selected_frames=frame_records, frame_durations_ms=durations,
                        frame_count=len(frames), playback_seconds=sum(durations)/1000,
                        sampled_data_span_seconds=(chosen[-1]['timestamp']-chosen[0]['timestamp'])/1e6,
                        final_frame_hold_seconds=durations[-1]/1000, outputs=[record(gif), record(contact_path)])
            print(f'{name}: {len(frames)} frames, {item["playback_seconds"]:.2f}s, {item["sampling_mode"]}', flush=True)
        except Exception as exc:
            item.update(status='export_failed', error=f'{type(exc).__name__}: {exc}')
            print(f'{name}: {item["error"]}', flush=True)
    for source in sources:
        if record(source['path'])['sha256'] != source['sha256']:
            raise ValueError('Source changed during export')
    report = {'created_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'stage': 'development_targeted_media_review', 'command': [sys.executable, *sys.argv],
        'script': record(__file__), 'inputs': sources, 'semantic_provenance_missing_files': missing,
        'scenes': findings, 'exported_count': sum(s['status']=='exported_verified' for s in findings),
        'limits': ['Development diagnostics, not expert blind evaluation.',
                  'CAM_FRONT only, no object boxes or verified target identity.',
                  'Timestamps refer to original camera metadata; final frame held one additional interval.',
                  'Camera records checked for existence; only exported frames fully decoded.',
                  'Original semantic analysis script absent; retained JSON not fully reproducible from its old recipe.']}
    with REPORT.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'Report: {REPORT}; exported {report["exported_count"]}/5', flush=True)


if __name__ == '__main__':
    main()
