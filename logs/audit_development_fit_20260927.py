"""Verify and summarize the single 700-scene development fit; no model tuning."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'HDBSCAN/scripts'))
from experiment_partition import (load_development_features, require_fit_provenance,
                                  file_record, provenance_path, assert_new_outputs)
from frozen_model import load_model, require_feature_provenance, validate_risk_inputs
from corner_scoring import calculate_corner_scores, calculate_frozen_corner_scores


def main():
    tables = ROOT / 'HDBSCAN/tables'
    feature_path = tables / 'scene_features_development_20260926.csv'
    cluster_path = tables / 'scene_features_development_20260927_umap_hdbscan.csv'
    score_path = tables / 'scene_features_development_20260927_with_corner_score.csv'
    rank_path = tables / 'development_priority_ranking_20260927.csv'
    summary_path = tables / 'development_fit_summary_20260927.json'
    assert_new_outputs([rank_path, summary_path])
    raw, features, partition = load_development_features(feature_path)
    require_feature_provenance(feature_path, raw)
    validate_risk_inputs(raw)
    expected = {r['scene_token'] for r in partition['rows'] if r['split'] == 'development'}
    assert len(raw) == 700 and set(raw.scene_token) == expected
    clusters = pd.read_csv(cluster_path)
    fit_record = require_fit_provenance(cluster_path, clusters, partition)
    scores = pd.read_csv(score_path)
    score_record = json.loads(provenance_path(score_path).read_text(encoding='utf-8'))
    assert score_record['stage'] == 'development_scoring'
    assert score_record['partition']['sha256'] == partition['file']['sha256']
    assert score_record['input']['sha256'] == file_record(cluster_path)['sha256']
    assert score_record['output']['sha256'] == file_record(score_path)['sha256']
    assert score_record['scene_names'] == raw.scene_name.tolist()
    pd.testing.assert_frame_equal(raw, clusters[raw.columns], check_exact=False, rtol=1e-12, atol=1e-12)
    pd.testing.assert_frame_equal(clusters, scores[clusters.columns], check_exact=False, rtol=1e-12, atol=1e-12)
    model_dir = cluster_path.with_suffix('.model')
    assert fit_record['extra']['model_manifest']['sha256'] == file_record(model_dir / 'manifest.json')['sha256']
    bundle = load_model(model_dir, trusted=True)
    assert bundle['manifest']['scene_tokens'] == raw.scene_token.tolist()
    np.testing.assert_array_equal(bundle['clusterer'].labels_, clusters.cluster)
    np.testing.assert_allclose(bundle['clusterer'].probabilities_, clusters.cluster_probability, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(bundle['clusterer'].outlier_scores_, clusters.cluster_outlier_score, rtol=1e-12, atol=1e-12)
    for recomputed in [calculate_corner_scores(clusters),
                       calculate_frozen_corner_scores(clusters, bundle['manifest']['score_reference'])]:
        pd.testing.assert_frame_equal(scores, recomputed[scores.columns], check_exact=False, rtol=1e-12, atol=1e-12)
    ranked = scores.sort_values(['corner_score', 'scene_name'], ascending=[False, True], kind='mergesort')
    ranked.insert(0, 'priority_rank', range(1, len(ranked) + 1))
    ranked.to_csv(rank_path, index=False)
    top = ranked.head(20)
    sizes = scores.cluster.value_counts().sort_index()
    report = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'development-only exploratory fit and ranking; not effectiveness evaluation',
        'python': sys.executable, 'command': [sys.executable, *sys.argv], 'script': file_record(__file__),
        'inputs': [file_record(p) for p in [feature_path, cluster_path, score_path]],
        'model_manifest': file_record(model_dir / 'manifest.json'),
        'ranking': file_record(rank_path), 'partition': partition['file'],
        'scene_count': len(raw), 'semantic_feature_count': len(features.columns),
        'cluster_count_excluding_noise': int((sizes.index >= 0).sum()),
        'noise_count': int(sizes.get(-1, 0)), 'noise_fraction': float((scores.cluster == -1).mean()),
        'cluster_sizes': {str(int(k)): int(v) for k, v in sizes.items()},
        'parameters': {k: fit_record['extra'][k] for k in ['umap', 'hdbscan']},
        'score_min': float(scores.corner_score.min()), 'score_max': float(scores.corner_score.max()),
        'top20_noise_count': int((top.cluster == -1).sum()),
        'top20_cluster_count_excluding_noise': int(top.loc[top.cluster >= 0, 'cluster'].nunique()),
        'top20': top[['priority_rank', 'scene_name', 'cluster', 'corner_score', 'risk', 'rarity',
                      'atypical_norm', 'longitudinal_risk', 'interaction_risk', 'vru_risk',
                      'ego_response_risk', 'decision_demand', 'min_ttc']].to_dict('records'),
        'verification': {'frozen_membership': True, 'preserved_input_features': True,
                         'trusted_model_reload': True, 'estimator_output_match': True,
                         'score_recomputation_match': True, 'training_reference_score_match': True},
        'limitations': ['One historical parameter setting, no grid search or seed stability study.',
                       'Training-set scores only; no held-out prediction or expert labels.',
                       'Original extraction still substitutes Inf/NaN; raw validity audit is absent.',
                       'Noise is a density-clustering result, not a danger label.',
                       'No image download or KMeans experiment. Plot skipped because matplotlib is unavailable.']
    }
    with summary_path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: report[k] for k in ['scene_count', 'cluster_count_excluding_noise',
                                            'noise_count', 'noise_fraction', 'top20_noise_count',
                                            'top20_cluster_count_excluding_noise', 'verification']}, indent=2))
    print(summary_path)


if __name__ == '__main__':
    main()
