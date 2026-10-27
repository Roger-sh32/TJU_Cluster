"""Prepare a file-level recovery inventory without changing source data."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import ssl
import sys
from urllib.request import Request, urlopen

import certifi

from evaluation_media_audit_20260926 import file_record, records

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'HDBSCAN/scripts'))
from experiment_partition import load_partition


def main():
    output = ROOT / 'exports/media_recovery_20260926'
    if output.exists():
        raise FileExistsError('Keep previous inventories; use a new batch directory')
    partition = load_partition()
    selected = {r['scene_token']: r for r in partition['rows']
                if r['split'] == 'evaluation'}
    data = ROOT / 'nuScenes'
    meta = data / 'v1.0-trainval'
    sensors = {r['token']: r for r in json.loads((meta / 'sensor.json').read_text())}
    calibration = {r['token']: sensors[r['sensor_token']]
                   for r in json.loads((meta / 'calibrated_sensor.json').read_text())}
    samples = {r['token']: r for r in json.loads((meta / 'sample.json').read_text())
               if r['scene_token'] in selected}
    context = ssl.create_default_context(cafile=certifi.where())
    packages = []
    for part in range(3, 11):
        url = ('https://motional-nuscenes.s3.amazonaws.com/public/v1.0/'
               f'v1.0-trainval{part:02}_blobs_camera.tgz')
        with urlopen(Request(url, method='HEAD'), context=context, timeout=30) as response:
            packages.append({'part': part, 'url': url,
                             'bytes': int(response.headers['Content-Length']),
                             'etag': response.headers.get('ETag'),
                             'accept_ranges': response.headers.get('Accept-Ranges')})
        print(f'Package {part:02}: HTTP HEAD verified', flush=True)
    output.mkdir(parents=True)
    listing = output / 'missing_evaluation_camera_files.jsonl'
    totals = Counter()
    channels = {}
    seen = set()
    rows = 0
    with listing.open('x', encoding='utf-8') as stream:
        for row in records(meta / 'sample_data.json'):
            rows += 1
            if rows % 500000 == 0:
                print(f'Metadata rows checked: {rows}', flush=True)
            sample = samples.get(row['sample_token'])
            if sample is None:
                continue
            sensor = calibration[row['calibrated_sensor_token']]
            if sensor['modality'] != 'camera':
                continue
            relative = row['filename']
            if relative in seen:
                raise ValueError('Duplicate media filename in selected metadata')
            seen.add(relative)
            path = (data / relative).resolve()
            path.relative_to(data.resolve())
            kind = 'keyframe' if row['is_key_frame'] else 'associated_nonkeyframe'
            status = 'present_nonempty' if path.is_file() and path.stat().st_size else 'missing_or_empty'
            totals[f'{kind}_{status}'] += 1
            channel = sensor['channel']
            channels.setdefault(channel, Counter())[f'{kind}_{status}'] += 1
            if status == 'present_nonempty':
                continue
            identity = selected[sample['scene_token']]
            stream.write(json.dumps({
                'filename': relative, 'scene_token': identity['scene_token'],
                'review_id': identity['review_id'], 'channel': channel,
                'sample_data_token': row['token'], 'is_key_frame': row['is_key_frame'],
                'timestamp': row['timestamp'], 'width': row['width'], 'height': row['height']
            }) + '\n')
    result = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'frozen_evaluation_camera_file_recovery_inventory',
        'python': sys.executable, 'command': [sys.executable, *sys.argv],
        'partition': partition['file'], 'script': file_record(Path(__file__).resolve()),
        'parser_script': file_record(ROOT / 'logs/evaluation_media_audit_20260926.py'),
        'metadata': [file_record(meta / n) for n in
                     ['sensor.json', 'calibrated_sensor.json', 'sample.json', 'sample_data.json']],
        'scene_count': len(selected), 'sample_data_rows_scanned': rows,
        'counts': dict(totals), 'channels': channels,
        'missing_file_list': file_record(listing),
        'candidate_packages': packages,
        'package_total_bytes': sum(p['bytes'] for p in packages),
        'free_disk_bytes_at_inventory': shutil.disk_usage(ROOT).free,
        'limits': [
            'Presence/nonempty check only; no image decoding or semantic review.',
            'Associated nonkeyframes can extend beyond the first keyframe playback start.',
            'Package 03-10 candidates are not a proven minimal scene-to-package mapping.',
            'HTTP length and ETag identify current objects; ETag is not assumed to be MD5.',
            'No archive downloaded, no source files changed, no split or labels changed.'
        ]
    }
    with (output / 'recovery_inventory.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'counts': result['counts'], 'package_total_bytes': result['package_total_bytes'],
                      'output': str(output)}, indent=2), flush=True)


if __name__ == '__main__':
    main()
