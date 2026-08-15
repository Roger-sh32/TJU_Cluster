import math
import unittest


class SceneFeatureRulesTest(unittest.TestCase):
    def setUp(self):
        from HDBSCAN.scripts import scene_feature_rules

        self.rules = scene_feature_rules

    def test_same_path_lead_is_not_crossing_or_merge(self):
        result = self.rules.classify_vehicle_interaction(
            forward_dist=20.0,
            lateral_dist=0.5,
            obj_forward_speed=5.0,
            obj_lateral_speed=0.1,
            ego_speed=8.0,
        )
        self.assertTrue(result.same_path)
        self.assertFalse(result.merge_conflict)
        self.assertFalse(result.crossing_exposure)

    def test_vehicle_near_lane_boundary_is_not_same_path_lead(self):
        result = self.rules.classify_vehicle_interaction(
            forward_dist=15.0,
            lateral_dist=2.4,
            obj_forward_speed=1.0,
            obj_lateral_speed=0.0,
            ego_speed=5.0,
        )
        self.assertFalse(result.same_path)

    def test_side_vehicle_closing_into_lane_is_merge_conflict(self):
        result = self.rules.classify_vehicle_interaction(
            forward_dist=12.0,
            lateral_dist=5.0,
            obj_forward_speed=4.0,
            obj_lateral_speed=-1.0,
            ego_speed=5.0,
        )
        self.assertTrue(result.merge_conflict)
        self.assertTrue(result.merge_exposure)
        self.assertFalse(result.same_path)

    def test_vehicle_behind_ego_is_not_merge_exposure(self):
        result = self.rules.classify_vehicle_interaction(
            forward_dist=-20.0,
            lateral_dist=3.0,
            obj_forward_speed=8.0,
            obj_lateral_speed=-0.2,
            ego_speed=6.0,
        )
        self.assertFalse(result.merge_exposure)
        self.assertFalse(result.merge_conflict)

    def test_cross_traffic_at_red_light_is_exposure_not_conflict(self):
        result = self.rules.classify_vehicle_interaction(
            forward_dist=8.0,
            lateral_dist=8.0,
            obj_forward_speed=0.0,
            obj_lateral_speed=-4.0,
            ego_speed=0.2,
        )
        self.assertTrue(result.crossing_exposure)
        self.assertFalse(result.crossing_conflict)

    def test_cross_traffic_reaching_moving_ego_path_is_conflict(self):
        result = self.rules.classify_vehicle_interaction(
            forward_dist=16.0,
            lateral_dist=8.0,
            obj_forward_speed=0.0,
            obj_lateral_speed=-4.0,
            ego_speed=8.0,
        )
        self.assertTrue(result.crossing_exposure)
        self.assertTrue(result.crossing_conflict)

    def test_vru_must_be_predicted_to_enter_ego_corridor(self):
        crossing = self.rules.is_vru_path_conflict(
            forward_dist=12.0,
            lateral_dist=5.0,
            obj_forward_speed=0.0,
            obj_lateral_speed=-2.0,
            ego_speed=4.0,
        )
        walking_away = self.rules.is_vru_path_conflict(
            forward_dist=12.0,
            lateral_dist=5.0,
            obj_forward_speed=0.0,
            obj_lateral_speed=2.0,
            ego_speed=4.0,
        )
        self.assertTrue(crossing)
        self.assertFalse(walking_away)

    def test_vru_crossing_exposure_does_not_require_simultaneous_overlap(self):
        exposed = self.rules.is_vru_crossing_exposure(
            forward_dist=25.0,
            lateral_dist=-5.0,
            obj_lateral_speed=0.8,
        )
        self.assertTrue(exposed)

    def test_same_lane_same_direction_vru_is_classified_separately(self):
        relation = self.rules.classify_vru_lane_relation(
            forward_dist=8.0,
            lateral_dist=0.5,
            obj_forward_speed=1.2,
            obj_lateral_speed=0.1,
        )
        self.assertTrue(relation.same_lane)
        self.assertTrue(relation.same_direction)

    def test_crossing_vru_is_not_same_direction(self):
        relation = self.rules.classify_vru_lane_relation(
            forward_dist=8.0,
            lateral_dist=0.5,
            obj_forward_speed=0.0,
            obj_lateral_speed=1.5,
        )
        self.assertTrue(relation.same_lane)
        self.assertFalse(relation.same_direction)

    def test_walkway_vru_is_not_assigned_to_ego_lane(self):
        relation = self.rules.classify_mapped_vru_lane_relation(
            on_walkway=True,
            lane_lateral_distance=0.8,
            obj_lane_forward_speed=1.0,
        )
        self.assertFalse(relation.same_lane)
        self.assertFalse(relation.same_direction)

    def test_lane_centerline_and_direction_define_mapped_vru_relation(self):
        same_direction = self.rules.classify_mapped_vru_lane_relation(
            on_walkway=False,
            lane_lateral_distance=1.2,
            obj_lane_forward_speed=1.0,
        )
        reverse = self.rules.classify_mapped_vru_lane_relation(
            on_walkway=False,
            lane_lateral_distance=1.2,
            obj_lane_forward_speed=-1.0,
        )
        self.assertTrue(same_direction.same_lane)
        self.assertTrue(same_direction.same_direction)
        self.assertTrue(reverse.same_lane)
        self.assertFalse(reverse.same_direction)

    def test_short_event_filter_removes_single_frame_speed_noise(self):
        filtered = self.rules.filter_short_events(
            [False, True, False, True, True],
            [0.0, 0.5, 1.0, 1.5, 2.0],
            minimum_duration=1.0,
        )
        self.assertEqual(filtered, [False, False, False, True, True])

    def test_vru_sustained_filter_keeps_two_frames_but_rejects_one(self):
        one_frame = self.rules.filter_short_events(
            [False, True, False],
            [0.0, 0.5, 1.0],
            minimum_duration=0.8,
        )
        two_frames = self.rules.filter_short_events(
            [False, True, True, False],
            [0.0, 0.45, 0.9, 1.35],
            minimum_duration=0.8,
        )
        self.assertEqual(one_frame, [False, False, False])
        self.assertEqual(two_frames, [False, True, True, False])

    def test_low_forward_speed_side_vehicle_is_not_merge(self):
        result = self.rules.classify_vehicle_interaction(
            forward_dist=12.0,
            lateral_dist=5.0,
            obj_forward_speed=0.1,
            obj_lateral_speed=-1.0,
            ego_speed=5.0,
        )
        self.assertFalse(result.merge_exposure)

    def test_front_vehicle_with_negative_forward_speed_is_oncoming(self):
        self.assertTrue(
            self.rules.is_oncoming_vehicle(
                forward_dist=25.0,
                lateral_dist=2.0,
                obj_forward_speed=-4.0,
            )
        )

    def test_observed_vru_requires_both_proximity_and_lane_entry(self):
        self.assertFalse(self.rules.is_observed_vru_relevant(3.0, False))
        self.assertFalse(self.rules.is_observed_vru_relevant(7.0, True))
        self.assertTrue(self.rules.is_observed_vru_relevant(3.0, True))

    def test_opposing_actor_heading_is_not_aligned_with_ego(self):
        self.assertTrue(self.rules.is_heading_aligned(0.1, 0.0))
        self.assertFalse(self.rules.is_heading_aligned(math.pi, 0.0))

    def test_context_window_keeps_only_events_after_obstacle_detection(self):
        flags = self.rules.events_within_context(
            [True, False, True, False, True],
            [0.0, 2.0, 4.0, 8.0, 12.0],
            start_index=1,
            horizon=6.0,
        )
        self.assertEqual(flags, [False, False, True, False, False])

    def test_event_summary_counts_runs_and_duration(self):
        summary = self.rules.summarize_events(
            [False, True, True, False, True],
            [0.0, 0.5, 1.0, 1.5, 2.0],
        )
        self.assertAlmostEqual(summary.ratio, 0.6)
        self.assertEqual(summary.count, 2)
        self.assertAlmostEqual(summary.max_duration, 1.0)

    def test_heading_change_wraps_across_pi_boundary(self):
        change = self.rules.wrapped_heading_change(
            [math.radians(179), math.radians(-179)]
        )
        self.assertAlmostEqual(change, math.radians(2), places=6)

    def test_overlapping_front_center_is_rejected(self):
        self.assertIsNone(
            self.rules.longitudinal_clearance(
                forward_dist=0.36,
                object_length=4.0,
            )
        )
        self.assertAlmostEqual(
            self.rules.longitudinal_clearance(
                forward_dist=10.0,
                object_length=4.0,
            ),
            5.75,
        )

    def test_initially_stopped_then_restarts_is_not_conflict_induced_stop(self):
        summary = self.rules.summarize_motion_decision(
            speeds=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 3.0, 4.0],
            timestamps=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
        )
        self.assertTrue(summary.stopped_at_start)
        self.assertFalse(summary.stop_from_motion)
        self.assertTrue(summary.restart_after_stop)

    def test_moving_then_sustained_stop_is_decision_stop(self):
        summary = self.rules.summarize_motion_decision(
            speeds=[5.0, 5.0, 4.0, 3.0, 1.0, 0.5, 0.0, 0.0, 2.5],
            timestamps=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            initial_window=2.0,
        )
        self.assertFalse(summary.stopped_at_start)
        self.assertTrue(summary.stop_from_motion)
        self.assertTrue(summary.restart_after_stop)
        self.assertAlmostEqual(summary.first_stop_time, 2.5)

    def test_lateral_shift_after_obstacle_uses_frozen_ego_heading(self):
        shift = self.rules.lateral_shift_after_index(
            positions=[(0.0, 0.0), (2.0, 0.0), (4.0, 1.0), (6.0, 3.0)],
            timestamps=[0.0, 0.5, 1.0, 1.5],
            start_index=1,
            start_heading=0.0,
        )
        self.assertAlmostEqual(shift, 3.0)

    def test_lane_change_heading_returns_near_initial_direction(self):
        change = self.rules.net_heading_change_after_index(
            yaws=[0.0, 0.0, 0.15, -0.10, 0.02],
            timestamps=[0.0, 0.5, 1.0, 1.5, 2.0],
            start_index=1,
            start_heading=0.0,
        )
        self.assertAlmostEqual(change, 0.02)

    def test_turning_maneuver_retains_large_heading_change(self):
        change = self.rules.net_heading_change_after_index(
            yaws=[0.0, 0.0, 0.2, 0.6, 1.0],
            timestamps=[0.0, 0.5, 1.0, 1.5, 2.0],
            start_index=1,
            start_heading=0.0,
        )
        self.assertAlmostEqual(change, 1.0)

    def test_evasive_lane_change_accepts_moderate_shift_with_heading_recovery(self):
        self.assertTrue(
            self.rules.is_evasive_lane_change(
                stationary_event_count=1,
                lateral_shift=1.7,
                net_heading_change=0.10,
            )
        )

    def test_evasive_lane_change_rejects_large_turn(self):
        self.assertFalse(
            self.rules.is_evasive_lane_change(
                stationary_event_count=1,
                lateral_shift=14.5,
                net_heading_change=1.05,
            )
        )

    def test_evasive_lane_change_rejects_brief_distant_obstacle_evidence(self):
        self.assertFalse(
            self.rules.is_evasive_lane_change(
                stationary_event_count=1,
                lateral_shift=3.0,
                net_heading_change=0.15,
                stationary_max_duration=0.5,
                stationary_min_distance=29.0,
            )
        )

    def test_evasive_lane_change_rejects_close_obstacle_if_brief(self):
        self.assertFalse(
            self.rules.is_evasive_lane_change(
                stationary_event_count=1,
                lateral_shift=2.0,
                net_heading_change=0.10,
                stationary_max_duration=0.5,
                stationary_min_distance=12.0,
            )
        )

    def test_evasive_lane_change_accepts_brief_obstacle_with_strong_recovered_shift(self):
        self.assertTrue(
            self.rules.is_evasive_lane_change(
                stationary_event_count=1,
                lateral_shift=4.8,
                net_heading_change=0.08,
                stationary_max_duration=0.5,
                stationary_min_distance=28.0,
            )
        )

    def test_turning_projection_artifact_requires_static_opposing_target_and_turn(self):
        self.assertTrue(
            self.rules.is_turning_projection_artifact(
                target_speed=0.08,
                heading_delta=2.73,
                local_heading_change=0.8,
            )
        )
        self.assertFalse(
            self.rules.is_turning_projection_artifact(
                target_speed=4.0,
                heading_delta=0.1,
                local_heading_change=0.8,
            )
        )

    def test_local_heading_change_uses_only_event_window(self):
        change = self.rules.local_heading_change_around_index(
            yaws=[0.0, 0.0, 0.1, 0.6, 1.0, 1.0, 1.0],
            timestamps=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
            event_index=3,
            window=0.6,
        )
        straight_after_turn = self.rules.local_heading_change_around_index(
            yaws=[0.0, 0.0, 0.1, 0.6, 1.0, 1.0, 1.0],
            timestamps=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
            event_index=6,
            window=0.6,
        )
        self.assertAlmostEqual(change, 0.9)
        self.assertAlmostEqual(straight_after_turn, 0.0)
        self.assertFalse(
            self.rules.is_turning_projection_artifact(
                target_speed=0.08,
                heading_delta=2.73,
                local_heading_change=0.1,
            )
        )

    def test_obstacle_induced_route_deviation_requires_sustained_close_blockage(self):
        self.assertTrue(
            self.rules.is_obstacle_induced_route_deviation(
                stationary_max_duration=3.0,
                stationary_min_distance=8.0,
                lateral_shift=6.6,
                net_heading_change=1.1,
            )
        )
        self.assertFalse(
            self.rules.is_obstacle_induced_route_deviation(
                stationary_max_duration=0.5,
                stationary_min_distance=11.0,
                lateral_shift=23.0,
                net_heading_change=0.33,
            )
        )

    def test_obstacle_induced_route_deviation_accepts_two_nuscenes_keyframes(self):
        self.assertTrue(
            self.rules.is_obstacle_induced_route_deviation(
                stationary_max_duration=0.9,
                stationary_min_distance=8.0,
                lateral_shift=6.6,
                net_heading_change=1.1,
            )
        )
        self.assertFalse(
            self.rules.is_obstacle_induced_route_deviation(
                stationary_max_duration=1.5,
                stationary_min_distance=30.0,
                lateral_shift=14.0,
                net_heading_change=0.35,
            )
        )

    def test_obstacle_induced_route_deviation_allows_early_turn_at_visible_blockage(self):
        self.assertTrue(
            self.rules.is_obstacle_induced_route_deviation(
                stationary_max_duration=0.9,
                stationary_min_distance=21.1,
                lateral_shift=6.6,
                net_heading_change=1.1,
            )
        )

    def test_route_deviation_demand_scales_blockage_ratio(self):
        self.assertEqual(
            self.rules.route_deviation_decision_demand(0.15, True),
            1.0,
        )
        self.assertEqual(
            self.rules.route_deviation_decision_demand(0.15, False),
            0.0,
        )

    def test_route_deviation_context_rejects_normal_intersection_turns(self):
        self.assertFalse(
            self.rules.is_route_deviation_context_supported(
                traffic_light_density=0.8,
                crossing_exposure_ratio=0.0,
                intersection_stop_ratio=0.0,
                left_turn_cross_traffic_ratio=0.0,
            )
        )
        self.assertFalse(
            self.rules.is_route_deviation_context_supported(
                traffic_light_density=0.0,
                crossing_exposure_ratio=0.125,
                intersection_stop_ratio=0.15,
                left_turn_cross_traffic_ratio=0.125,
            )
        )
        self.assertTrue(
            self.rules.is_route_deviation_context_supported(
                traffic_light_density=0.0,
                crossing_exposure_ratio=0.0,
                intersection_stop_ratio=0.0,
                left_turn_cross_traffic_ratio=0.0,
            )
        )

    def test_faster_aligned_side_vehicle_is_overtaking_exposure(self):
        self.assertTrue(
            self.rules.is_overtaking_exposure(
                forward_dist=5.0,
                lateral_dist=4.0,
                obj_forward_speed=9.0,
                ego_speed=6.0,
                heading_aligned=True,
            )
        )

    def test_observed_merge_requires_actual_ego_lane_entry(self):
        self.assertFalse(self.rules.is_observed_merge_relevant(4.0, False))
        self.assertTrue(self.rules.is_observed_merge_relevant(4.0, True))

    def test_observed_path_distance_rejects_distant_future_interaction(self):
        distance = self.rules.synchronized_path_min_distance(
            ego_positions=[(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (5.0, 10.0)],
            ego_timestamps=[0.0, 1.0, 2.0, 3.0],
            actor_positions=[(40.0, 0.0), (35.0, 0.0), (30.0, 0.0), (25.0, 0.0)],
            actor_timestamps=[0.0, 1.0, 2.0, 3.0],
            start_time=0.0,
            horizon=3.0,
        )
        self.assertAlmostEqual(distance, math.sqrt(500.0))

    def test_observed_path_distance_detects_shared_future_point(self):
        distance = self.rules.synchronized_path_min_distance(
            ego_positions=[(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)],
            ego_timestamps=[0.0, 1.0, 2.0],
            actor_positions=[(10.0, 5.0), (10.0, 2.0), (10.0, 0.0)],
            actor_timestamps=[0.0, 1.0, 2.0],
            start_time=0.0,
            horizon=2.0,
        )
        self.assertAlmostEqual(distance, 0.0)

    def test_synchronized_closest_approach_returns_relative_time(self):
        approach = self.rules.synchronized_path_closest_approach(
            ego_positions=[(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)],
            ego_timestamps=[10.0, 11.0, 12.0],
            actor_positions=[(10.0, 5.0), (10.0, 2.0), (10.0, 0.0)],
            actor_timestamps=[10.0, 11.0, 12.0],
            start_time=10.0,
            horizon=2.0,
        )
        self.assertAlmostEqual(approach.distance, 0.0)
        self.assertAlmostEqual(approach.relative_time, 2.0)

    def test_stop_line_types_distinguish_signal_and_non_signal_control(self):
        controls = self.rules.classify_stop_line_controls(
            ["STOP_SIGN", "TURN_STOP"]
        )
        self.assertFalse(controls.traffic_light)
        self.assertTrue(controls.stop_sign)
        self.assertTrue(controls.turn_stop)
        self.assertTrue(controls.non_signalized)

    def test_scene_batch_uses_start_index_and_safe_end_bound(self):
        scenes = list(range(8))
        self.assertEqual(self.rules.select_scene_batch(scenes, 2, 3), [2, 3, 4])
        self.assertEqual(self.rules.select_scene_batch(scenes, 6, 5), [6, 7])
        self.assertEqual(self.rules.select_scene_batch(scenes, 8, 5), [])

    def test_stopped_lead_history_separates_static_and_temporarily_stopped(self):
        split = self.rules.split_stopped_lead_history(
            ["parked", "moving", None, "moving"],
            {"parked": 0.1, "moving": 4.0},
        )
        self.assertEqual(split.static_flags, [True, False, False, False])
        self.assertEqual(split.temporary_flags, [False, True, False, True])

    def test_event_partition_uses_first_stop_time(self):
        partition = self.rules.partition_events_at_time(
            [True, False, True, True],
            [0.0, 1.0, 2.0, 3.0],
            cutoff_time=2.0,
        )
        self.assertEqual(partition.before, [True, False, True, False])
        self.assertEqual(partition.after, [False, False, False, True])

    def test_signed_heading_change_distinguishes_left_and_right(self):
        self.assertGreater(self.rules.signed_net_heading_change([0.0, 0.4, 0.8]), 0)
        self.assertLess(self.rules.signed_net_heading_change([0.0, -0.4, -0.8]), 0)

    def test_lower_ttc_event_keeps_candidate_provenance(self):
        current = {"ttc": 4.0, "token": "old"}
        candidate = {"ttc": 1.5, "token": "new", "category": "vehicle.car"}
        self.assertEqual(
            self.rules.select_lower_ttc_event(current, candidate),
            candidate,
        )

    def test_left_turn_cross_traffic_keeps_exposure_when_conflict_precedes_yield(self):
        flags = self.rules.left_turn_cross_traffic_flags(
            exposure_flags=[True, True, False],
            left_turn=True,
            has_conflict_or_yield=True,
        )
        self.assertEqual(flags, [True, True, False])
        self.assertEqual(
            self.rules.left_turn_cross_traffic_flags(
                [True, True, False],
                left_turn=False,
                has_conflict_or_yield=True,
            ),
            [False, False, False],
        )


if __name__ == "__main__":
    unittest.main()
