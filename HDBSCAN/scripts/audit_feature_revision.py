"""Compare feature revisions without inventing cluster labels or corner scores."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from corner_scoring import calculate_grouped_risk
from feature_selection import select_clustering_features


COMPARISON_FIELDS = [
    'ego_evasive_lane_change_flag', 'stationary_lead_obstacle_ratio',
    'min_ttc', 'min_ttc_target_category', 'side_entry_candidate_ratio',
    'adjacent_lane_intrusion_ratio', 'crossing_vehicle_conflict_ratio',
    'crossing_route_conflict_ratio', 'stop_sign_stop_candidate',
    'interaction_risk', 'decision_demand', 'risk',
]


def file_record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def with_risk(frame):
    result = frame.copy()
    for column, values in calculate_grouped_risk(frame).items():
        result[column] = values
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, action='append', default=[],
                        help='Repeat in priority order; the last matching scene wins.')
    parser.add_argument('--output-prefix', type=Path, required=True)
    args = parser.parse_args()
    current = pd.read_csv(args.features)
    for column in ['scene_name', 'scene_token']:
        if current[column].isna().any() or not current[column].is_unique:
            raise ValueError(f'Missing or duplicate {column}')
    if not np.isfinite(current.select_dtypes(include='number').to_numpy()).all():
        raise ValueError('Non-finite numeric features')
    selected = select_clustering_features(current)
    current = with_risk(current)
    previous = {}
    for path in args.baseline:
        frame = with_risk(pd.read_csv(path))
        for _, row in frame.iterrows():
            previous[row.scene_name] = (row, str(path))
    comparisons = []
    for _, row in current.iterrows():
        old, source = previous.get(row.scene_name, (pd.Series(dtype=object), 'unavailable'))
        for field in COMPARISON_FIELDS:
            comparisons.append({'scene_name': row.scene_name, 'feature': field,
                                'before': old.get(field), 'after': row.get(field),
                                'baseline_source': source})
    prefix = args.output_prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    scored = Path(str(prefix) + '_risk.csv')
    compared = Path(str(prefix) + '_comparison.csv')
    manifest = Path(str(prefix) + '_manifest.json')
    inputs = [args.features, *args.baseline]
    if any(output.resolve() == source.resolve()
           for output in [scored, compared, manifest] for source in inputs):
        raise ValueError('Audit outputs must not overwrite inputs')
    current.to_csv(scored, index=False)
    pd.DataFrame(comparisons).to_csv(compared, index=False)
    scripts = Path(__file__).resolve().parent
    manifest.write_text(json.dumps({
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.executable,
        'python_version': sys.version,
        'packages': {name: version(name) for name in ['numpy', 'pandas', 'nuscenes-devkit', 'shapely']},
        'inputs': [file_record(path) for path in inputs],
        'scripts_at_audit_time': [file_record(scripts / name) for name in [
            'audit_feature_revision.py', 'scene_feature_hdbscan.py',
            'scene_feature_rules.py', 'corner_scoring.py', 'feature_selection.py']],
        'scene_count': len(current),
        'scene_names': current.scene_name.tolist(),
        'semantic_feature_count': len(selected.columns),
        'semantic_features': selected.columns.tolist(),
        'all_zero_semantic_features': selected.columns[(selected == 0).all()].tolist(),
        'missing_baseline_scenes': sorted(set(current.scene_name) - set(previous)),
        'outputs': [file_record(path) for path in [scored, compared]],
        'note': 'Risk-only audit; no clustering or corner-score rerun. Baseline risks '
                'are recalculated with the current scorer and historical available fields.',
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(current[['scene_name', 'ego_evasive_lane_change_flag', 'min_ttc',
                   'side_entry_candidate_ratio', 'stop_sign_stop_candidate',
                   'interaction_risk', 'decision_demand', 'risk']].to_string(index=False))
    print(f'{len(current)} scenes; {len(selected.columns)} semantic features; {manifest}')


if __name__ == '__main__':
    main()
