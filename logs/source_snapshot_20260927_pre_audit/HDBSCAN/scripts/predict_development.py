"""Diagnose frozen predictions on development scenes excluded from the model fit."""

import argparse
from pathlib import Path

import pandas as pd

from experiment_partition import (assert_new_outputs, provenance_path, preflight,
                                  load_partition, write_run_manifest, file_record)
from frozen_model import (inspect_model, load_model, validate_prediction_input,
                          predict_development, require_feature_provenance)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--trusted-local-model', action='store_true',
                        help='Acknowledge this is your own trusted pickle, not a downloaded model.')
    args = parser.parse_args()
    assert_new_outputs([args.output, provenance_path(args.output)])
    manifest = inspect_model(args.model)
    frame = pd.read_csv(args.input)
    provenance = require_feature_provenance(args.input, frame)
    if provenance['stage'] != manifest['feature_kind']:
        raise ValueError('Cannot mix synthetic test data with extracted scene features')
    features = validate_prediction_input(frame, manifest)
    partition = load_partition()
    if args.preflight:
        return preflight('development_frozen_prediction', frame, partition, features)
    bundle = load_model(args.model, trusted=args.trusted_local_model)
    result = predict_development(bundle, frame)
    result.to_csv(args.output, index=False)
    write_run_manifest(args.output, 'development_frozen_prediction', args.input, frame,
                       partition, __file__, features,
                       {'model_manifest': file_record(args.model / 'manifest.json'),
                        'model_training_scene_count': len(manifest['scene_tokens']),
                        'scope': 'development diagnostics, not held-out evaluation',
                        'ranking_column': 'corner_score'})
    print(f'Development frozen predictions saved: {args.output}')


if __name__ == '__main__':
    main()
