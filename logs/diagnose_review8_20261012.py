"""Reproduce eight frozen development rows and diagnose targets without changing rules."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import runpy
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs.build_semantic_review_pack_20261001 import record
from HDBSCAN.scripts.experiment_partition import assert_development_frame, assert_new_outputs, load_partition
from HDBSCAN.scripts.frozen_model import require_feature_provenance, source_hashes
from HDBSCAN.scripts.scene_feature_rules import local_heading_change_around_index, is_turning_projection_artifact
from HDBSCAN.scripts.audit_interaction_events import scene_events

TABLES = ROOT / 'HDBSCAN/tables'
NAMES = ('scene-0002', 'scene-0093', 'scene-0102', 'scene-0453',
         'scene-0552', 'scene-0669', 'scene-0815', 'scene-0816')
FEATURES = TABLES / 'scene_features_target_diagnosis8_20261012.csv'
TRAJECTORY = TABLES / 'target_diagnosis8_trajectory_20261012.json'
PROTOCOL = TABLES / 'target_diagnosis8_protocol_20261012.json'
REPORT = TABLES / 'target_diagnosis8_20261012.json'
STATUS = ROOT / 'logs/review8_target_diagnosis_20261012_status.json'
EXTRACTOR = ROOT / 'HDBSCAN/scripts/scene_feature_hdbscan.py'
BASELINE = TABLES / 'scene_features_development_candidate700_20261001.csv'
ENVIRONMENT = {'SCENE_CLUSTER_SCENE_NAMES': ','.join(NAMES), 'SCENE_CLUSTER_MAX_SCENES': '8',
    'SCENE_CLUSTER_START_INDEX': '0', 'SCENE_CLUSTER_FEATURE_OUTPUT': FEATURES.name,
    'SCENE_CLUSTER_AUDIT_OUTPUT': TRAJECTORY.name, 'OMP_NUM_THREADS': '1',
    'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMBA_NUM_THREADS': '1',
    'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8'}


def projection_blockers(evidence):
    reasons = []
    if not evidence['future_complete']:
        reasons.append('incomplete_future')
    if evidence['yielding_response']:
        reasons.append('low_speed_or_braking_response')
    values = [evidence[k] for k in ('heading_change', 'minimum_future_route_distance', 'actor_bounding_diameter')]
    if not np.isfinite(values).all():
        reasons.append('nonfinite_geometry')
    else:
        if evidence['heading_change'] <= .35:
            reasons.append('turn_below_threshold')
        if evidence['actor_bounding_diameter'] < 0:
            reasons.append('invalid_actor_size')
        if evidence['minimum_future_route_distance'] <= 2.5 + evidence['actor_bounding_diameter'] / 2:
            reasons.append('within_footprint_route_margin')
    if evidence['rejected_turning_projection'] != (not reasons):
        raise ValueError('Diagnostic rejection reasons contradict the frozen rule')
    return reasons


def exact_rows(frame, reference):
    if not frame.scene_name.is_unique or not frame.scene_token.is_unique:
        raise ValueError('Duplicate replay identities')
    expected = reference.set_index('scene_name').loc[frame.scene_name].reset_index()
    pd.testing.assert_frame_equal(frame.reset_index(drop=True), expected[frame.columns],
                                  check_dtype=False, rtol=0, atol=0)
    if list(frame.columns) != list(reference.columns):
        raise ValueError('Replay schema changed')


def write_json(path, value, exclusive=True):
    with path.open('x' if exclusive else 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False,
                  default=lambda v: v.item() if isinstance(v, np.generic) else str(v))


def verify_records(items):
    for item in items:
        if record(item['path'])['sha256'] != item['sha256']:
            raise ValueError('Bound source changed: ' + item['path'])


def preflight():
    outputs = [FEATURES, Path(str(FEATURES) + '.manifest.json'), Path(str(FEATURES) + '.quality.json'),
               TRAJECTORY, PROTOCOL, REPORT, STATUS]
    assert_new_outputs(outputs)
    comparison = json.loads((TABLES / 'development_candidate700_comparison_20261001.json').read_text())
    if comparison['source_hashes'] != source_hashes():
        raise ValueError('Current sources differ from v4')
    partition = load_partition()
    reference = pd.read_csv(BASELINE, float_precision='round_trip')
    require_feature_provenance(BASELINE, reference)
    selected = reference[reference.scene_name.isin(NAMES)].copy()
    assert_development_frame(selected, partition)
    if set(selected.scene_name) != set(NAMES) or len(selected) != 8:
        raise ValueError('Eight unique development cases required')
    print('PREFLIGHT PASS: eight v4 development cases; no output collisions.', flush=True)
    return reference, partition


def vru_candidates(ns, audit, scene, expected_ratio):
    nusc = ns['nusc']
    sample = nusc.get('sample', scene['first_sample_token'])
    samples = []
    while True:
        samples.append(sample)
        if not sample['next']:
            break
        sample = nusc.get('sample', sample['next'])
    if len(samples) != len(audit['times']):
        raise ValueError('VRU timeline length mismatch')
    map_name = nusc.get('log', scene['log_token'])['location']
    nusc_map = ns['map_cache'][map_name][0]
    found, positive_frames = [], set()
    for i, sample in enumerate(samples):
        ego = audit['ego_positions'][i]
        yaw = audit['ego_yaws'][i]
        for token in sample['anns']:
            ann = nusc.get('sample_annotation', token)
            if not ann['category_name'].startswith('human'):
                continue
            position = ann['translation'][:2]
            velocity = ns['compute_ann_velocity_xy'](nusc, ann)
            forward, lateral = ns['ego_frame_delta'](position, *ego, yaw)
            vf, vl = ns['ego_frame_vector'](velocity, yaw)
            candidate = (-5 <= forward <= 30 and abs(lateral) <= 8 and ns['is_vru_path_conflict'](
                forward, lateral, vf, vl, audit['ego_speeds'][i]))
            if not candidate:
                continue
            positive_frames.add(i)
            layer = nusc_map.layers_on_point(*position, ['walkway', 'road_segment', 'lane', 'lane_connector'])
            geometry = ns['mapped_actor_lane_geometry'](nusc_map, *ego, position, {})
            actor_positions, actor_times = [], []
            current = ann
            origin = sample['timestamp'] / 1e6
            while True:
                t = nusc.get('sample', current['sample_token'])['timestamp'] / 1e6
                if t - origin > 8:
                    break
                actor_positions.append(current['translation'][:2])
                actor_times.append(t - samples[0]['timestamp'] / 1e6)
                if not current['next']:
                    break
                current = nusc.get('sample_annotation', current['next'])
            approach = ns['synchronized_path_closest_approach'](
                audit['ego_positions'], audit['times'], actor_positions, actor_times, audit['times'][i], horizon=8.)
            found.append({'index': i, 'time_s': audit['times'][i], 'annotation_token': token,
                'instance_token': ann['instance_token'], 'category': ann['category_name'],
                'forward_m': float(forward), 'lateral_m': float(lateral),
                'lateral_speed_mps': float(vl), 'ego_speed_mps': audit['ego_speeds'][i],
                'on_walkway': bool(layer.get('walkway')),
                'map_layers': layer, 'ego_lane_center_distance_m': float(geometry[0]) if geometry else None,
                'observed_closest_distance_m': float(approach.distance) if math.isfinite(approach.distance) else None,
                'future_actor_span_s': actor_times[-1] - audit['times'][i],
                'future_actor_count': len(actor_times),
                'physical_barrier_verified_by_map': False})
    if len(positive_frames) / len(samples) != expected_ratio:
        raise ValueError('Independent VRU candidates do not reproduce feature ratio')
    return found


def diagnose(ns, frame):
    nusc = ns['nusc']
    audits = json.loads(TRAJECTORY.read_text(encoding='utf-8'))
    rows = frame.set_index('scene_name')
    results = []
    if [a['scene_name'] for a in audits] != frame.scene_name.tolist():
        raise ValueError('Trajectory identity/order mismatch')
    for audit in audits:
        name = audit['scene_name']
        row = rows.loc[name]
        if audit['scene_token'] != row.scene_token:
            raise ValueError('Trajectory token mismatch')
        scene = nusc.get('scene', row.scene_token)
        crossing = []
        for evidence in audit['crossing_projection_audit']:
            i = evidence['index']
            track = audit['vehicle_tracks'][evidence['instance_token']]
            target = next(r for r in track if r['index'] == i)
            future = [r for r in track if 0 <= audit['times'][r['index']] - audit['times'][i] <= 6.]
            crossing.append({**evidence, 'time_s': audit['times'][i],
                'retained': target['crossing_conflict'], 'raw_candidate': target['raw_crossing_conflict'],
                'rejection_blockers': projection_blockers(evidence),
                'ego_speed_mps': audit['ego_speeds'][i], 'forward_m': target['forward'],
                'lateral_m': target['lateral'], 'actor_heading_delta': target['heading_delta'],
                'ego_available_future_s': min(6., audit['times'][-1] - audit['times'][i]),
                'actor_observed_future_s': audit['times'][future[-1]['index']] - audit['times'][i]})
        ttc = None
        if row.min_ttc_target_instance_token != 'none':
            ann = nusc.get('sample_annotation', row.min_ttc_target_annotation_token)
            token = ann['sample_token']
            start = nusc.get('sample', scene['first_sample_token'])['timestamp']
            t = (nusc.get('sample', token)['timestamp'] - start) / 1e6
            i = int(np.argmin(np.abs(np.asarray(audit['times']) - t)))
            if abs(audit['times'][i] - row.min_ttc_scene_time) > .001:
                raise ValueError('TTC annotation/timeline mismatch')
            turn = local_heading_change_around_index(audit['ego_yaws'], audit['times'], i)
            target = next(r for r in audit['vehicle_tracks'][ann['instance_token']] if r['index'] == i)
            future = [r for r in audit['vehicle_tracks'][ann['instance_token']]
                      if 0 <= audit['times'][r['index']] - audit['times'][i] <= 6.]
            route = [p for j, p in enumerate(audit['ego_positions'])
                     if 0 <= audit['times'][j] - audit['times'][i] <= 6.]
            route_distance = min(ns['distance_to_polyline'](r['position'], route) for r in future)
            ttc = {'time_s': row.min_ttc_scene_time, 'ttc_s': row.min_ttc,
                'instance_token': ann['instance_token'], 'category': ann['category_name'],
                'target_speed_mps': row.min_ttc_target_speed, 'heading_delta_rad': row.min_ttc_target_heading_delta,
                'local_heading_change_rad': turn, 'current_filter_rejects': is_turning_projection_artifact(
                    row.min_ttc_target_speed, row.min_ttc_target_heading_delta, turn),
                'ego_lane_center_distance_m': next((r['lane_distance'] for r in audit['lane_targets']
                    if r['index'] == i and r['instance'] == ann['instance_token']), None),
                'future_actor_to_ego_route_min_distance_m': float(route_distance),
                'future_complete_not_asserted': True, 'target_forward_m': target['forward'],
                'target_lateral_m': target['lateral']}
        static = [{'index': i, 'time_s': audit['times'][i],
                   'instance_token': audit['stationary_lead_instances'][i]}
                  for i, flag in enumerate(audit['static_obstacle_flags']) if flag]
        vru = vru_candidates(ns, audit, scene, row.vru_path_conflict_ratio)
        results.append({'scene_name': name, 'scene_token': row.scene_token,
            'crossing_candidates': crossing, 'minimum_ttc': ttc, 'vru_candidates': vru,
            'static_obstacle_frames': static, 'temporal_events': scene_events(audit),
            'human_feedback_not_automatic_label': True})
        print(f'DIAGNOSED {name}: {len(crossing)} crossing, {len(vru)} VRU, {len(static)} static frames', flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    reference, partition = preflight()
    if args.preflight:
        return
    inputs = [BASELINE, Path(str(BASELINE) + '.manifest.json'), Path(str(BASELINE) + '.quality.json'),
        TABLES / 'development_candidate700_comparison_20261001.json', Path(partition['file']['path']),
        ROOT / 'logs/development_review_feedback_20261012.md', Path(__file__),
        ROOT / 'logs/test_review8_target_diagnosis_20261012.py', ROOT / 'logs/build_semantic_review_pack_20261001.py',
        ROOT / 'logs/evaluation_media_audit_20260926.py', ROOT / 'HDBSCAN/scripts/audit_interaction_events.py']
    inputs += [ROOT / 'HDBSCAN/scripts' / name for name in source_hashes()]
    meta = ROOT / 'nuScenes/v1.0-trainval'
    inputs += list(meta.glob('*.json')) + list((ROOT / 'nuScenes/maps/expansion').glob('*.json'))
    bound = [record(p) for p in inputs]
    command = [sys.executable, *sys.argv]
    write_json(PROTOCOL, {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Eight development targets; exact v4 reproduction and sidecar diagnostics only',
        'command': command, 'environment': ENVIRONMENT, 'inputs': bound, 'names': NAMES,
        'source_hashes': source_hashes(), 'runtime': {'python': platform.python_version(),
        'executable': record(sys.executable), 'packages': {p: importlib.metadata.version(p)
            for p in ['numpy', 'pandas', 'nuscenes-devkit', 'shapely', 'pyquaternion']}}})
    write_json(STATUS, {'phase': 'extracting', 'pid': os.getpid(), 'protocol': record(PROTOCOL)})
    try:
        sys.path.insert(0, str(EXTRACTOR.parent))
        old_env = {k: os.environ.get(k) for k in ENVIRONMENT}
        old_args = sys.argv[:]
        try:
            os.environ.update(ENVIRONMENT)
            sys.argv = [str(EXTRACTOR)]
            ns = runpy.run_path(str(EXTRACTOR), run_name='__main__')
        finally:
            sys.argv = old_args
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        frame = pd.read_csv(FEATURES, float_precision='round_trip')
        assert_development_frame(frame, partition)
        require_feature_provenance(FEATURES, frame)
        if set(frame.scene_name) != set(NAMES) or len(frame) != 8:
            raise ValueError('Replay scope changed')
        exact_rows(frame, reference)
        quality = json.loads(Path(str(FEATURES) + '.quality.json').read_text())
        bad_nonfinite = [r for r in quality['nonfinite_cells'] if r['kind'] != 'positive_inf'
                        or r['column'] not in {'merge_observed_min_distance', 'vru_observed_min_distance'}]
        if quality['query_exception_count'] or bad_nonfinite:
            raise ValueError('Replay quality checks failed')
        write_json(STATUS, {'phase': 'diagnosing', 'pid': os.getpid(), 'protocol': record(PROTOCOL)}, False)
        findings = diagnose(ns, frame)
        verify_records(bound)
        write_json(REPORT, {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'command': command,
            'protocol': record(PROTOCOL), 'features': record(FEATURES), 'trajectory': record(TRAJECTORY),
            'quality': record(Path(str(FEATURES) + '.quality.json')), 'scenes': findings,
            'exact_candidate_rows_reproduced': True, 'query_exception_count': quality['query_exception_count'],
            'nonfinite_diagnostic_cell_count': quality['nonfinite_cell_count'],
            'evaluation_used': False, 'production_rules_changed': False, 'semantic_acceptance': False})
        write_json(STATUS, {'phase': 'completed_diagnostics_requires_review', 'pid': os.getpid(),
            'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'report': record(REPORT)}, False)
        print('COMPLETED: eight exact frozen rows and target diagnostics; no rule changes.', flush=True)
    except Exception as exc:
        write_json(STATUS, {'phase': 'failed', 'pid': os.getpid(), 'error': f'{type(exc).__name__}: {exc}'}, False)
        raise


if __name__ == '__main__':
    main()
