"""Four approved development configurations, five seeds each; no automatic selection."""

import argparse
from datetime import datetime, timezone
from itertools import combinations
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

try:
    from . import experiment_partition as guard
    from .frozen_model import require_feature_provenance, runtime_versions, source_hashes
    from .corner_scoring import calculate_corner_scores, calculate_grouped_risk
    from .seed_stability import compare_runs, top_names
except ImportError:
    import experiment_partition as guard
    from frozen_model import require_feature_provenance, runtime_versions, source_hashes
    from corner_scoring import calculate_corner_scores, calculate_grouped_risk
    from seed_stability import compare_runs, top_names

SEEDS = (42, 7, 19, 73, 101)


def configurations():
    return [{'id': f'n{neighbors}_s{samples}', 'n_neighbors': neighbors,
             'min_samples': samples, 'min_cluster_size': 20}
            for neighbors in (15, 30) for samples in (1, 5)]


def cluster_diagnostics(labels):
    counts = labels[labels >= 0].value_counts()
    return {'clusters': len(counts), 'noise_count': int((labels == -1).sum()),
            'noise_fraction': float((labels == -1).mean()),
            'largest_cluster_fraction': float(counts.max() / len(labels)) if len(counts) else 0.0,
            'degenerate': len(counts) < 2}


def summarize_configuration(results, rows, k=20):
    if set(results) != set(SEEDS) or len(rows) != len(SEEDS) or {r['seed'] for r in rows} != set(SEEDS):
        raise ValueError('All five successful seeds are required')
    pairs = [{'seed_a': a, 'seed_b': b, **compare_runs(results[a], results[b], k)}
             for a, b in combinations(SEEDS, 2)]
    summary = {'successful_runs': len(rows), 'degenerate_runs': sum(r['degenerate'] for r in rows),
               'top20_all_seed_intersection': sorted(set.intersection(
                   *(set(top_names(results[s], k)) for s in SEEDS)))}
    for key in ('clusters', 'noise_fraction', 'largest_cluster_fraction'):
        values = [r[key] for r in rows]
        summary.update({key + '_min': min(values), key + '_median': float(np.median(values)),
                        key + '_max': max(values)})
    for key in ('ari_all', 'top_k_overlap_fraction', 'top_k_jaccard'):
        values = [r[key] for r in pairs]
        summary.update({key + '_min': min(values), key + '_median': float(np.median(values)),
                        key + '_max': max(values)})
    return summary, pairs


