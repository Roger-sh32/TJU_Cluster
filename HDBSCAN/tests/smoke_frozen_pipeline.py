"""Manual native-library smoke test. Synthetic values are NOT experiment results."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'HDBSCAN/scripts'))
from experiment_partition import load_partition, CLUSTERING_FEATURES, file_record, write_run_manifest
from corner_scoring import FROZEN_RISK_INPUTS
from frozen_model import load_model, predict_development


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    partition = load_partition()
    dev = [r for r in partition['rows'] if r['split'] == 'development']
    rng = np.random.RandomState(27)
    centers = rng.normal(0, 5, (3, len(CLUSTERING_FEATURES)))
    def synthetic(rows):
        values = np.array([centers[i % 3] + rng.normal(0, .1, len(CLUSTERING_FEATURES))
                           for i in range(len(rows))])
        frame = pd.DataFrame(values, columns=CLUSTERING_FEATURES)
        for column in FROZEN_RISK_INPUTS:
            if column not in frame:
                frame[column] = 0.0
        frame['min_ttc'] = 30.0
        frame['scene_name'] = [r['scene_name'] for r in rows]
        frame['scene_token'] = [r['scene_token'] for r in rows]
        return frame
    train, query = synthetic(dev[:105]), synthetic(dev[105:108])
    input_path, query_path = args.output_dir / 'SYNTHETIC_train.csv', args.output_dir / 'SYNTHETIC_query.csv'
    train.to_csv(input_path, index=False)
    query.to_csv(query_path, index=False)
    for path, frame in [(input_path, train), (query_path, query)]:
        write_run_manifest(path, 'synthetic_features', path, frame, partition,
                           ROOT / 'HDBSCAN/scripts/scene_feature_hdbscan.py',
                           extra={'feature_rules': file_record(ROOT / 'HDBSCAN/scripts/scene_feature_rules.py'),
                                  'generator': file_record(__file__), 'synthetic': True})
    output = args.output_dir / 'SYNTHETIC_clusters.csv'
    env = {k: v for k, v in os.environ.items() if not k.startswith('SCENE_CLUSTER_')}
    env.update(SCENE_CLUSTER_FEATURE_INPUT=str(input_path.resolve()),
               SCENE_CLUSTER_CLUSTER_OUTPUT=str(output.resolve()),
               SCENE_CLUSTER_CLUSTER_FIGURE=str((args.output_dir / 'SYNTHETIC_plot.png').resolve()))
    print('Fitting synthetic development data through the actual entry point', flush=True)
    subprocess.run([sys.executable, str(ROOT / 'HDBSCAN/scripts/cluster_umap_hdbscan.py')],
                   env=env, cwd=ROOT, check=True, timeout=180)
    print('Loading frozen estimators and predicting unseen development identities', flush=True)
    bundle = load_model(output.with_suffix('.model'), trusted=True)
    predictions = predict_development(bundle, query)
    singles = pd.concat([predict_development(bundle, query.iloc[[i]]) for i in range(len(query))])
    pd.testing.assert_frame_equal(predictions, singles)
    reloaded = predict_development(load_model(output.with_suffix('.model'), trusted=True), query)
    pd.testing.assert_frame_equal(predictions, reloaded)
    command = [sys.executable, str(ROOT / 'HDBSCAN/scripts/predict_development.py'),
               '--model', str(output.with_suffix('.model').resolve()),
               '--input', str(query_path.resolve()),
               '--output', str((args.output_dir / 'SYNTHETIC_predictions.csv').resolve())]
    subprocess.run(command + ['--preflight'], cwd=ROOT, check=True, timeout=60)
    subprocess.run(command + ['--trusted-local-model'], cwd=ROOT, check=True, timeout=180)
    result = {'scope': 'synthetic pipeline verification only; not scene research results',
              'training_count': len(train), 'prediction_count': len(query),
              'partition': partition['file'], 'script': file_record(__file__),
              'model_manifest': file_record(output.with_suffix('.model') / 'manifest.json'),
              'batch_invariance': True, 'reload_invariance': True,
              'prediction_entry_passed': True,
              'python': sys.executable}
    with (args.output_dir / 'smoke_result.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
