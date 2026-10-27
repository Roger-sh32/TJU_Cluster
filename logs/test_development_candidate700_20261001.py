"""Tests for the dated full-development rebuild checker."""

from pathlib import Path
import unittest

import pandas as pd

try:
    from logs import development_candidate700_20261001 as recipe
except ImportError:
    recipe = None


class CandidateChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(recipe, 'Candidate rebuild recipe has not been implemented')

    def frame(self):
        return pd.DataFrame({'scene_name': ['scene-a', 'scene-b'],
                             'scene_token': ['a', 'b'], 'feature': [0.0, 1.0]})

    def validate(self, frame):
        recipe.validate_frame(frame, ['scene-a', 'scene-b'],
                              ['scene_name', 'scene_token', 'feature'], ['feature'])

    def test_valid_zero_is_not_missing(self):
        self.validate(self.frame())

    def test_membership_order_or_duplicates_fail(self):
        for frame in (self.frame().iloc[::-1], self.frame().iloc[[0, 0]]):
            with self.assertRaises(ValueError):
                self.validate(frame)

    def test_nonfinite_or_nonnumeric_feature_fails(self):
        for value in (float('nan'), float('inf'), 'bad'):
            frame = self.frame().astype({'feature': 'object'})
            frame.loc[0, 'feature'] = value
            with self.assertRaises(ValueError):
                self.validate(frame)

    def test_control_subset_must_reproduce_exactly(self):
        control = self.frame().iloc[[1]].reset_index(drop=True)
        recipe.assert_controls(self.frame(), control)
        changed = self.frame()
        changed.loc[1, 'feature'] += 1e-12
        with self.assertRaises(AssertionError):
            recipe.assert_controls(changed, control)

    def test_review_flags_do_not_assume_risk_decreases(self):
        changes = [{'scene_name': 'scene-0552', 'column': 'crossing_conflict_post_stop_ratio'},
                   {'scene_name': 'scene-0999', 'column': 'route_deviation_decision_demand'}]
        before = pd.DataFrame({'scene_name': ['scene-0552', 'scene-0999'], 'risk': [.35, .1]})
        after = pd.DataFrame({'scene_name': ['scene-0552', 'scene-0999'], 'risk': [.2, .3]})
        flags = recipe.review_flags(changes, before, after)
        self.assertEqual(flags['unexpected_columns'], [])
        self.assertEqual(flags['risk_increased_scenes'], ['scene-0999'])
        self.assertIn('scene-0552', flags['pending_semantic_scenes'])
        self.assertTrue(flags['requires_review'])

    def test_unexpected_dependency_requires_review(self):
        risk = pd.DataFrame({'scene_name': ['scene-0151'], 'risk': [.1]})
        flags = recipe.review_flags([{'scene_name': 'scene-0151', 'column': 'min_ttc'}], risk, risk)
        self.assertEqual(flags['unexpected_columns'], ['min_ttc'])
        self.assertTrue(flags['requires_review'])

    def test_bound_input_mutation_fails(self):
        record = recipe.file_record(Path(__file__))
        recipe.verify_records([record])
        changed_record = dict(record, sha256='0' * 64)
        with self.assertRaises(ValueError):
            recipe.verify_records([changed_record])


if __name__ == '__main__':
    unittest.main()