def write_json(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args(argv)
    raw, features, partition = guard.load_development_features(args.input)
    provenance = require_feature_provenance(args.input, raw)
    expected = {r['scene_token'] for r in partition['rows'] if r['split'] == 'development'}
    if provenance['stage'] != 'feature_extraction' or len(raw) != 700 or set(raw.scene_token) != expected:
        raise ValueError('Study requires the full audited 700-scene development extraction')
    quality_path = Path(str(args.input) + '.quality.json')
    quality = json.loads(quality_path.read_text(encoding='utf-8'))
    if quality['query_exception_count'] or any(
            counts['nan'] or counts['negative_inf'] or (counts['positive_inf'] and name not in
                {'merge_observed_min_distance', 'vru_observed_min_distance'})
            for name, counts in quality['nonfinite_by_column'].items()):
        raise ValueError('Extraction quality findings require review before parameter experiments')
    guard.assert_new_outputs([args.output_dir])
    if args.preflight:
        guard.preflight('bounded_parameter_stability', raw, partition, features)
        print('4 configurations x 5 seeds; 10 UMAP fits, 20 HDBSCAN fits; no model selection')
        return
    configs = configurations()
    protocol = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'stage': 'development_parameter_stability',
        'fit_scope': 'development', 'scene_count': len(raw), 'semantic_features': list(features.columns),
        'input': guard.file_record(args.input), 'partition': partition['file'],
        'extraction_manifest': guard.file_record(guard.provenance_path(args.input)),
        'quality': guard.file_record(quality_path), 'script': guard.file_record(__file__),
        'comparison_code': guard.file_record(Path(__file__).with_name('seed_stability.py')),
        'sources': source_hashes(), 'runtime': runtime_versions(),
        'command': [sys.executable, *sys.argv], 'seeds': list(SEEDS), 'configurations': configs,
        'threads': {k: os.getenv(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS')},
        'umap_fixed': {'min_dist': 0.0, 'n_components': 10, 'metric': 'cosine', 'n_jobs': 1, 'low_memory': True},
        'hdbscan_fixed': {'min_cluster_size': 20, 'prediction_data': True},
        'score_weights': {'rarity': .20, 'atypical_norm': .25, 'risk': .55},
        'top_k': 20, 'selected_configuration': None,
        'limitations': ['No expert labels, held-out prediction, best-seed or automatic parameter selection.',
                       'Largest cluster fraction excludes noise in numerator but includes all scenes in denominator.',
                       'ARI includes noise as a label; joint-nonnoise ARI and subset size are also reported.',
                       'Stability alone does not establish useful clusters or meaningful risk rankings.',
                       'Degenerate means fewer than two nonnoise clusters; no dominance cutoff selected.']}
    args.output_dir.mkdir(parents=True)
    write_json(args.output_dir / 'protocol.json', protocol)
    # Native libraries are deliberately deferred until after provenance and preflight.
    import umap
    import hdbscan
    from sklearn.preprocessing import StandardScaler
    scaled = StandardScaler().fit_transform(features)
    reference_risk = calculate_grouped_risk(raw).risk.to_numpy()
    rows, outputs = [], []
    results = {c['id']: {} for c in configs}
    for neighbors in (15, 30):
        for seed in SEEDS:
            start = time.monotonic()
            embedding_error = None
            try:
                embedding = umap.UMAP(n_neighbors=neighbors, random_state=seed,
                                      **protocol['umap_fixed']).fit_transform(scaled)
                if not np.isfinite(embedding).all():
                    raise ValueError('Nonfinite embedding')
            except Exception as exc:
                embedding_error = f'{type(exc).__name__}: {exc}'
            embedding_seconds = time.monotonic() - start
            for config in [c for c in configs if c['n_neighbors'] == neighbors]:
                row = dict(config, seed=seed, run_status='failed', error='', embedding_seconds=embedding_seconds)
                start = time.monotonic()
                try:
                    if embedding_error:
                        raise RuntimeError(embedding_error)
                    clusterer = hdbscan.HDBSCAN(min_samples=config['min_samples'], **protocol['hdbscan_fixed']).fit(embedding)
                    clustered = raw.assign(cluster=clusterer.labels_, cluster_probability=clusterer.probabilities_,
                                           cluster_outlier_score=clusterer.outlier_scores_)
                    guard.validate_cluster_columns(clustered)
                    scored = calculate_corner_scores(clustered)
                    np.testing.assert_allclose(scored.risk, reference_risk, rtol=1e-12, atol=1e-12)
                    columns = ['scene_name', 'scene_token', 'cluster', 'cluster_probability', 'cluster_outlier_score',
                               'risk', 'rarity', 'atypical_norm', 'corner_score']
                    scored = scored[columns].sort_values(['corner_score', 'scene_name'], ascending=[False, True])
                    scored.insert(0, 'priority_rank', range(1, len(scored) + 1))
                    path = args.output_dir / f"{config['id']}_seed{seed}.csv"
                    scored.to_csv(path, index=False, mode='x')
                    outputs.append(guard.file_record(path))
                    results[config['id']][seed] = scored
                    row.update(cluster_diagnostics(scored.cluster), run_status='ok', top20=top_names(scored, 20))
                except Exception as exc:
                    row['error'] = f'{type(exc).__name__}: {exc}'
                row['clustering_scoring_seconds'] = time.monotonic() - start
                rows.append(row)
                print(json.dumps(row), flush=True)
    summaries, pairs = [], []
    for config in configs:
        successful = [r for r in rows if r['id'] == config['id'] and r['run_status'] == 'ok']
        if len(successful) != len(SEEDS):
            summaries.append(dict(config, status='incomplete', successful_runs=len(successful)))
            continue
        summary, comparisons = summarize_configuration(results[config['id']], successful)
        summaries.append(dict(config, status='complete', **summary))
        pairs.extend(dict(configuration=config['id'], **p) for p in comparisons)
    if source_hashes() != protocol['sources'] or guard.file_record(args.input) != protocol['input']:
        raise ValueError('Input/source changed during study; refusing completion report')
    for name, data in [('runs.csv', rows), ('configurations.csv', summaries), ('pairwise.csv', pairs)]:
        path = args.output_dir / name
        # Lists remain in JSON; tabular summaries contain only scalar fields.
        pd.DataFrame([{k: v for k, v in r.items() if not isinstance(v, list)} for r in data]).to_csv(path, index=False, mode='x')
        outputs.append(guard.file_record(path))
    report = dict(protocol, completed_at_utc=datetime.now(timezone.utc).isoformat(), runs=rows,
                  configurations_summary=summaries, pairwise=pairs, outputs=outputs,
                  successful_runs=sum(r['run_status'] == 'ok' for r in rows), planned_runs=20)
    report['status'] = 'complete' if report['successful_runs'] == 20 else 'incomplete'
    write_json(args.output_dir / 'summary.json', report)
    print(f"{report['status']}: {report['successful_runs']}/20; {args.output_dir / 'summary.json'}", flush=True)
    if report['status'] != 'complete':
        raise RuntimeError('Study incomplete; inspect explicit failure records')


if __name__ == '__main__':
    main()
