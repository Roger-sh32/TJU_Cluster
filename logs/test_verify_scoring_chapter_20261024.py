"""Bounded writing checks, not feature/scoring correctness or author approval."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).with_name("verify_scoring_chapter_20261024.py")


class WritingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = None
        if PATH.exists():
            spec = importlib.util.spec_from_file_location("scoring_writing_check", PATH)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def api(self, name):
        self.assertIsNotNone(self.module, "Writing verifier not implemented")
        function = getattr(self.module, name, None)
        self.assertTrue(callable(function), name)
        return function

    def test_document_rejects_missing_unknown_fact_and_unclosed_math(self):
        check = self.api("validate_text")
        facts = [{"id": "P01", "sources": ["C01"]}]
        sources = {"C01": {"path": "source"}}
        self.assertTrue(check("内容【P01】\n$$\nx=1\n$$\n", facts, sources))
        for text in ["内容", "内容【P01】【P99】", "内容【P01】\n$$\nx=1\n"]:
            with self.assertRaises(ValueError):
                check(text, facts, sources)
        with self.assertRaises(ValueError):
            check("内容【P01】", facts, {})
        with self.assertRaises(ValueError):
            check("内容【P01】", facts + facts, sources)

    def test_ast_weights_are_extracted_without_importing_production(self):
        weights = self.api("assignment_weights")
        source = "def f(df):\n    df[column] = 0\n    df['s'] = 0.2 * df['a'] + 0.8 * df['b']\n"
        self.assertEqual(weights(source, "f", "s"), {"a": .2, "b": .8})
        with self.assertRaises(ValueError):
            weights(source, "f", "missing")

    def test_registered_source_values_and_hand_example(self):
        values = self.api("registered_values")()
        self.assertEqual(values["clustering_columns"], 52)
        self.assertEqual(values["frozen_risk_columns"], 33)
        self.assertEqual(values["observed_weights"],
                         {"longitudinal_risk": .35, "interaction_risk": .30,
                          "vru_risk": .25, "ego_response_risk": .10})
        self.assertEqual(values["combined_weights"], {"rarity": .20, "atypical_norm": .25, "risk": .55})
        self.assertEqual(values["risk_addition"], {"observed_risk": 1., "decision_demand": .20})
        self.assertAlmostEqual(values["SYN_score"], .475)
        self.assertAlmostEqual(values["SYN_normalized"], .55)

    def test_refuse_existing_index_and_require_original_digest(self):
        check = self.api("ensure_new")
        self.assertEqual(self.module.REVIEW_STATE["status"], "not_completed_usage_limit")
        self.assertFalse(self.module.REVIEW_STATE["result_received"])
        with self.assertRaises(FileExistsError):
            check(Path(__file__))
        with self.assertRaises(ValueError):
            self.module.verify_index(None)


if __name__ == "__main__":
    unittest.main()
