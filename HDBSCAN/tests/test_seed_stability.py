import importlib
from pathlib import Path
import unittest

import pandas as pd


class SeedStabilityTest(unittest.TestCase):
    def api(self):
        self.assertTrue((Path(__file__).parents[1] / 'scripts/seed_stability.py').exists(),
                        'Stability implementation missing')
        return importlib.import_module('HDBSCAN.scripts.seed_stability')

    def frame(self):
        return pd.DataFrame({'scene_name': ['b', 'a', 'c', 'd'],
                             'cluster': [0, 0, 1, -1], 'corner_score': [1., 1., .5, 0.]})

    def test_top_k_ties_are_deterministic(self):
        self.assertEqual(self.api().top_names(self.frame(), 2), ['a', 'b'])

    def test_labels_can_be_permuted_and_rows_reordered(self):
        a = self.frame()
        b = a.assign(cluster=[5, 5, 9, -1]).iloc[::-1]
        result = self.api().compare_runs(a, b, 2)
        self.assertEqual(result['ari_all'], 1.)
        self.assertEqual(result['top_k_overlap_fraction'], 1.)
        self.assertEqual(result['top_k_jaccard'], 1.)

    def test_identity_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            self.api().compare_runs(self.frame(), self.frame().iloc[:3], 2)

    def test_all_noise_has_no_nonnoise_ari(self):
        result = self.api().compare_runs(self.frame().assign(cluster=-1), self.frame(), 2)
        self.assertIsNone(result['ari_joint_nonnoise'])
