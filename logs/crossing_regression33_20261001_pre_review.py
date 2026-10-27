"""Dated metadata-only regression recipe; does not modify experiment sources."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from HDBSCAN.scripts.corner_scoring import calculate_grouped_risk
from HDBSCAN.scripts.experiment_partition import assert_development_frame, assert_new_outputs, file_record, load_partition
from HDBSCAN.scripts.feature_selection import CLUSTERING_FEATURES
from HDBSCAN.scripts.frozen_model import require_feature_provenance, source_hashes
from logs.check_development_audit700_20260927 import compare_frames, review_reasons

TABLES = ROOT / 'HDBSCAN/tables'
BASELINE = TABLES / 'scene_features_development_audit700_20260927.csv'
OUTPUT = TABLES / 'scene_features_crossing_regression33_20261001.csv'
PROTOCOL = TABLES / 'crossing_regression33_protocol_20261001.json'
REPORT = TABLES / 'crossing_regression33_comparison_20261001.json'
RISK = TABLES / 'crossing_regression33_risk_20261001.csv'
SEVEN = TABLES / 'scene_features_semantic_feedback7_20261001_v4.csv'
REVIEW11 = TABLES / 'scene_features_review11_20260925.csv'
SNAPSHOT = ROOT / 'logs/source_snapshot_20261001_pre_turning_crossing/HDBSCAN/scripts'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def baseline(partition):
    frame = pd.read_csv(BASELINE, float_precision='round_trip')
    assert_development_frame(frame, partition)
    expected = {r['scene_name'] for r in partition['rows'] if r['split'] == 'development'}
    if set(frame.scene_name) != expected:
        raise ValueError('Historical development corpus incomplete')
    manifest = read_json(Path(str(BASELINE) + '.manifest.json'))
    if manifest['output']['sha256'] != file_record(BASELINE)['sha256']:
        raise ValueError('Historical baseline hash mismatch')
    for record in (manifest['script'], manifest['feature_schema'], manifest['extra']['feature_rules'],
                   manifest['extra']['extraction_audit_code']):
        if record['sha256'] != file_record(SNAPSHOT / Path(record['path']).name)['sha256']:
            raise ValueError('Historical baseline snapshot mismatch')
    if manifest['partition']['sha256'] != partition['file']['sha256']:
        raise ValueError('Historical baseline partition mismatch')
    return frame


def prepare():
    assert_new_outputs([PROTOCOL, OUTPUT, Path(str(OUTPUT) + '.manifest.json'),
                        Path(str(OUTPUT) + '.quality.json'), REPORT, RISK])
    partition = load_partition()
    old = baseline(partition)
    seven = pd.read_csv(SEVEN, float_precision='round_trip')
    require_feature_provenance(SEVEN, seven)
    review = pd.read_csv(REVIEW11)
    assert_development_frame(review, partition)
    controls = set(seven.scene_name) | set(review.scene_name)
    if len(controls) != 21:
        raise ValueError('Unexpected fixed control membership')
    pool = old.merge(pd.DataFrame(partition['rows'])[['scene_name', 'log_token']], on='scene_name', validate='one_to_one')
    selected = {name: ['previous7' if name in set(seven.scene_name) else 'review11_control'] for name in controls}
    used_logs = set(pool.loc[pool.scene_name.isin(controls), 'log_token'])
    rng = np.random.default_rng(20261001)
    pool['selection_random_key'] = rng.random(len(pool))
    predicates = {
        'turning_predicted_crossing': (pool.crossing_vehicle_conflict_ratio > 0) & (pool.ego_signed_heading_change.abs() > .35),
        'response_protected_crossing': (pool.crossing_vehicle_conflict_ratio > 0) &
            ((pool.ego_stop_from_motion_flag > 0) | (pool.ego_stopped_at_scene_start > 0) | (pool.ego_hard_brake_ratio > 0)),
        'no_predicted_crossing': pool.crossing_vehicle_conflict_ratio == 0,
    }
    for location in sorted(pool.log_location.unique()):
        for reason, mask in predicates.items():
            eligible = pool.loc[mask & pool.log_location.eq(location) & ~pool.scene_name.isin(selected)].copy()
            if eligible.empty:
                raise ValueError('Empty selection stratum: ' + location + '/' + reason)
            eligible['already_used_log'] = eligible.log_token.isin(used_logs)
            row = eligible.sort_values(['already_used_log', 'selection_random_key', 'scene_name']).iloc[0]
            selected[row.scene_name] = [location + '/' + reason]
            used_logs.add(row.log_token)
    if len(selected) != 33:
        raise ValueError('Unexpected bounded batch size')
    names = old.loc[old.scene_name.isin(selected), 'scene_name'].tolist()
    protocol = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'stage': 'fixed-before-extraction',
        'scope': 'development-only targeted regression, not a random effectiveness sample',
        'command': [sys.executable, *sys.argv], 'script': file_record(__file__),
        'baseline': file_record(BASELINE), 'seven_controls': file_record(SEVEN), 'review11_controls': file_record(REVIEW11),
        'partition': partition['file'], 'source_hashes': source_hashes(),
        'seed': 20261001, 'fixed_controls': sorted(controls), 'scene_names': names,
        'selection_reasons': selected, 'scene_count': len(names),
        'location_counts': pool.loc[pool.scene_name.isin(names), 'log_location'].value_counts().to_dict(),
        'log_count': int(pool.loc[pool.scene_name.isin(names), 'log_token'].nunique()),
        'selection_policy': '21 fixed controls + three strata per location, prefer fresh logs; never replace after extraction',
        'feature_output': str(OUTPUT), 'trajectory_export': False, 'fit_requested': False,
        'limitations': ['Historical prediction and response strata are candidates, not expert labels.',
                       'Selection is enriched for regression and cannot estimate corpus accuracy or false-positive rate.'],
    }
    with PROTOCOL.open('x', encoding='utf-8') as stream:
        json.dump(protocol, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(protocol, ensure_ascii=False, indent=2))


def check(check_only):
    protocol = read_json(PROTOCOL)
    if protocol['source_hashes'] != source_hashes():
        raise ValueError('Sources changed since selection; no regression accepted')
    for record in (protocol['baseline'], protocol['seven_controls'], protocol['review11_controls'], protocol['partition']):
        if file_record(Path(record['path']))['sha256'] != record['sha256']:
            raise ValueError('Selection input changed')
    current = pd.read_csv(OUTPUT, float_precision='round_trip')
    require_feature_provenance(OUTPUT, current)
    if current.scene_name.tolist() != protocol['scene_names'] or current.shape != (33, 129):
        raise ValueError('Regression identity/schema mismatch')
    if not np.isfinite(current.select_dtypes(include='number').to_numpy()).all():
        raise ValueError('Nonfinite output')
    old = baseline(load_partition()).set_index('scene_name').loc[current.scene_name].reset_index()
    comparison = compare_frames(old, current)
    before, after = calculate_grouped_risk(old), calculate_grouped_risk(current)
    quality = read_json(Path(str(OUTPUT) + '.quality.json'))
    anomalies = review_reasons(quality, 0)
    if anomalies:
        raise ValueError('Quality blockers: ' + str(anomalies))
    seven = pd.read_csv(SEVEN, float_precision='round_trip')
    pd.testing.assert_frame_equal(current.set_index('scene_name').loc[seven.scene_name].reset_index(),
                                  seven, check_dtype=False, rtol=0, atol=0)
    risk = current[['scene_name', 'scene_token', 'log_location']].copy()
    for column in before:
        risk[column + '_before'] = before[column]
        risk[column + '_after'] = after[column]
    risk['risk_delta'] = after.risk - before.risk
    changed = (old[CLUSTERING_FEATURES] != current[CLUSTERING_FEATURES])
    changed_fields = {r['column'] for r in comparison['changes']}
    # No new numerical rules: report all deltas, including any unexpected ones.
    allowed = {'crossing_vehicle_conflict_ratio', 'crossing_conflict_pre_stop_ratio',
               'crossing_conflict_post_stop_ratio', 'crossing_conflict_max_duration',
               'crossing_route_conflict_ratio', 'crossing_route_conflict_max_duration',
               'left_turn_cross_traffic_interaction_ratio'}
    unexpected = sorted(changed_fields - allowed)
    if unexpected or (after.risk > before.risk + 1e-15).any():
        raise ValueError('Unexpected regression changes: ' + str(unexpected))
    report = {
        'scope': protocol['scope'], 'protocol': file_record(PROTOCOL), 'script': file_record(__file__),
        'input': file_record(OUTPUT), 'manifest': file_record(Path(str(OUTPUT) + '.manifest.json')),
        'quality': file_record(Path(str(OUTPUT) + '.quality.json')), 'baseline': protocol['baseline'],
        'source_hashes': protocol['source_hashes'], 'scene_count': len(current), 'column_count': len(current.columns),
        'location_counts': protocol['location_counts'], 'log_count': protocol['log_count'],
        'query_exception_count': quality['query_exception_count'], 'nonfinite_by_column': quality['nonfinite_by_column'],
        'seven_controls_exactly_reproduced': True, 'feature_comparison': comparison,
        'changed_clustering_cell_count': int(changed.to_numpy().sum()),
        'changed_clustering_fields': changed.columns[changed.any()].tolist(),
        'risk_changed_scenes': risk.loc[risk.risk_delta.abs() > 1e-15].to_dict('records'),
        'risk_increases': 0, 'semantic_validity_verified': False, 'model_or_ranking_replaced': False,
    }
    if check_only:
        assert read_json(REPORT) == report, 'Saved report differs from fresh verification'
        pd.testing.assert_frame_equal(pd.read_csv(RISK, float_precision='round_trip'), risk, check_dtype=False, rtol=0, atol=0)
    else:
        assert_new_outputs([REPORT, RISK])
        with REPORT.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        risk.to_csv(RISK, index=False, mode='x')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'check'])
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.stage == 'prepare':
        if args.check_only:
            parser.error('--check-only applies to check stage')
        prepare()
    else:
        check(args.check_only)
