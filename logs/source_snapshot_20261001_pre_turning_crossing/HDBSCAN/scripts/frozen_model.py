"""Trusted local estimator bundles and development-only out-of-fit diagnostics.

Pickle is executable code: hashes detect corruption, not a malicious publisher.
Never load downloaded or otherwise untrusted estimator bundles.
"""

from datetime import datetime, timezone
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import pickle
import platform

import numpy as np
import pandas as pd

try:
    from . import experiment_partition as guard
    from .corner_scoring import fit_score_reference, calculate_frozen_corner_scores, FROZEN_RISK_INPUTS
except ImportError:
    import experiment_partition as guard
    from corner_scoring import fit_score_reference, calculate_frozen_corner_scores, FROZEN_RISK_INPUTS


SOURCE_NAMES = ('frozen_model.py', 'corner_scoring.py', 'feature_selection.py',
                'scene_feature_rules.py', 'scene_feature_hdbscan.py', 'experiment_partition.py',
                'extraction_audit.py')


def runtime_versions():
    return {'python': platform.python_version(), 'platform': platform.system(),
            **{name: version(name) for name in
               ('numpy', 'pandas', 'scikit-learn', 'umap-learn', 'hdbscan', 'numba', 'joblib')}}


def source_hashes():
    return {name: guard.file_record(Path(__file__).with_name(name))['sha256']
            for name in SOURCE_NAMES}


def metadata_digest(manifest):
    metadata = {k: v for k, v in manifest.items() if k != 'estimators'}
    return hashlib.sha256(json.dumps(metadata, sort_keys=True).encode('utf-8')).hexdigest()


def require_feature_provenance(path, frame):
    """Accept only current protected extraction or explicitly synthetic test data."""
    manifest_path = guard.provenance_path(path)
    if not manifest_path.is_file():
        raise ValueError('Missing feature extraction provenance')
    record = json.loads(manifest_path.read_text(encoding='utf-8'))
    partition = guard.load_partition()
    guard.assert_development_frame(frame, partition)
    if (record.get('stage') not in {'feature_extraction', 'synthetic_features'}
            or record.get('fit_scope') != 'development'
            or record.get('scene_names') != frame.scene_name.tolist()
            or record['output']['sha256'] != guard.file_record(path)['sha256']
            or record['partition']['sha256'] != partition['file']['sha256']
            or record['script']['sha256'] != source_hashes()['scene_feature_hdbscan.py']
            or record['feature_schema']['sha256'] != source_hashes()['feature_selection.py']
            or record.get('extra', {}).get('feature_rules', {}).get('sha256') != source_hashes()['scene_feature_rules.py']):
        raise ValueError('Feature extraction version/provenance mismatch')
    if record['stage'] == 'feature_extraction':
        quality_path = Path(str(path) + '.quality.json')
        extra = record.get('extra', {})
        if (not quality_path.is_file()
                or extra.get('quality_audit', {}).get('sha256') != guard.file_record(quality_path)['sha256']
                or extra.get('extraction_audit_code', {}).get('sha256') != source_hashes()['extraction_audit.py']):
            raise ValueError('Missing or mismatched extraction quality audit')
        quality = json.loads(quality_path.read_text(encoding='utf-8'))
        if (quality.get('scene_names') != frame.scene_name.tolist()
                or quality.get('scene_count') != len(frame)
                or quality.get('script', {}).get('sha256') != source_hashes()['scene_feature_hdbscan.py']
                or quality.get('audit_code', {}).get('sha256') != source_hashes()['extraction_audit.py']
                or quality.get('partition', {}).get('sha256') != partition['file']['sha256']):
            raise ValueError('Invalid extraction quality audit identity or source')
    validate_risk_inputs(frame)
    return record


def validate_risk_inputs(frame):
    if not set(FROZEN_RISK_INPUTS).issubset(frame.columns):
        raise ValueError('Missing frozen risk input columns')
    if not np.isfinite(frame[list(FROZEN_RISK_INPUTS)].apply(pd.to_numeric, errors='coerce').to_numpy()).all():
        raise ValueError('Non-finite or invalid frozen risk input values')


