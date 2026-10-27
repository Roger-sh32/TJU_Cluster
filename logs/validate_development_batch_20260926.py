"""Read-only structural QA after the already-running 700-scene extraction."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'HDBSCAN/scripts'))
from experiment_partition import load_development_features, provenance_path, file_record
from frozen_model import require_feature_provenance, validate_risk_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-seconds', type=int, default=0)
    args = parser.parse_args()
    source = ROOT / 'HDBSCAN/tables/scene_features_development_20260926.csv'
    output = ROOT / 'HDBSCAN/tables/development_quality_20260926.json'
    if output.exists():
        raise FileExistsError('Quality report already exists; do not overwrite')
    deadline = time.monotonic() + args.wait_seconds
    while not provenance_path(source).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('Extraction completion manifest has not appeared; no result claimed')
        time.sleep(min(15, max(0, deadline - time.monotonic())))
    raw, features, partition = load_development_features(source)
    require_feature_provenance(source, raw)
    validate_risk_inputs(raw)
    expected = {r['scene_token'] for r in partition['rows'] if r['split'] == 'development'}
    if len(raw) != 700 or set(raw.scene_token) != expected:
        raise ValueError('Incomplete or mismatched 700-scene development batch')
    numeric = raw.select_dtypes(include='number')
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError('Non-finite numeric output')
    columns = {}
    for name in features:
        column = features[name]
        columns[name] = {'min': float(column.min()), 'max': float(column.max()),
                         'mean': float(column.mean()), 'unique': int(column.nunique()),
                         'zero_count': int((column == 0).sum())}
    report = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'development structural quality only, not semantic validation',
        'python': sys.executable, 'command': [sys.executable, *sys.argv],
        'script': file_record(__file__), 'input': file_record(source),
        'extraction_manifest': file_record(provenance_path(source)),
        'partition': partition['file'], 'scene_count': len(raw),
        'column_count': len(raw.columns), 'clustering_feature_count': len(features.columns),
        'all_development_members_present_once': True,
        'all_output_numeric_values_finite': True,
        'map_available_scene_count': int((raw.map_available == 1).sum()),
        'intersection_flag_positive_count': int((raw.intersection_flag == 1).sum()),
        'constant_clustering_features': [name for name, data in columns.items() if data['unique'] == 1],
        'all_zero_clustering_features': [name for name, data in columns.items() if data['zero_count'] == len(raw)],
        'features': columns,
        'limitations': [
            'Extractor currently replaces Inf with 30 and NaN with zero before writing.',
            'Finite output does not prove that intermediate calculations were all valid.',
            'No source-level nonfinite replacement audit exists for this run.',
            'No semantic or expert validation, no evaluation prediction, no model fit in this QA.',
            'Constant fields are reported, not automatically dropped or retuned.'
        ]
    }
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    print(json.dumps({k: report[k] for k in ['scene_count', 'column_count', 'clustering_feature_count',
                                            'map_available_scene_count', 'intersection_flag_positive_count',
                                            'constant_clustering_features']}, indent=2), flush=True)
    print(output, flush=True)


if __name__ == '__main__':
    main()
