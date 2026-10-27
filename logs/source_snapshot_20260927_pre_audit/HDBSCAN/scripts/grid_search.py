"""Development-only UMAP/HDBSCAN parameter search."""

import argparse
from itertools import product
import os
from pathlib import Path

import numpy as np
import pandas as pd

from experiment_partition import (
    load_development_features, assert_new_outputs, provenance_path,
    preflight, write_run_manifest,
)

TABLES_DIR = Path(__file__).resolve().parents[1] / 'tables'


def evaluate(labels, embedding, validity_fn):
    count = len(set(labels) - {-1})
    result = {'clusters': count, 'noise_ratio': float(np.mean(labels == -1)),
              'dbcv': np.nan, 'metric_status': 'not_applicable', 'metric_error': ''}
    if count < 2:
        return result
    try:
        score = float(validity_fn(np.asarray(embedding, dtype=np.float64), labels))
        if not np.isfinite(score):
            raise ValueError('DBCV is non-finite')
        result.update(dbcv=score, metric_status='ok')
    except Exception as exc:
        result.update(metric_status='failed', metric_error=str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    input_path = TABLES_DIR / os.getenv('SCENE_CLUSTER_FEATURE_INPUT', 'scene_features_development.csv')
    output = TABLES_DIR / os.getenv('SCENE_CLUSTER_GRID_OUTPUT', 'development_umap_hdbscan_grid_search.csv')
    raw, features, partition = load_development_features(input_path)
    assert_new_outputs([output, provenance_path(output)])
    if args.preflight:
        return preflight('parameter_search', raw, partition, features)

    import umap
    import hdbscan
    from hdbscan import validity
    from sklearn.preprocessing import StandardScaler

    scaled = StandardScaler().fit_transform(features)
    # Retained historical search space; results are not a final parameter choice.
    umap_options = list(product([5, 10, 15, 30], [0.0, 0.05, 0.1, 0.2],
                                ['euclidean', 'manhattan', 'cosine'], [5, 10]))
    hdb_options = list(product([5, 10, 20, 30], [1, 5, 10]))
    print(f'{len(umap_options)} UMAP fits; {len(umap_options)*len(hdb_options)} clustering candidates')
    rows = []
    for neighbors, min_dist, metric, dimensions in umap_options:
        config = dict(n_neighbors=neighbors, min_dist=min_dist, metric=metric, n_components=dimensions)
        try:
            embedded = umap.UMAP(**config, random_state=42, n_jobs=1,
                                 low_memory=True).fit_transform(scaled)
            embedding_error = None
        except Exception as exc:
            embedded, embedding_error = None, str(exc)
        for size, samples in hdb_options:
            row = dict(config, min_cluster_size=size, min_samples=samples,
                       clusters=np.nan, noise_ratio=np.nan, dbcv=np.nan,
                       metric_status='not_run', metric_error='', run_status='failed', error='')
            try:
                if embedding_error is not None:
                    raise RuntimeError('UMAP failed: ' + embedding_error)
                model = hdbscan.HDBSCAN(min_cluster_size=size, min_samples=samples,
                                       prediction_data=True)
                labels = model.fit_predict(embedded)
                row.update(evaluate(labels, embedded, validity.validity_index))
                row['run_status'] = 'ok'
            except Exception as exc:
                row['error'] = str(exc)
            rows.append(row)
        print(f'Completed {len(rows)} candidates', flush=True)
    result = pd.DataFrame(rows)
    result.to_csv(output, index=False)
    write_run_manifest(output, 'parameter_search', input_path, raw, partition, __file__, features,
                       {'seed': 42, 'umap_configurations': umap_options,
                        'hdbscan_configurations': hdb_options,
                        'note': 'DBCV is not cluster persistence or cross-seed stability.'})
    print(f'Search diagnostics saved: {output}')


if __name__ == '__main__':
    main()
