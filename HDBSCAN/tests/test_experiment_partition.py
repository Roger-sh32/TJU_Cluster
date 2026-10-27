import json
import io
import os
from pathlib import Path
import runpy
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import pandas as pd

from HDBSCAN.scripts import experiment_partition as guard
from HDBSCAN.scripts.feature_selection import CLUSTERING_FEATURES


class ExperimentPartitionTest(unittest.TestCase):
    def setUp(self):
        self.partition = guard.load_partition()
        self.dev = next(r for r in self.partition['rows'] if r['split'] == 'development')
        self.evaluation = next(r for r in self.partition['rows'] if r['split'] == 'evaluation')

    def frame(self, row):
        return pd.DataFrame([{**{c: 0.0 for c in CLUSTERING_FEATURES},
                              'scene_name': row['scene_name'], 'scene_token': row['scene_token']}])

    def test_current_development_frame_passes(self):
        frame = self.frame(self.dev)
        guard.assert_development_frame(frame, self.partition)
        self.assertEqual(list(guard.current_features(frame)), CLUSTERING_FEATURES)

    def test_mixed_or_evaluation_input_is_rejected_not_filtered(self):
        for frame in [self.frame(self.evaluation), pd.concat([self.frame(self.dev), self.frame(self.evaluation)])]:
            with self.assertRaisesRegex(ValueError, 'evaluation'):
                guard.assert_development_frame(frame, self.partition)

    def test_identity_and_duplicate_checks(self):
        frame = self.frame(self.dev)
        for changed in [frame.assign(scene_token='wrong'), frame.assign(scene_name='scene-9999'),
                        frame.assign(log_token='wrong'), frame.assign(split='evaluation'),
                        pd.concat([frame, frame]), frame.drop(columns='scene_token'), frame.iloc[:0]]:
            with self.assertRaises(ValueError):
                guard.assert_development_frame(changed, self.partition)

    def test_old_schema_and_nonfinite_features_are_rejected(self):
        frame = self.frame(self.dev)
        for changed in [frame.drop(columns=CLUSTERING_FEATURES[-1]),
                        frame.assign(avg_speed=float('inf')), frame.assign(avg_speed='unknown')]:
            with self.assertRaises(ValueError):
                guard.current_features(changed)

    def test_scene_selection_defaults_to_700_and_blocks_named_evaluation(self):
        scenes = [{'name': r['scene_name'], 'token': r['scene_token'], 'log_token': r['log_token']}
                  for r in self.partition['rows']]
        self.assertEqual(len(guard.select_development_scenes(scenes, self.partition)), 700)
        self.assertEqual(len(guard.select_development_scenes(scenes, self.partition, limit=5)), 5)
        for name in [self.evaluation['scene_name'], 'scene-9999']:
            with self.assertRaises(ValueError):
                guard.select_development_scenes(scenes, self.partition, requested=name)

    def test_modified_partition_hash_rejected(self):
        original = guard.file_record
        def altered(path):
            return dict(original(path), sha256='changed')
        with patch.object(guard, 'file_record', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'hash'):
                guard.load_partition()

    def test_existing_output_is_protected(self):
        with self.assertRaises(FileExistsError):
            guard.assert_new_outputs([guard.DEFAULT_SPLIT])

    def test_scoring_rejects_unproven_legacy_cluster_file(self):
        path = guard.DEFAULT_SPLIT.parent / 'scene_features_route_tightening_0051_0100_umap_hdbscan.csv'
        with self.assertRaisesRegex(ValueError, 'provenance'):
            guard.require_fit_provenance(path, pd.read_csv(path), self.partition)

    def test_provenance_roundtrip_and_tampered_output(self):
        from HDBSCAN.tests.test_evaluation_split import workspace_tempdir
        with workspace_tempdir() as root:
            output = root / 'synthetic_clusters.csv'
            frame = self.frame(self.dev).assign(cluster=0, cluster_probability=1.0, cluster_outlier_score=0.0)
            frame.to_csv(output, index=False)
            guard.write_run_manifest(output, 'cluster_fit', guard.DEFAULT_SPLIT, frame,
                                     self.partition, __file__)
            guard.require_fit_provenance(output, frame, self.partition)
            frame.assign(cluster=1).to_csv(output, index=False)
            with self.assertRaisesRegex(ValueError, 'provenance'):
                guard.require_fit_provenance(output, frame, self.partition)

    def test_nonfinite_cluster_evidence_is_rejected(self):
        frame = self.frame(self.dev).assign(cluster=0, cluster_probability=1.0, cluster_outlier_score=float('nan'))
        with self.assertRaises(ValueError):
            guard.validate_cluster_columns(frame)


