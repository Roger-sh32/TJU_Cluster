"""Run a reproducible KMeans baseline on the HDBSCAN semantic feature set."""

import argparse
import json
import os
import sys
from itertools import combinations
from pathlib import Path
from typing import NamedTuple

# The current Windows conda environment mixes MKL and multiple OpenMP runtimes.
# Keeping MKL sequential prevents small SVD/KMeans jobs from hanging indefinitely.
os.environ.setdefault("MKL_THREADING_LAYER", "SEQUENTIAL")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

SCRIPT_DIR = Path(__file__).resolve().parent
KMEANS_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = KMEANS_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from HDBSCAN.scripts.experiment_partition import (
    load_development_features, assert_new_outputs, provenance_path,
    preflight as report_preflight, write_run_manifest,
)


TABLES_DIR = KMEANS_ROOT / "tables"
PICTURES_DIR = KMEANS_ROOT / "pictures"
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "HDBSCAN"
    / "tables"
    / "scene_features_development.csv"
)


class Representation(NamedTuple):
    matrix: np.ndarray
    components: int
    explained_variance: float


class CandidateSelection(NamedTuple):
    status: str
    metrics: dict


def select_supported_features(features, minimum_support=3):
    """Exclude constant and singleton-like axes from Euclidean clustering."""
    support = features.ne(0).sum(axis=0)
    variable = features.nunique(dropna=False) > 1
    keep = (support >= int(minimum_support)) & variable
    if not keep.any():
        raise ValueError("No features meet the minimum support requirement.")
    audit = {column: int(count) for column, count in support.items()}
    return features.loc[:, keep].copy(), audit


def build_representations(
    matrix,
    variance_levels=(0.8, 0.9, 0.95),
    prefix="",
):
    """Return direct standardized features and predefined PCA variants."""
    matrix = np.asarray(matrix, dtype=float)
    representations = {
        f"{prefix}direct": Representation(matrix, matrix.shape[1], 1.0),
    }
    for variance in variance_levels:
        pca = PCA(n_components=float(variance), svd_solver="full")
        transformed = pca.fit_transform(matrix)
        name = f"{prefix}pca_{int(round(variance * 100))}"
        representations[name] = Representation(
            transformed,
            transformed.shape[1],
            float(np.sum(pca.explained_variance_ratio_)),
        )
    return representations


def evaluate_kmeans(matrix, k, seeds=(42, 7, 21, 84, 168), n_init=20):
    """Evaluate one K with separation, balance, and cross-seed stability."""
    matrix = np.asarray(matrix, dtype=float)
    labels_by_seed = []
    inertias = []
    for seed in seeds:
        model = KMeans(
            n_clusters=int(k),
            random_state=int(seed),
            n_init=int(n_init),
        )
        labels_by_seed.append(model.fit_predict(matrix))
        inertias.append(float(model.inertia_))

    reference_labels = labels_by_seed[0]
    pairwise_stability = [
        adjusted_rand_score(left, right)
        for left, right in combinations(labels_by_seed, 2)
    ]
    counts = np.bincount(reference_labels, minlength=int(k))
    return {
        "k": int(k),
        "silhouette": float(silhouette_score(matrix, reference_labels)),
        "davies_bouldin": float(davies_bouldin_score(matrix, reference_labels)),
        "calinski_harabasz": float(
            calinski_harabasz_score(matrix, reference_labels)
        ),
        "stability_ari": float(np.mean(pairwise_stability)),
        "inertia_mean": float(np.mean(inertias)),
        "inertia_std": float(np.std(inertias)),
        "min_cluster_size": int(np.min(counts)),
        "max_cluster_size": int(np.max(counts)),
        "max_cluster_fraction": float(np.max(counts) / len(reference_labels)),
    }


def reliability_mask(
    metrics,
    n_samples,
    minimum_silhouette=0.20,
    minimum_stability=0.80,
    minimum_cluster_size=None,
    maximum_cluster_fraction=0.80,
):
    """Return the predefined reliability gate for every candidate row."""
    if minimum_cluster_size is None:
        minimum_cluster_size = max(3, int(np.ceil(0.05 * n_samples)))
    return (
        (metrics["silhouette"] >= minimum_silhouette)
        & (metrics["stability_ari"] >= minimum_stability)
        & (metrics["min_cluster_size"] >= minimum_cluster_size)
        & (metrics["max_cluster_fraction"] <= maximum_cluster_fraction)
    )


