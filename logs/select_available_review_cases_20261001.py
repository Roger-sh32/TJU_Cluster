"""Choose available development supplements for missing targeted review media."""

import csv
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'logs'))
from evaluation_media_audit_20260926 import records, file_record


def main():
    output = ROOT / 'HDBSCAN/tables/semantic_review_supplements_20261001.json'
    if output.exists():
        raise FileExistsError(output)
    raw_path = ROOT / 'HDBSCAN/tables/scene_features_development_audit700_20260927.csv'
    run_path = ROOT / 'HDBSCAN/tables/parameter_stability_20260930/n30_s1_seed42.csv'
    split_path = ROOT / 'HDBSCAN/tables/evaluation_split_20260924.csv'
    sem_path = ROOT / 'HDBSCAN/tables/cluster_semantics_20260930.json'
    raw = pd.read_csv(raw_path, float_precision='round_trip').set_index('scene_name')
    run = pd.read_csv(run_path, float_precision='round_trip').set_index('scene_name')
    split = pd.read_csv(split_path).set_index('scene_name')
    development = split[split.split.eq('development')]
    if set(raw.index) != set(development.index) or set(run.index) != set(raw.index):
        raise ValueError('Not the frozen complete development set')
    for name in raw.index:
        if raw.loc[name, 'scene_token'] != split.loc[name, 'scene_token'] or raw.loc[name, 'scene_token'] != run.loc[name, 'scene_token']:
            raise ValueError('Identity mismatch')
    meta = ROOT / 'nuScenes/v1.0-trainval'
    scenes = {r['token']: r for r in json.loads((meta / 'scene.json').read_text(encoding='utf-8'))
              if r['token'] in set(development.scene_token)}
    samples = {r['token']: r for r in json.loads((meta / 'sample.json').read_text(encoding='utf-8'))
               if r['scene_token'] in scenes}
    sensors = {r['token']: r['channel'] for r in json.loads((meta / 'sensor.json').read_text(encoding='utf-8'))}
    channels = {r['token']: sensors[r['sensor_token']] for r in json.loads((meta / 'calibrated_sensor.json').read_text(encoding='utf-8'))}
    keyframes = {t: [] for t in scenes}
    for count, row in enumerate(records(meta / 'sample_data.json'), 1):
        if count % 500000 == 0:
            print(f'Metadata rows scanned: {count}', flush=True)
        sample = samples.get(row['sample_token'])
        if sample and row['is_key_frame'] and channels[row['calibrated_sensor_token']] == 'CAM_FRONT':
            path = (ROOT / 'nuScenes' / row['filename']).resolve()
            path.relative_to((ROOT / 'nuScenes').resolve())
            keyframes[sample['scene_token']].append({'sample_token': row['sample_token'],
                'filename': row['filename'], 'exists_nonempty': path.is_file() and path.stat().st_size > 0})
    eligible = []
    for token, frame_rows in keyframes.items():
        if len(frame_rows) == scenes[token]['nbr_samples'] and len({r['sample_token'] for r in frame_rows}) == len(frame_rows) and all(r['exists_nonempty'] for r in frame_rows):
            eligible.append(scenes[token]['name'])
    # Existing exports are a conservative proxy for previously reviewed scenes.
    excluded = {p.name[:10] for p in (ROOT / 'exports').rglob('scene-*.gif')}
    original = ('scene-0158', 'scene-0905', 'scene-0544', 'scene-0997', 'scene-0703')
    excluded.update(original)
    features = json.loads(sem_path.read_text(encoding='utf-8'))['semantic_features']
    scale = raw[features].std(ddof=0)
    pairs = []
    used_logs = {split.loc['scene-0158', 'log_token']}
    for target in original[1:]:
        cluster = int(run.loc[target, 'cluster'])
        options = [name for name in eligible if name not in excluded and int(run.loc[name, 'cluster']) == cluster]
        fresh_logs = [name for name in options if split.loc[name, 'log_token'] not in used_logs]
        pool = fresh_logs or options
        if not pool:
            pairs.append({'missing_target': target, 'cluster': cluster, 'supplement': None, 'status': 'no_unreviewed_available_same_cluster'})
            print(f'{target}: no available unreviewed supplement', flush=True)
            continue
        distance = (((raw.loc[pool, features] - raw.loc[target, features]) / scale) ** 2).mean(axis=1)
        selected = min(pool, key=lambda name: (distance[name], name))
        excluded.add(selected)
        used_logs.add(split.loc[selected, 'log_token'])
        pair = {'missing_target': target, 'cluster': cluster, 'supplement': selected,
            'scene_token': raw.loc[selected, 'scene_token'], 'log_token': split.loc[selected, 'log_token'],
            'location': raw.loc[selected, 'log_location'], 'standardized_feature_rms_distance': float(np.sqrt(distance[selected])),
            'priority_rank': int(run.loc[selected, 'priority_rank']), 'risk': float(run.loc[selected, 'risk']),
            'description': scenes[raw.loc[selected, 'scene_token']]['description'], 'status': 'keyframes_exist_not_yet_decoded'}
        pairs.append(pair)
        print(f'{target} -> {selected}, C{cluster}, rank {pair["priority_rank"]}, risk {pair["risk"]:.3f}', flush=True)
    sources = [file_record(p) for p in [raw_path, run_path, split_path, sem_path, Path(__file__), ROOT / 'logs/evaluation_media_audit_20260926.py']]
    sources += [file_record(meta / n) for n in ['scene.json', 'sample.json', 'sample_data.json', 'sensor.json', 'calibrated_sensor.json']]
    report = {'created_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
              'stage': 'development_media_available_supplement_selection', 'inputs': sources,
              'command': [sys.executable, *sys.argv], 'eligible_keyframes_exist_count': len(eligible),
              'existing_gif_scene_exclusion_count': len({p.name[:10] for p in (ROOT / 'exports').rglob('scene-*.gif')}),
              'selection_rule': 'Same anchor cluster; exclude existing GIF scenes and original targets; prefer fresh logs; nearest standardized 52-feature RMS distance to missing target, tie by name.',
              'supplements': pairs,
              'limits': ['Availability-based purposive development sampling, not random sampling or evaluation substitution.',
                         'Supplement cannot validate the missing original case; original questions remain pending.',
                         'Keyframes checked for existence/nonempty only; decode and sweeps checked during export.']}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'Available development scenes: {len(eligible)}; report {output}', flush=True)


if __name__ == '__main__':
    main()
