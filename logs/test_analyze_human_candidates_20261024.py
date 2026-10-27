"""Read-only cause decomposition, not new feature or safety decisions."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "logs/analyze_human_candidates_20261024.py"


class CandidateAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = None
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location("human_cause_analysis", MODULE)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def api(self, name):
        self.assertIsNotNone(self.module, "Analysis not implemented")
        function = getattr(self.module, name, None)
        self.assertTrue(callable(function), name)
        return function

    def test_original_confirmation_conditions_are_separate_not_safety_labels(self):
        reason = self.api("confirmation_reason")
        self.assertEqual(reason(5.0, True), "original_observed_confirmed")
        self.assertEqual(reason(6.0, True), "original_observed_confirmed")
        self.assertEqual(reason(7.0, True), "distance_only_not_met")
        self.assertEqual(reason(5.0, False), "lane_evidence_only_not_met")
        self.assertEqual(reason(7.0, False), "both_original_conditions_not_met")
        self.assertEqual(reason(None, False), "distance_unknown")

    def test_prediction_uses_original_linear_inputs_without_new_gate(self):
        describe = self.api("prediction_details")
        row = dict(forward_m=20, lateral_m=5, forward_speed_mps=0,
                   lateral_speed_mps=-2, ego_speed_mps=5)
        result = describe(row)
        self.assertEqual(result["nominal_overlap_time_s"], 4)
        self.assertEqual(result["predicted_lateral_m"], -3)
        self.assertTrue(result["original_formula_result"])
        self.assertNotIn("safe", result)
        row["ego_speed_mps"] = 0
        self.assertIsNone(describe(row)["nominal_overlap_time_s"])
        self.assertFalse(describe(row)["original_formula_result"])

    def test_anchor_identity_and_raw_flag_mismatch_fail(self):
        analyze = self.api("analyze_scene")
        row = dict(token="a", instance_token="i", category_name="human.pedestrian.adult",
                   index=0, time_s=0, raw_path_candidate=True, forward_m=20, lateral_m=5,
                   forward_speed_mps=0, lateral_speed_mps=-2, ego_speed_mps=5)
        anchor = dict(annotation_token="a", instance_token="i", index=0, time_s=0,
                      closest_distance_m=7, legacy_enters_ego_lane=False,
                      legacy_observed_relevant=False, current_point_layers={"walkway": "w"},
                      future={"ego_available_future_s": 1, "target_available_future_s": .5,
                              "legacy_observed_span_s": .5, "physical_barrier_evidence": "unknown",
                              "future_safety": "not_inferred", "extrapolated": False})
        scene = dict(scene_name="scene-a", human_tracks={"i": [row]}, candidate_anchors=[anchor],
                     frame_flags={"path": [True], "observed": [False]})
        result = analyze(scene)
        self.assertEqual(result[0]["original_reason"], "both_original_conditions_not_met")
        self.assertEqual(result[0]["physical_isolation"], "unknown")
        self.assertFalse(result[0]["safety_label_assigned"])
        anchor["instance_token"] = "j"
        with self.assertRaises(ValueError):
            analyze(scene)

    def test_true_observed_positive_is_not_cleared_by_walkway_or_short_future(self):
        analyze = self.api("analyze_scene")
        row = dict(token="a", instance_token="i", category_name="human.pedestrian.adult",
                   index=0, time_s=0, raw_path_candidate=True, forward_m=20, lateral_m=5,
                   forward_speed_mps=0, lateral_speed_mps=-2, ego_speed_mps=5)
        anchor = dict(annotation_token="a", instance_token="i", index=0, time_s=0,
                      closest_distance_m=5, legacy_enters_ego_lane=True,
                      legacy_observed_relevant=True, current_point_layers={"walkway": "w"},
                      future={"ego_available_future_s": 0, "target_available_future_s": 0,
                              "legacy_observed_span_s": 0, "physical_barrier_evidence": "unknown",
                              "future_safety": "not_inferred", "extrapolated": False})
        scene = dict(scene_name="scene-a", human_tracks={"i": [row]}, candidate_anchors=[anchor],
                     frame_flags={"path": [True], "observed": [True]})
        result = analyze(scene)[0]
        self.assertEqual(result["original_reason"], "original_observed_confirmed")
        self.assertTrue(result["legacy_observed_relevant"])
        self.assertFalse(result["safety_label_assigned"])


if __name__ == "__main__":
    unittest.main()