def select_candidate(metrics, n_samples):
    """Select the best reliable candidate or label the best diagnostic as weak."""
    if metrics.empty:
        raise ValueError("No KMeans candidates were evaluated.")
    reliable = metrics[reliability_mask(metrics, n_samples)]
    pool = reliable if not reliable.empty else metrics
    selected = pool.sort_values(
        ["silhouette", "stability_ari"],
        ascending=[False, False],
    ).iloc[0]
    return CandidateSelection(
        status="reliable" if not reliable.empty else "unreliable",
        metrics=selected.to_dict(),
    )


def _parse_float_list(value):
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def _parse_int_list(value):
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _json_safe(mapping):
    result = {}
    for key, value in mapping.items():
        if isinstance(value, (np.integer,)):
            result[key] = int(value)
        elif isinstance(value, (np.floating,)):
            result[key] = float(value)
        else:
            result[key] = value
    return result


def _save_debug_plot(matrix, labels, output_path, title):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        return None, str(exc)

    coordinates = PCA(n_components=2).fit_transform(matrix)
    plt.figure(figsize=(9, 7))
    scatter = plt.scatter(
        coordinates[:, 0],
        coordinates[:, 1],
        c=labels,
        cmap="tab10",
        s=42,
        alpha=0.85,
        edgecolors="white",
        linewidths=0.4,
    )
    plt.title(title)
    plt.xlabel("PCA 1")
    plt.ylabel("PCA 2")
    plt.grid(alpha=0.2)
    plt.colorbar(scatter, label="Cluster")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()
    return str(output_path), None


