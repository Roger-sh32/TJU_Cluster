"""Bounded CAM_FRONT review of eight changed development scenes; no fitting."""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'logs'))
from build_semantic_review_pack_20261001 import record
from evaluation_media_audit_20260926 import records

NAMES = ('scene-0002', 'scene-0552', 'scene-0093', 'scene-0102',
         'scene-0453', 'scene-0669', 'scene-0815', 'scene-0816')
TABLES = ROOT / 'HDBSCAN/tables'
DEST = ROOT / 'exports/development_review_20261012'
REPORT = TABLES / 'development_review_media_20261012.json'
PROTOCOL = TABLES / 'development_review_protocol_20261012.json'
DOCUMENT = ROOT / 'outputs/人工复核/候选特征八场景复核包_20261012.md'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    result = {r['scene_name']: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate scene identity')
    return result


def validate_members(names, split, features):
    for name in names:
        if (name not in split or name not in features or split[name]['split'] != 'development'
                or split[name]['scene_token'] != features[name]['scene_token']):
            raise ValueError('Only identity-matched frozen development cases allowed: ' + name)


def select_frames(pool):
    selected = {}
    tick = pool[0]['timestamp']
    while tick <= pool[-1]['timestamp']:
        row = min(pool, key=lambda r: (abs(r['timestamp'] - tick), r['timestamp']))
        selected[row['token']] = row
        tick += 1000000 / 6
    selected[pool[-1]['token']] = pool[-1]
    return sorted(selected.values(), key=lambda r: r['timestamp'])


def timing(chosen):
    start = chosen[0]['timestamp']
    elapsed = [round((r['timestamp'] - start) / 10000) for r in chosen]
    durations = [10 * (b - a) for a, b in zip(elapsed, elapsed[1:])]
    if not durations or min(durations) <= 0:
        raise ValueError('Invalid camera timing')
    return durations + [durations[-1]]


def verify_record(item):
    actual = record(item['path'])
    if actual['sha256'] != item['sha256']:
        raise ValueError('Source hash mismatch: ' + item['path'])
    if 'bytes' in item and actual['bytes'] != item['bytes']:
        raise ValueError('Source size mismatch: ' + item['path'])


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def export_scene(scene, pool, start):
    chosen = select_frames(pool)
    durations = timing(chosen)
    frames, provenance = [], []
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 20)
    for index, row in enumerate(chosen):
        path = (ROOT / 'nuScenes' / row['filename']).resolve()
        path.relative_to((ROOT / 'nuScenes').resolve())
        source = record(path)
        with Image.open(path) as original:
            original.load()
            if original.format != 'JPEG' or original.size != (row['width'], row['height']):
                raise ValueError('Camera image format/dimensions mismatch')
            frame = ImageOps.contain(original.convert('RGB'), (960, 540), Image.Resampling.LANCZOS)
        canvas = Image.new('RGB', (960, 576), 'black')
        canvas.paste(frame, ((960 - frame.width) // 2, 36 + (540 - frame.height) // 2))
        relative = (row['timestamp'] - start) / 1000000
        ImageDraw.Draw(canvas).text((12, 7),
            f'{scene["name"]} | CAM_FRONT | data t={relative:06.2f}s', font=font, fill='white')
        frames.append(canvas)
        provenance.append({'index': index, 'token': row['token'], 'filename': row['filename'],
                           'timestamp': row['timestamp'], 'scene_relative_seconds': relative, 'source': source})
    gif = DEST / f'{scene["name"]}_CAM_FRONT_timestamped.gif'
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False)
    contact = Image.new('RGB', (960, 576), 'black')
    for tile in range(6):
        index = round(tile * (len(frames) - 1) / 5)
        thumb = ImageOps.contain(frames[index], (320, 288), Image.Resampling.LANCZOS)
        contact.paste(thumb, ((tile % 3) * 320, (tile // 3) * 288 + (288 - thumb.height) // 2))
    contact_path = DEST / f'{scene["name"]}_contact.jpg'
    contact.save(contact_path, quality=90)
    return {'scene_name': scene['name'], 'scene_token': scene['token'], 'log_token': scene['log_token'],
            'description': scene['description'], 'split': 'development', 'review_status': 'pending_human',
            'camera_record_count': len(pool), 'keyframe_count': sum(r['is_key_frame'] for r in pool),
            'selected_frames': provenance, 'frame_count': len(frames), 'frame_durations_ms': durations,
            'data_span_seconds': (chosen[-1]['timestamp'] - chosen[0]['timestamp']) / 1000000,
            'playback_seconds': sum(durations) / 1000, 'final_frame_hold_seconds': durations[-1] / 1000,
            'outputs': [record(gif), record(contact_path)]}


def verify():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_record(report['protocol'])
    for item in protocol['inputs']:
        verify_record(item)
    if tuple(s['scene_name'] for s in report['scenes']) != NAMES:
        raise ValueError('Review identity/order changed')
    split = read_csv(TABLES / 'evaluation_split_20260924.csv')
    features = read_csv(TABLES / 'scene_features_development_candidate700_20261001.csv')
    validate_members(NAMES, split, features)
    for scene in report['scenes']:
        name = scene['scene_name']
        if scene['scene_token'] != split[name]['scene_token'] or scene['log_token'] != split[name]['log_token']:
            raise ValueError('Media scene identity mismatch')
        frames = scene['selected_frames']
        if not all(a['timestamp'] < b['timestamp'] for a, b in zip(frames, frames[1:])):
            raise ValueError('Non-monotonic frame times')
        for frame in frames:
            verify_record(frame['source'])
        for output in scene['outputs']:
            verify_record(output)
            with Image.open(output['path']) as image:
                if output['path'].endswith('.gif'):
                    if image.n_frames != scene['frame_count'] or image.size != (960, 576):
                        raise ValueError('GIF frame count/dimensions mismatch')
                    durations = []
                    for index in range(image.n_frames):
                        image.seek(index)
                        image.load()
                        durations.append(image.info['duration'])
                    if durations != scene['frame_durations_ms']:
                        raise ValueError('GIF duration mismatch')
                    if abs(sum(durations[:-1]) / 1000 - scene['data_span_seconds']) > .01:
                        raise ValueError('GIF timeline drift')
                else:
                    image.load()
    print('VERIFIED: eight development identities, bound sources, source images, GIF decode/timing.', flush=True)


def main():
    if any(p.exists() for p in (DEST, REPORT, PROTOCOL, DOCUMENT)):
        raise FileExistsError('Dated review already exists; verify instead of overwriting')
    comparison_path = TABLES / 'development_candidate700_comparison_20261001.json'
    comparison = json.loads(comparison_path.read_text(encoding='utf-8'))
    for key in ('protocol', 'input', 'manifest', 'quality'):
        verify_record(comparison[key])
    for module, digest in comparison['source_hashes'].items():
        verify_record({'path': str(ROOT / 'HDBSCAN/scripts' / module), 'sha256': digest})
    recovery_path = TABLES / 'media_recovery_audit_20261011.json'
    status = json.loads((ROOT / 'logs/media_recovery_20261011_status.json').read_text())
    verify_record(status['report'])
    recovery = json.loads(recovery_path.read_text(encoding='utf-8'))
    if status['phase'] != 'completed' or not recovery['all_selected_media_present_and_required_decode_checks_passed']:
        raise ValueError('Media recovery not verified complete')
    features_path = TABLES / 'scene_features_development_candidate700_20261001.csv'
    old_path = TABLES / 'scene_features_development_audit700_20260927.csv'
    split_path = TABLES / 'evaluation_split_20260924.csv'
    risk_path = TABLES / 'development_candidate700_risk_20261001.csv'
    split, features, old, risk = [read_csv(p) for p in (split_path, features_path, old_path, risk_path)]
    validate_members(NAMES, split, features)
    validate_members(NAMES, split, old)
    validate_members(NAMES, split, risk)
    meta = ROOT / 'nuScenes/v1.0-trainval'
    sources = [comparison_path, recovery_path, features_path, old_path, split_path, risk_path,
               Path(__file__), ROOT / 'logs/test_development_media_review_20261012.py',
               ROOT / 'logs/build_semantic_review_pack_20261001.py', ROOT / 'logs/evaluation_media_audit_20260926.py']
    sources += [meta / name for name in ('scene.json', 'sample.json', 'sample_data.json',
                                       'sensor.json', 'calibrated_sensor.json')]
    sources += [ROOT / 'HDBSCAN/scripts' / name for name in comparison['source_hashes']]
    bound = [record(p) for p in sources]
    write_json(PROTOCOL, {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Eight fixed development cases, CAM_FRONT media review only; no evaluation semantics or fit',
        'names': NAMES, 'inputs': bound, 'command': [sys.executable, *sys.argv],
        'sampling_hz': 6, 'final_frame_hold': 'one additional interval', 'overwrite_allowed': False})
    scenes = {r['name']: r for r in json.loads((meta / 'scene.json').read_text()) if r['name'] in NAMES}
    if set(scenes) != set(NAMES):
        raise ValueError('Missing scene metadata')
    tokens = {r['token']: name for name, r in scenes.items()}
    samples = {r['token']: r for r in json.loads((meta / 'sample.json').read_text()) if r['scene_token'] in tokens}
    sensors = {r['token']: r['channel'] for r in json.loads((meta / 'sensor.json').read_text())}
    channels = {r['token']: sensors[r['sensor_token']] for r in json.loads((meta / 'calibrated_sensor.json').read_text())}
    camera = {name: [] for name in NAMES}
    for index, row in enumerate(records(meta / 'sample_data.json'), 1):
        sample = samples.get(row['sample_token'])
        if sample and channels[row['calibrated_sensor_token']] == 'CAM_FRONT':
            camera[tokens[sample['scene_token']]].append(row)
        if index % 500000 == 0:
            print(f'Metadata scanned: {index}', flush=True)
    DEST.mkdir(parents=True)
    findings = []
    for name in NAMES:
        scene = scenes[name]
        if scene['token'] != features[name]['scene_token'] or scene['log_token'] != split[name]['log_token']:
            raise ValueError('Scene metadata mismatch')
        pool = sorted(camera[name], key=lambda r: r['timestamp'])
        keys = [r for r in pool if r['is_key_frame']]
        if len(keys) != scene['nbr_samples'] or len({r['sample_token'] for r in keys}) != len(keys):
            raise ValueError('Incomplete front keyframes')
        pool = [r for r in pool if keys[0]['timestamp'] <= r['timestamp'] <= keys[-1]['timestamp']]
        for row in pool:
            path = (ROOT / 'nuScenes' / row['filename']).resolve()
            path.relative_to((ROOT / 'nuScenes').resolve())
            if not path.is_file() or not path.stat().st_size:
                raise FileNotFoundError(path)
        item = export_scene(scene, pool, samples[scene['first_sample_token']]['timestamp'])
        changes = [c for c in comparison['feature_comparison']['changes'] if c['scene_name'] == name]
        for change in changes:
            if float(old[name][change['column']]) != change['old'] or float(features[name][change['column']]) != change['new']:
                raise ValueError('Saved feature difference mismatch')
        item.update(changes=changes, risk=risk[name], features=features[name])
        findings.append(item)
        print(f'{name}: {item["frame_count"]} frames, {item["playback_seconds"]:.2f}s', flush=True)
    for source in bound:
        verify_record(source)
    write_json(REPORT, {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'protocol': record(PROTOCOL),
        'scenes': findings, 'human_feedback_received': False, 'evaluation_used': False,
        'limits': ['Targeted development diagnostics, not random sampling or effectiveness validation.',
                   'Front camera only; no object boxes or verified target identification.',
                   'Only exported frames decoded in this batch; recovery report has wider checks.',
                   'Current candidate has no fit/ranking. Risk decreases are not accepted improvements.']})
    verify()
    print('Review media report: ' + str(REPORT), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--verify']:
        verify()
    elif sys.argv[1:]:
        raise SystemExit('Use no arguments to export, or --verify for read-only verification')
    else:
        main()