def save_model(destination, scaler, reducer, clusterer, raw, clustered, input_path, partition):
    destination = Path(destination)
    guard.assert_new_outputs([destination])
    guard.assert_development_frame(raw, partition)
    features = guard.current_features(raw)
    feature_provenance = require_feature_provenance(input_path, raw)
    guard.assert_development_frame(clustered, partition)
    guard.validate_cluster_columns(clustered)
    if raw.scene_token.tolist() != clustered.scene_token.tolist():
        raise ValueError('Training row order does not match clustering evidence')
    try:
        pd.testing.assert_frame_equal(raw, clustered[raw.columns], check_dtype=False,
                                      rtol=1e-12, atol=1e-12)
    except (AssertionError, KeyError) as exc:
        raise ValueError('Raw and clustered feature/risk evidence mismatch') from exc
    for column, actual in [('cluster', clusterer.labels_),
                           ('cluster_probability', clusterer.probabilities_),
                           ('cluster_outlier_score', clusterer.outlier_scores_)]:
        if not np.array_equal(clustered[column].to_numpy(), actual):
            raise ValueError('Estimator and clustering evidence mismatch')
    source = pd.read_csv(input_path, float_precision='round_trip')
    try:
        pd.testing.assert_frame_equal(raw.reset_index(drop=True), source,
                                      check_dtype=False, rtol=1e-12, atol=1e-12)
    except AssertionError as exc:
        raise ValueError('Training input file does not match fitted frame') from exc
    numeric_columns = sorted(set(guard.CLUSTERING_FEATURES) | set(FROZEN_RISK_INPUTS))
    if not np.isfinite(raw[numeric_columns].to_numpy(dtype=float)).all():
        raise ValueError('Non-finite scoring inputs in training data')
    if scaler.n_features_in_ != len(guard.CLUSTERING_FEATURES):
        raise ValueError('Scaler feature count mismatch')
    from sklearn.preprocessing import StandardScaler
    expected = StandardScaler().fit(features)
    if (not np.array_equal(scaler.feature_names_in_, features.columns)
            or any(not np.array_equal(getattr(scaler, key), getattr(expected, key))
                   for key in ['mean_', 'var_', 'scale_', 'n_samples_seen_'])):
        raise ValueError('Scaler was fitted on different data or feature order')
    scaled = scaler.transform(features)
    if (scaled.shape != reducer._raw_data.shape
            or not np.allclose(scaled, reducer._raw_data, rtol=1e-6, atol=1e-7)):
        raise ValueError('Reducer was fitted on different data')
    if not np.array_equal(reducer.embedding_, clusterer._raw_data):
        raise ValueError('Clusterer was fitted on a different embedding')
    # Access the property now so a model lacking prediction_data fails before saving.
    clusterer.prediction_data_
    manifest = {
        'format_version': 1, 'stage': 'development_model', 'fit_scope': 'development',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'partition': partition['file'], 'input': guard.file_record(input_path),
        'feature_provenance': guard.file_record(guard.provenance_path(input_path)),
        'feature_kind': feature_provenance['stage'],
        'features': list(guard.CLUSTERING_FEATURES), 'numeric_input_columns': numeric_columns,
        'scene_names': raw.scene_name.tolist(), 'scene_tokens': raw.scene_token.tolist(),
        'runtime': runtime_versions(), 'sources': source_hashes(),
        'score_reference': fit_score_reference(clustered),
        'predictable': bool((clustered.cluster >= 0).any()),
        'estimator_classes': [type(obj).__module__ + '.' + type(obj).__name__
                              for obj in (scaler, reducer, clusterer)],
        'prediction_scope': 'unseen development scenes only; not formal evaluation',
        'transform_policy': 'one_row_at_a_time',
        'outlier_policy': 'hdbscan.prediction.approximate_predict_scores',
        'ranking_column': 'corner_score',
    }
    destination.mkdir(parents=True)
    payload = destination / 'estimators.pkl'
    with payload.open('xb') as stream:
        pickle.dump({'scaler': scaler, 'reducer': reducer, 'clusterer': clusterer,
                     'metadata_sha256': metadata_digest(manifest)},
                    stream, protocol=pickle.HIGHEST_PROTOCOL)
    manifest['estimators'] = guard.file_record(payload)
    # Manifest is the completion marker; partial exports are not loadable.
    with (destination / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    return manifest


def inspect_model(directory):
    """Check metadata before any deserialization or native model imports."""
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    partition = guard.load_partition()
    if (manifest.get('format_version') != 1 or manifest.get('stage') != 'development_model'
            or manifest.get('fit_scope') != 'development'
            or manifest.get('features') != list(guard.CLUSTERING_FEATURES)
            or manifest.get('runtime') != runtime_versions()
            or manifest.get('sources') != source_hashes()
            or manifest.get('transform_policy') != 'one_row_at_a_time'
            or manifest['partition']['sha256'] != partition['file']['sha256']):
        raise ValueError('Model schema, source, runtime or partition mismatch')
    training = pd.DataFrame({'scene_name': manifest['scene_names'],
                             'scene_token': manifest['scene_tokens']})
    guard.assert_development_frame(training, partition)
    if manifest['score_reference']['total'] != len(training):
        raise ValueError('Scoring reference size mismatch')
    if guard.file_record(directory / 'estimators.pkl')['sha256'] != manifest['estimators']['sha256']:
        raise ValueError('Estimator hash mismatch')
    return manifest


def load_model(directory, *, trusted=False):
    if not trusted:
        raise ValueError('Only explicitly trusted local pickle models may be loaded')
    manifest = inspect_model(directory)
    with (Path(directory) / 'estimators.pkl').open('rb') as stream:
        bundle = pickle.load(stream)
    if bundle.get('metadata_sha256') != metadata_digest(manifest):
        raise ValueError('Model metadata mismatch against serialized payload')
    return {**bundle, 'manifest': manifest}


def validate_prediction_input(frame, manifest):
    guard.assert_development_frame(frame, guard.load_partition())
    features = guard.current_features(frame)
    validate_risk_inputs(frame)
    if set(frame.scene_token) & set(manifest['scene_tokens']):
        raise ValueError('Prediction input overlaps model training scenes')
    required = manifest['numeric_input_columns']
    if not set(required).issubset(frame.columns):
        raise ValueError('Missing frozen numeric/scoring input columns')
    values = frame[required].apply(pd.to_numeric, errors='coerce').to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Non-finite frozen scoring inputs')
    if not manifest['predictable']:
        raise ValueError('All-noise fitted model has no clusters for approximate prediction')
    return features


def predict_development(bundle, frame):
    """Transform only, never fit; fixed row policy avoids query-batch dependence."""
    features = validate_prediction_input(frame, bundle['manifest'])
    from hdbscan import approximate_predict
    from hdbscan.prediction import approximate_predict_scores
    scaled = bundle['scaler'].transform(features)
    embedded = np.vstack([bundle['reducer'].transform(row.reshape(1, -1)) for row in scaled])
    if not np.isfinite(embedded).all():
        raise ValueError('Non-finite frozen embedding')
    labels, strengths = approximate_predict(bundle['clusterer'], embedded)
    outliers = approximate_predict_scores(bundle['clusterer'], embedded)
    result = frame.copy()
    for index in range(embedded.shape[1]):
        result[f'umap_{index}'] = embedded[:, index]
    result['cluster'] = labels
    result['cluster_probability'] = strengths
    result['cluster_outlier_score'] = outliers
    guard.validate_cluster_columns(result)
    return calculate_frozen_corner_scores(result, bundle['manifest']['score_reference'])
