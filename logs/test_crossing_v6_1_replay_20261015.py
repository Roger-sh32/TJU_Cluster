import importlib.util
import unittest

import pandas as pd


class ReplayContracts(unittest.TestCase):
    def recipe(self):
        self.assertIsNotNone(importlib.util.find_spec('logs.crossing_v6_1_replay_20261015'))
        from logs import crossing_v6_1_replay_20261015
        return crossing_v6_1_replay_20261015

    def test_current_crossing_column_cannot_change(self):
        recipe = self.recipe()
        old = pd.DataFrame([dict(scene_name='SYN-1', scene_token='SYN-T1',
                                 crossing_vehicle_conflict_ratio=.1)])
        new = old.copy()
        new.loc[0, 'crossing_vehicle_conflict_ratio'] = .2
        with self.assertRaisesRegex(ValueError, 'Unrelated change'):
            recipe.compare_frames(new, old)

    def test_only_local_history_and_documented_dependencies_allowed(self):
        recipe = self.recipe()
        old = pd.DataFrame([dict(scene_name='SYN-1', scene_token='SYN-T1',
                                 left_turn_cross_traffic_interaction_ratio=.1)])
        new = old.copy()
        new.loc[0, 'left_turn_cross_traffic_interaction_ratio'] = .2
        self.assertEqual(recipe.compare_frames(new, old)[0]['v6_1'], .2)

    def test_identity_order_is_frozen(self):
        recipe = self.recipe()
        old = pd.DataFrame([dict(scene_name='SYN-1', scene_token='SYN-T1'),
                            dict(scene_name='SYN-2', scene_token='SYN-T2')])
        with self.assertRaises(ValueError):
            recipe.compare_frames(old.iloc[::-1], old)

    def test_check_requires_original_digest(self):
        recipe = self.recipe()
        with self.assertRaises(ValueError):
            recipe.check(None)

    def test_unrelated_car_cannot_be_restored_by_truck(self):
        recipe = self.recipe()
        function = getattr(recipe, 'check_boundary_controls', None)
        self.assertIsNotNone(function)
        with self.assertRaises(ValueError):
            function([dict(scene_name='scene-0068', restored=[dict(index=24,
                instance_token='64a805096d9047a6bbc73734b0a90e67')], target_flags={})])


if __name__ == '__main__':
    unittest.main()
