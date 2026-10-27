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
VERIFICATION_PROTOCOL = TABLES / 'crossing_regression33_verification_protocol_20261001.json'
ORIGINAL_RECIPE = ROOT / 'logs/crossing_regression33_20261001_pre_review.py'
COMPARISON_HELPER = ROOT / 'logs/check_development_audit700_20260927.py'
REPORT = TABLES / 'crossing_regression33_comparison_20261001.json'
RISK = TABLES / 'crossing_regression33_risk_20261001.csv'
SEVEN = TABLES / 'scene_features_semantic_feedback7_20261001_v4.csv'
REVIEW11 = TABLES / 'scene_features_review11_20260925.csv'
SNAPSHOT = ROOT / 'logs/source_snapshot_20261001_pre_turning_crossing/HDBSCAN/scripts'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def revision_review_flags(changed_fields, before, after):
    allowed = {'crossing_vehicle_conflict_ratio', 'crossing_conflict_pre_stop_ratio',
               'crossing_conflict_post_stop_ratio', 'crossing_conflict_max_duration',
               'crossing_route_conflict_ratio', 'crossing_route_conflict_max_duration',
               'left_turn_cross_traffic_interaction_ratio', 'obstacle_induced_route_deviation_flag',
               'route_deviation_decision_demand'}
    unexpected = sorted(set(changed_fields) - allowed)
    increases = after.loc[after.risk > before.risk + 1e-15, 'scene_name'].tolist()
    return {'unexpected_columns': unexpected, 'risk_increased_scenes': increases,
            'requires_review': bool(unexpected or increases)}


def freeze_check():
    assert_new_outputs([VERIFICATION_PROTOCOL, REPORT, RISK])
    protocol = read_json(PROTOCOL)
    if protocol['script']['sha256'] != file_record(ORIGINAL_RECIPE)['sha256']:
        raise ValueError('Frozen original recipe mismatch')
    if protocol['source_hashes'] != source_hashes():
        raise ValueError('Sources changed since selection')
    amendment = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'review corrections before reading extraction values; original sampling protocol unchanged',
        'protocol': file_record(PROTOCOL), 'original_recipe': file_record(ORIGINAL_RECIPE),
        'checker': file_record(__file__), 'comparison_helper': file_record(COMPARISON_HELPER),
        'reasons': ['Risk can increase when removed left-turn gating restores merge risk; record instead of rejecting.',
                    'Route deviation flag and decision demand are known downstream dependencies.',
                    'Bind original and amended analysis recipes and the imported comparison helper.'],
        'new_outcome_values_inspected': False, 'sampling_or_production_sources_changed': False,
    }
    with VERIFICATION_PROTOCOL.open('x', encoding='utf-8') as stream:
        json.dump(amendment, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(amendment, ensure_ascii=False, indent=2))


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
    if protocol['script']['sha256'] != file_record(ORIGINAL_RECIPE)['sha256']:
        raise ValueError('Frozen original recipe mismatch')
    verification = read_json(VERIFICATION_PROTOCOL)
    for record in (verification['protocol'], verification['original_recipe'], verification['checker'],
                   verification['comparison_helper']):
        if file_record(Path(record['path']))['sha256'] != record['sha256']:
            raise ValueError('Frozen verification source mismatch')
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
    # Flags preserve evidence; a dependency-driven increase is not a failed calculation.
    flags = revision_review_flags(changed_fields, before.assign(scene_name=current.scene_name),
                                  after.assign(scene_name=current.scene_name))
    flags['newly_changed_scenes'] = sorted({r['scene_name'] for r in comparison['changes']} - {'scene-0151'})
    flags['requires_review'] |= bool(flags['newly_changed_scenes'])
    report = {
        'scope': protocol['scope'], 'protocol': file_record(PROTOCOL),
        'verification_protocol': file_record(VERIFICATION_PROTOCOL), 'script': file_record(__file__),
        'input': file_record(OUTPUT), 'manifest': file_record(Path(str(OUTPUT) + '.manifest.json')),
        'quality': file_record(Path(str(OUTPUT) + '.quality.json')), 'baseline': protocol['baseline'],
        'source_hashes': protocol['source_hashes'], 'scene_count': len(current), 'column_count': len(current.columns),
        'location_counts': protocol['location_counts'], 'log_count': protocol['log_count'],
        'query_exception_count': quality['query_exception_count'], 'nonfinite_by_column': quality['nonfinite_by_column'],
        'seven_controls_exactly_reproduced': True, 'feature_comparison': comparison,
        'changed_clustering_cell_count': int(changed.to_numpy().sum()),
        'changed_clustering_fields': changed.columns[changed.any()].tolist(),
        'risk_changed_scenes': risk.loc[risk.risk_delta.abs() > 1e-15].to_dict('records'),
        'risk_increases': len(flags['risk_increased_scenes']), 'review_flags': flags,
        'semantic_validity_verified': False, 'model_or_ranking_replaced': False,
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
    parser.add_argument('stage', choices=['prepare', 'freeze-check', 'check'])
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.stage == 'prepare':
        if args.check_only:
            parser.error('--check-only applies to check stage')
        prepare()
    elif args.stage == 'freeze-check':
        if args.check_only:
            parser.error('--check-only applies to check stage')
        freeze_check()
    else:
        check(args.check_only)
