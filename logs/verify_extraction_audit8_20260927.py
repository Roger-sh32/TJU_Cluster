"""Verify the new eight-scene audit against the preserved 700-scene baseline."""

import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'HDBSCAN/scripts'))
from experiment_partition import load_development_features, file_record, provenance_path, assert_new_outputs
from frozen_model import require_feature_provenance
from corner_scoring import calculate_grouped_risk


def main():
    tables = ROOT / 'HDBSCAN/tables'
    source = tables / 'scene_features_audit8_20260927.csv'
    baseline = tables / 'scene_features_development_20260926.csv'
    output = tables / 'extraction_audit8_comparison_20260927.json'
    assert_new_outputs([output])
    current, features, partition = load_development_features(source)
    require_feature_provenance(source, current)
    old, _, _ = load_development_features(baseline)
    old_manifest = json.loads(provenance_path(baseline).read_text(encoding='utf-8'))
    assert old_manifest['output']['sha256'] == file_record(baseline)['sha256']
    snapshot = ROOT / 'logs/source_snapshot_20260927_pre_audit/HDBSCAN/scripts'
    assert old_manifest['script']['sha256'] == file_record(snapshot / 'scene_feature_hdbscan.py')['sha256']
    old = old.set_index('scene_name').loc[current.scene_name].reset_index()
    pd.testing.assert_frame_equal(current, old[current.columns], check_exact=True)
    pd.testing.assert_frame_equal(calculate_grouped_risk(current), calculate_grouped_risk(old), check_exact=True)
    quality = json.loads(Path(str(source) + '.quality.json').read_text(encoding='utf-8'))
    report = {'scope': 'targeted development regression; not representative full-batch validation',
              'command': [sys.executable, *sys.argv], 'script': file_record(__file__),
              'current': file_record(source), 'baseline': file_record(baseline),
              'quality': file_record(Path(str(source) + '.quality.json')), 'partition': partition['file'],
              'scene_count': len(current), 'column_count': len(current.columns),
              'scene_names': current.scene_name.tolist(), 'locations': sorted(current.log_location.unique()),
              'all_features_exactly_unchanged': True, 'grouped_risk_exactly_unchanged': True,
              'nonfinite_cell_count': quality['nonfinite_cell_count'],
              'nonfinite_by_column': quality['nonfinite_by_column'],
              'query_exception_count': quality['query_exception_count'],
              'nonfinite_clustering_columns': sorted(set(quality['nonfinite_by_column']) & set(features.columns)),
              'limitations': ['Audit observes aggregates and caught exceptions, not every intermediate.',
                              'Eight targeted scenes cannot clear all 700 development scenes.',
                              'Positive Inf diagnostic distances need context, not automatic error classification.']}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
