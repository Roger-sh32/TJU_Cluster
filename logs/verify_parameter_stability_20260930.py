"""Read-only verification of all bounded-study artifacts and score components."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'HDBSCAN/scripts'))
from experiment_partition import file_record, load_development_features, validate_cluster_columns
from frozen_model import require_feature_provenance, source_hashes
from corner_scoring import calculate_corner_scores
from parameter_stability import configurations, SEEDS, cluster_diagnostics, summarize_configuration


def main():
    folder = ROOT / 'HDBSCAN/tables/parameter_stability_20260930'
    report = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    for record in report['outputs'] + [report[k] for k in ('input', 'quality', 'extraction_manifest', 'script', 'comparison_code', 'partition')]:
        assert file_record(record['path'])['sha256'] == record['sha256']
    assert report['sources'] == source_hashes()
    assert report['status'] == 'complete' and report['successful_runs'] == 20
    assert report['configurations'] == configurations() and report['seeds'] == list(SEEDS)
    assert report['selected_configuration'] is None
    raw, _, _ = load_development_features(report['input']['path'])
    require_feature_provenance(report['input']['path'], raw)
    pairwise = []
    for config in configurations():
        results, rows = {}, []
        for seed in SEEDS:
            data = pd.read_csv(folder / f"{config['id']}_seed{seed}.csv", float_precision='round_trip')
            assert len(data) == 700 and data.scene_name.is_unique and data.scene_token.is_unique
            assert data.priority_rank.tolist() == list(range(1, 701))
            pd.testing.assert_frame_equal(data, data.sort_values(['corner_score', 'scene_name'], ascending=[False, True]))
            evidence = data[['scene_name', 'scene_token', 'cluster', 'cluster_probability', 'cluster_outlier_score']]
            merged = raw.merge(evidence, on=['scene_name', 'scene_token'], validate='one_to_one')
            assert len(merged) == 700
            validate_cluster_columns(merged)
            scored = calculate_corner_scores(merged).set_index('scene_name').loc[data.scene_name]
            for column in ['risk', 'rarity', 'atypical_norm', 'corner_score']:
                np.testing.assert_allclose(scored[column], data[column], rtol=1e-12, atol=1e-12)
            if config['id'] == 'n15_s1':
                historical = pd.read_csv(ROOT / f'HDBSCAN/tables/seed_stability_20260927/seed_{seed}.csv')
                aligned = data.set_index('scene_name').loc[historical.scene_name]
                np.testing.assert_array_equal(aligned.cluster, historical.cluster)
                np.testing.assert_allclose(aligned.corner_score, historical.corner_score, rtol=1e-12, atol=1e-12)
            results[seed] = data
            rows.append(dict(seed=seed, **cluster_diagnostics(data.cluster)))
        summary, pairs = summarize_configuration(results, rows)
        expected = next(r for r in report['configurations_summary'] if r['id'] == config['id'])
        for key, value in summary.items():
            assert expected[key] == value, (config['id'], key)
        pairwise.extend(dict(configuration=config['id'], **p) for p in pairs)
    assert pairwise == report['pairwise'] and len(pairwise) == 40
    print('PASS: 20 runs x 700 identities, artifact/source hashes, score recomputation, 40 pairs, summaries; all five baseline seeds reproduced')


if __name__ == '__main__':
    main()
