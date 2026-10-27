"""Freeze and replay existing development29 tracks; no NuScenes extraction or fit."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs import crossing_v5_2_regression_20261013 as parent
from logs.build_semantic_review_pack_20261001 import record
from logs.diagnose_review8_20261012 import verify_records, write_json
from HDBSCAN.scripts import crossing_candidate_v6 as rules
from HDBSCAN.scripts.experiment_partition import assert_new_outputs, assert_development_frame, load_partition
from HDBSCAN.scripts.frozen_model import require_feature_provenance
from HDBSCAN.scripts.scene_feature_rules import distance_to_polyline
from HDBSCAN.scripts.feature_selection import CLUSTERING_FEATURES

TABLES = ROOT / 'HDBSCAN/tables'
PROTOCOL = TABLES / 'crossing_v6_replay29_protocol_20261014.json'
FEATURES = TABLES / 'scene_features_crossing_v6_replay29_20261014.csv'
MANIFEST = Path(str(FEATURES)+'.manifest.json')
EVIDENCE = TABLES / 'crossing_v6_replay29_evidence_20261014.json'
REPORT = TABLES / 'crossing_v6_replay29_comparison_20261014.json'
DOCUMENT = ROOT / 'outputs/人工复核/横向交互v6重放对照_20261014.md'
STATUS = ROOT / 'logs/crossing_v6_replay29_20261014_status.json'
OUTPUTS = [FEATURES, MANIFEST, EVIDENCE, REPORT, DOCUMENT]
ALLOWED = parent.ALLOWED
EVENT_CONTROLS = {
    'scene-0068': {'crossing': {'727349048e9044d98846cbeeb3a1b5fd': [15, 16]}},
    'scene-0552': {'local_left': {'8f7327b31d334c768455a9e22adbc6db': [0, 1, 2],
                                  '8300fb2dc4554627a01ba8a3084325fe': [0, 1, 2, 3, 4, 5]}}}


def compare_frames(current, reference):
    if (list(current.columns) != list(reference.columns)
            or not current.scene_name.is_unique or not current.scene_token.is_unique
            or current.scene_name.tolist() != reference.scene_name.tolist()
            or current.scene_token.tolist() != reference.scene_token.tolist()):
        raise ValueError('Identity/order/schema drift')
    changes = []
    for old, new in zip(reference.to_dict('records'), current.to_dict('records')):
        for column in current.columns:
            if new[column] != old[column]:
                if column not in ALLOWED:
                    raise ValueError(f'Unrelated change: {new["scene_name"]}/{column}')
                changes.append(dict(scene_name=new['scene_name'], column=column,
                                    v5_2=old[column], v6=new[column]))
    return changes


def check_controls(current, reference):
    a, b = current.set_index('scene_name'), reference.set_index('scene_name')
    for name, columns in {'scene-0068': ['crossing_vehicle_conflict_ratio',
            'left_turn_cross_traffic_interaction_ratio'],
            'scene-0552': ['left_turn_cross_traffic_interaction_ratio']}.items():
        for column in columns:
            if name not in a.index or not a.loc[name, column] > 0:
                raise ValueError(f'Lost positive control: {name}/{column}')
    for name, columns in {'scene-0107': ['adjacent_lane_intrusion_ratio'],
            'scene-0453': ['stop_sign_stop_candidate', 'crossing_vehicle_exposure_ratio'],
            'scene-0552': ['stop_sign_stop_candidate', 'crossing_vehicle_exposure_ratio']}.items():
        for column in columns:
            if name not in a.index or a.loc[name, column] != b.loc[name, column]:
                raise ValueError(f'Changed protected context: {name}/{column}')
    return dict(rolling_yield_nonzero_representation=True, bus_context_nonzero_representation=True,
                bus_intrusion_unchanged=True, stop_and_raw_exposure_unchanged=True,
                later_pickup_causal_detection_claimed=False, semantic_acceptance=False)


def check_event_controls(audits, diagnostic):
    old, new = ({a['scene_name']: a for a in group} for group in (audits, diagnostic))
    for name, kinds in EVENT_CONTROLS.items():
        if name not in old or name not in new:
            raise ValueError('Missing protected event scene')
        a, b = old[name], new[name]
        for instance, indices in kinds.get('crossing', {}).items():
            for index in indices:
                identity = (index, instance)
                original = [r for r in a['crossing_v5_audit']
                            if (r['index'], r['instance_token']) == identity]
                current = [r for r in b['crossing']
                           if (r['index'], r['instance_token']) == identity]
                if (len(original) != 1 or not original[0]['effective_conflict']
                        or len(current) != 1 or not current[0]['effective_conflict']):
                    raise ValueError(f'Lost same-target crossing control: {name}/{identity}')
        for instance, indices in kinds.get('local_left', {}).items():
            track = a['vehicle_tracks'].get(instance)
            if not track or not any(r['category'].startswith('vehicle.bus') for r in track):
                raise ValueError('Protected bus context missing')
            evidence = [r for r in b['crossing'] if r['instance_token'] == instance]
            baseline_evidence = [r for r in a['crossing_v5_audit'] if r['instance_token'] == instance]
            original = parent.local_left_interaction_flags(a['times'], a['ego_yaws'],
                {instance: track}, baseline_evidence, a['crossing_yield_flags'], a['ego_speeds'])
            current = rules.local_left_interaction_flags(a['times'], a['ego_yaws'],
                {instance: track}, evidence, a['crossing_yield_flags'], a['ego_speeds'],
                route_evidence=[r for r in b['routes'] if r['instance_token'] == instance])
            if any(not original[i] or not current[i] for i in indices):
                raise ValueError(f'Lost same-target local bus context: {name}/{instance}')
    return dict(fixed_target_frames_retained=EVENT_CONTROLS,
                bus_visual_identity_individually_confirmed=False, causal_acceptance=False)


def route_flags(audit, evidence):
    times, positions = np.array(audit['times']), np.array(audit['ego_positions'])
    flags = [False]*len(times)
    for item in evidence:
        if not item['effective_conflict']:
            continue
        k = item['index']
        future = np.flatnonzero((times >= times[k]) & (times-times[k] <= 6.))
        route = positions[future].tolist()
        for row in audit['vehicle_tracks'][item['instance_token']]:
            i = row['index']
            if i in future and (distance_to_polyline(row['position'], route) <= 2.5
                    and np.linalg.norm(np.array(row['position'])-positions[i]) <= 10.):
                flags[k] = True
                break
    return flags


def replay(frame, audits):
    if (frame.shape != (29, 129) or len(audits) != 29
            or frame.scene_name.tolist() != [a['scene_name'] for a in audits]
            or frame.scene_token.tolist() != [a['scene_token'] for a in audits]):
        raise ValueError('Fixed29/schema/trajectory identity mismatch')
    current, diagnostic = frame.copy(), []
    for i, audit in enumerate(audits):
        if route_flags(audit, audit['crossing_v5_audit']) != audit['crossing_route_flags']:
            raise ValueError('Cannot exactly replay parent route flags; do not approximate')
        routes = rules.audit_route_relations(audit['ego_positions'], audit['times'],
                                            audit['ego_yaws'], audit['vehicle_tracks'])
        evidence = rules.crossing_candidate_audit(audit['ego_positions'], audit['times'],
            audit['ego_yaws'], audit['ego_speeds'], audit['vehicle_tracks'], audit['crossing_projection_audit'])
        conflict = [False]*len(audit['times'])
        for item in evidence:
            conflict[item['index']] |= item['effective_conflict']
        left = rules.local_left_interaction_flags(audit['times'], audit['ego_yaws'],
            audit['vehicle_tracks'], evidence, audit['crossing_yield_flags'], audit['ego_speeds'],
            route_evidence=routes)
        updated = {**audit, 'crossing_route_flags': route_flags(audit, evidence)}
        for column, value in parent.recompute_crossing_row(frame.iloc[i], updated, conflict, left).items():
            current.at[i, column] = value
        old_unknown = {(r['index'], r['instance_token']) for r in audit['crossing_v5_audit'] if r['unresolved']}
        new_unknown = {(r['index'], r['instance_token']) for r in evidence if r['unresolved']}
        if not old_unknown <= new_unknown:
            raise ValueError('Lost parent uncertainty')
        diagnostic.append(dict(scene_name=audit['scene_name'], scene_token=audit['scene_token'],
            routes=routes, crossing=evidence, conflict_flags=conflict, local_left_flags=left,
            route_flags=updated['crossing_route_flags']))
    return current, diagnostic


def inputs():
    return [parent.PROTOCOL, parent.COMPARISON, parent.FEATURES, parent.TRACKS,
        Path(str(parent.FEATURES)+'.manifest.json'), Path(str(parent.FEATURES)+'.quality.json'),
        ROOT/'HDBSCAN/tables/evaluation_split_20260924.csv',
        ROOT/'HDBSCAN/tables/evaluation_split_20260924_manifest.json',
        ROOT/'logs/development_review_feedback10_20261014.md',
        ROOT/'HDBSCAN/scripts/crossing_candidate_v6.py',
        ROOT/'HDBSCAN/tests/test_crossing_candidate_v6.py', Path(__file__),
        ROOT/'logs/test_crossing_v6_replay_20261014.py',
        ROOT/'logs/crossing_v5_2_regression_20261013.py']


def prepare():
    parent.check(write=False)
    assert_new_outputs([PROTOCOL, STATUS, *OUTPUTS])
    frame = pd.read_csv(parent.FEATURES, float_precision='round_trip')
    assert_development_frame(frame, load_partition())
    protocol = dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
        version=rules.CANDIDATE_VERSION, stage='fixed_before_candidate_replay',
        names=frame.scene_name.tolist(), scene_tokens=frame.scene_token.tolist(),
        inputs=[record(p) for p in inputs()], runtime=parent.runtime_record(),
        outputs=[str(p.resolve()) for p in OUTPUTS],
        allowed_changed_columns=sorted(ALLOWED),
        event_controls=EVENT_CONTROLS,
        command=[sys.executable, *sys.argv],
        geometry_model='Piecewise-linear centers/sizes; shortest yaw; conservative swept rectangle envelopes',
        route_window='Same-target real six-second bracket versus remaining observed ego route; no extrapolation',
        passage='Require travel and end-clearance gain each >= ego length after closest observed body approach',
        clearance_margin_m=1., ego_length_m=4.5, ego_width_m=2.,
        annotation='Conditional observed-route filter, not lane identity, causal inference or continuous real-world safety proof',
        new_extraction=False, fit_allowed=False, evaluation_used=False,
        deferred=['TTC', 'VRU', 'partial_truck_bypass', 'weather', 'weights', 'full700'])
    write_json(PROTOCOL, protocol)
    write_json(STATUS, dict(phase='prepared', protocol=record(PROTOCOL)))
    print('PREPARED original protocol SHA256='+record(PROTOCOL)['sha256'], flush=True)


def load_protocol(expected):
    if not expected or len(expected) != 64:
        raise ValueError('Original expected protocol SHA256 required; never refresh seal')
    if record(PROTOCOL)['sha256'] != expected:
        raise ValueError('Original protocol mismatch')
    status = json.loads(STATUS.read_text(encoding='utf-8'))
    verify_records([status['protocol']])
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_records(protocol['inputs'])
    parent.validate_runtime(protocol['runtime'])
    parent.check(write=False)
    if (protocol['version'] != rules.CANDIDATE_VERSION or protocol['allowed_changed_columns'] != sorted(ALLOWED)
            or protocol['event_controls'] != EVENT_CONTROLS
            or protocol['outputs'] != [str(p.resolve()) for p in OUTPUTS]):
        raise ValueError('Replay contract drift')
    return protocol, status


def compute(protocol):
    frame = pd.read_csv(parent.FEATURES, float_precision='round_trip')
    assert_development_frame(frame, load_partition())
    if frame.scene_name.tolist() != protocol['names'] or frame.scene_token.tolist() != protocol['scene_tokens']:
        raise ValueError('Frozen replay membership drift')
    audits = json.loads(parent.TRACKS.read_text(encoding='utf-8'))
    current, diagnostic = replay(frame, audits)
    changes = compare_frames(current, frame)
    controls = check_controls(current, frame)
    controls.update(check_event_controls(audits, diagnostic))
    states = Counter(r['state'] for a in diagnostic for r in a['crossing'])
    route_states = Counter(r['relation'] for a in diagnostic for r in a['routes'])
    return frame, current, diagnostic, changes, controls, dict(states), dict(route_states)


def document(frame, current, changes):
    old, new = frame.set_index('scene_name'), current.set_index('scene_name')
    lines = ['# 横向交互 v6 固定29条轨迹重放', '',
        '2026-10-14。只重放冻结v5.2开发29的轨迹，没有重新提取nuScenes或拟合。候选不能用于正式拟合。', '',
        f'{len(set(c["scene_name"] for c in changes))}条/{len(changes)}格变化。帧比不是危险概率，下降不等于独立有效性通过。', '',
        '| 场景 | 横向候选 v5.2 → v6 | 局部左转交互 v5.2 → v6 |', '| --- | --- | --- |']
    for name in frame.scene_name:
        lines.append(f'| {name} | {old.loc[name,"crossing_vehicle_conflict_ratio"]:.6f} → '
            f'{new.loc[name,"crossing_vehicle_conflict_ratio"]:.6f} | '
            f'{old.loc[name,"left_turn_cross_traffic_interaction_ratio"]:.6f} → '
            f'{new.loc[name,"left_turn_cross_traffic_interaction_ratio"]:.6f} |')
    lines += ['', '## 逐格变化', '', '| 场景 | 字段 | v5.2 | v6 |', '| --- | --- | ---: | ---: |']
    lines += [f'| {c["scene_name"]} | {c["column"]} | {c["v5_2"]} | {c["v6"]} |' for c in changes]
    lines += ['', '## 解释边界', '',
        '沿用1m裕度及4.5m×2m自车尺寸；目标真实六秒括界与自车剩余观测路线分别作带方向车身包络。'
        '包络之间分离且已观测到驶离相关区域，才能排除路线无关候选；没有通行完成证据、缺帧或未来不足则未知。'
        '当前未同时接近不能删除成功让行：目标可能占用自车稍后通过的路线。包络接近只表示可能相关，不证明实际冲突。', '',
        '这是条件于观测路线和分段线性/最短角模型的事后候选过滤，不是因果归因、精确车道识别或在线预警；'
        '大曲率、标注尺寸误差和反事实意图仍有限。约1m边缘的结果须审慎，未做参数敏感性评价。'
        '原始曝光与规则停车保留，后续皮卡的因果识别未新增；0552部分卡车绕行、VRU与TTC尚未修复。', '',
        '12个原v5.2未知目标不清零；新路线证据不足另记未知，不贴安全标签。'
        '本轮没有新查询异常审计，原提取质量属于v5.2来源，不冒称重提结果。', '',
        '[人工原话](F:/Scene_cluster/logs/development_review_feedback10_20261014.md)，'
        '[执行记录](F:/Scene_cluster/logs/crossing_v6_replay_20261014.md)。']
    return '\n'.join(lines)+'\n'


def run(expected):
    protocol, status = load_protocol(expected)
    if status['phase'] != 'prepared':
        raise ValueError('Replay already started; do not rerun or overwrite')
    assert_new_outputs(OUTPUTS)
    write_json(STATUS, dict(phase='replaying', protocol=status['protocol']), False)
    try:
        old, current, diagnostic, changes, controls, states, route_states = compute(protocol)
        verify_records(protocol['inputs'])
        with FEATURES.open('x', encoding='utf-8', newline='') as stream:
            current.to_csv(stream, index=False)
        write_json(EVIDENCE, dict(version=rules.CANDIDATE_VERSION, protocol=record(PROTOCOL), scenes=diagnostic))
        write_json(MANIFEST, dict(stage='candidate_feature_replay', fit_scope='development',
            scene_names=protocol['names'], output=record(FEATURES), partition=load_partition()['file'],
            input=record(parent.FEATURES), script=record(Path(__file__)),
            feature_schema=record(ROOT/'HDBSCAN/scripts/feature_selection.py'),
            extra=dict(formal_fit_allowed=False, new_extraction=False,
                       feature_rules=record(ROOT/'HDBSCAN/scripts/scene_feature_rules.py'))))
        try:
            require_feature_provenance(FEATURES, current)
        except ValueError as exc:
            if 'Feature extraction version/provenance mismatch' not in str(exc):
                raise
        else:
            raise ValueError('Formal fitter accepted replay candidate')
        with DOCUMENT.open('x', encoding='utf-8') as stream:
            stream.write(document(old, current, changes))
        report = dict(version=rules.CANDIDATE_VERSION, protocol=record(PROTOCOL),
            outputs=[record(p) for p in [FEATURES, MANIFEST, EVIDENCE, DOCUMENT]], changes=changes,
            changed_scenes=sorted(set(c['scene_name'] for c in changes)),
            clustering_changes=[c for c in changes if c['column'] in CLUSTERING_FEATURES],
            crossing_states=states, route_states=route_states, controls=controls,
            formal_fit_refused=True, new_extraction=False, evaluation_used=False, semantic_acceptance=False)
        write_json(REPORT, report)
        write_json(STATUS, dict(phase='completed_candidate_requires_review', protocol=status['protocol'],
            report=record(REPORT), completed_at_utc=datetime.now(timezone.utc).isoformat()), False)
        print(json.dumps(dict(phase='completed', scenes=29, changed=report['changed_scenes'],
                             cells=len(changes), crossing_states=states, route_states=route_states)), flush=True)
    except Exception as exc:
        write_json(STATUS, dict(phase='failed_requires_inspection', protocol=status['protocol'],
                                error=f'{type(exc).__name__}: {exc}'), False)
        raise


def check(expected):
    protocol, status = load_protocol(expected)
    if status['phase'] != 'completed_candidate_requires_review':
        raise ValueError('Replay not completed')
    verify_records([status['report']])
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    verify_records([report['protocol'], *report['outputs']])
    old, current, diagnostic, changes, controls, states, route_states = compute(protocol)
    saved = pd.read_csv(FEATURES, float_precision='round_trip')
    pd.testing.assert_frame_equal(current, saved, check_dtype=False, rtol=1e-12, atol=1e-12)
    if (json.loads(EVIDENCE.read_text(encoding='utf-8'))['scenes'] != diagnostic
            or changes != report['changes'] or controls != report['controls']
            or states != report['crossing_states'] or route_states != report['route_states']
            or DOCUMENT.read_text(encoding='utf-8') != document(old, current, changes)):
        raise ValueError('Exact replay mismatch')
    print('VERIFIED original source/runtime/output seals and exact29 replay; no extraction/fit/evaluation.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'check'])
    parser.add_argument('--expected-protocol-sha')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'run':
        run(args.expected_protocol_sha)
    else:
        check(args.expected_protocol_sha)
