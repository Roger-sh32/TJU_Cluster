import json
from pathlib import Path
import unittest

from HDBSCAN.tests.test_evaluation_split import workspace_tempdir


class ReadinessContracts(unittest.TestCase):
    def test_synthetic_fixture_never_uses_real_scene_or_expert_ids(self):
        from logs.prepare_experiment_readiness_20261013 import synthetic_demo
        payload = synthetic_demo()
        self.assertTrue(payload['synthetic_only'])
        self.assertFalse(payload['real_evaluation_accessed'])
        self.assertEqual(payload['cohort_size'], 40)
        self.assertTrue(all(i.startswith('SYN') for i in payload['labels']))
        self.assertEqual(payload, synthetic_demo())

    def test_bound_report_refuses_changed_linked_artifact(self):
        from logs.prepare_experiment_readiness_20261013 import bound_summary, record
        with workspace_tempdir() as directory:
            source, summary = directory/'source.json', directory/'summary.json'
            source.write_text('original')
            summary.write_text(json.dumps({'output': record(source)}))
            bound_summary(summary, ['output'])
            source.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'hash'):
                bound_summary(summary, ['output'])

    def test_output_scope_refuses_outside_deliverables(self):
        from logs.prepare_experiment_readiness_20261013 import validate_destination, ROOT
        with self.assertRaises(ValueError):
            validate_destination(ROOT/'nuScenes')
        validate_destination(ROOT/'outputs/实验准备/synthetic')

    def test_altered_packet_seal_is_refused_before_reading_payload(self):
        from logs import prepare_experiment_readiness_20261013 as recipe
        from unittest.mock import patch
        with workspace_tempdir() as directory:
            manifest = directory/'manifest.json'
            manifest.write_text('{}')
            original = recipe.record(manifest)['sha256']
            manifest.write_text('{"changed":true}')
            with patch.object(recipe, 'validate_destination', return_value=directory):
                with self.assertRaisesRegex(ValueError, 'manifest hash'):
                    recipe.check_packet(directory, original)

    def test_existing_packet_is_refused_without_overwrite(self):
        from logs import prepare_experiment_readiness_20261013 as recipe
        from unittest.mock import patch
        with workspace_tempdir() as directory:
            marker = directory/'preserved.txt'
            marker.write_text('keep')
            with patch.object(recipe, 'validate_destination', return_value=directory), \
                    patch.object(recipe.sys, 'argv', ['recipe','--synthetic-demo']):
                with self.assertRaises(FileExistsError):
                    recipe.main()
            self.assertEqual(marker.read_text(), 'keep')

    def test_recorded_runtime_mismatch_is_refused_before_replay(self):
        from logs import prepare_experiment_readiness_20261013 as recipe
        from unittest.mock import patch
        with workspace_tempdir() as directory:
            path = directory/'manifest.json'
            path.write_text(json.dumps({'python':'incompatible', 'executable':recipe.record(recipe.sys.executable),
                                        'inputs':[], 'outputs':[]}))
            seal = recipe.record(path)['sha256']
            with patch.object(recipe, 'validate_destination', return_value=directory):
                with self.assertRaisesRegex(ValueError, 'runtime'):
                    recipe.check_packet(directory, seal)


if __name__ == '__main__':
    unittest.main()
