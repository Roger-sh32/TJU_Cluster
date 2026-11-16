import unittest
from HDBSCAN.scripts import target_obstruction_v8_1 as m


class BlockedIdentityTests(unittest.TestCase):
    def test_update_preserves_short_avoidance_and_recomputes_dependents(self):
        audit = dict(times=[0., .5, 1.], ego_positions=[[0., 0.], [5., 0.], [10., 6.]],
                     ego_yaws=[0., .1, .4])
        context = dict(traffic_light_control_density=0., crossing_vehicle_exposure_ratio=0.,
                       intersection_stop_ratio=0., left_turn_cross_traffic_interaction_ratio=0.)
        fields = dict(ego_evasive_lane_change_flag=1, min_ttc=2., blocked_path_obstacle_ratio=1.,
                      obstacle_induced_route_deviation_flag=1, route_deviation_decision_demand=1.)
        trace = dict(stationary_ids=['a', 'b', 'c'], static_flags=[True]*3,
                     selected=[dict(clearance=10.)]*3)
        result, evidence = m.update_blockage(audit, context, fields, trace)
        self.assertEqual(result['blocked_path_obstacle_ratio'], 0.)
        self.assertEqual(result['obstacle_induced_route_deviation_flag'], 0)
        self.assertEqual(result['route_deviation_decision_demand'], 0.)
        self.assertEqual(result['ego_evasive_lane_change_flag'], 1)
        self.assertEqual(result['min_ttc'], 2.)
        self.assertEqual(fields['blocked_path_obstacle_ratio'], 1.)
        trace['stationary_ids'] = ['a']*3
        result, evidence = m.update_blockage(audit, context, fields, trace)
        self.assertEqual(result['blocked_path_obstacle_ratio'], 1.)
        self.assertEqual(result['obstacle_induced_route_deviation_flag'], 1)

    def test_different_single_frame_targets_do_not_form_blockage(self):
        flags, episodes = m.blocked_evidence(['a', 'b', 'c'], [0., .5, 1.])
        self.assertEqual(flags, [False]*3)
        self.assertEqual(len(episodes), 3)

    def test_same_target_keeps_legacy_two_frame_tail(self):
        flags, episodes = m.blocked_evidence(['a', 'a', 'b'], [0., .5, 1.])
        self.assertEqual(flags, [True, True, False])
        self.assertEqual(episodes[0]['qualifying_duration'], 1.)

    def test_gap_breaks_same_target_without_bridging(self):
        flags, _ = m.blocked_evidence(['a', 'a'], [0., 2.])
        self.assertEqual(flags, [False, False])

    def test_absence_preserves_short_obstacle_but_not_blockage(self):
        flags, episodes = m.blocked_evidence(['a', None, 'a'], [0., .5, 1.])
        self.assertEqual(flags, [False]*3)
        self.assertEqual([e['indices'] for e in episodes], [[0], [2]])
