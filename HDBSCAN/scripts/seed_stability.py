"""Bounded development-only seed sensitivity, not parameter selection."""

import argparse
from datetime import datetime, timezone
from itertools import combinations
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd


def top_names(frame, k):
    return frame.sort_values(['corner_score', 'scene_name'], ascending=[False, True],
                             kind='mergesort').head(k).scene_name.tolist()


def compare_runs(left, right, k=20):
    from sklearn.metrics import adjusted_rand_score
    if (left.scene_name.duplicated().any() or right.scene_name.duplicated().any()
            or set(left.scene_name) != set(right.scene_name) or not 0 < k <= len(left)):
        raise ValueError('Mismatched identities or invalid top-k')
    a = left.set_index('scene_name').sort_index()
    b = right.set_index('scene_name').reindex(a.index)
    mask = (a.cluster >= 0) & (b.cluster >= 0)
    top_a, top_b = set(top_names(left, k)), set(top_names(right, k))
    return {
        'ari_all': float(adjusted_rand_score(a.cluster, b.cluster)),
        'ari_joint_nonnoise': (float(adjusted_rand_score(a.loc[mask, 'cluster'], b.loc[mask, 'cluster']))
                              if mask.sum() >= 2 else None),
        'joint_nonnoise_count': int(mask.sum()),
        'noise_membership_agreement': float(((a.cluster == -1) == (b.cluster == -1)).mean()),
        'top_k_overlap_count': len(top_a & top_b),
        'top_k_overlap_fraction': len(top_a & top_b) / k,
        'top_k_jaccard': len(top_a & top_b) / len(top_a | top_b),
    }


def main():
    from experiment_partition import (load_development_features, file_record, preflight,
                                      assert_new_outputs, require_fit_provenance)
    from frozen_model import require_feature_provenance, runtime_versions, source_hashes
    from corner_scoring import calculate_corner_scores
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    raw, features, partition = load_development_features(args.input)
    require_feature_provenance(args.input, raw)
    baseline = pd.read_csv(args.baseline)
    fit = require_fit_provenance(args.baseline, baseline, partition)
    if fit['input']['sha256'] != file_record(args.input)['sha256']:
        raise ValueError('Baseline input mismatch')
    pd.testing.assert_frame_equal(raw, baseline[raw.columns], check_exact=False, atol=1e-12, rtol=1e-12)
    assert_new_outputs([args.output_dir])
    if args.preflight:
        return preflight('seed_stability', raw, partition, features)
    import umap
    import hdbscan
    from sklearn.preprocessing import StandardScaler
    seeds = [42, 7, 19, 73, 101]
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'development seed sensitivity only; no model selection or expert validation',
              'command': [sys.executable, *sys.argv], 'script': file_record(__file__),
              'input': file_record(args.input), 'baseline': file_record(args.baseline),
              'partition': partition['file'], 'sources': source_hashes(), 'runtime': runtime_versions(),
              'seeds': seeds, 'parameters': fit['extra'], 'scene_count': len(raw),
              'runs': [], 'pairwise': [], 'outputs': [],
              'limitations': ['ARI includes noise as one label; joint-nonnoise ARI also reported.',
                              'Top20 uses raw score with deterministic scene-name tie breaking.',
                              'Five seeds only; no parameter search, resampling or held-out validation.',
                              'Inherits original extraction fallback limitations. No best seed selected.']}
    args.output_dir.mkdir(parents=True)
    scaled = StandardScaler().fit_transform(features)
    results = {}
    reference = calculate_corner_scores(baseline)
    for seed in seeds:
        start = time.monotonic()
        config = dict(fit['extra']['umap'], random_state=seed)
        embedding = umap.UMAP(**config).fit_transform(scaled)
        model = hdbscan.HDBSCAN(**fit['extra']['hdbscan']).fit(embedding)
        clustered = raw.assign(cluster=model.labels_, cluster_probability=model.probabilities_,
                               cluster_outlier_score=model.outlier_scores_)
        from experiment_partition import validate_cluster_columns
        validate_cluster_columns(clustered)
        scored = calculate_corner_scores(clustered)
        np.testing.assert_allclose(scored.risk, reference.risk, atol=1e-12, rtol=1e-12)
        cols = ['scene_name', 'scene_token', 'cluster', 'cluster_probability', 'cluster_outlier_score',
                'risk', 'rarity', 'atypical_norm', 'corner_score']
        scored = scored[cols].sort_values(['corner_score', 'scene_name'], ascending=[False, True])
        scored.insert(0, 'priority_rank', range(1, len(scored) + 1))
        path = args.output_dir / f'seed_{seed}.csv'
        scored.to_csv(path, index=False)
        results[seed] = scored
        row = {'seed': seed, 'clusters': len(set(model.labels_) - {-1}),
               'noise_count': int((model.labels_ == -1).sum()),
               'elapsed_seconds': time.monotonic() - start,
               'top20': top_names(scored, 20), 'vs_baseline': compare_runs(reference, scored)}
        if seed == 42:
            aligned = scored.set_index('scene_name').loc[reference.scene_name]
            np.testing.assert_array_equal(aligned.cluster, reference.cluster)
            np.testing.assert_allclose(aligned.corner_score, reference.corner_score, atol=1e-12, rtol=1e-12)
            report['seed42_reproduced_baseline'] = True
        report['runs'].append(row)
        report['outputs'].append(file_record(path))
        print(json.dumps(row), flush=True)
    for a, b in combinations(seeds, 2):
        report['pairwise'].append({'seed_a': a, 'seed_b': b, **compare_runs(results[a], results[b])})
    report['top20_all_seed_intersection'] = sorted(set.intersection(*(set(top_names(v, 20)) for v in results.values())))
    with (args.output_dir / 'summary.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print('Completed: ' + str(args.output_dir / 'summary.json'), flush=True)


if __name__ == '__main__':
    main()
