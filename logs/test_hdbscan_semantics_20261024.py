"""SYN-only semantic checks; no scene data or estimator fit."""
import ast
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).with_name("hdbscan_semantics_20261024.py")


class SemanticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = None
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location("hdbscan_semantics", MODULE)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def api(self, name):
        self.assertIsNotNone(self.module, "Semantic probe not implemented")
        function = getattr(self.module, name, None)
        self.assertTrue(callable(function), name)
        return function

    def test_hand_stability_uses_birth_and_child_size(self):
        compute = self.api("hand_stability")
        self.assertEqual(compute([(5, 4, .5, 1), (5, 6, 1, 2), (5, 7, 1, 2),
                                  (6, 0, 2, 1), (6, 1, 4, 1),
                                  (7, 2, 2, 1), (7, 3, 2, 1)]), {5: 4.5, 6: 4., 7: 2.})
        with self.assertRaises(ValueError):
            compute([(2, 3, 2, 2), (3, 0, 1, 1), (3, 1, 3, 1)])

    def test_original_digest_is_required_and_mismatch_rejected(self):
        verify = self.api("verify")
        with self.assertRaises(ValueError):
            verify({"path": str(__file__), "sha256": "0" * 64})

    def test_native_synthetic_counterexample_and_eom_leaf(self):
        result = self.api("synthetic_cases")()
        dense = result["SYN-DENSE"]
        self.assertEqual(dense["native"], [[1., 1., 4.], [1., 1., 3.], [4., 3., 3.]])
        self.assertEqual(dense["native"], dense["hand"])
        noise = result["SYN-NOISE"]
        self.assertEqual(noise["labels"][-1], -1)
        self.assertEqual(noise["membership"][-1], 0)
        self.assertNotEqual(noise["membership"][-1], 1 - noise["outlier"][-1])
        self.assertEqual(noise["native_stability"], noise["hand_stability"])
        nested = result["SYN-EOM-LEAF"]
        self.assertEqual(nested["eom"]["labels"], [0, 0, 0, 0, 0, 1, 1])
        self.assertEqual(nested["leaf"]["labels"], [-1, 1, 1, 2, 2, 0, 0])
        self.assertEqual(nested["eom"]["membership"][0], 1)
        self.assertEqual(nested["leaf"]["membership"][0], 0)

    def test_probe_has_no_estimator_fit_or_scene_loading(self):
        self.api("synthetic_cases")
        tree = ast.parse(MODULE.read_text(encoding="utf8"))
        forbidden = {"fit", "fit_predict", "fit_transform", "load_development_features",
                     "NuScenes", "read_csv", "read_pickle", "load_model"}
        called = {node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
                  for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and isinstance(node.func, (ast.Name, ast.Attribute))}
        self.assertFalse(called & forbidden, called & forbidden)


if __name__ == "__main__":
    unittest.main()
