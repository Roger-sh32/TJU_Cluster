"""One-off read-only media audit for the frozen evaluation set, without semantic review."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'HDBSCAN/scripts'))
from experiment_partition import load_partition


def file_record(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}


def records(path):
    """Incrementally parse an array without loading the 1.3 GB table into RAM."""
    decoder = json.JSONDecoder()
    with path.open(encoding='utf-8') as stream:
        buffer, index, eof = '', 0, False
        def extend():
            nonlocal buffer, index, eof
            chunk = stream.read(1024 * 1024)
            buffer, index = buffer[index:] + chunk, 0
            eof = not chunk
        extend()
        if not buffer.lstrip().startswith('['):
            raise ValueError('Expected a JSON array')
        index = buffer.index('[') + 1
        while True:
            while index < len(buffer) and buffer[index] in ' \r\n\t,':
                index += 1
            if index == len(buffer):
                if eof:
                    raise ValueError('Truncated metadata array')
                extend()
                continue
            if buffer[index] == ']':
                if (buffer[index + 1:] + stream.read()).strip():
                    raise ValueError('Unexpected trailing metadata')
                return
            try:
                value, index = decoder.raw_decode(buffer, index)
            except json.JSONDecodeError:
                if eof:
                    raise
                extend()
                continue
            yield value


def main():
    destination = ROOT / 'HDBSCAN/tables/evaluation_media_audit_20260926.json'
    if destination.exists():
        raise FileExistsError('Use a new dated audit; do not overwrite the old report')
    partition = load_partition()
    evaluation = [r for r in partition['rows'] if r['split'] == 'evaluation']
    assert len(evaluation) == 150
    data = ROOT / 'nuScenes'
    meta = data / 'v1.0-trainval'
    sensors = {r['token']: r for r in json.loads((meta / 'sensor.json').read_text())}
    calibrations = {r['token']: sensors[r['sensor_token']]
                    for r in json.loads((meta / 'calibrated_sensor.json').read_text())}
    channels = sorted({s['channel'] for s in sensors.values() if s['modality'] == 'camera'})
    assert len(channels) == 6 and 'CAM_FRONT' in channels
    selected = {r['scene_token']: r for r in evaluation}
    samples = {r['token']: r for r in json.loads((meta / 'sample.json').read_text())
               if r['scene_token'] in selected}
    scene_metadata = {r['token']: r for r in json.loads((meta / 'scene.json').read_text())
                      if r['token'] in selected}
    expected = Counter(r['scene_token'] for r in samples.values())
    if any(expected[t] != scene_metadata[t]['nbr_samples'] for t in selected):
        raise ValueError('Sample counts disagree with scene metadata')
    stats = {(token, channel): {'keyframe_records': 0, 'unique_samples': set(),
             'duplicate_keyframes': 0, 'status_counts': Counter(), 'examples': {},
             'associated_nonkeyframe_records': 0}
             for token in selected for channel in channels}
    rows_scanned = checked = 0
    print(f'Auditing {len(evaluation)} evaluation scenes, {len(samples)} samples, six cameras; no scene content shown.', flush=True)
    for row in records(meta / 'sample_data.json'):
        rows_scanned += 1
        if rows_scanned % 500000 == 0:
            print(f'Metadata rows scanned: {rows_scanned}; camera keyframes checked: {checked}', flush=True)
        sample = samples.get(row['sample_token'])
        if sample is None:
            continue
        sensor = calibrations[row['calibrated_sensor_token']]
        if sensor['modality'] != 'camera':
            continue
        channel = sensor['channel']
        stat = stats[sample['scene_token'], channel]
        if not row['is_key_frame']:
            stat['associated_nonkeyframe_records'] += 1
            continue
        checked += 1
        stat['keyframe_records'] += 1
        if row['sample_token'] in stat['unique_samples']:
            stat['duplicate_keyframes'] += 1
        stat['unique_samples'].add(row['sample_token'])
        path = (data / row['filename']).resolve()
        error = None
        try:
            path.relative_to(data.resolve())
            if not path.is_file():
                status = 'missing'
            elif path.stat().st_size == 0:
                status = 'empty'
            elif channel != 'CAM_FRONT':
                status = 'exists_not_decoded'
            else:
                with Image.open(path) as picture:
                    picture.load()
                    status = ('decoded' if picture.size == (row['width'], row['height'])
                              else 'dimension_mismatch')
        except Exception as exc:
            status, error = 'unreadable', f'{type(exc).__name__}: {exc}'
        stat['status_counts'][status] += 1
        if status not in {'decoded', 'exists_not_decoded'}:
            examples = stat['examples'].setdefault(status, [])
            if len(examples) < 3:
                examples.append({'filename': row['filename'], 'sample_token': row['sample_token'], 'error': error})
    output_scenes = []
    for identity in evaluation:
        token = identity['scene_token']
        per_channel = {}
        for channel in channels:
            stat = stats[token, channel]
            per_channel[channel] = {
                'expected_keyframes': expected[token],
                'keyframe_records': stat['keyframe_records'],
                'missing_sample_metadata': expected[token] - len(stat['unique_samples']),
                'duplicate_keyframes': stat['duplicate_keyframes'],
                'status_counts': dict(stat['status_counts']),
                'failure_examples_at_most_three_per_status': stat['examples'],
                'associated_nonkeyframe_records_not_file_checked': stat['associated_nonkeyframe_records']}
        front = per_channel['CAM_FRONT']
        ready = (front['status_counts'].get('decoded', 0) == expected[token]
                 and front['duplicate_keyframes'] == 0 and front['missing_sample_metadata'] == 0)
        all_exist = all(c['keyframe_records'] == expected[token] and c['duplicate_keyframes'] == 0
                        and sum(c['status_counts'].get(s, 0) for s in ['decoded', 'exists_not_decoded']) == expected[token]
                        for c in per_channel.values())
        output_scenes.append({'review_id': identity['review_id'], 'scene_name': identity['scene_name'],
                              'scene_token': token, 'log_token': identity['log_token'],
                              'front_keyframes_decode_complete': ready,
                              'all_camera_keyframes_exist_nonempty': all_exist,
                              'channels': per_channel})
    totals = {c: dict(sum((stats[t, c]['status_counts'] for t in selected), Counter())) for c in channels}
    report = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.executable,
        'command': [sys.executable, *sys.argv], 'scope': 'evaluation_media_integrity_only',
        'partition': partition['file'], 'script': file_record(Path(__file__).resolve()),
        'metadata': [file_record(meta / n) for n in ['sensor.json', 'calibrated_sensor.json', 'sample.json', 'scene.json', 'sample_data.json']],
        'scene_count': len(evaluation), 'sample_count': len(samples), 'sample_data_rows_scanned': rows_scanned,
        'front_complete_scene_count': sum(r['front_keyframes_decode_complete'] for r in output_scenes),
        'all_camera_keyframes_exist_scene_count': sum(r['all_camera_keyframes_exist_nonempty'] for r in output_scenes),
        'channel_totals': totals, 'scenes': output_scenes,
        'limits': ['No semantic image inspection or labels.', 'Nonkeyframe media files were not checked.',
                   'Only CAM_FRONT keyframes were fully decoded; other cameras checked for nonempty files.',
                   'Up to three file examples per scene/channel/status, not a complete download list.',
                   'Media availability never changes split membership or substitutes a risk label.']}
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in ['scene_count', 'sample_count', 'front_complete_scene_count',
                                          'all_camera_keyframes_exist_scene_count', 'channel_totals']}, indent=2), flush=True)
    print(destination, flush=True)


if __name__ == '__main__':
    main()
