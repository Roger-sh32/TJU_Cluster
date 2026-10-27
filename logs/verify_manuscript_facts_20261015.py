"""Read-only manuscript fact-table/source checks; no experiments or model loads."""

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs import prepare_experiment_readiness_20261013 as statistics
from logs import diagnose_short_static_v2_20261015 as latest
from logs.diagnose_review8_20261012 import verify_records, write_json

DOCUMENT = ROOT/'outputs/论文初稿/方法与开发验证事实稿_20261015.md'
INDEX = ROOT/'outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json'
STAT_SHA = '444e398e9feee9f958b5cba941efa4a1aade85e81b28327c017ee472be4986e7'
LATEST_SHA = 'b7fb9861781d08ffd69a225ba986543556630e844eba5e6cd29f60771570afd6'
LATEST_SEAL_SHA = 'c951debde5f186a8269e52c3981c5cc604c777a313837f1521370a658d0ecf0b'
FACT_SOURCES = dict(F01='S01', F02='S01', F03='S09', F04='S10', F05='S11',
    F06='S11', F07='S11', F08='S12', F09='S13', F10='S14', F11='S15',
    F12='S16', F13='S17', F14='S05')
record = statistics.record


def literal_parameters(source, name):
    values = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            if not isinstance(node.value, ast.Call) or not isinstance(node.value.func, ast.Name) or node.value.func.id != 'dict':
                raise ValueError('Expected literal dict parameters')
            if node.value.args or any(k.arg is None for k in node.value.keywords):
                raise ValueError('Dynamic parameter arguments refused')
            try:
                values.append({k.arg: ast.literal_eval(k.value) for k in node.value.keywords})
            except (ValueError, TypeError) as exc:
                raise ValueError('Nonliteral parameters') from exc
    if len(values) != 1:
        raise ValueError('Missing/ambiguous parameter assignment')
    return values[0]


def validate_fact_table(text, facts):
    found = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.split('|')]
        if len(cells) >= 5 and re.fullmatch(r'F\d+', cells[1]):
            key = cells[1]
            if key in found:
                raise ValueError('Duplicate fact ID: '+key)
            if key not in FACT_SOURCES or cells[4] != FACT_SOURCES[key]:
                raise ValueError('Wrong fact source: '+key)
            found[key] = cells[3]
    if found != facts:
        raise ValueError('Fact table differs from source-derived values')


