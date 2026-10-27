"""Fixed development-only v5 regression; candidate provenance cannot enter formal fitting."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs.build_semantic_review_pack_20261001 import record
from logs.diagnose_review8_20261012 import NAMES, verify_records, write_json
from HDBSCAN.scripts.crossing_candidate_v5 import (
    CANDIDATE_VERSION, crossing_candidate_audit, local_left_interaction_flags,
)
from HDBSCAN.scripts.scene_feature_rules import (
    summarize_events, partition_events_at_time, is_route_deviation_context_supported,
    route_deviation_decision_demand,
)
from HDBSCAN.scripts.corner_scoring import calculate_grouped_risk
from HDBSCAN.scripts.feature_selection import CLUSTERING_FEATURES
from HDBSCAN.scripts.frozen_model import source_hashes, require_feature_provenance
from HDBSCAN.scripts.experiment_partition import load_partition, assert_development_frame, assert_new_outputs

TABLES = ROOT / 'HDBSCAN/tables'
BASELINE = TABLES / 'scene_features_development_candidate700_20261001.csv'
EXTRACTOR = ROOT / 'HDBSCAN/scripts/scene_feature_hdbscan_v5.py'
FEATURES = TABLES / 'scene_features_crossing_v5_regression29_20261013.csv'
TRACKS = TABLES / 'crossing_v5_regression29_trajectory_20261013.json'
PROTOCOL = TABLES / 'crossing_v5_regression29_protocol_20261013.json'
COMPARISON = TABLES / 'crossing_v5_regression29_comparison_20261013.json'
SCORES = TABLES / 'crossing_v5_regression29_risk_20261013.csv'
STATUS = ROOT / 'logs/crossing_v5_regression29_20261013_status.json'
DOCUMENT = ROOT / 'outputs/人工复核/横向交互v5回归对照_20261013.md'
PENDING = ROOT / 'outputs/人工复核/待人工复核清单_20261013.md'
ALLOWED = {'crossing_vehicle_conflict_ratio', 'crossing_conflict_max_duration',
    'crossing_conflict_pre_stop_ratio', 'crossing_conflict_post_stop_ratio',
    'crossing_route_conflict_ratio', 'crossing_route_conflict_max_duration',
    'left_turn_cross_traffic_interaction_ratio', 'obstacle_induced_route_deviation_flag',
    'route_deviation_decision_demand'}
DEPENDENT = {'obstacle_induced_route_deviation_flag', 'route_deviation_decision_demand'}


def runtime_record():
    return {'python': platform.python_version(), 'executable': record(sys.executable),
            'packages': {p: importlib.metadata.version(p) for p in
                         ['numpy', 'pandas', 'nuscenes-devkit', 'shapely', 'pyquaternion']}}


def validate_runtime(expected):
    if runtime_record() != expected:
        raise ValueError('Frozen runtime mismatch; do not silently switch environments')


def load_bound_protocol():
    status = json.loads(STATUS.read_text(encoding='utf-8'))
    if Path(status['protocol']['path']).resolve() != PROTOCOL.resolve():
        raise ValueError('Protocol path mismatch')
    verify_records([status['protocol']])
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    validate_runtime(protocol['runtime'])
    verify_records(protocol['inputs'])
    if protocol['names'] != selection()[0] or protocol['environment'] != environment(protocol['names']):
        raise ValueError('Fixed candidate selection/environment changed')
    return protocol, status


def compare_frames(current, reference):
    if (list(current.columns) != list(reference.columns)
            or not current.scene_name.is_unique or not current.scene_token.is_unique
            or current.scene_name.tolist() != reference.scene_name.tolist()
            or current.scene_token.tolist() != reference.scene_token.tolist()):
        raise ValueError('Identity, order or schema drift')
    changes = []
    for old, new in zip(reference.to_dict('records'), current.to_dict('records')):
        for column in current.columns:
            if new[column] != old[column]:
                if column not in ALLOWED:
                    raise ValueError(f'Unrelated change: {new["scene_name"]}/{column}')
                changes.append({'scene_name': new['scene_name'], 'column': column,
                                'v4': old[column], 'v5': new[column]})
    return changes


def recompute_crossing_row(row, audit, conflict, left):
    times = audit['times']
    split = partition_events_at_time(conflict, times,
        row['ego_first_stop_time'] if row['ego_first_stop_time'] >= 0 else float('inf'))
    crossing, before, after = (summarize_events(flags, times) for flags in (conflict, split.before, split.after))
    route = summarize_events(audit['crossing_route_flags'], times)
    left_summary = summarize_events(left, times)
    supported = is_route_deviation_context_supported(row['traffic_light_control_density'],
        row['crossing_vehicle_exposure_ratio'], row['intersection_stop_ratio'], left_summary.ratio)
    deviation = bool(audit['obstacle_induced_route_deviation_candidate'] and supported)
    return {'crossing_vehicle_conflict_ratio': crossing.ratio,
        'crossing_conflict_max_duration': crossing.max_duration,
        'crossing_conflict_pre_stop_ratio': before.ratio, 'crossing_conflict_post_stop_ratio': after.ratio,
        'crossing_route_conflict_ratio': route.ratio, 'crossing_route_conflict_max_duration': route.max_duration,
        'left_turn_cross_traffic_interaction_ratio': left_summary.ratio,
        'obstacle_induced_route_deviation_flag': int(deviation),
        'route_deviation_decision_demand': route_deviation_decision_demand(row['blocked_path_obstacle_ratio'], deviation)}


def selection():
    controls = json.loads((TABLES/'crossing_regression33_protocol_20261001.json').read_text(encoding='utf-8'))['fixed_controls']
    selected = set(NAMES) | set(controls)
    metadata = json.loads((ROOT/'nuScenes/v1.0-trainval/scene.json').read_text(encoding='utf-8'))
    names = [r['name'] for r in metadata if r['name'] in selected]
    if len(names) != 29 or len(selected) != 29:
        raise ValueError('Fixed 8+21 scope drift')
    return names, controls


def environment(names):
    return {'SCENE_CLUSTER_SCENE_NAMES': ','.join(names), 'SCENE_CLUSTER_MAX_SCENES': str(len(names)),
        'SCENE_CLUSTER_START_INDEX': '0', 'SCENE_CLUSTER_FEATURE_OUTPUT': FEATURES.name,
        'SCENE_CLUSTER_AUDIT_OUTPUT': TRACKS.name, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1', 'NUMBA_NUM_THREADS': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'}


def prepare():
    names, controls = selection()
    assert_new_outputs([FEATURES, Path(str(FEATURES)+'.manifest.json'), Path(str(FEATURES)+'.quality.json'),
        TRACKS, PROTOCOL, STATUS, COMPARISON, SCORES, DOCUMENT, PENDING])
    baseline = pd.read_csv(BASELINE, float_precision='round_trip')
    require_feature_provenance(BASELINE, baseline)
    selected = baseline.set_index('scene_name').loc[names].reset_index()
    assert_development_frame(selected, load_partition())
    historical = json.loads((TABLES/'development_candidate700_comparison_20261001.json').read_text(encoding='utf-8'))
    if source_hashes() != historical['source_hashes']:
        raise ValueError('v4 must remain unchanged')
    bound = [BASELINE, Path(str(BASELINE)+'.manifest.json'), Path(str(BASELINE)+'.quality.json'),
        TABLES/'evaluation_split_20260924.csv', TABLES/'evaluation_split_20260924_manifest.json',
        TABLES/'crossing_regression33_protocol_20261001.json', EXTRACTOR,
        ROOT/'HDBSCAN/scripts/crossing_candidate_v5.py', ROOT/'HDBSCAN/tests/test_crossing_candidate_v5.py',
        Path(__file__), ROOT/'logs/test_crossing_v5_regression_20261013.py',
        ROOT/'logs/diagnose_review8_20261012.py', ROOT/'logs/build_semantic_review_pack_20261001.py',
        ROOT/'HDBSCAN/tests/test_evaluation_split.py']
    bound += [ROOT/'HDBSCAN/scripts'/name for name in source_hashes()]
    bound += list((ROOT/'nuScenes/v1.0-trainval').glob('*.json'))
    bound += list((ROOT/'nuScenes/maps/expansion').glob('*.json'))
    env = environment(names)
    subprocess.run([sys.executable, str(EXTRACTOR), '--preflight'], cwd=ROOT,
                   env={**os.environ, **env}, check=True)
    write_json(PROTOCOL, {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': CANDIDATE_VERSION, 'stage': 'fixed_before_candidate_extraction',
        'command': [sys.executable, *sys.argv], 'names': names, 'controls': controls,
        'selection': 'Eight diagnosed targets plus all21 previously fixed positive/negative controls, metadata order',
        'environment': env, 'inputs': [record(p) for p in bound], 'v4_sources': source_hashes(),
        'allowed_changed_columns': sorted(ALLOWED), 'evaluation_used': False, 'fit_allowed': False,
        'runtime': runtime_record()})
    write_json(STATUS, {'phase': 'prepared', 'protocol': record(PROTOCOL)})
    print('PREPARED:29 development scenes; independent v5, v4 unchanged', flush=True)


def check(write=True):
    protocol, status = load_bound_protocol()
    if source_hashes() != protocol['v4_sources']:
        raise ValueError('v4 sources changed')
    frame = pd.read_csv(FEATURES, float_precision='round_trip')
    assert_development_frame(frame, load_partition())
    if frame.scene_name.tolist() != protocol['names'] or frame.shape != (29, 129):
        raise ValueError('Candidate batch schema/identity drift')
    old = pd.read_csv(BASELINE, float_precision='round_trip').set_index('scene_name').loc[protocol['names']].reset_index()
    old = old[frame.columns]
    changes = compare_frames(frame, old)
    manifest_path, quality_path = Path(str(FEATURES)+'.manifest.json'), Path(str(FEATURES)+'.quality.json')
    manifest, quality = (json.loads(p.read_text(encoding='utf-8')) for p in (manifest_path, quality_path))
    verify_records([manifest[k] for k in ('input', 'output', 'partition', 'script', 'guard', 'feature_schema')])
    verify_records([manifest['extra'][k] for k in
                    ('candidate_rules', 'base_extractor', 'feature_rules', 'extraction_audit_code', 'quality_audit', 'trajectory_audit')])
    if (manifest['stage'] != 'candidate_feature_extraction' or manifest['extra']['formal_fit_allowed']
            or manifest['scene_names'] != protocol['names'] or manifest['extra']['candidate_version'] != CANDIDATE_VERSION):
        raise ValueError('Candidate manifest contract failed')
    try:
        require_feature_provenance(FEATURES, frame)
    except ValueError as exc:
        if 'Feature extraction version/provenance mismatch' not in str(exc):
            raise
    else:
        raise ValueError('Formal fitter unexpectedly accepted candidate')
    if (quality['query_exception_count'] or quality['scene_names'] != protocol['names']
            or any(r['kind'] != 'positive_inf' or r['column'] not in
                   {'merge_observed_min_distance', 'vru_observed_min_distance'} for r in quality['nonfinite_cells'])):
        raise ValueError('Candidate quality failed')
    verify_records([quality[k] for k in ('input', 'partition', 'script', 'audit_code')])
    audits = json.loads(TRACKS.read_text(encoding='utf-8'))
    if [r['scene_name'] for r in audits] != protocol['names']:
        raise ValueError('Trajectory identities mismatch')
    inclusive = frame.copy()
    states, unresolved, evidence_by_scene = Counter(), {}, {}
    for i, audit in enumerate(audits):
        if audit['scene_token'] != frame.iloc[i].scene_token:
            raise ValueError('Trajectory token mismatch')
        evidence = crossing_candidate_audit(audit['ego_positions'], audit['times'], audit['ego_yaws'],
            audit['ego_speeds'], audit['vehicle_tracks'], audit['crossing_projection_audit'])
        if evidence != audit['crossing_v5_audit']:
            raise ValueError('Candidate target evidence mismatch')
        effective, unknown = [False]*len(audit['times']), [False]*len(audit['times'])
        for item in evidence:
            effective[item['index']] |= item['effective_conflict']
            unknown[item['index']] |= item['unresolved']
            states[item['state']] += 1
        left = local_left_interaction_flags(audit['times'], audit['ego_yaws'], audit['vehicle_tracks'], evidence, audit['crossing_yield_flags'])
        if effective != audit['crossing_conflict_flags'] or unknown != audit['crossing_unresolved_flags'] or left != audit['left_turn_cross_traffic_interaction_flags']:
            raise ValueError('Candidate frame aggregation mismatch')
        recomputed = recompute_crossing_row(frame.iloc[i], audit, effective, left)
        for column, value in recomputed.items():
            np.testing.assert_allclose(value, frame.iloc[i][column], rtol=0, atol=1e-12)
        unknown_included = [a or b for a, b in zip(effective, unknown)]
        sensitivity_evidence = [{**item, 'effective_conflict': item['effective_conflict'] or item['unresolved']} for item in evidence]
        sensitivity_left = local_left_interaction_flags(audit['times'], audit['ego_yaws'], audit['vehicle_tracks'], sensitivity_evidence, audit['crossing_yield_flags'])
        for column, value in recompute_crossing_row(frame.iloc[i], audit, unknown_included, sensitivity_left).items():
            inclusive.at[i, column] = value
        unresolved[audit['scene_name']] = sum(unknown)/len(unknown)
        evidence_by_scene[audit['scene_name']] = evidence
    score = frame[['scene_name', 'scene_token']].copy()
    for prefix, source in [('v4', old), ('v5_resolved', frame), ('v5_with_unresolved', inclusive)]:
        for column, values in calculate_grouped_risk(source).items():
            score[prefix+'_'+column] = values.to_numpy()
    score['unresolved_crossing_ratio'] = [unresolved[n] for n in protocol['names']]
    changed_names = sorted({r['scene_name'] for r in changes})
    clustering = [r for r in changes if r['column'] in CLUSTERING_FEATURES]
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'version': CANDIDATE_VERSION,
        'protocol': record(PROTOCOL), 'features': record(FEATURES), 'quality': record(quality_path),
        'trajectory': record(TRACKS), 'manifest': record(manifest_path), 'changes': changes,
        'changed_scenes': changed_names, 'clustering_changes': clustering, 'candidate_state_counts': dict(states),
        'unresolved_by_scene': unresolved, 'query_exception_count': quality['query_exception_count'],
        'nonfinite_diagnostic_cells': quality['nonfinite_cell_count'], 'v4_unchanged': True,
        'formal_fit_refused': True, 'evaluation_used': False, 'semantic_acceptance': False,
        'score_note': 'Resolved vs uncertainty-inclusive sensitivity, not safety labels or monotone bounds; no weights changed.'}
    if write:
        assert_new_outputs([COMPARISON, SCORES, DOCUMENT, PENDING])
        with SCORES.open('x', encoding='utf-8', newline='') as stream:
            score.to_csv(stream, index=False)
        publish(frame, score, report, evidence_by_scene)
        report.update({'risk_comparison': record(SCORES), 'document': record(DOCUMENT), 'pending': record(PENDING)})
        write_json(COMPARISON, report)
        write_json(STATUS, {'phase': 'completed_candidate_requires_review', 'protocol': status['protocol'],
                            'updated_at_utc': datetime.now(timezone.utc).isoformat(),
                            'comparison': record(COMPARISON)}, False)
    else:
        saved = json.loads(COMPARISON.read_text(encoding='utf-8'))
        verify_records([saved[k] for k in ('protocol', 'features', 'quality', 'trajectory', 'manifest', 'risk_comparison', 'document', 'pending')])
        if saved['changes'] != changes or saved['candidate_state_counts'] != dict(states):
            raise ValueError('Saved comparison drift')
        expected_score = pd.read_csv(SCORES, float_precision='round_trip')
        pd.testing.assert_frame_equal(score, expected_score, check_dtype=False, rtol=1e-12, atol=1e-12)
    print(json.dumps({'phase': 'verified', 'scenes': len(frame), 'changed': changed_names,
                      'cells': len(changes), 'states': dict(states)}, ensure_ascii=False), flush=True)


def publish(frame, score, report, evidence):
    rows = score.set_index('scene_name')
    lines = ['# 横向交互 v5 小批回归对照', '', '2026-10-13。八条问题场景 + 21 条已有控制，开发集限定 29 条。'
        '这是候选版本回归，不是独立评价或危险标签。v4 来源/结果/模型不变，正式拟合入口拒绝本候选。', '',
        f'129 列/52 聚类字段清单不变；{len(report["changed_scenes"])} 条、{len(report["changes"])} 格变化，'
        f'其中聚类字段 {len(report["clustering_changes"])} 格。查询异常 0，'
        f'{report["nonfinite_diagnostic_cells"]} 个正 Inf 仅已知诊断距离。', '',
        '已解析分仍可能包含保护性/完整预测，不是已确认危险；包含未知分是假设未知预测保留的敏感性对照，'
        '两者不是上下界。未来未知不当作无风险，分数下降不等于改善。', '',
        '| 场景 | v4 固定分 | v5 已解析分 | v5 含未知分 | 未知帧比 | 状态计数 |',
        '| --- | ---: | ---: | ---: | ---: | --- |']
    for name in frame.scene_name:
        row = rows.loc[name]
        counts = dict(Counter(r['state'] for r in evidence[name]))
        lines.append(f'| {name} | {row.v4_risk:.6f} | {row.v5_resolved_risk:.6f} | '
                     f'{row.v5_with_unresolved_risk:.6f} | {row.unresolved_crossing_ratio:.4f} | {counts} |')
    lines += ['', '## 逐字段变化', '', '| 场景 | 字段 | v4 | v5 |', '| --- | --- | ---: | ---: |']
    lines += [f'| {r["scene_name"]} | {r["column"]} | {r["v4"]} | {r["v5"]} |' for r in report['changes']]
    lines += ['', '## 限制与待复核', '',
        '自车尺寸 4.5m×2m、1m 裕度与分段线性/最短角插值是工程假设，未做敏感性评价；'
        '响应保护不等于确认交通因果，地图/护栏、天气、VRU、TTC 本轮未修改。'
        '原始横向曝光和其他预筛参与者字段仍保留，不能把总体固定分直接解释为危险概率。', '',
        '[统一人工队列](F:/Scene_cluster/outputs/人工复核/待人工复核清单_20261013.md)，'
        '[执行记录](F:/Scene_cluster/logs/crossing_candidate_v5_20261013.md)。']
    with DOCUMENT.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(lines)+'\n')
    pending = ['# 待人工复核清单', '', '2026-10-13。统一暂存，不要求立即回复。仅开发反馈，不用于独立评价成绩。', '',
        '## 优先复核', '',
        '- 0815：末尾远车现在列未来未知；不认定无风险。起步邻车的既有过滤不变。',
        '- 0816：同步分离及局部传播修正是否符合环岛实际；仍须人工确认，不以分数下降验收。',
        '- 0453：规则停车与随后皮卡约束的并存；原始已删 0.499s 目标不是后续皮卡。',
        '- 0552：保护前段公交让行、后段卡车部分占道绕行；13.4/13.9s 已删小汽车身份仍未确认。', '',
        '## 本批新增变化或未知', '', '| 场景 | 改变字段 | 未知比例 | 逐目标状态 |', '| --- | --- | ---: | --- |']
    for name in frame.scene_name:
        changed = [r['column'] for r in report['changes'] if r['scene_name'] == name]
        if changed or report['unresolved_by_scene'][name] or name in ('scene-0453', 'scene-0552'):
            targets = '; '.join(f'{r["time_s"]:.3f}s/{r["instance_token"]}/{r["state"]}' for r in evidence[name]) or '无原始横向冲突候选'
            pending.append(f'| {name} | {", ".join(changed) or "无数值变化，仍须保护真实交互"} | '
                           f'{report["unresolved_by_scene"][name]:.4f} | {targets} |')
    pending += ['', '## 后续批次（本轮未改）', '',
        '- 0102：人行道 VRU 原始投影及护栏隔离，保留人工证据，不宣称自动修复。',
        '- 0669：对向静止车 TTC/障碍目标，转弯路线占用须另改；不是本轮横向修正效果。',
        '- 雨天、图像模糊仍是人工环境观察，没有新增自动天气风险特征。', '',
        '[本批完整对照](F:/Scene_cluster/outputs/人工复核/横向交互v5回归对照_20261013.md)。'
        '已有带时间 GIF 继续使用，本轮不重复导出。']
    with PENDING.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(pending)+'\n')


def run():
    protocol, status = load_bound_protocol()
    if status['phase'] != 'prepared':
        raise ValueError('Do not duplicate or resume a started batch implicitly')
    assert_new_outputs([FEATURES, Path(str(FEATURES)+'.manifest.json'), Path(str(FEATURES)+'.quality.json'), TRACKS])
    write_json(STATUS, {'phase': 'extracting', 'pid': os.getpid(), 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                        'protocol': status['protocol']}, False)
    try:
        subprocess.run([sys.executable, str(EXTRACTOR)], cwd=ROOT,
                       env={**os.environ, **protocol['environment']}, check=True)
        check()
    except Exception as exc:
        write_json(STATUS, {'phase': 'failed_requires_inspection', 'protocol': status['protocol'],
                            'error': f'{type(exc).__name__}: {exc}'}, False)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'check'])
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'run':
        run()
    else:
        check(write=False)
