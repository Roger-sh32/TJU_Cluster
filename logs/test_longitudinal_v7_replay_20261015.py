import importlib.util
import unittest
import json
from pathlib import Path
from contextlib import contextmanager
from uuid import uuid4
from unittest.mock import patch


class ReplayContracts(unittest.TestCase):
    @contextmanager
    def scratch(self, module):
        # Windows sandbox cannot reopen tempfile's owner-only mode0700 folders.
        root = module.ROOT/'logs'/('longitudinal_test_'+uuid4().hex)
        root.mkdir()
        try:
            yield root
        finally:
            for path in root.iterdir():
                path.unlink()
            root.rmdir()

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('logs.longitudinal_v7_replay_20261015'))
        from logs import longitudinal_v7_replay_20261015
        return longitudinal_v7_replay_20261015

    def test_baseline_difference_is_not_silently_tolerated(self):
        m = self.module()
        self.assertEqual(m.field_differences({'x': 1.}, {'x': 1.}), [])
        self.assertEqual(len(m.field_differences({'x': 1.}, {'x': 1.+1e-14})), 1)

    def test_mismatched_static_trace_stops_before_gate(self):
        m = self.module()
        with self.assertRaisesRegex(ValueError, 'Baseline'):
            m.require_baseline({'passed': False})

    def test_new_evasion_dependency_is_not_published_with_stale_vru(self):
        m = self.module()
        with self.assertRaisesRegex(ValueError, 'dependency'):
            m.check_dependencies({'ego_evasive_lane_change_flag': 0},
                                 {'ego_evasive_lane_change_flag': 1}, {}, {})

    def test_existing_evasion_cannot_change_first_obstacle(self):
        m = self.module()
        with self.assertRaisesRegex(ValueError, 'dependency'):
            m.check_dependencies({'ego_evasive_lane_change_flag': 1},
                                 {'ego_evasive_lane_change_flag': 1},
                                 {'first_static_index': 1}, {'first_static_index': 2})

    def test_unrelated_column_change_is_rejected(self):
        m = self.module()
        import pandas as pd
        a = pd.DataFrame([dict(scene_name='SYN-1', scene_token='syn1', vru_conflict_ratio=0.)])
        b = a.copy()
        b.at[0, 'vru_conflict_ratio'] = 1.
        with self.assertRaisesRegex(ValueError, 'Unrelated'):
            m.compare_frames(b, a)

    def test_exclusive_run_claim_does_not_overwrite_first_owner(self):
        m = self.module()
        self.assertIsNotNone(getattr(m, 'claim_run', None))
        with self.scratch(m) as d:
            path = Path(d)/'claim.json'
            with patch.object(m, 'CLAIM', path):
                m.claim_run({'protocol': {'sha256': 'original'}})
                before = path.read_bytes()
                with self.assertRaises(FileExistsError):
                    m.claim_run({'protocol': {'sha256': 'another'}})
                self.assertEqual(path.read_bytes(), before)

    def test_failed_baseline_prevents_gate_and_feature_publication(self):
        m = self.module()
        with self.scratch(m) as d:
            root = Path(d)
            proof = {'passed': False, 'mismatches': ['synthetic drift']}
            with patch.multiple(m, CLAIM=root/'claim.json', STATUS=root/'status.json',
                                BASELINE=root/'baseline.json', FEATURES=root/'features.csv',
                                OUTPUTS=[root/'baseline.json', root/'features.csv']), \
                    patch.object(m, 'load_protocol', return_value=({}, {'phase': 'prepared', 'protocol': {}})), \
                    patch.object(m, 'baseline', return_value=(None, None, proof)), \
                    patch.object(m, 'candidate') as gate:
                with self.assertRaisesRegex(ValueError, 'Baseline'):
                    m.run('synthetic')
                gate.assert_not_called()
                self.assertFalse((root/'features.csv').exists())
                self.assertEqual(json.loads((root/'status.json').read_text())['phase'],
                                 'failed_requires_inspection')


if __name__ == '__main__':
    unittest.main()
