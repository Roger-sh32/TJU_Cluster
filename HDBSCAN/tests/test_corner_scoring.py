import unittest

import pandas as pd


def score_row(**overrides):
    from HDBSCAN.scripts.corner_scoring import calculate_grouped_risk

    values = {
        "min_ttc": 30.0,
        "ttc_valid_ratio": 0.0,
        "dangerous_ttc_frame_ratio": 0.0,
        "dangerous_ttc_max_duration": 0.0,
        "close_following_ratio": 0.0,
        "merge_conflict_ratio": 0.0,
        "merge_max_duration": 0.0,
        "crossing_vehicle_exposure_ratio": 0.0,
        "crossing_vehicle_conflict_ratio": 0.0,
        "crossing_conflict_max_duration": 0.0,
        "vru_path_conflict_ratio": 0.0,
        "vru_conflict_max_duration": 0.0,
        "ego_hard_brake_ratio": 0.0,
        "ego_decel_min": 0.0,
        "intersection_stop_ratio": 0.0,
    }
    values.update(overrides)
    return calculate_grouped_risk(pd.DataFrame([values])).iloc[0]


class CornerScoringTest(unittest.TestCase):
    def test_uncontrolled_yield_preserves_approach_conflict_when_ego_stops_safely(self):
        result = score_row(crossing_vehicle_conflict_ratio=0.2,
                           crossing_conflict_max_duration=3.0,
                           crossing_route_conflict_ratio=0.0,
                           crossing_route_conflict_max_duration=0.0,
                           stop_sign_stop_candidate=0)
        self.assertGreater(result.interaction_risk, 0.0)

    def test_side_entry_exposure_adds_decision_value_without_claiming_observed_merge(self):
        result = score_row(side_entry_candidate_ratio=0.2)
        self.assertEqual(result.interaction_risk, 0.0)
        self.assertGreater(result.decision_demand, 0.0)
        self.assertLessEqual(result.decision_demand, 0.3)

    def test_stop_sign_without_route_conflict_preserves_uncertain_approach_risk(self):
        result = score_row(
            crossing_vehicle_exposure_ratio=0.6,
            crossing_vehicle_conflict_ratio=0.2,
            crossing_conflict_max_duration=3.0,
            crossing_route_conflict_ratio=0.0,
            crossing_route_conflict_max_duration=0.0,
            non_signalized_intersection_density=0.8,
            stop_sign_stop_candidate=1,
            ego_stop_from_motion_flag=1,
        )
        self.assertGreater(result.interaction_risk, 0.0)
        self.assertGreater(result.decision_demand, 0.0)
        self.assertLessEqual(result.decision_demand, 0.4)

    def test_stop_sign_does_not_suppress_left_turn_gap_selection(self):
        result = score_row(
            crossing_vehicle_exposure_ratio=0.125,
            crossing_route_conflict_ratio=0.0,
            non_signalized_intersection_density=0.8,
            stop_sign_stop_candidate=1,
            ego_stop_from_motion_flag=1,
            left_turn_cross_traffic_interaction_ratio=0.125,
        )
        self.assertAlmostEqual(result.decision_demand, 0.3125)

    def test_stop_sign_does_not_remove_confirmed_route_conflict(self):
        result = score_row(
            crossing_vehicle_exposure_ratio=0.6,
            crossing_route_conflict_ratio=0.2,
            crossing_route_conflict_max_duration=3.0,
            non_signalized_intersection_density=0.8,
            stop_sign_stop_candidate=1,
        )
        self.assertGreater(result.interaction_risk, 0.0)
        self.assertGreater(result.decision_demand, 0.4)

    def test_observed_intrusion_contributes_even_without_instantaneous_merge(self):
        result = score_row(adjacent_lane_intrusion_ratio=0.1,
                           adjacent_lane_intrusion_max_duration=1.5)
        self.assertGreater(result.interaction_risk, 0.0)

    def test_no_valid_ttc_is_not_longitudinal_risk(self):
        result = score_row(min_ttc=0.5, ttc_valid_ratio=0.0)
        self.assertEqual(result.longitudinal_risk, 0.0)
        self.assertEqual(result.risk, 0.0)

    def test_ttc_above_three_seconds_is_not_critical(self):
        result = score_row(min_ttc=6.0, ttc_valid_ratio=0.5)
        self.assertEqual(result.longitudinal_risk, 0.0)

    def test_red_light_cross_traffic_exposure_alone_is_not_risk(self):
        result = score_row(
            crossing_vehicle_exposure_ratio=1.0,
            crossing_vehicle_conflict_ratio=0.0,
            intersection_stop_ratio=1.0,
        )
        self.assertEqual(result.interaction_risk, 0.0)
        self.assertEqual(result.risk, 0.0)

    def test_sustained_vru_conflict_is_high_risk(self):
        result = score_row(
            vru_path_conflict_ratio=0.25,
            vru_conflict_max_duration=2.0,
        )
        self.assertGreaterEqual(result.vru_risk, 0.9)
        self.assertGreater(result.risk, 0.2)

    def test_observed_vru_relevance_overrides_distant_predicted_conflict(self):
        result = score_row(
            vru_path_conflict_ratio=0.25,
            vru_conflict_max_duration=2.0,
            vru_observed_relevance_ratio=0.0,
            vru_observed_max_duration=0.0,
        )
        self.assertEqual(result.vru_risk, 0.0)

    def test_sustained_vru_relevance_overrides_single_frame_observed_proximity(self):
        result = score_row(
            vru_observed_relevance_ratio=0.025,
            vru_observed_max_duration=0.5,
            vru_sustained_relevance_ratio=0.0,
            vru_sustained_max_duration=0.0,
        )
        self.assertEqual(result.vru_risk, 0.0)

    def test_sustained_merge_conflict_is_high_interaction_risk(self):
        result = score_row(
            merge_conflict_ratio=0.25,
            merge_max_duration=2.0,
        )
        self.assertGreaterEqual(result.interaction_risk, 0.9)

    def test_unobserved_merge_prediction_does_not_create_interaction_risk(self):
        result = score_row(
            merge_conflict_ratio=0.20,
            merge_max_duration=2.0,
            merge_observed_relevance_ratio=0.0,
        )
        self.assertEqual(result.interaction_risk, 0.0)

    def test_left_turn_cross_traffic_is_not_double_counted_as_merge_risk(self):
        result = score_row(
            merge_conflict_ratio=0.20,
            merge_max_duration=2.0,
            merge_observed_relevance_ratio=0.20,
            left_turn_cross_traffic_interaction_ratio=0.20,
            crossing_vehicle_conflict_ratio=0.0,
        )
        self.assertEqual(result.interaction_risk, 0.0)

    def test_signalized_initial_queue_attenuates_close_following_risk(self):
        queue = score_row(
            close_following_ratio=0.25,
            ego_stopped_at_scene_start=1.0,
            traffic_light_control_density=1.0,
        )
        moving = score_row(
            close_following_ratio=0.25,
            ego_stopped_at_scene_start=0.0,
            traffic_light_control_density=0.0,
        )
        self.assertLess(queue.longitudinal_risk, moving.longitudinal_risk)
        self.assertLessEqual(queue.longitudinal_risk, 0.03)

    def test_planned_intersection_stop_attenuates_lateral_risk(self):
        moving = score_row(
            crossing_vehicle_conflict_ratio=0.20,
            crossing_conflict_max_duration=2.0,
        )
        yielding = score_row(
            crossing_vehicle_conflict_ratio=0.20,
            crossing_conflict_max_duration=2.0,
            intersection_stop_ratio=0.40,
        )
        self.assertGreater(moving.interaction_risk, yielding.interaction_risk)
        self.assertLessEqual(yielding.interaction_risk, 0.25)

    def test_stop_after_moving_reduces_observed_conflict_but_keeps_decision_demand(self):
        result = score_row(
            crossing_vehicle_conflict_ratio=0.20,
            crossing_conflict_max_duration=2.0,
            crossing_vehicle_exposure_ratio=0.60,
            intersection_stop_ratio=0.40,
            ego_stopped_at_scene_start=0.0,
            ego_stop_from_motion_flag=1.0,
            non_signalized_intersection_density=1.0,
        )
        self.assertLessEqual(result.interaction_risk, 0.25)
        self.assertGreaterEqual(result.decision_demand, 0.9)
        self.assertGreater(result.risk, result.observed_risk)

    def test_non_signalized_intersection_keeps_decision_demand_when_initially_stopped(self):
        result = score_row(
            ego_stopped_at_scene_start=1.0,
            non_signalized_intersection_density=1.0,
            crossing_vehicle_exposure_ratio=0.6,
            vru_crossing_exposure_ratio=0.6,
        )
        self.assertGreaterEqual(result.decision_demand, 0.35)
        self.assertGreater(result.risk, 0.0)

    def test_moving_approach_has_more_decision_demand_than_initial_stop(self):
        stopped = score_row(
            ego_stopped_at_scene_start=1.0,
            non_signalized_intersection_density=1.0,
            crossing_vehicle_exposure_ratio=0.6,
        )
        moving = score_row(
            ego_stopped_at_scene_start=0.0,
            non_signalized_intersection_density=1.0,
            crossing_vehicle_exposure_ratio=0.6,
        )
        self.assertGreater(moving.decision_demand, stopped.decision_demand)
        self.assertGreater(moving.risk, stopped.risk)

    def test_traffic_light_suppresses_non_signalized_decision_demand(self):
        unsignalized = score_row(
            ego_stopped_at_scene_start=0.0,
            non_signalized_intersection_density=0.4,
            traffic_light_control_density=0.0,
            crossing_vehicle_exposure_ratio=0.6,
        )
        signalized = score_row(
            ego_stopped_at_scene_start=0.0,
            non_signalized_intersection_density=0.4,
            traffic_light_control_density=0.5,
            crossing_vehicle_exposure_ratio=0.6,
        )
        self.assertLess(signalized.decision_demand, unsignalized.decision_demand)
        self.assertLessEqual(signalized.decision_demand, 0.25)

    def test_route_deviation_demand_preserves_blocked_path_decision_value(self):
        result = score_row(route_deviation_decision_demand=0.8)
        self.assertEqual(result.decision_demand, 0.8)
        self.assertAlmostEqual(result.risk, 0.16)


if __name__ == "__main__":
    unittest.main()
