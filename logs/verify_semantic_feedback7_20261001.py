"""Read-only regression checks; writes only a new, dated comparison report."""

import hashlib
import json
import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from HDBSCAN.scripts.corner_scoring import calculate_grouped_risk
from HDBSCAN.scripts.feature_selection import CLUSTERING_FEATURES
from HDBSCAN.scripts.frozen_model import require_feature_provenance

TABLES = ROOT / 'HDBSCAN/tables'
SNAPSHOT = ROOT / 'logs/source_snapshot_20261001_pre_turning_crossing'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', choices=['v4'], default='v4', help='Current-source final regression only')
    parser.add_argument('--check-only', action='store_true', help='Recheck without writing or overwriting a report')
    args = parser.parse_args()
    old_path = TABLES / 'scene_features_semantic_feedback7_20261001.csv'
    new_path = TABLES / f'scene_features_semantic_feedback7_20261001_{args.version}.csv'
    full_path = TABLES / 'scene_features_development_audit700_20260927.csv'
    old, new, full = [pd.read_csv(p, float_precision='round_trip').set_index('scene_name', drop=False)
                      for p in (old_path, new_path, full_path)]
    assert old.shape == new.shape == (7, 129)
    pd.testing.assert_frame_equal(old, full.loc[old.index], check_dtype=False, rtol=0, atol=0)
    require_feature_provenance(new_path, new.reset_index(drop=True))
    # Historical sources are verified against their own snapshot, never relabeled.
    for path in (old_path, full_path):
        manifest = read_json(Path(str(path) + '.manifest.json'))
        assert digest(path) == manifest['output']['sha256']
        for record in (manifest['script'], manifest['feature_schema'],
                       manifest['extra']['feature_rules'], manifest['extra']['extraction_audit_code']):
            name = Path(record['path']).name
            assert digest(SNAPSHOT / 'HDBSCAN/scripts' / name) == record['sha256']
        assert digest(SNAPSHOT / 'HDBSCAN/tables/evaluation_split_20260924.csv') == manifest['partition']['sha256']
    try:
        require_feature_provenance(full_path, full.reset_index(drop=True))
    except ValueError as error:
        assert 'version/provenance' in str(error)
    else:
        raise AssertionError('Historical full table was accepted as current')
    quality = read_json(Path(str(new_path) + '.quality.json'))
    assert quality['nonfinite_cell_count'] == 9
    assert set(quality['nonfinite_by_column']) == {'merge_observed_min_distance', 'vru_observed_min_distance'}
    assert all(r['kind'] == 'positive_inf' for r in quality['nonfinite_cells'])
    assert quality['query_exception_count'] == 0
    assert len(CLUSTERING_FEATURES) == 52
    pd.testing.assert_frame_equal(old[CLUSTERING_FEATURES], new[CLUSTERING_FEATURES], rtol=0, atol=0)
    changes = []
    for scene in old.index:
        for column in old.columns:
            if old.loc[scene, column] != new.loc[scene, column]:
                changes.append({'scene_name': scene, 'column': column,
                                'before': old.loc[scene, column], 'after': new.loc[scene, column]})
    assert {r['scene_name'] for r in changes} == {'scene-0151'}
    assert {r['column'] for r in changes} == {'crossing_vehicle_conflict_ratio',
                                             'crossing_conflict_pre_stop_ratio', 'crossing_conflict_max_duration'}
    before, after = calculate_grouped_risk(old), calculate_grouped_risk(new)
    pd.testing.assert_frame_equal(before.drop('scene-0151'), after.drop('scene-0151'), rtol=0, atol=0)
    assert after.loc['scene-0151', 'interaction_risk'] == 0
    assert abs(after.loc['scene-0151', 'risk'] - (before.loc['scene-0151', 'risk'] - .3 * before.loc['scene-0151', 'interaction_risk'])) < 1e-15
    trajectories = read_json(TABLES / f'semantic_feedback7_trajectory_20261001_{args.version}.json')
    rejected = []
    for scene in trajectories:
        for record in scene['crossing_projection_audit']:
            if record['rejected_turning_projection']:
                rejected.append({'scene_name': scene['scene_name'], **record})
    assert len(rejected) == 2
    assert {r['scene_name'] for r in rejected} == {'scene-0151'}
    assert {r['instance_token'] for r in rejected} == {'31a8227b9a194e099a25cf1b0deac81b'}
    report = {'scope': 'seven development scenes only; no clustering fit or evaluation',
              'baseline_sha256': digest(old_path), 'new_sha256': digest(new_path),
              'snapshot_verified': True, 'current_provenance_passed': True,
              'historical_current_provenance_rejected': True,
              'shape': list(new.shape), 'clustering_fields_identical': 52,
              'caught_exceptions': 0, 'positive_inf_diagnostic_cells': 9,
              'changed_cells': changes, 'rejected_candidates': rejected,
              'risk_before': before.reset_index().to_dict(orient='records'),
              'risk_after': after.reset_index().to_dict(orient='records')}
    output = TABLES / f'semantic_feedback7_comparison_20261001_{args.version}.json'
    if args.check_only:
        assert read_json(output) == report, 'Saved comparison differs from fresh verification'
    else:
        with output.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
