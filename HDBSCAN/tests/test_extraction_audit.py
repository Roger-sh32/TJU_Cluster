import importlib
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd


class ExtractionAuditTest(unittest.TestCase):
    def api(self):
        self.assertTrue((Path(__file__).parents[1] / 'scripts/extraction_audit.py').exists(),
                        'Extraction audit implementation missing')
        return importlib.import_module('HDBSCAN.scripts.extraction_audit')

    def test_raw_nonfinite_cells_are_identified_without_mutation(self):
        audit = self.api().ExtractionAudit()
        frame = pd.DataFrame({'scene_name': ['scene-a', 'scene-b', 'scene-c'],
                              'scene_token': ['a', 'b', 'c'],
                              'x': [np.nan, np.inf, -np.inf], 'valid_zero': [0., 0., 0.]})
        original = frame.copy(deep=True)
        report = audit.report(frame)
        pd.testing.assert_frame_equal(frame, original)
        self.assertEqual(report['nonfinite_cell_count'], 3)
        self.assertEqual(report['nonfinite_by_column']['x'], {'nan': 1, 'positive_inf': 1, 'negative_inf': 1})
        self.assertEqual([r['kind'] for r in report['nonfinite_cells']], ['nan', 'positive_inf', 'negative_inf'])
        self.assertEqual([r['scene_token'] for r in report['nonfinite_cells']], ['a', 'b', 'c'])
        json.dumps(report, allow_nan=False)

    def test_error_counts_are_exact_examples_are_bounded(self):
        audit = self.api().ExtractionAudit(example_limit=2)
        for i in range(7):
            audit.record_error({'name': 'scene-a', 'token': 'a'}, 'intersection', ValueError('bad'), i)
        report = audit.report(pd.DataFrame({'scene_name': ['scene-a'], 'scene_token': ['a'], 'x': [0]}))
        self.assertEqual(report['query_exception_count'], 7)
        self.assertEqual(report['query_errors'][0]['count'], 7)
        self.assertEqual(len(report['query_errors'][0]['examples']), 2)
        self.assertEqual(report['nonfinite_cell_count'], 0)
        self.assertFalse(report['observed_checks_clean'])

    def test_clean_frame_is_not_semantic_acceptance(self):
        report = self.api().ExtractionAudit().report(pd.DataFrame(
            {'scene_name': ['scene-a'], 'scene_token': ['a'], 'x': [0]}))
        self.assertTrue(report['observed_checks_clean'])
        self.assertFalse(report['semantic_validity_verified'])

    def test_all_broad_handlers_are_instrumented(self):
        import ast
        tree = ast.parse((Path(__file__).parents[1] / 'scripts/scene_feature_hdbscan.py').read_text(encoding='utf-8'))
        handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)
                    and isinstance(n.type, ast.Name) and n.type.id == 'Exception']
        self.assertGreater(len(handlers), 0)
        for handler in handlers:
            self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                                and n.func.attr == 'record_error' for n in ast.walk(handler)),
                            'Unrecorded handler at line %s' % handler.lineno)
