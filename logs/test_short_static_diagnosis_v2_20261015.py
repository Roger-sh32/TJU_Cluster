import importlib.util
import unittest
from unittest.mock import Mock, patch


class ShortStaticTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('logs.diagnose_short_static_v2_20261015'))
        from logs import diagnose_short_static_v2_20261015
        return diagnose_short_static_v2_20261015

    def test_static_anchor_survives_absent_blocked_flag(self):
        m = self.module()
        trace = dict(static_flags=[False, True], stationary_ids=[None, 'truck'],
                     selected=[None, dict(instance_token='truck', annotation_token='ann')],
                     blocked_flags=[False, False])
        self.assertEqual(m.static_anchors(trace), {(1, 'truck')})

    def test_missing_static_target_identity_is_not_guessed(self):
        trace = dict(static_flags=[True], stationary_ids=[None], selected=[None], blocked_flags=[False])
        with self.assertRaises(ValueError):
            self.module().static_anchors(trace)

    def test_selected_and_stationary_identity_must_match(self):
        trace = dict(static_flags=[True], stationary_ids=['a'],
                     selected=[dict(instance_token='b', annotation_token='ann')], blocked_flags=[True])
        with self.assertRaises(ValueError):
            self.module().static_anchors(trace)

    def test_no_static_flags_proves_no_absence_of_obstacles(self):
        m = self.module()
        trace = dict(static_flags=[False], stationary_ids=[None], selected=[None], blocked_flags=[False])
        self.assertEqual(m.static_anchors(trace), set())
        self.assertFalse(m.ABSENCE_INFERRED)

    def test_strict_boolean_static_flags(self):
        trace = dict(static_flags=[1], stationary_ids=['a'],
                     selected=[dict(instance_token='a', annotation_token='ann')], blocked_flags=[True])
        with self.assertRaises(ValueError):
            self.module().static_anchors(trace)

    def test_static_and_minimum_event_roles_do_not_collapse(self):
        m = self.module()
        minimum = dict(frame_index=2, instance_token='moving-car')
        roles = m.anchor_roles({(1, 'parked-truck')}, minimum)
        self.assertEqual(roles, {(1, 'parked-truck'): ['static_selected'],
                                 (2, 'moving-car'): ['minimum_ttc']})

    def test_same_anchor_can_have_both_roles(self):
        roles = self.module().anchor_roles({(1, 'a')}, dict(frame_index=1, instance_token='a'))
        self.assertEqual(roles[(1, 'a')], ['static_selected', 'minimum_ttc'])

    def test_parent_diagnosis_original_seal_required(self):
        m = self.module()
        with patch.object(m.prior, 'load_protocol'), \
                patch.object(m, 'record', return_value={'sha256': 'refreshed'}):
            with self.assertRaisesRegex(ValueError, 'Original diagnosis seal'):
                m.verify_ancestors()

    def test_brief_static_integration_keeps_legacy_strict_evasion(self):
        m = self.module()
        a = dict(scene_name='SYN-short', scene_token='synshort', times=[0., .5, 1., 1.5],
            ego_yaws=[0.]*4, ego_speeds=[0., 2., 2., 2.],
            ego_positions=[[0., 0.], [10., 0.], [20., 5.], [30., 5.]],
            instance_max_speeds={'a': 0.}, bounded_stationary_instances=['a'])
        a['vehicle_tracks'] = {'a': [dict(index=i, position=[42., 0.], heading_delta=0., width=2., length=4.)
                                   for i in range(4)]}
        c = dict(instance_token='a', annotation_token='ann-a', clearance=27.75, category='vehicle.truck',
                 heading_delta=0., target_speed=0., supported=True)
        trace = dict(static_flags=[False, True, False, False], stationary_ids=[None, 'a', None, None],
            selected=[None, c, None, None], blocked_flags=[False]*4, temporary_flags=[False]*4,
            events=[], legacy_postfiltered_events=[])
        row = dict(stationary_lead_obstacle_ratio=.25, stationary_lead_event_count=1,
            stationary_lead_min_dist=27.75, ego_evasive_lateral_shift=5., ego_evasive_net_heading_change=0.,
            ego_evasive_lane_change_flag=1, min_ttc_scene_time=-1., min_ttc_target_annotation_token='none')
        saved = dict(candidate=trace, ledger=[[], [c], [], []], rejected=[])
        result = m.diagnose(a, saved, row)
        self.assertEqual(result['reproduced_strict_fields']['ego_evasive_lane_change_flag'], 1)
        self.assertEqual(result['blocked_anchor_count'], 0)
        self.assertEqual(result['static_anchor_count'], 1)
        self.assertEqual(result['route_queries'][0]['diagnostic_roles'], ['static_selected'])
        self.assertEqual(result['route_queries'][0]['relation'], 'unknown')
        self.assertFalse(result['target_identity_human_confirmed'])

    def test_candidate_stage_counts_keep_rejection_and_measurement_distinct(self):
        m = self.module()
        candidates = [dict(instance_token=str(i), supported=True, clearance=10.) for i in range(8)]
        candidates[0]['supported'] = False
        candidates[1]['clearance'] = None
        selected = candidates.copy()
        selected[0] = selected[1] = selected[6] = None
        selected[7] = dict(instance_token='closer')
        trace = dict(selected=selected, static_flags=[False, False, False, True, False, False, False, False],
            temporary_flags=[False, False, False, False, True, False, False, False],
            legacy_postfiltered_events=[dict(frame_index=5, instance_token='5')])
        result = m.candidate_stages(dict(candidate=trace, ledger=[[c] for c in candidates], rejected=[[6, '6']]))
        self.assertEqual(result, dict(map_unsupported=1, no_positive_clearance=1, selected_not_static=1,
            selected_static=1, selected_temporary_stop=1, legacy_ttc_postfilter=1,
            v7_preselection_gated=1, not_selected_nearest=1))


if __name__ == '__main__':
    unittest.main()