def validate_math(text):
    if sum(line.strip() == '$$' for line in text.splitlines()) % 2:
        raise ValueError('Unclosed display-math block')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sources_and_facts():
    statistics.check_packet(statistics.DEFAULT_OUTPUT, STAT_SHA)
    latest.load_protocol(LATEST_SHA)
    if record(latest.SEAL)['sha256'] != LATEST_SEAL_SHA:
        raise ValueError('Original latest diagnosis seal required')
    seal = read_json(latest.SEAL)
    verify_records([seal['protocol'], *seal['outputs']])
    table = ROOT/'HDBSCAN/tables'
    paths = {
        'S01': table/'evaluation_split_20260924_manifest.json',
        'S02': ROOT/'HDBSCAN/scripts/feature_selection.py',
        'S03': ROOT/'HDBSCAN/scripts/scene_feature_rules.py',
        'S04': ROOT/'HDBSCAN/scripts/scene_feature_hdbscan_v5_2.py',
        'S05': ROOT/'HDBSCAN/scripts/cluster_umap_hdbscan.py',
        'S06': ROOT/'HDBSCAN/scripts/corner_scoring.py',
        'S07': ROOT/'HDBSCAN/scripts/frozen_model.py',
        'S08': ROOT/'HDBSCAN/scripts/experiment_partition.py',
        'S09': table/'development_audit700_comparison_20260927.json',
        'S10': table/'development_fit_summary_20260927.json',
        'S11': table/'parameter_stability_20260930/summary.json',
        'S12': table/'development_candidate700_comparison_20261001.json',
        'S13': table/'crossing_v6_1_replay29_comparison_20261015.json',
        'S14': table/'longitudinal_v7_replay29_comparison_20261015.json',
        'S15': table/'longitudinal_v7_replay29_ledger_20261015.json',
        'S16': latest.EVIDENCE,
        'S17': latest.prior.EVIDENCE,
        'S18': ROOT/'HDBSCAN/scripts/evaluation_metrics.py',
        'S19': ROOT/'HDBSCAN/scripts/longitudinal_candidate_v7.py',
        'S20': ROOT/'HDBSCAN/scripts/crossing_candidate_v6.py',
        'S21': ROOT/'HDBSCAN/scripts/crossing_candidate_v6_1.py',
        'S22': statistics.DEFAULT_OUTPUT/'manifest.json',
        'S23': latest.SEAL,
        'S24': ROOT/'outputs/论文初稿/基于聚类的自动驾驶路测关键场景识别研究_导师审查骨架稿.md',
        'S25': ROOT/'outputs/中期/中期报告初始大纲.md',
    }
    bindings = {key: record(path) for key, path in paths.items()}
    data = {key: read_json(paths[key]) for key in ('S01','S09','S10','S11','S12','S13','S14','S15','S16','S17')}
    split, audit, fit, study, v4 = (data[k] for k in ('S01','S09','S10','S11','S12'))
    config = {s['id']: s for s in study['configurations_summary']}
    v7, ledger = data['S14'], data['S15']['scenes']
    short = next(s for s in data['S16']['scenes'] if s['scene_name'] == 'scene-0011')
    target = next(q for q in short['route_queries'] if q['diagnostic_roles'] == ['static_selected'])
    tail = next(s for s in data['S17']['scenes'] if s['scene_name'] == 'scene-0026')
    source = paths['S05'].read_text(encoding='utf-8')
    u, h = literal_parameters(source, 'umap_params'), literal_parameters(source, 'hdb_params')
    facts = {
        'F01': f"{split['counts']['development']} / {split['counts']['evaluation']}",
        'F02': f"{split['log_counts']['development']} / {split['log_counts']['evaluation']}",
        'F03': f"{audit['scene_count']} / {audit['column_count']} / {audit['clustering_feature_count']}",
        'F04': f"{fit['scene_count']} / {fit['cluster_count_excluding_noise']} / {fit['noise_count']}",
        'F05': f"{len(study['configurations'])} / {len(study['seeds'])} / {study['successful_runs']}",
        'F06': f"{config['n15_s1']['ari_all_median']:.6f} / {100*config['n15_s1']['top_k_overlap_fraction_median']:.1f}%",
        'F07': f"{config['n30_s1']['ari_all_median']:.6f} / {100*config['n30_s1']['top_k_overlap_fraction_median']:.1f}%",
        'F08': f"{v4['scene_count']} / {v4['column_count']} / {v4['clustering_feature_count']}",
        'F09': f"{len(read_json(data['S13']['protocol']['path'])['names'])} / {len(data['S13']['changes'])}",
        'F10': f"{len(ledger)} / {len(v7['changed_scenes'])} / {len(v7['changes'])} / {len(v7['clustering_changes'])}",
        'F11': f"{sum(sum(map(len,s['ledger'])) for s in ledger)} / {sum(len(s['rejected']) for s in ledger)}",
        'F12': f"{target['scene_time_s']:.6f} / {target['spatial_clearance_lower_m']:.6f} / {short['static_anchor_count']} / {short['blocked_anchor_count']}",
        'F13': f"{tail['minimum_ttc_event']['ttc']:.6f} / {tail['minimum_ttc_event']['scene_time']:.6f} / {tail['minimum_event_window']['sampled_span_s']:.1f}",
        'F14': f"{u['n_neighbors']} / {u['n_components']} / {h['min_cluster_size']} / {h['min_samples']}",
    }
    return bindings, facts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true')
    parser.add_argument('--expected-index-sha')
    args = parser.parse_args()
    if args.seal:
        if INDEX.exists():
            raise FileExistsError('Use a separately versioned manuscript/index; never reseal in place')
    else:
        if not args.expected_index_sha or record(INDEX)['sha256'] != args.expected_index_sha:
            raise ValueError('Original manuscript index SHA256 required')
        saved = read_json(INDEX)
        verify_records([saved['document'], saved['verifier'], saved['test'], *saved['sources'].values()])
    bindings, facts = sources_and_facts()
    text = DOCUMENT.read_text(encoding='utf-8')
    validate_fact_table(text, facts)
    validate_math(text)
    if set(re.findall(r'【(S\d+)】', text)) - set(bindings):
        raise ValueError('Unregistered manuscript source anchor')
    for binding in bindings.values():
        statistics.verify(binding)
    if args.seal:
        write_json(INDEX, dict(stage='source_bound_writing_draft_not_formal_results',
            created_at_utc=datetime.now(timezone.utc).isoformat(), command=[sys.executable,*sys.argv],
            python=sys.executable, document=record(DOCUMENT), verifier=record(Path(__file__)),
            test=record(ROOT/'logs/test_manuscript_facts_20261015.py'), sources=bindings, facts=facts,
            scope='Fact-table/source validation only; prose/formulas require human or independent static review',
            new_experiments=False, evaluation_accessed=False, formal_parameter_freeze=False))
        print('SEALED original index SHA256='+record(INDEX)['sha256'], flush=True)
    elif saved['facts'] != facts or saved['sources'] != bindings:
        raise ValueError('Exact source-derived fact replay mismatch')
    else:
        print('VERIFIED14 fact rows,25 source bindings and original manuscript/verifier hashes; no experiment.', flush=True)


if __name__ == '__main__':
    main()
