"""Verify one changed development case and audit front-keyframe existence only."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from HDBSCAN.scripts.experiment_partition import assert_new_outputs, file_record
from HDBSCAN.scripts.frozen_model import require_feature_provenance
from logs.evaluation_media_audit_20260926 import records


def main():
    tables = ROOT / 'HDBSCAN/tables'
    output = tables / 'crossing_case0552_diagnosis_20261001.json'
    assert_new_outputs([output])
    source = tables / 'scene_features_crossing_case0552_20261001.csv'
    batch = tables / 'scene_features_crossing_regression33_20261001.csv'
    trajectory = tables / 'crossing_case0552_trajectory_20261001.json'
    frame = pd.read_csv(source, float_precision='round_trip')
    require_feature_provenance(source, frame)
    expected = pd.read_csv(batch, float_precision='round_trip')
    require_feature_provenance(batch, expected)
    pd.testing.assert_frame_equal(frame, expected[expected.scene_name.eq('scene-0552')].reset_index(drop=True),
                                  check_dtype=False, rtol=0, atol=0)
    audit = json.loads(trajectory.read_text(encoding='utf-8'))[0]
    assert audit['scene_name'] == 'scene-0552' and audit['scene_token'] == frame.scene_token.iloc[0]
    rejected = []
    for evidence in audit['crossing_projection_audit']:
        if evidence['rejected_turning_projection']:
            i = evidence['index']
            row = next(r for r in audit['vehicle_tracks'][evidence['instance_token']] if r['index'] == i)
            assert row['raw_crossing_conflict'] and not row['crossing_conflict']
            rejected.append({**evidence, 'scene_time_s': audit['times'][i] - audit['times'][0],
                             'ego_speed_mps': audit['ego_speeds'][i],
                             'actor_forward_m': row['forward'], 'actor_lateral_m': row['lateral']})
    assert len(rejected) == 2
    meta = ROOT / 'nuScenes/v1.0-trainval'
    scenes = json.loads((meta / 'scene.json').read_text(encoding='utf-8'))
    scene = next(s for s in scenes if s['name'] == 'scene-0552')
    samples = {r['token']: r for r in json.loads((meta / 'sample.json').read_text(encoding='utf-8'))
               if r['scene_token'] == scene['token']}
    assert len(samples) == scene['nbr_samples']
    sensors = {r['token']: r['channel'] for r in json.loads((meta / 'sensor.json').read_text(encoding='utf-8'))}
    channels = {r['token']: sensors[r['sensor_token']] for r in
                json.loads((meta / 'calibrated_sensor.json').read_text(encoding='utf-8'))}
    keyframes = []
    for row in records(meta / 'sample_data.json'):
        if row['sample_token'] in samples and row['is_key_frame'] and channels[row['calibrated_sensor_token']] == 'CAM_FRONT':
            path = ROOT / 'nuScenes' / row['filename']
            keyframes.append({'sample_token': row['sample_token'], 'timestamp': row['timestamp'],
                              'path': str(path), 'exists_nonempty': path.is_file() and path.stat().st_size > 0})
    assert len(keyframes) == len(samples) == len({r['sample_token'] for r in keyframes})
    keyframes.sort(key=lambda r: r['timestamp'])
    sources = [source, batch, trajectory, Path(str(source) + '.quality.json'), Path(__file__),
               ROOT / 'logs/evaluation_media_audit_20260926.py']
    sources += [meta / name for name in ('scene.json', 'sample.json', 'sample_data.json', 'sensor.json', 'calibrated_sensor.json')]
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'command': [sys.executable, *sys.argv],
              'scope': 'single development trajectory diagnosis and media existence, not semantic acceptance',
              'inputs': [file_record(p) for p in sources], 'scene_name': scene['name'], 'scene_token': scene['token'],
              'description': scene['description'], 'exact_batch_reproduction': True, 'rejected_candidates': rejected,
              'keyframe_count': len(keyframes), 'keyframes_present': sum(r['exists_nonempty'] for r in keyframes),
              'keyframes': keyframes, 'keyframes_decoded': False, 'sweeps_checked': False,
              'semantic_validity_verified': False, 'expert_review_required': True}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: report[k] for k in ('scene_name', 'description', 'rejected_candidates',
                                            'keyframe_count', 'keyframes_present')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
