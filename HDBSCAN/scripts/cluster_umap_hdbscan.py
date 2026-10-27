"""Fit UMAP/HDBSCAN only on validated development features."""

import argparse
import os
from pathlib import Path

from experiment_partition import (
    load_development_features, assert_new_outputs, provenance_path,
    preflight, write_run_manifest, validate_cluster_columns, file_record,
)

ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = ROOT / 'tables'
PICTURES_DIR = ROOT / 'pictures'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    input_path = TABLES_DIR / os.getenv('SCENE_CLUSTER_FEATURE_INPUT', 'scene_features_development.csv')
    output = TABLES_DIR / os.getenv('SCENE_CLUSTER_CLUSTER_OUTPUT', 'scene_features_development_umap_hdbscan.csv')
    figure = PICTURES_DIR / os.getenv('SCENE_CLUSTER_CLUSTER_FIGURE', 'development_umap_hdbscan.png')
    model_dir = output.with_suffix('.model')
    raw, features, partition = load_development_features(input_path)
    from frozen_model import require_feature_provenance, save_model
    require_feature_provenance(input_path, raw)
    assert_new_outputs([output, provenance_path(output), figure, model_dir])
    if args.preflight:
        return preflight('cluster_fit', raw, partition, features)

    # Native clustering libraries are loaded only after the guard.
    import umap
    import hdbscan
    from sklearn.preprocessing import StandardScaler

    # Historical defaults, not parameters validated on the frozen development set.
    umap_params = dict(n_neighbors=15, min_dist=0.0, n_components=10, metric='cosine',
                       random_state=42, n_jobs=1, low_memory=True)
    hdb_params = dict(min_cluster_size=20, min_samples=1, prediction_data=True)
    scaler = StandardScaler()
    reducer = umap.UMAP(**umap_params)
    scaled = scaler.fit_transform(features)
    embedded = reducer.fit_transform(scaled)
    clusterer = hdbscan.HDBSCAN(**hdb_params)
    labels = clusterer.fit_predict(embedded)
    result = raw.copy()
    for index in range(embedded.shape[1]):
        result[f'umap_{index}'] = embedded[:, index]
    result['cluster'] = labels
    result['cluster_probability'] = clusterer.probabilities_
    result['cluster_outlier_score'] = clusterer.outlier_scores_
    validate_cluster_columns(result)
    save_model(model_dir, scaler, reducer, clusterer, raw, result, input_path, partition)
    result.to_csv(output, index=False)
    write_run_manifest(output, 'cluster_fit', input_path, raw, partition, __file__, features,
                       {'umap': umap_params, 'hdbscan': hdb_params,
                        'model_manifest': file_record(model_dir / 'manifest.json'),
                        'scope': 'development fit with frozen estimator export; formal evaluation prediction pending'})
    print(f'Clustering saved: {output}; development scenes={len(raw)}')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError as exc:
        print(f'Matplotlib unavailable; plot skipped: {exc}')
        return
    PICTURES_DIR.mkdir(exist_ok=True)
    plt.figure(figsize=(8, 6))
    plt.scatter(embedded[:, 0], embedded[:, 1], c=labels, cmap='Spectral', s=12)
    plt.title('Development UMAP + HDBSCAN')
    plt.savefig(figure, dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == '__main__':
    main()
