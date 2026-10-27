import importlib
from pathlib import Path
import unittest

import pandas as pd


class Audit700CheckTest(unittest.TestCase):
    def api(self):
        self.assertTrue((Path(__file__).parents[2] / 'logs/check_development_audit700_20260927.py').exists(),
                        'Full-batch checker missing')
        return importlib.import_module('logs.check_development_audit700_20260927')

    def frame(self):
        return pd.DataFrame({'scene_name': ['a', 'b'], 'scene_token': ['x', 'y'], 'value': [0., 1.]})

    def test_row_order_does_not_create_a_feature_change(self):
        result = self.api().compare_frames(self.frame(), self.frame().iloc[::-1])
        self.assertEqual(result['changed_cell_count'], 0)

    def test_real_changes_are_recorded_with_identity(self):
        result = self.api().compare_frames(self.frame(), self.frame().assign(value=[0., 2.]))
        self.assertEqual(result['changed_cell_count'], 1)
        self.assertEqual(result['changes'][0], {'scene_name': 'b', 'scene_token': 'y',
                                              'column': 'value', 'old': 1., 'new': 2.})

    def test_identity_and_schema_mismatch_fail(self):
        for frame in [self.frame().iloc[:1], self.frame().assign(scene_token=['y', 'x']),
                      self.frame().drop(columns='value'), pd.concat([self.frame(), self.frame()])]:
            with self.assertRaises(ValueError):
                self.api().compare_frames(self.frame(), frame)

    def test_known_distance_sentinel_does_not_hide_other_findings(self):
        clean = {'query_exception_count': 0, 'nonfinite_by_column': {
            'merge_observed_min_distance': {'nan': 0, 'positive_inf': 2, 'negative_inf': 0}}}
        self.assertEqual(self.api().review_reasons(clean, 0), [])
        self.assertTrue(self.api().review_reasons(clean, 1))
        self.assertTrue(self.api().review_reasons(dict(clean, query_exception_count=1), 0))
        for counts in [{'nan': 1, 'positive_inf': 0, 'negative_inf': 0},
                       {'nan': 0, 'positive_inf': 0, 'negative_inf': 1}]:
            self.assertTrue(self.api().review_reasons(
                dict(clean, nonfinite_by_column={'merge_observed_min_distance': counts}), 0))
        self.assertTrue(self.api().review_reasons(dict(clean, nonfinite_by_column={
            'avg_speed': {'nan': 0, 'positive_inf': 1, 'negative_inf': 0}}), 0))
