import os
import unittest

# Must be set before NumPy/sklearn load MKL in the current Windows environment.
os.environ.setdefault("MKL_THREADING_LAYER", "SEQUENTIAL")

import numpy as np
import pandas as pd
from sklearn.datasets import make_blobs


class KMeansSemanticBaselineTest(unittest.TestCase):
    def setUp(self):
        from Kmeans.scripts import kmeans_semantic_baseline

        self.baseline = kmeans_semantic_baseline

    def test_select_candidate_rejects_unstable_and_tiny_clusters(self):
        metrics = pd.DataFrame([
            {
                "variant": "direct",
                "k": 2,
                "silhouette": 0.31,
                "stability_ari": 0.92,
                "min_cluster_size": 12,
                "max_cluster_fraction": 0.76,
            },
            {
                "variant": "pca_90",
                "k": 3,
                "silhouette": 0.42,
                "stability_ari": 0.62,
                "min_cluster_size": 8,
                "max_cluster_fraction": 0.54,
            },
            {
                "variant": "pca_95",
                "k": 4,
                "silhouette": 0.36,
                "stability_ari": 0.95,
                "min_cluster_size": 2,
                "max_cluster_fraction": 0.50,
            },
        ])

        selection = self.baseline.select_candidate(metrics, n_samples=50)

        self.assertEqual(selection.status, "reliable")
        self.assertEqual(selection.metrics["variant"], "direct")
        self.assertEqual(selection.metrics["k"], 2)

    def test_select_candidate_marks_weak_separation_unreliable(self):
        metrics = pd.DataFrame([
            {
                "variant": "direct",
                "k": 2,
                "silhouette": 0.12,
                "stability_ari": 0.95,
                "min_cluster_size": 20,
                "max_cluster_fraction": 0.60,
            },
            {
                "variant": "pca_90",
                "k": 3,
                "silhouette": 0.18,
                "stability_ari": 0.90,
                "min_cluster_size": 10,
                "max_cluster_fraction": 0.60,
            },
        ])

        selection = self.baseline.select_candidate(metrics, n_samples=50)

        self.assertEqual(selection.status, "unreliable")
        self.assertEqual(selection.metrics["variant"], "pca_90")

    def test_evaluate_kmeans_reports_stable_separated_blobs(self):
        matrix, _ = make_blobs(
            n_samples=60,
            centers=[(-5, -5), (5, 5)],
            cluster_std=0.45,
            random_state=42,
        )

        result = self.baseline.evaluate_kmeans(
            matrix,
            k=2,
            seeds=(42, 7, 21),
        )

        self.assertGreater(result["silhouette"], 0.8)
        self.assertGreater(result["stability_ari"], 0.95)
        self.assertGreaterEqual(result["min_cluster_size"], 25)
        self.assertLessEqual(result["max_cluster_fraction"], 0.6)

    def test_build_representations_keeps_direct_and_reduces_pca(self):
        rng = np.random.default_rng(42)
        base = rng.normal(size=(80, 4))
        matrix = np.column_stack([base, base[:, 0] + base[:, 1]])

        representations = self.baseline.build_representations(
            matrix,
            variance_levels=(0.8, 0.9),
        )

        self.assertEqual(representations["direct"].matrix.shape, matrix.shape)
        self.assertLess(representations["pca_80"].matrix.shape[1], matrix.shape[1])
        self.assertLessEqual(
            representations["pca_80"].matrix.shape[1],
            representations["pca_90"].matrix.shape[1],
        )

    def test_select_supported_features_removes_singletons_and_constants(self):
        features = pd.DataFrame({
            "supported": [1.0, 0.5, 0.2, 0.0, 0.0],
            "singleton": [1.0, 0.0, 0.0, 0.0, 0.0],
            "all_zero": [0.0, 0.0, 0.0, 0.0, 0.0],
            "constant": [1.0, 1.0, 1.0, 1.0, 1.0],
        })

        selected, audit = self.baseline.select_supported_features(
            features,
            minimum_support=3,
        )

        self.assertEqual(list(selected.columns), ["supported"])
        self.assertEqual(audit["supported"], 3)
        self.assertEqual(audit["singleton"], 1)


if __name__ == "__main__":
    unittest.main()
