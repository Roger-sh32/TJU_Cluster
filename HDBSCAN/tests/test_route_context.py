import math
import unittest

from HDBSCAN.scripts import scene_feature_rules as rules


class RouteContextTest(unittest.TestCase):
    def test_oncoming_requires_opposing_heading_and_motion(self):
        self.assertTrue(rules.is_oncoming_vehicle(
            25, 2, -4, obj_lateral_speed=0.5, heading_delta=math.pi - 0.1))
        self.assertFalse(rules.is_oncoming_vehicle(
            25, 2, -4, obj_lateral_speed=7, heading_delta=-1.98))
        self.assertFalse(rules.is_oncoming_vehicle(
            25, 2, -4, obj_lateral_speed=7, heading_delta=math.pi))
        self.assertFalse(rules.is_oncoming_vehicle(
            25, 2, -4, obj_lateral_speed=0, heading_delta=0))
        self.assertFalse(rules.is_oncoming_vehicle(
            25, 2, -4, obj_lateral_speed=float('nan'), heading_delta=math.pi))

    def test_bounded_annotation_jitter_can_recover_static_obstacle(self):
        split = rules.split_stopped_lead_history(
            ['parked'], {'parked': 0.58},
            bounded_stationary_instances={'parked'})
        self.assertEqual(split.static_flags, [True])
        self.assertEqual(split.temporary_flags, [False])

    def test_stationary_evidence_cannot_override_observed_motion(self):
        split = rules.split_stopped_lead_history(
            ['moving', 'unknown'], {'moving': 2.0, 'unknown': 0.58},
            bounded_stationary_instances={'moving'})
        self.assertEqual(split.static_flags, [False, False])
        self.assertEqual(split.temporary_flags, [True, False])

    def test_bounded_track_rejects_creep_sparse_tracks_and_out_and_back_motion(self):
        times = [i * 0.5 for i in range(12)]
        jitter = [(0.0, 0.0)] * 10 + [(0.29, 0.0), (0.29, 0.0)]
        self.assertTrue(rules.is_bounded_stationary_track(jitter, times))
        self.assertFalse(rules.is_bounded_stationary_track(
            [(i * 0.3, 0.0) for i in range(12)], times))
        self.assertFalse(rules.is_bounded_stationary_track(
            [(0, 0), (0, 0)], [0, 5]))
        self.assertFalse(rules.is_bounded_stationary_track(
            [(0, 0), (0, 0), (2, 0), (0, 0), (0, 0)], [0, .5, 1, 1.5, 2]))
        self.assertFalse(rules.is_bounded_stationary_track(
            jitter[:5], [0, .5, 1, 4, 4.5]))

    def test_curved_route_is_not_evasive_even_with_recovered_heading(self):
        for shift in (17.23, 22.29, 50.89, 18.79):
            self.assertFalse(rules.is_evasive_lane_change(
                1, shift, 0.08, stationary_max_duration=1.5,
                stationary_min_distance=25.0))

    def test_known_short_avoidance_remains_supported(self):
        self.assertTrue(rules.is_evasive_lane_change(
            1, 4.83, 0.076, stationary_max_duration=0.5,
            stationary_min_distance=27.86))

    def test_offroad_bicycle_is_not_a_longitudinal_target(self):
        self.assertFalse(rules.is_lane_supported_target(False))
        self.assertTrue(rules.is_lane_supported_target(True))
        self.assertTrue(rules.is_lane_supported_target(None))

    def test_actor_on_unvisited_straight_extension_is_not_on_turn_route(self):
        self.assertGreater(rules.distance_to_polyline((15, 0), [(0, 0), (5, 0), (5, -10)]), 5)
        self.assertAlmostEqual(rules.distance_to_polyline((5, -5), [(0, 0), (5, 0), (5, -10)]), 0)

    def test_intrusion_requires_actor_movement_toward_lane(self):
        args = dict(initial_lateral=3.5, final_lateral=1.5,
                    actor_lateral_displacement=-1.6, forward_clearance=12,
                    duration=1.5, heading_aligned=True)
        self.assertTrue(rules.is_adjacent_lane_intrusion(**args))
        self.assertFalse(rules.is_adjacent_lane_intrusion(**dict(args, actor_lateral_displacement=0.0)))
        self.assertFalse(rules.is_adjacent_lane_intrusion(**dict(args, final_lateral=3.3)))
        self.assertFalse(rules.is_adjacent_lane_intrusion(**dict(args, forward_clearance=40)))

    def test_slow_inward_facing_side_vehicle_is_candidate_not_parallel_parked_car(self):
        self.assertTrue(rules.is_side_entry_candidate(12, 6, -0.7, 0.2))
        self.assertFalse(rules.is_side_entry_candidate(12, 6, 0.0, 0.2))
        self.assertFalse(rules.is_side_entry_candidate(12, 6, 0.7, 0.2))
        self.assertFalse(rules.is_side_entry_candidate(-12, 6, -0.7, 0.2))


if __name__ == '__main__':
    unittest.main()