def run_experiment(
    input_path=DEFAULT_INPUT,
    output_prefix="kmeans_development",
    k_min=2,
    k_max=10,
    seeds=(42, 7, 21, 84, 168),
    variance_levels=(0.8, 0.9, 0.95),
    minimum_feature_support=3,
    preflight_only=False,
):
    """Run all predefined KMeans candidates and persist traceable outputs."""
    input_path = Path(input_path).resolve()
    raw, features, partition = load_development_features(input_path)
    planned_clusters = TABLES_DIR / f'{output_prefix}_clusters.csv'
    assert_new_outputs([TABLES_DIR / f'{output_prefix}_{suffix}' for suffix in
                        ['metrics.csv', 'clusters.csv', 'cluster_sizes.csv', 'profiles.csv', 'summary.json']]
                       + [provenance_path(planned_clusters), PICTURES_DIR / f'{output_prefix}_pca.png'])
    if preflight_only:
        return report_preflight('kmeans_fit', raw, partition, features)

    supported_features, support_audit = select_supported_features(
        features,
        minimum_support=minimum_feature_support,
    )
    dropped_features = [
        column for column in features.columns if column not in supported_features.columns
    ]

    raw_scaled = StandardScaler().fit_transform(features)
    supported_scaled = StandardScaler().fit_transform(supported_features)
    representations = {}
    representations.update(
        build_representations(raw_scaled, variance_levels, prefix="raw_")
    )
    representations.update(
        build_representations(
            supported_scaled,
            variance_levels,
            prefix="supported_",
        )
    )

    rows = []
    maximum_k = min(int(k_max), len(raw) - 1)
    for variant, representation in representations.items():
        for k in range(int(k_min), maximum_k + 1):
            metrics = evaluate_kmeans(representation.matrix, k, seeds=seeds)
            metrics.update({
                "variant": variant,
                "components": representation.components,
                "explained_variance": representation.explained_variance,
                "used_feature_count": (
                    features.shape[1]
                    if variant.startswith("raw_")
                    else supported_features.shape[1]
                ),
            })
            rows.append(metrics)

    metrics_df = pd.DataFrame(rows)
    metrics_df["reliable"] = reliability_mask(metrics_df, len(raw))
    selection = select_candidate(metrics_df, len(raw))
    selected_variant = str(selection.metrics["variant"])
    selected_k = int(selection.metrics["k"])
    selected_matrix = representations[selected_variant].matrix
    final_model = KMeans(
        n_clusters=selected_k,
        random_state=42,
        n_init=20,
    )
    labels = final_model.fit_predict(selected_matrix)

    TABLES_DIR.mkdir(exist_ok=True)
    PICTURES_DIR.mkdir(exist_ok=True)
    metrics_path = TABLES_DIR / f"{output_prefix}_metrics.csv"
    clusters_path = TABLES_DIR / f"{output_prefix}_clusters.csv"
    sizes_path = TABLES_DIR / f"{output_prefix}_cluster_sizes.csv"
    profiles_path = TABLES_DIR / f"{output_prefix}_profiles.csv"
    summary_path = TABLES_DIR / f"{output_prefix}_summary.json"
    figure_path = PICTURES_DIR / f"{output_prefix}_pca.png"

    metrics_df.sort_values(["variant", "k"]).to_csv(metrics_path, index=False)
    clustered = raw.copy()
    clustered["kmeans_cluster"] = labels
    clustered["kmeans_representation"] = selected_variant
    clustered["kmeans_selection_status"] = selection.status
    clustered.to_csv(clusters_path, index=False)

    sizes = (
        pd.Series(labels, name="cluster")
        .value_counts()
        .sort_index()
        .rename_axis("cluster")
        .reset_index(name="scene_count")
    )
    sizes["scene_fraction"] = sizes["scene_count"] / len(raw)
    sizes.to_csv(sizes_path, index=False)

    standardized = pd.DataFrame(raw_scaled, columns=features.columns)
    standardized["cluster"] = labels
    profiles = standardized.groupby("cluster").mean().reset_index()
    size_by_cluster = sizes.set_index("cluster")["scene_count"]
    profiles.insert(1, "scene_count", profiles["cluster"].map(size_by_cluster))
    profiles.to_csv(profiles_path, index=False)

    saved_figure, plot_error = _save_debug_plot(
        selected_matrix,
        labels,
        figure_path,
        f"KMeans semantic baseline: {selected_variant}, K={selected_k}",
    )

    raw_best = metrics_df[metrics_df["variant"].str.startswith("raw_")].sort_values(
        ["silhouette", "stability_ari"], ascending=False
    ).iloc[0]
    supported_best = metrics_df[
        metrics_df["variant"].str.startswith("supported_")
    ].sort_values(["silhouette", "stability_ari"], ascending=False).iloc[0]
    summary = {
        "input": str(input_path),
        "samples": int(len(raw)),
        "feature_count": int(features.shape[1]),
        "feature_names": list(features.columns),
        "minimum_feature_support": int(minimum_feature_support),
        "supported_feature_count": int(supported_features.shape[1]),
        "supported_feature_names": list(supported_features.columns),
        "dropped_features": dropped_features,
        "feature_support": support_audit,
        "k_range": [int(k_min), int(maximum_k)],
        "seeds": list(seeds),
        "selection_status": selection.status,
        "selected": _json_safe(selection.metrics),
        "raw_best_by_silhouette": _json_safe(raw_best.to_dict()),
        "supported_best_by_silhouette": _json_safe(supported_best.to_dict()),
        "raw_reliable_candidate_count": int(
            metrics_df[metrics_df["variant"].str.startswith("raw_")][
                "reliable"
            ].sum()
        ),
        "supported_reliable_candidate_count": int(
            metrics_df[metrics_df["variant"].str.startswith("supported_")][
                "reliable"
            ].sum()
        ),
        "selected_vs_raw_best": {
            "silhouette_delta": float(
                selection.metrics["silhouette"] - raw_best["silhouette"]
            ),
            "stability_ari_delta": float(
                selection.metrics["stability_ari"] - raw_best["stability_ari"]
            ),
        },
        "outputs": {
            "metrics": str(metrics_path),
            "clusters": str(clusters_path),
            "cluster_sizes": str(sizes_path),
            "profiles": str(profiles_path),
            "figure": saved_figure,
        },
        "plot_error": plot_error,
        "caution": (
            "Development-only fitting; this run is not an independent evaluation result."
        ),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_run_manifest(clusters_path, 'kmeans_fit', input_path, raw, partition, __file__, features,
                       {'summary': str(summary_path), 'seeds': list(seeds),
                        'minimum_feature_support': minimum_feature_support})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run KMeans on the current HDBSCAN semantic feature set."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-prefix", default="kmeans_development")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--k-min", type=int, default=2)
    parser.add_argument("--k-max", type=int, default=10)
    parser.add_argument("--seeds", default="42,7,21,84,168")
    parser.add_argument("--pca-variances", default="0.8,0.9,0.95")
    parser.add_argument("--minimum-feature-support", type=int, default=3)
    return parser


def main():
    args = build_parser().parse_args()
    run_experiment(
        input_path=args.input,
        output_prefix=args.output_prefix,
        k_min=args.k_min,
        k_max=args.k_max,
        seeds=_parse_int_list(args.seeds),
        variance_levels=_parse_float_list(args.pca_variances),
        minimum_feature_support=args.minimum_feature_support,
        preflight_only=args.preflight,
    )


if __name__ == "__main__":
    main()
