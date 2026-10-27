import unittest

from logs.diagnose_review8_20261012 import projection_blockers, exact_rows


class DiagnosticContracts(unittest.TestCase):
    def evidence(self):
        return {'future_complete': True, 'yielding_response': False,
                'heading_change': .5, 'minimum_future_route_distance': 9.,
                'actor_bounding_diameter': 4., 'rejected_turning_projection': True}

    def test_complete_far_turn_is_rejected(self):
        self.assertEqual(projection_blockers(self.evidence()), [])

    def test_short_future_and_response_are_separate_blockers(self):
        row = self.evidence()
        row.update(future_complete=False, yielding_response=True, rejected_turning_projection=False)
        self.assertEqual(projection_blockers(row), ['incomplete_future', 'low_speed_or_braking_response'])

    def test_near_route_is_not_proof_of_safety(self):
        row = self.evidence()
        row.update(minimum_future_route_distance=4., rejected_turning_projection=False)
        self.assertEqual(projection_blockers(row), ['within_footprint_route_margin'])

    def test_unknown_size_cannot_clear_actor(self):
        row = self.evidence()
        row.update(actor_bounding_diameter=float('nan'), rejected_turning_projection=False)
        self.assertEqual(projection_blockers(row), ['nonfinite_geometry'])

    def test_exact_rows_rejects_drift_and_duplicate(self):
        import pandas as pd
        row = pd.DataFrame([{'scene_name': 'scene-0002', 'scene_token': 'a', 'value': 0.}])
        exact_rows(row, row)
        changed = row.copy()
        changed.loc[0, 'value'] = .001
        with self.assertRaises(AssertionError):
            exact_rows(changed, row)
        with self.assertRaises(ValueError):
            exact_rows(pd.concat([row, row]), row)


if __name__ == '__main__':
    unittest.main()
