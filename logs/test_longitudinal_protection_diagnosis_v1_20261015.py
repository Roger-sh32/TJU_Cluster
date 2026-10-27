import importlib.util
import math
import unittest
import copy
from unittest.mock import Mock, patch


class DiagnosisTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('logs.diagnose_longitudinal_protection_v1_20261015'))
        from logs import diagnose_longitudinal_protection_v1_20261015
        return diagnose_longitudinal_protection_v1_20261015

    def test_target_switch_splits_episode(self):
        m = self.module()
        self.assertEqual(m.target_episodes([True]*4, ['a', 'a', 'b', 'b'], [0., .5, 1., 1.5]),
                         [[0, 1], [2, 3]])

    def test_gap_splits_episode_without_inventing_coverage(self):
        m = self.module()
        self.assertEqual(m.target_episodes([True]*3, ['a']*3, [0., .5, 2.]), [[0, 1], [2]])

    def test_active_frame_without_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.module().target_episodes([True], [None], [0.])

    def scene(self):
        return dict(times=[0., .5, 1., 1.5], ego_yaws=[0.]*4,
                    ego_positions=[[0., 0.], [1., 0.], [2., 0.], [3., 0.]],
                    ego_speeds=[0., 2., 2., 2.])

    def test_initial_placeholder_not_an_observed_stop(self):
        m = self.module()
        profile = m.motion_window(self.scene(), 0, 1.)
        self.assertEqual(profile['observed_speed_min_mps'], 2.)
        self.assertEqual(profile['observed_speed_count'], 2)

    def test_tail_has_unknown_motion_not_safe_zero(self):
        p = self.module().motion_window(self.scene(), 3, 3.)
        self.assertFalse(p['complete_bracket'])
        self.assertIsNone(p['lateral_shift_m'])
        self.assertIsNone(p['net_heading_change_rad'])

    def test_gap_cannot_be_a_complete_motion_window(self):
        a = self.scene()
        a['times'] = [0., .5, 2., 2.5]
        p = self.module().motion_window(a, 0, 2.)
        self.assertFalse(p['complete_bracket'])
        self.assertIsNone(p['lateral_shift_m'])

    def test_normal_curve_can_trigger_frozen_raw_rule(self):
        m = self.module()
        a = self.scene()
        a['ego_positions'] = [[0., 0.], [2., 1.], [3., 3.], [4., 5.]]
        a['ego_yaws'] = [0., .3, .6, .9]
        p = m.motion_window(a, 0, 1.5)
        self.assertAlmostEqual(p['net_heading_change_rad'], .9)
        self.assertEqual(p['lateral_shift_m'], 5.)
        self.assertTrue(m.r.is_obstacle_induced_route_deviation(1., 20.,
                         p['lateral_shift_m'], p['net_heading_change_rad']))

    def test_wrapped_yaw_not_full_circle_change(self):
        a = self.scene()
        a['ego_yaws'] = [3.1, -3.1, -3., -2.9]
        p = self.module().motion_window(a, 0, 1.)
        self.assertAlmostEqual(p['net_heading_change_rad'], 2*math.pi-6.1)

    def test_invalid_timeline_and_boolean_anchor_rejected(self):
        m = self.module()
        with self.assertRaises(ValueError):
            m.motion_window(self.scene(), True, 1.)
        a = self.scene()
        a['ego_speeds'][1] = float('nan')
        with self.assertRaises(ValueError):
            m.motion_window(a, 1, 1.)

    def test_route_diagnosis_does_not_mutate_protected_source(self):
        m = self.module()
        a = self.scene()
        a['vehicle_tracks'] = {'a': [dict(index=i, position=[12., 0.], heading_delta=0.,
             width=2., length=4., crossing_exposure=False, crossing_conflict=False,
             raw_crossing_conflict=False) for i in range(4)]}
        before = copy.deepcopy(a)
        result = m.route_queries(a, {(3, 'a')})
        self.assertEqual(result[0]['relation'], 'unknown')
        self.assertEqual(a, before)

    def test_missing_geometry_identity_cannot_be_silently_skipped(self):
        a = self.scene()
        a['vehicle_tracks'] = {}
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.module().route_queries(a, {(1, 'missing')})

    def test_wrong_original_digest_fails_before_reading_protocol(self):
        m = self.module()
        with patch.object(m, 'record', return_value={'sha256': 'original'}):
            with self.assertRaisesRegex(ValueError, 'Original'):
                m.load_protocol('wrong')

    def test_original_parent_report_digest_is_pinned_before_trusting_outputs(self):
        m = self.module()
        report = Mock()
        report.read_text.return_value = '{"protocol": {}, "outputs": []}'
        status = dict(phase='completed_candidate_requires_review', report={}, claim={})
        with patch.object(m.parent, 'load_protocol', return_value=({}, status)), \
                patch.object(m.parent, 'REPORT', report), patch.object(m, 'verify_records'), \
                patch.object(m, 'record', return_value={'sha256': 'refreshed-not-original'}):
            with self.assertRaisesRegex(ValueError, 'Original parent report'):
                m.verify_parent()

    def test_non_grid_bracket_complete_but_sample_span_disclosed(self):
        a = self.scene()
        p = self.module().motion_window(a, 0, .7)
        self.assertTrue(p['complete_bracket'])
        self.assertEqual(p['sampled_span_s'], .5)

    def test_partial_tail_reports_observation_without_complete_future(self):
        p = self.module().motion_window(self.scene(), 2, 3.)
        self.assertFalse(p['complete_bracket'])
        self.assertEqual(p['sampled_span_s'], .5)
        self.assertEqual(p['lateral_shift_m'], 0.)

    def test_minimum_target_is_queried_even_without_static_blockage(self):
        m = self.module()
        a = self.scene()
        a.update(scene_name='SYN-1', scene_token='syn1', obstacle_induced_route_deviation_candidate=False)
        a['vehicle_tracks'] = {'a': [dict(index=i, position=[12., 0.], heading_delta=0.,
                                       width=2., length=4.) for i in range(4)]}
        event = dict(frame_index=3, scene_time=1.5, annotation_token='ann-a', instance_token='a')
        trace = dict(blocked_flags=[False]*4, stationary_ids=[None]*4, selected=[None]*4,
                     raw_deviation=False, events=[event])
        row = dict(ego_evasive_lane_change_flag=0, obstacle_induced_route_deviation_flag=0,
                   min_ttc_scene_time=1.5, min_ttc_target_annotation_token='ann-a')
        result = m.diagnose_scene(a, dict(candidate=trace, protected_context=False), row)
        self.assertEqual(result['episodes'], [])
        self.assertEqual(result['minimum_ttc_event'], event)
        self.assertEqual(result['route_queries'][0]['relation'], 'unknown')
        self.assertIsNone(result['minimum_event_window']['lateral_shift_m'])

    def test_global_raw_protection_can_mix_different_target_episodes(self):
        m = self.module()
        a = dict(scene_name='SYN-mix', scene_token='synmix', times=[0., .5, 1., 1.5, 2., 2.5],
            ego_yaws=[0., .3, .6, .9, .9, .9], ego_speeds=[0., 2., 2., 2., 2., 2.],
            ego_positions=[[0., 0.], [2., 1.], [3., 3.], [4., 5.], [5., 6.], [6., 7.]],
            obstacle_induced_route_deviation_candidate=True)
        a['vehicle_tracks'] = {t: [dict(index=i, position=[40., 0.], heading_delta=0., width=2., length=4.)
                                  for i in own] for t, own in [('b', [0, 1]), ('a', [4, 5])]}
        selected = [dict(instance_token='b', category='vehicle.car', clearance=40., heading_delta=0., target_speed=0.)]*2
        selected += [None, None]
        selected += [dict(instance_token='a', category='vehicle.car', clearance=20., heading_delta=0., target_speed=0.)]*2
        trace = dict(blocked_flags=[True, True, False, False, True, True],
            stationary_ids=['b', 'b', None, None, 'a', 'a'], selected=selected, raw_deviation=True, events=[])
        row = dict(ego_evasive_lane_change_flag=0, obstacle_induced_route_deviation_flag=0,
                   min_ttc_scene_time=-1., min_ttc_target_annotation_token='none')
        result = m.diagnose_scene(a, dict(candidate=trace, protected_context=True), row)
        self.assertTrue(result['protection_causes']['raw_deviation'])
        self.assertFalse(any(e['frozen_rule_per_episode'] for e in result['episodes']))
        self.assertIsNone(result['minimum_ttc_event'])


if __name__ == '__main__':
    unittest.main()
