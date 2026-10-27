"""Read-only full-development audit and exact baseline comparison after extraction."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def compare_frames(old, new):
    if list(old.columns) != list(new.columns):
        raise ValueError('Feature schema mismatch')
    for frame in [old, new]:
        if (frame.empty or not {'scene_name', 'scene_token'}.issubset(frame)
                or not frame.scene_name.is_unique or not frame.scene_token.is_unique
                or frame[['scene_name', 'scene_token']].isna().any().any()):
            raise ValueError('Missing or duplicate scene identity')
    if set(zip(old.scene_name, old.scene_token)) != set(zip(new.scene_name, new.scene_token)):
        raise ValueError('Scene identity mismatch')
    before = old.set_index('scene_name').loc[new.scene_name].reset_index()
    changes = []
    for a, b in zip(before.to_dict('records'), new.to_dict('records')):
        for column in new.columns:
            if a[column] != b[column] and not (pd.isna(a[column]) and pd.isna(b[column])):
                changes.append({'scene_name': b['scene_name'], 'scene_token': b['scene_token'],
                                'column': column, 'old': a[column], 'new': b[column]})
    return {'changed_cell_count': len(changes),
            'changed_scene_count': len({r['scene_name'] for r in changes}),
            'changed_columns': sorted({r['column'] for r in changes}), 'changes': changes}


def review_reasons(quality, changed_count):
    reasons = []
    if changed_count:
        reasons.append('Feature values differ from the prior full-development extraction')
    if quality['query_exception_count']:
        reasons.append('Caught query exceptions require review')
    sentinel_columns = {'merge_observed_min_distance', 'vru_observed_min_distance'}
    for name, counts in quality['nonfinite_by_column'].items():
        if counts['nan'] or counts['negative_inf'] or (counts['positive_inf'] and name not in sentinel_columns):
            reasons.append('Unexpected pre-fill nonfinite values: ' + name)
    return reasons


def main():
    sys.path.insert(0, str(ROOT / 'HDBSCAN/scripts'))
    from experiment_partition import load_development_features, file_record, provenance_path, assert_new_outputs
    from frozen_model import require_feature_provenance
    from corner_scoring import calculate_grouped_risk
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-seconds', type=int, default=0)
    args = parser.parse_args()
    if args.wait_seconds < 0:
        raise ValueError('Negative wait')
    tables = ROOT / 'HDBSCAN/tables'
    source = tables / 'scene_features_development_audit700_20260927.csv'
    baseline = tables / 'scene_features_development_20260926.csv'
    output = tables / 'development_audit700_comparison_20260927.json'
    assert_new_outputs([output])
    deadline = time.monotonic() + args.wait_seconds
    print('Waiting for extraction completion manifest: ' + str(provenance_path(source)), flush=True)
    while not provenance_path(source).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('No extraction completion manifest; no QA result claimed')
        time.sleep(min(15, max(0, deadline - time.monotonic())))
    current, features, partition = load_development_features(source)
    require_feature_provenance(source, current)
    expected = {r['scene_token'] for r in partition['rows'] if r['split'] == 'development'}
    if len(current) != 700 or set(current.scene_token) != expected:
        raise ValueError('Incomplete frozen development batch')
    if not np.isfinite(current.select_dtypes(include='number').to_numpy()).all():
        raise ValueError('Non-finite numeric output')
    old, _, _ = load_development_features(baseline)
    old_record = json.loads(provenance_path(baseline).read_text(encoding='utf-8'))
    snapshot = ROOT / 'logs/source_snapshot_20260927_pre_audit/HDBSCAN/scripts'
    if (old_record['output']['sha256'] != file_record(baseline)['sha256']
            or old_record['partition']['sha256'] != partition['file']['sha256']
            or old_record['script']['sha256'] != file_record(snapshot / 'scene_feature_hdbscan.py')['sha256']):
        raise ValueError('Historical baseline provenance mismatch')
    comparison = compare_frames(old, current)
    ordered_old = old.set_index('scene_name').loc[current.scene_name].reset_index()
    risk_before, risk_after = calculate_grouped_risk(ordered_old), calculate_grouped_risk(current)
    risk_changes = int((risk_before != risk_after).to_numpy().sum())
    quality_path = Path(str(source) + '.quality.json')
    quality = json.loads(quality_path.read_text(encoding='utf-8'))
    reasons = review_reasons(quality, comparison['changed_cell_count'])
    if risk_changes:
        reasons.append('Grouped risk values changed')
    report = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'full-development structural audit; not expert or semantic acceptance',
        'command': [sys.executable, *sys.argv], 'script': file_record(__file__),
        'input': file_record(source), 'baseline': file_record(baseline),
        'extraction_manifest': file_record(provenance_path(source)),
        'quality': file_record(quality_path), 'partition': partition['file'],
        'scene_count': len(current), 'column_count': len(current.columns),
        'clustering_feature_count': len(features.columns),
        'all_development_members_present_once': True, 'all_output_numeric_values_finite': True,
        'map_available_scene_count': int(current.map_available.eq(1).sum()),
        'intersection_flag_positive_count': int(current.intersection_flag.gt(0).sum()),
        'constant_clustering_features': [c for c in features if features[c].nunique() == 1],
        'nonfinite_cell_count': quality['nonfinite_cell_count'],
        'nonfinite_by_column': quality['nonfinite_by_column'],
        'query_exception_count': quality['query_exception_count'],
        'query_exception_counts_by_stage': quality['query_exception_counts_by_stage'],
        'feature_comparison': comparison, 'changed_risk_cell_count': risk_changes,
        'requires_review': bool(reasons), 'review_reasons': reasons,
        'semantic_validity_verified': False, 'fit_started': False,
        'limitations': ['Known positive-Inf diagnostic sentinels are listed, not treated as measured 30m.',
                       'No guarantee for intermediate values or explicit finite fallbacks.',
                       'No automatic parameter selection, model fit, evaluation or expert labels.']}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: report[k] for k in ['scene_count', 'nonfinite_cell_count', 'query_exception_count',
                                           'changed_risk_cell_count', 'requires_review', 'review_reasons']}, indent=2), flush=True)
    print(output, flush=True)


if __name__ == '__main__':
    main()
