import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import hdbscan

from HDBSCAN.scripts import corner_scoring, experiment_partition as guard
from HDBSCAN.tests.test_evaluation_split import workspace_tempdir


class RecordedProjection:
    """Test-only fitted transformer; no dependency on the host BLAS runtime."""
    def fit(self, values):
        self._raw_data = values.copy()
        self.embedding_ = values[:, :2].copy()
        return self

    def transform(self, values):
        return values[:, :2].copy()


def synthetic_provenance(path, frame, partition):
    scripts = Path(__file__).parents[1] / 'scripts'
    guard.write_run_manifest(path, 'synthetic_features', path, frame, partition,
                             scripts / 'scene_feature_hdbscan.py',
                             extra={'feature_rules': guard.file_record(scripts / 'scene_feature_rules.py')})


class FrozenScoringTest(unittest.TestCase):
    def test_reference_is_fixed_across_prediction_batches(self):
        self.assertTrue(hasattr(corner_scoring, 'fit_score_reference'))
        train = pd.DataFrame({'cluster': [0, 0, 0, 1],
                              'cluster_outlier_score': [0.1, 0.2, 0.3, 0.4]})
        reference = corner_scoring.fit_score_reference(train)
        query = pd.DataFrame({'cluster': [1, -1, 0],
                              'cluster_outlier_score': [0.5, 0.8, 0.0]})
        whole = corner_scoring.calculate_frozen_corner_scores(query, reference)
        singles = pd.concat([corner_scoring.calculate_frozen_corner_scores(query.iloc[[i]], reference)
                             for i in range(len(query))])
        pd.testing.assert_frame_equal(whole, singles)
        np.testing.assert_allclose(whole.rarity, [0.75, 0.75, 0.25])
        self.assertTrue(whole.corner_score_norm.between(0, 1).all())

    def test_unknown_cluster_is_not_silently_treated_as_rare(self):
        self.assertTrue(hasattr(corner_scoring, 'fit_score_reference'))
        train = pd.DataFrame({'cluster': [0, 0], 'cluster_outlier_score': [0.0, 0.2]})
        with self.assertRaisesRegex(ValueError, 'Unknown cluster'):
            corner_scoring.calculate_frozen_corner_scores(train.assign(cluster=4),
                                                         corner_scoring.fit_score_reference(train))


class FrozenModelTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).parents[1] / 'scripts/frozen_model.py').exists(),
                        'Frozen model implementation is missing')
        self.api = importlib.import_module('HDBSCAN.scripts.frozen_model')
        self.partition = guard.load_partition()
        dev = [r for r in self.partition['rows'] if r['split'] == 'development']
        rng = np.random.RandomState(12)
        values = np.r_[rng.normal(-3, .1, (20, 52)), rng.normal(3, .1, (20, 52))]
        self.raw = pd.DataFrame(values, columns=guard.CLUSTERING_FEATURES)
        for column in getattr(corner_scoring, 'FROZEN_RISK_INPUTS', ['min_ttc', 'ttc_valid_ratio']):
            if column not in self.raw:
                self.raw[column] = 0.0
        self.raw['min_ttc'] = 30.0
        self.raw['scene_name'] = [r['scene_name'] for r in dev[:40]]
        self.raw['scene_token'] = [r['scene_token'] for r in dev[:40]]
        self.query = self.raw.iloc[:2].copy()
        self.query['scene_name'] = [r['scene_name'] for r in dev[40:42]]
        self.query['scene_token'] = [r['scene_token'] for r in dev[40:42]]
        self.scaler = StandardScaler().fit(guard.current_features(self.raw))
        self.reducer = RecordedProjection().fit(self.scaler.transform(guard.current_features(self.raw)))
        embedded = self.reducer.transform(self.scaler.transform(guard.current_features(self.raw)))
        self.clusterer = hdbscan.HDBSCAN(min_cluster_size=5, prediction_data=True).fit(embedded)
        self.clustered = self.raw.assign(cluster=self.clusterer.labels_,
                                         cluster_probability=self.clusterer.probabilities_,
                                         cluster_outlier_score=self.clusterer.outlier_scores_)

    def save(self, root):
        source = root / 'input.csv'
        self.raw.to_csv(source, index=False)
        synthetic_provenance(source, self.raw, self.partition)
        destination = root / 'model'
        self.api.save_model(destination, self.scaler, self.reducer, self.clusterer,
                            self.raw, self.clustered, source, self.partition)
        return destination

    def test_roundtrip_predictions_do_not_refit_and_preserve_batch_results(self):
        with workspace_tempdir() as root:
            dest = self.save(root)
            with self.assertRaisesRegex(ValueError, 'trusted'):
                self.api.load_model(dest)
            bundle = self.api.load_model(dest, trusted=True)
            with patch.object(bundle['scaler'], 'fit', side_effect=AssertionError('refit')), \
                    patch.object(bundle['reducer'], 'fit', side_effect=AssertionError('refit')), \
                    patch.object(bundle['clusterer'], 'fit', side_effect=AssertionError('refit')):
                result = self.api.predict_development(bundle, self.query)
                singles = pd.concat([self.api.predict_development(bundle, self.query.iloc[[i]]) for i in range(2)])
            pd.testing.assert_frame_equal(result, singles)
            self.assertTrue(np.isfinite(result.corner_score).all())
            self.assertEqual(result.scene_name.tolist(), self.query.scene_name.tolist())
            shuffled = self.api.predict_development(bundle, self.query[self.query.columns[::-1]])
            np.testing.assert_allclose(result.corner_score, shuffled.corner_score)

    def test_preflight_integrity_check_never_unpickles(self):
        with workspace_tempdir() as root:
            dest = self.save(root)
            with patch('pickle.load', side_effect=AssertionError('unpickle')):
                self.api.inspect_model(dest)

    def test_audit_implementation_is_bound_to_model_sources(self):
        self.assertIn('extraction_audit.py', self.api.source_hashes())

    def test_real_extraction_requires_hash_bound_quality_audit(self):
        with workspace_tempdir() as root:
            source = root / 'input.csv'
            self.raw.to_csv(source, index=False)
            synthetic_provenance(source, self.raw, self.partition)
            path = guard.provenance_path(source)
            record = json.loads(path.read_text())
            record['stage'] = 'feature_extraction'
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'quality audit'):
                self.api.require_feature_provenance(source, self.raw)
            scripts = Path(__file__).parents[1] / 'scripts'
            quality_path = Path(str(source) + '.quality.json')
            quality = {'scene_names': self.raw.scene_name.tolist(), 'scene_count': len(self.raw),
                       'script': guard.file_record(scripts / 'scene_feature_hdbscan.py'),
                       'audit_code': guard.file_record(scripts / 'extraction_audit.py'),
                       'partition': self.partition['file']}
            quality_path.write_text(json.dumps(quality))
            record['extra'].update(quality_audit=guard.file_record(quality_path),
                                   extraction_audit_code=quality['audit_code'])
            path.write_text(json.dumps(record))
            self.api.require_feature_provenance(source, self.raw)
            quality_path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'quality audit'):
                self.api.require_feature_provenance(source, self.raw)
            record['extra']['quality_audit'] = guard.file_record(quality_path)
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'quality audit'):
                self.api.require_feature_provenance(source, self.raw)

    def test_tamper_is_rejected_before_unpickle(self):
        with workspace_tempdir() as root:
            dest = self.save(root)
            with (dest / 'estimators.pkl').open('ab') as stream:
                stream.write(b'changed')
            with patch('pickle.load', side_effect=AssertionError('unpickle')):
                with self.assertRaisesRegex(ValueError, 'hash'):
                    self.api.load_model(dest, trusted=True)

    def test_version_and_feature_order_mismatch_rejected(self):
        with workspace_tempdir() as root:
            dest = self.save(root)
            path = dest / 'manifest.json'
            original = json.loads(path.read_text())
            for key, value in [('features', list(reversed(original['features']))), ('runtime', {})]:
                changed = {**original, key: value}
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    self.api.inspect_model(dest)
            path.write_text(json.dumps(original))

    def test_evaluation_fit_overlap_bad_schema_and_overwrite_are_rejected(self):
        with workspace_tempdir() as root:
            dest = self.save(root)
            bundle = self.api.load_model(dest, trusted=True)
            evaluation = next(r for r in self.partition['rows'] if r['split'] == 'evaluation')
            invalid = [self.raw.iloc[:1], self.query.drop(columns='avg_speed'),
                       self.query.assign(avg_speed=np.nan),
                       self.query.iloc[:1].assign(scene_name=evaluation['scene_name'], scene_token=evaluation['scene_token'])]
            for frame in invalid:
                with self.assertRaises(ValueError):
                    self.api.predict_development(bundle, frame)
            with self.assertRaises(FileExistsError):
                self.api.save_model(dest, self.scaler, self.reducer, self.clusterer,
                                    self.raw, self.clustered, root / 'input.csv', self.partition)

    def test_export_rejects_mismatched_clustering_evidence(self):
        with workspace_tempdir() as root:
            source = root / 'input.csv'
            self.raw.to_csv(source, index=False)
            synthetic_provenance(source, self.raw, self.partition)
            with self.assertRaises(ValueError):
                self.api.save_model(root / 'model', self.scaler, self.reducer, self.clusterer,
                                    self.raw, self.clustered.assign(cluster=-1), source, self.partition)

    def test_export_rejects_other_batch_scaler_and_reducer(self):
        with workspace_tempdir() as root:
            source = root / 'input.csv'
            self.raw.to_csv(source, index=False)
            synthetic_provenance(source, self.raw, self.partition)
            other_scaler = StandardScaler().fit(guard.current_features(self.raw) + 100)
            other_reducer = RecordedProjection().fit(self.reducer._raw_data[::-1])
            for scaler, reducer in [(other_scaler, self.reducer), (self.scaler, other_reducer)]:
                with self.assertRaises(ValueError):
                    self.api.save_model(root / 'model', scaler, reducer, self.clusterer,
                                        self.raw, self.clustered, source, self.partition)

    def test_export_rejects_changed_risk_evidence_and_bad_risk_dtype(self):
        with workspace_tempdir() as root:
            source = root / 'input.csv'
            self.raw.to_csv(source, index=False)
            synthetic_provenance(source, self.raw, self.partition)
            with self.assertRaises(ValueError):
                self.api.save_model(root / 'model', self.scaler, self.reducer, self.clusterer,
                                    self.raw, self.clustered.assign(min_ttc=.1), source, self.partition)
        with workspace_tempdir() as root:
            self.raw['min_ttc'] = 'broken'
            self.clustered['min_ttc'] = 'broken'
            with self.assertRaises(ValueError):
                self.save(root)

    def test_feature_provenance_rejects_missing_or_old_rule_manifest(self):
        self.assertTrue(hasattr(self.api, 'require_feature_provenance'))
        with workspace_tempdir() as root:
            path = root / 'input.csv'
            self.raw.to_csv(path, index=False)
            with self.assertRaises(ValueError):
                self.api.require_feature_provenance(path, self.raw)
            synthetic_provenance(path, self.raw, self.partition)
            manifest_path = guard.provenance_path(path)
            record = json.loads(manifest_path.read_text())
            record['extra']['feature_rules']['sha256'] = 'old rules'
            manifest_path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                self.api.require_feature_provenance(path, self.raw)

    def test_each_risk_input_rejects_missing_invalid_and_nonfinite_values(self):
        for column in corner_scoring.FROZEN_RISK_INPUTS:
            for changed in [self.raw.drop(columns=column), self.raw.assign(**{column: 'bad'}),
                            self.raw.assign(**{column: np.nan}), self.raw.assign(**{column: np.inf})]:
                with self.assertRaises(ValueError, msg=column):
                    self.api.validate_risk_inputs(changed)

    def test_all_noise_reference_is_rejected_for_prediction(self):
        with workspace_tempdir() as root:
            bundle = self.api.load_model(self.save(root), trusted=True)
            bundle['manifest']['predictable'] = False
            with self.assertRaisesRegex(ValueError, 'All-noise'):
                self.api.predict_development(bundle, self.query)

    def test_changed_manifest_score_reference_rejected_on_load(self):
        with workspace_tempdir() as root:
            dest = self.save(root)
            path = dest / 'manifest.json'
            record = json.loads(path.read_text())
            record['score_reference']['score_max'] = 900
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'metadata'):
                self.api.load_model(dest, trusted=True)


if __name__ == '__main__':
    unittest.main()
