"""Analysis-checker regression tests; no experiment outputs are read or written."""

import copy
import unittest
from unittest.mock import patch

import pandas as pd

from logs import crossing_regression33_20261001 as recipe


class AnalysisChecksTest(unittest.TestCase):
    def test_risk_increase_is_recorded_not_rejected(self):
        before = pd.DataFrame({'scene_name': ['s'], 'risk': [.075]})
        after = pd.DataFrame({'scene_name': ['s'], 'risk': [.300]})
        result = recipe.revision_review_flags({'left_turn_cross_traffic_interaction_ratio'}, before, after)
        self.assertEqual(result['risk_increased_scenes'], ['s'])
        self.assertTrue(result['requires_review'])
        self.assertEqual(result['unexpected_columns'], [])

    def test_route_deviation_fields_are_known_dependencies(self):
        frame = pd.DataFrame({'scene_name': ['s'], 'risk': [.1]})
        result = recipe.revision_review_flags({'obstacle_induced_route_deviation_flag',
                                               'route_deviation_decision_demand'}, frame, frame)
        self.assertEqual(result['unexpected_columns'], [])

    def test_unrelated_change_is_explicit_review_blocker(self):
        frame = pd.DataFrame({'scene_name': ['s'], 'risk': [.1]})
        self.assertTrue(recipe.revision_review_flags({'min_ttc'}, frame, frame)['requires_review'])

    def test_tampered_frozen_recipe_refused_before_reading_outputs(self):
        protocol = copy.deepcopy(recipe.read_json(recipe.PROTOCOL))
        protocol['script']['sha256'] = '0' * 64
        with patch.object(recipe, 'read_json', return_value=protocol), \
                patch.object(recipe.pd, 'read_csv', side_effect=AssertionError('Read output before source check')):
            with self.assertRaisesRegex(ValueError, 'Frozen'):
                recipe.check(True)


if __name__ == '__main__':
    unittest.main()
