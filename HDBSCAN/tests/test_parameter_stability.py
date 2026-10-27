import importlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

import pandas as pd

from HDBSCAN.tests.test_evaluation_split import workspace_tempdir


class ParameterStabilityTest(unittest.TestCase):
    def fixture(self, root):
        """Current-source unit fixture, isolated from immutable historical manifests."""
        import json
        from HDBSCAN.scripts.extraction_audit import ExtractionAudit
        from HDBSCAN.scripts.experiment_partition import file_record, load_partition, write_run_manifest
        scripts = Path(__file__).parents[1] / 'scripts'
        historical = Path(__file__).parents[1] / 'tables/scene_features_development_audit700_20260927.csv'
        source = root / 'synthetic_test_fixture.csv'
        frame = pd.read_csv(historical, float_precision='round_trip')
        frame.to_csv(source, index=False)
        partition = load_partition()
        quality = ExtractionAudit().report(frame)
        quality.update(input=file_record(historical), partition=partition['file'],
                       script=file_record(scripts / 'scene_feature_hdbscan.py'),
                       audit_code=file_record(scripts / 'extraction_audit.py'))
        quality_path = Path(str(source) + '.quality.json')
        quality_path.write_text(json.dumps(quality), encoding='utf-8')
        write_run_manifest(source, 'feature_extraction', historical, frame, partition,
                           scripts / 'scene_feature_hdbscan.py', extra={
                               'unit_test_fixture_only': True,
                               'feature_rules': file_record(scripts / 'scene_feature_rules.py'),
                               'extraction_audit_code': file_record(scripts / 'extraction_audit.py'),
                               'quality_audit': file_record(quality_path)})
        return source

    def api(self):
        self.assertTrue((Path(__file__).parents[1] / 'scripts/parameter_stability.py').exists(),
                        'Bounded parameter study implementation missing')
        return importlib.import_module('HDBSCAN.scripts.parameter_stability')

    def test_exact_approved_search_space(self):
        api = self.api()
        configs = api.configurations()
        self.assertEqual(len(configs), 4)
        self.assertEqual(api.SEEDS, (42, 7, 19, 73, 101))
        self.assertEqual({(r['n_neighbors'], r['min_samples']) for r in configs},
                         {(15, 1), (15, 5), (30, 1), (30, 5)})
        self.assertTrue(all(r['min_cluster_size'] == 20 for r in configs))

    def test_largest_cluster_excludes_noise_but_denominator_is_all_scenes(self):
        api = self.api()
        row = api.cluster_diagnostics(pd.Series([-1, -1, 0, 0, 0, 1]))
        self.assertEqual(row['clusters'], 2)
        self.assertEqual(row['largest_cluster_fraction'], .5)
        self.assertEqual(row['noise_fraction'], 2 / 6)
        self.assertFalse(row['degenerate'])
        for labels in [[-1, -1], [0, 0]]:
            self.assertTrue(api.cluster_diagnostics(pd.Series(labels))['degenerate'])

    def test_preflight_does_not_import_native_libraries_or_create_outputs(self):
        api = self.api()
        with workspace_tempdir() as root:
            source = self.fixture(root)
            out = root / 'study'
            with patch.dict('sys.modules', {'umap': None, 'hdbscan': None}), redirect_stdout(io.StringIO()):
                api.main(['--input', str(source), '--output-dir', str(out), '--preflight'])
            self.assertFalse(out.exists())
            out.mkdir()
            with self.assertRaises(FileExistsError):
                api.main(['--input', str(source), '--output-dir', str(out), '--preflight'])

    def test_full_corpus_is_rejected_not_silently_filtered(self):
        api = self.api()
        source = Path(__file__).parents[1] / 'tables/scene_features.csv'
        with workspace_tempdir() as root, patch.dict('sys.modules', {'umap': None, 'hdbscan': None}):
            with self.assertRaisesRegex(ValueError, 'evaluation'):
                api.main(['--input', str(source), '--output-dir', str(root / 'study'), '--preflight'])

    def test_configuration_summary_requires_all_five_successful_seeds(self):
        api = self.api()
        with self.assertRaises(ValueError):
            api.summarize_configuration({}, [], k=2)

    def test_summary_uses_all_ten_pairs_and_preserves_dominance(self):
        api = self.api()
        frame = pd.DataFrame({'scene_name': ['a', 'b', 'c', 'd'],
                              'cluster': [0, 0, 0, -1], 'corner_score': [1., .8, .4, .2]})
        rows = [dict(seed=s, **api.cluster_diagnostics(frame.cluster)) for s in api.SEEDS]
        summary, pairs = api.summarize_configuration({s: frame for s in api.SEEDS}, rows, k=2)
        self.assertEqual(len(pairs), 10)
        self.assertEqual(summary['ari_all_median'], 1.)
        self.assertEqual(summary['degenerate_runs'], 5)
        self.assertEqual(summary['largest_cluster_fraction_median'], .75)

    def test_failed_fits_cannot_be_summarized_as_complete(self):
        from types import SimpleNamespace
        import numpy as np
        api = self.api()
        reducer_calls, clusterer_calls = [], []
        class Reducer:
            def __init__(self, **kwargs):
                reducer_calls.append(kwargs)
            def fit_transform(self, values):
                return np.zeros((len(values), 2))
        class Clusterer:
            def __init__(self, min_samples, **kwargs):
                clusterer_calls.append(dict(min_samples=min_samples, **kwargs))
                self.fail = min_samples == 5
            def fit(self, values):
                if self.fail:
                    raise ValueError('injected fit failure')
                self.labels_ = np.arange(len(values)) % 2
                self.probabilities_ = np.ones(len(values))
                self.outlier_scores_ = np.zeros(len(values))
                return self
        with workspace_tempdir() as root:
            source = self.fixture(root)
            out = root / 'study'
            with patch.dict('sys.modules', {'umap': SimpleNamespace(UMAP=Reducer),
                                           'hdbscan': SimpleNamespace(HDBSCAN=Clusterer)}), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                    api.main(['--input', str(source), '--output-dir', str(out)])
            import json
            report = json.loads((out / 'summary.json').read_text())
            self.assertEqual(report['status'], 'incomplete')
            self.assertEqual(report['successful_runs'], 10)
            failed = [r for r in report['runs'] if r['run_status'] == 'failed']
            self.assertEqual(len(failed), 10)
            self.assertTrue(all('injected fit failure' in r['error'] for r in failed))
            self.assertIsNone(report['selected_configuration'])
            self.assertEqual(len(reducer_calls), 10)
            self.assertEqual({(r['n_neighbors'], r['random_state']) for r in reducer_calls},
                             {(n, s) for n in (15, 30) for s in api.SEEDS})
            self.assertTrue(all(r['n_components'] == 10 and r['metric'] == 'cosine'
                                and r['min_dist'] == 0.0 for r in reducer_calls))
            self.assertEqual(len(clusterer_calls), 20)
            self.assertEqual(sum(r['min_samples'] == 1 for r in clusterer_calls), 10)
            self.assertTrue(all(r['min_cluster_size'] == 20 and r['prediction_data']
                                for r in clusterer_calls))

    def test_historical_table_is_rejected_after_extraction_source_change(self):
        api = self.api()
        source = Path(__file__).parents[1] / 'tables/scene_features_development_audit700_20260927.csv'
        with workspace_tempdir() as root:
            with self.assertRaisesRegex(ValueError, 'version/provenance'):
                api.main(['--input', str(source), '--output-dir', str(root / 'study'), '--preflight'])