class EntryPointPreflightTest(unittest.TestCase):
    def run_entry(self, script, **env):
        root = Path(__file__).resolve().parents[2]
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith('SCENE_CLUSTER_')}
        clean_env.update(env)
        output = io.StringIO()
        with patch.dict(os.environ, clean_env, clear=True), \
                patch.object(sys, 'argv', [str(root / script), '--preflight']), \
                patch.object(sys, 'path', [str(root / 'HDBSCAN/scripts'), *sys.path]), \
                patch.dict(sys.modules, {'umap': None, 'hdbscan': None}), redirect_stdout(output):
            runpy.run_path(str(root / script), run_name='__main__')
        return output.getvalue()

    def test_hdbscan_and_grid_preflight_do_not_import_native_fit_libraries(self):
        from HDBSCAN.tests.test_evaluation_split import workspace_tempdir
        from HDBSCAN.tests.test_frozen_model import synthetic_provenance
        from HDBSCAN.scripts.corner_scoring import FROZEN_RISK_INPUTS
        partition = guard.load_partition()
        dev = next(r for r in partition['rows'] if r['split'] == 'development')
        frame = pd.DataFrame([{**{c: 0.0 for c in set(guard.CLUSTERING_FEATURES) | set(FROZEN_RISK_INPUTS)},
                               'scene_name': dev['scene_name'], 'scene_token': dev['scene_token']}])
        with workspace_tempdir() as root:
            source = root / 'synthetic.csv'
            frame.to_csv(source, index=False)
            synthetic_provenance(source, frame, partition)
            for script in ['cluster_umap_hdbscan.py', 'grid_search.py']:
                output = self.run_entry('HDBSCAN/scripts/' + script,
                                       SCENE_CLUSTER_FEATURE_INPUT=str(source))
                self.assertIn('"scene_count": 1', output)
                self.assertIn('"preflight_only": true', output)

    def test_both_fit_entries_reject_full_corpus_before_native_import(self):
        for script in ['cluster_umap_hdbscan.py', 'grid_search.py']:
            with self.assertRaisesRegex(ValueError, 'evaluation'):
                self.run_entry('HDBSCAN/scripts/' + script, SCENE_CLUSTER_FEATURE_INPUT='scene_features.csv')

    def test_kmeans_preflight_and_leak_rejection_before_scaling(self):
        from Kmeans.scripts import kmeans_semantic_baseline as baseline
        tables = guard.DEFAULT_SPLIT.parent
        with patch.object(baseline, 'StandardScaler', side_effect=AssertionError('Unexpected scaler fit')):
            with redirect_stdout(io.StringIO()):
                report = baseline.run_experiment(tables / 'scene_features_review8_20260922.csv', preflight_only=True)
            self.assertEqual(report['scene_count'], 14)
            with self.assertRaisesRegex(ValueError, 'evaluation'):
                baseline.run_experiment(tables / 'scene_features.csv', preflight_only=True)

    def test_extractor_preflight_never_constructs_nuscenes(self):
        with patch('nuscenes.NuScenes', side_effect=AssertionError('Unexpected dataset load')):
            with self.assertRaises(SystemExit) as exit_result:
                self.run_entry('HDBSCAN/scripts/scene_feature_hdbscan.py')
            self.assertEqual(exit_result.exception.code, 0)

    def test_named_evaluation_scene_rejected_before_dataset_load(self):
        evaluation = next(r for r in guard.load_partition()['rows'] if r['split'] == 'evaluation')
        with patch('nuscenes.NuScenes', side_effect=AssertionError('Unexpected dataset load')):
            with self.assertRaisesRegex(ValueError, 'evaluation'):
                self.run_entry('HDBSCAN/scripts/scene_feature_hdbscan.py',
                               SCENE_CLUSTER_SCENE_NAMES=evaluation['scene_name'])

    def test_extractor_rejects_colliding_audit_paths_before_dataset_load(self):
        aliases = ['./audit_collision.csv.quality.json', './audit_collision.csv']
        if os.name == 'nt':
            aliases.append('AUDIT_COLLISION.CSV.QUALITY.JSON')
        with patch('nuscenes.NuScenes', side_effect=AssertionError('Unexpected dataset load')):
            for alias in aliases:
                with self.assertRaisesRegex(ValueError, 'Colliding'):
                    self.run_entry('HDBSCAN/scripts/scene_feature_hdbscan.py',
                                   SCENE_CLUSTER_FEATURE_OUTPUT='audit_collision.csv',
                                   SCENE_CLUSTER_AUDIT_OUTPUT=alias)

    def test_scoring_entry_preflight_with_synthetic_provenance(self):
        from HDBSCAN.tests.test_evaluation_split import workspace_tempdir
        partition = guard.load_partition()
        dev = next(r for r in partition['rows'] if r['split'] == 'development')
        frame = pd.DataFrame([{'scene_name': dev['scene_name'], 'scene_token': dev['scene_token'],
                               'cluster': 0, 'cluster_probability': 1.0, 'cluster_outlier_score': 0.0}])
        with workspace_tempdir() as root:
            output = root / 'synthetic_clusters.csv'
            frame.to_csv(output, index=False)
            guard.write_run_manifest(output, 'cluster_fit', guard.DEFAULT_SPLIT, frame,
                                     partition, __file__)
            text = self.run_entry('HDBSCAN/scripts/corner_case_detection.py',
                                  SCENE_CLUSTER_CLUSTER_INPUT=str(output))
            self.assertIn('"preflight_only": true', text)
            self.assertIn('"stage": "development_scoring"', text)

    def test_grid_metric_failure_is_not_a_zero_score(self):
        import numpy as np
        root = Path(__file__).resolve().parents[1] / 'scripts'
        with patch.object(sys, 'path', [str(root), *sys.path]):
            functions = runpy.run_path(str(root / 'grid_search.py'))
        def failed(*args):
            raise ValueError('diagnostic failure')
        result = functions['evaluate'](np.array([0, 0, 1, 1]), np.zeros((4, 2)), failed)
        self.assertEqual(result['metric_status'], 'failed')
        self.assertTrue(np.isnan(result['dbcv']))
        result = functions['evaluate'](np.array([-1, -1]), np.zeros((2, 2)), failed)
        self.assertEqual(result['metric_status'], 'not_applicable')


if __name__ == '__main__':
    unittest.main()
