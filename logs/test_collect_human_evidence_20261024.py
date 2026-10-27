"""Contracts for an append-only development human-evidence collector."""

import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "logs/collect_human_evidence_20261024.py"


class HumanEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = None
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location("human_evidence", MODULE)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def api(self, name):
        self.assertIsNotNone(self.module, "Evidence collector is not implemented")
        function = getattr(self.module, name, None)
        self.assertTrue(callable(function), f"Missing {name}")
        return function

    def test_stream_accepts_small_chunks_and_rejects_malformed_arrays(self):
        reader = self.api("iter_records")
        self.assertEqual(list(reader(io.StringIO('[{"x":1},{"x":2}]'), 3)),
                         [{"x": 1}, {"x": 2}])
        self.assertEqual(list(reader(io.StringIO("[]"), 1)), [])
        for text in ['[{},]', '[{} {}]', '[{}', '[{}] trailing', '{}']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                list(reader(io.StringIO(text), 2))

    def test_scope_refuses_evaluation_duplicate_or_changed_members(self):
        check = self.api("validate_scope")
        names = ["scene-a", "scene-b"]
        rows = [{"scene_name": n, "scene_token": n + "-t"} for n in names]
        partition = {r["scene_name"]: {**r, "split": "development"} for r in rows}
        self.assertEqual(check(names, rows, partition, expected_size=2), names)
        for bad in [rows + [rows[0]], [rows[0]], [{**rows[0], "scene_token": "bad"}, rows[1]]]:
            with self.assertRaises(ValueError):
                check(names, bad, partition, expected_size=2)
        partition["scene-b"]["split"] = "evaluation"
        with self.assertRaises(ValueError):
            check(names, rows, partition, expected_size=2)

    def test_only_selected_humans_retained_before_geometry_access(self):
        select = self.api("select_humans")
        human = dict(token="h", sample_token="s", instance_token="i", prev="", next="",
                     translation=[2, 1, 0], rotation=[1, 0, 0, 0], size=[1, 1, 2])
        ignored = {"token": "outside", "sample_token": "other"}
        bike = dict(human, token="bike", instance_token="b", translation="INVALID")
        result = select([ignored, bike, human], {"s": "scene-a"},
                        {"i": "human.pedestrian.adult", "b": "vehicle.bicycle"})
        self.assertEqual(list(result), ["h"])
        self.assertEqual(result["h"]["category_name"], "human.pedestrian.adult")
        with self.assertRaises(ValueError):
            select([human, human], {"s": "scene-a"}, {"i": "human.pedestrian.adult"})
        with self.assertRaises(ValueError):
            select([human], {"s": "scene-a"}, {})

    def test_human_chain_cannot_cross_scene_or_drop_next(self):
        validate = self.api("validate_human_chains")
        one = dict(token="a", sample_token="s0", instance_token="i", prev="", next="b")
        two = dict(token="b", sample_token="s1", instance_token="i", prev="a", next="")
        samples = {"s0": {"scene_token": "X", "timestamp": 0},
                   "s1": {"scene_token": "X", "timestamp": 500000}}
        validate({"a": one, "b": two}, samples)
        with self.assertRaises(ValueError):
            validate({"a": one}, samples)
        samples["s1"]["scene_token"] = "Y"
        with self.assertRaises(ValueError):
            validate({"a": one, "b": two}, samples)

    def test_future_keeps_legacy_window_and_real_bracket_without_extrapolation(self):
        window = self.api("future_window")
        samples = {f"s{i}": {"timestamp": int(t * 1e6), "index": i}
                   for i, t in enumerate([0, 0.5, 1.1, 1.6])}
        anns = {str(i): dict(token=str(i), sample_token=f"s{i}", instance_token="i",
                            next=str(i + 1) if i < 3 else "")
                for i in range(4)}
        used, facts = window(anns["0"], anns, samples, 1.0, ego_end_us=1600000)
        self.assertEqual([a["token"] for a in used], ["0", "1"])
        self.assertEqual(facts["first_beyond_horizon_token"], "2")
        self.assertEqual(facts["legacy_observed_span_s"], 0.5)
        self.assertFalse(facts["extrapolated"])
        used, facts = window(anns["3"], anns, samples, 1.0, ego_end_us=1600000)
        self.assertEqual(len(used), 1)
        self.assertEqual(facts["ego_available_future_s"], 0)
        self.assertEqual(facts["target_available_future_s"], 0)

    def test_outputs_refuse_existing_file(self):
        check = self.api("ensure_new")
        path = Path(__file__)
        before = path.read_bytes()
        check([ROOT / "logs/human_evidence_unit_never_created.json"])
        with self.assertRaises(FileExistsError):
            check([path])
        self.assertEqual(path.read_bytes(), before)

    def test_summary_counts_candidate_frames_not_target_count(self):
        summarize = self.api("summarize_human_flags")
        flags = {key: [False] * 3 for key in
                 ("nearby", "front", "path", "crossing", "same_lane",
                  "same_direction", "observed", "crosswalk", "crosswalk_nearby")}
        flags["path"] = [True, True, False]
        flags["front"] = [True, True, True]
        flags["crosswalk"] = [True, False, False]
        values = summarize(flags, [0, .5, 1.], 2.5, .5, [False] * 3, False)
        self.assertEqual(values["vru_path_conflict_ratio"], 2 / 3)
        self.assertEqual(values["vru_conflict_event_count"], 1)
        self.assertEqual(values["vru_crosswalk_conflict_ratio"], 1 / 3)
        self.assertEqual(values["vru_observed_min_distance"], 2.5)
        self.assertEqual(values["vru_observed_relevance_ratio"], 0)

    def test_original_helpers_preserve_velocity_and_do_not_execute_main(self):
        helpers = self.api("load_helpers")()
        tables = self.module.SelectedTables(
            {"s0": {"timestamp": 0}, "s1": {"timestamp": 500000}},
            {"a": dict(sample_token="s0", translation=[0, 0, 0], prev="", next="b"),
             "b": dict(sample_token="s1", translation=[1, 0, 0], prev="a", next="")})
        function = helpers["compute_ann_velocity_xy"]
        self.assertEqual(function(tables, tables.get("sample_annotation", "a")), (2, 0))
        self.assertEqual(function(tables, tables.get("sample_annotation", "b")), (2, 0))
        self.assertEqual(function(tables, dict(sample_token="s0", prev="", next="",
                                               translation=[1, 0, 0])), (0, 0))
        self.assertEqual({k for k in helpers if callable(helpers[k])} & self.module.HELPERS,
                         self.module.HELPERS)
        self.assertNotIn("nusc", helpers)

    def test_positive_and_empty_human_replay_keeps_censored_candidates(self):
        collect = self.api("collect_scene")

        class Map:
            def get_records_in_radius(self, x, y, radius, layers):
                return {"ped_crossing": ["crosswalk"]}

            def get_closest_lane(self, x, y, radius):
                return "lane"

            def discretize_lanes(self, tokens, resolution):
                return {"lane": [(i, 0, 0) for i in range(21)]}

            def layers_on_point(self, x, y, layers):
                return {layer: "" for layer in layers}

        track = dict(scene_name="scene-a", scene_token="X", times=[0, .5, 1],
                     ego_positions=[[0, 0], [2.5, 0], [5, 0]], ego_yaws=[0] * 3,
                     ego_speeds=[0, 5, 5], static_obstacle_flags=[False] * 3)
        samples = {f"s{i}": dict(token=f"s{i}", scene_token="X", timestamp=i * 500000, index=i)
                   for i in range(3)}
        humans = {str(i): dict(token=str(i), sample_token=f"s{i}", instance_token="i",
                               category_name="human.pedestrian.adult",
                               prev=str(i - 1) if i else "", next=str(i + 1) if i < 2 else "",
                               translation=[10, y, 0], rotation=[1, 0, 0, 0], size=[1, 1, 2])
                  for i, y in enumerate([4, 2.5, 1])}
        result = collect(track, {"ego_evasive_lane_change_flag": "0"}, samples, humans,
                         Map(), self.module.load_helpers())
        self.assertEqual(result["frame_flags"]["path"], [False, True, True])
        self.assertEqual(result["frame_flags"]["observed"], [False, True, True])
        self.assertEqual(len(result["candidate_anchors"]), 2)
        self.assertEqual(result["candidate_anchors"][-1]["future"]["ego_available_future_s"], 0)
        self.assertEqual(result["candidate_anchors"][-1]["physical_isolation"], "unknown")
        empty = collect(track, {"ego_evasive_lane_change_flag": "0"}, samples, {},
                        Map(), self.module.load_helpers())
        self.assertEqual(empty["human_tracks"], {})
        self.assertEqual(empty["legacy_vru_reproduction"]["vru_path_conflict_ratio"], 0)
        self.assertTrue(empty["minimum_is_no_candidate_fill"])
        self.assertEqual(empty["legacy_vru_reproduction"]["vru_observed_min_distance"], 30)

    def test_compare_rejects_changed_summary_and_check_requires_original_digest(self):
        compare = self.api("compare_baseline")
        scene = {"scene_name": "scene-a", "legacy_vru_reproduction": {"vru": .5}}
        self.assertEqual(compare(scene, {"vru": ".5"}, {"vru": ".5"}, ["vru"]), [])
        self.assertEqual(len(compare(scene, {"vru": ".4"}, {"vru": ".4"}, ["vru"])), 2)
        with self.assertRaises(ValueError):
            self.module.check_only(None)

    def test_raw_instance_endpoints_cannot_point_to_another_human(self):
        load = self.api("selected_metadata")
        track = dict(scene_name="scene-a", scene_token="X", times=[0], ego_positions=[[0, 0]],
                     ego_yaws=[0], ego_speeds=[0], static_obstacle_flags=[False])
        scene = dict(token="X", name="scene-a", log_token="L", first_sample_token="s",
                     last_sample_token="s", nbr_samples=1)
        sample = dict(token="s", scene_token="X", timestamp=0, prev="", next="")
        anns = [dict(token=token, sample_token="s", instance_token=instance, prev="", next="",
                     translation=[1, 1, 0], rotation=[1, 0, 0, 0], size=[1, 1, 2])
                for token, instance in (("a", "i"), ("b", "j"))]
        instances = [dict(token=instance, category_token="c", nbr_annotations=1,
                          first_annotation_token=token, last_annotation_token=token)
                     for token, instance in (("a", "i"), ("b", "j"))]
        tables = {"scene": [scene], "sample": [sample], "sample_annotation": anns,
                  "instance": instances, "category": [dict(token="c", name="human.pedestrian.adult")]}
        part = {"scene-a": dict(scene_token="X", log_token="L")}
        with patch.object(self.module, "table_records", side_effect=lambda key: iter(tables[key])):
            self.assertEqual(len(load(part, [track])[1]), 2)
            instances[0]["first_annotation_token"] = "b"
            instances[0]["last_annotation_token"] = "b"
            with self.assertRaises(ValueError):
                load(part, [track])


if __name__ == "__main__":
    unittest.main()
