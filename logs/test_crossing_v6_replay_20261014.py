import importlib.util
import unittest

import pandas as pd


class ReplayContracts(unittest.TestCase):
    def recipe(self):
        self.assertIsNotNone(importlib.util.find_spec('logs.crossing_v6_replay_20261014'),
                             'Bounded replay recipe is missing')
        from logs import crossing_v6_replay_20261014
        return crossing_v6_replay_20261014

    def test_rejects_unrelated_feature_change(self):
        recipe = self.recipe()
        old = pd.DataFrame([dict(scene_name='SYN-1', scene_token='SYN-T1', min_ttc=4.)])
        new = old.copy()
        new.loc[0, 'min_ttc'] = 5.
        with self.assertRaises(ValueError):
            recipe.compare_frames(new, old)

    def test_rejects_identity_reorder(self):
        recipe = self.recipe()
        old = pd.DataFrame([dict(scene_name='SYN-1', scene_token='SYN-T1'),
                            dict(scene_name='SYN-2', scene_token='SYN-T2')])
        with self.assertRaises(ValueError):
            recipe.compare_frames(old.iloc[::-1], old)

    def test_allowed_crossing_change_has_explicit_parent_value(self):
        recipe = self.recipe()
        old = pd.DataFrame([dict(scene_name='SYN-1', scene_token='SYN-T1',
                                 crossing_vehicle_conflict_ratio=.1)])
        new = old.copy()
        new.loc[0, 'crossing_vehicle_conflict_ratio'] = 0.
        changes = recipe.compare_frames(new, old)
        self.assertEqual(changes[0]['v5_2'], .1)
        self.assertEqual(changes[0]['v6'], 0.)

    def test_positive_control_loss_fails(self):
        recipe = self.recipe()
        frame = pd.DataFrame([dict(scene_name='scene-0068', crossing_vehicle_conflict_ratio=0.,
                                   left_turn_cross_traffic_interaction_ratio=.1)])
        with self.assertRaises(ValueError):
            recipe.check_controls(frame, frame)

    def test_route_flag_requires_effective_same_target(self):
        recipe = self.recipe()
        audit = dict(times=[0., .5], ego_positions=[[0., 0.], [2., 0.]],
                     vehicle_tracks={'a': [dict(index=0, position=[1., 0.])]})
        evidence = [dict(index=0, instance_token='a', effective_conflict=False)]
        self.assertEqual(recipe.route_flags(audit, evidence), [False, False])
        evidence[0]['effective_conflict'] = True
        self.assertEqual(recipe.route_flags(audit, evidence), [True, False])

    def test_original_protocol_digest_required_for_check(self):
        recipe = self.recipe()
        with self.assertRaises(ValueError):
            recipe.check(None)

    def test_distractor_cannot_replace_reviewed_yield_target(self):
        recipe = self.recipe()
        function = getattr(recipe, 'check_event_controls', None)
        self.assertIsNotNone(function, 'Same-target event protection is missing')
        old = [dict(scene_name='scene-0068', crossing_v5_audit=[
            dict(index=15, instance_token='727349048e9044d98846cbeeb3a1b5fd', effective_conflict=True),
            dict(index=16, instance_token='727349048e9044d98846cbeeb3a1b5fd', effective_conflict=True)])]
        new = [dict(scene_name='scene-0068', crossing=[
            dict(index=15, instance_token='distractor', effective_conflict=True),
            dict(index=16, instance_token='727349048e9044d98846cbeeb3a1b5fd', effective_conflict=False)])]
        with self.assertRaisesRegex(ValueError, 'Lost same-target crossing control: scene-0068/\\(15,'):
            function(old, new)


if __name__ == '__main__':
    unittest.main()
