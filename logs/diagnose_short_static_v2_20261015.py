"""Selected static anchors including brief events; independent diagnostic only."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs import diagnose_longitudinal_protection_v1_20261015 as prior
from logs.build_semantic_review_pack_20261001 import record
from logs.diagnose_review8_20261012 import verify_records, write_json

r = prior.r
parent = prior.parent
VERSION = 'short_static_diagnosis_v2_20261015'
PRIOR_SHA = 'fd405aeee930f47ad9534bbb84b5f4a49c09ffc74eed1b4377aa954fa5a7637b'
PRIOR_SEAL_SHA = '9678da24c4ff50e2d37dff18354a22cd6926350d7bc9aa98c33d90cbcc50caf5'
FOCUS = ['scene-0011', 'scene-0030', 'scene-0042', 'scene-0074', 'scene-0669']
ABSENCE_INFERRED = False
PROTOCOL = ROOT/'logs/short_static_diagnosis_v2_protocol_20261015.json'
EVIDENCE = ROOT/'logs/short_static_diagnosis_v2_evidence_20261015.json'
DOCUMENT = ROOT/'outputs/人工复核/短暂静态障碍与持续受阻对照_20261015.md'
SEAL = ROOT/'logs/short_static_diagnosis_v2_seal_20261015.json'
OUTPUTS = [EVIDENCE, DOCUMENT, SEAL]


def static_anchors(trace):
    flags = trace['static_flags']
    ids, selected, blocked = (trace[k] for k in ('stationary_ids', 'selected', 'blocked_flags'))
    if any(len(v) != len(flags) for v in (ids, selected, blocked)):
        raise ValueError('Static timeline mismatch')
    anchors = set()
    for i, flag in enumerate(flags):
        if type(flag) is not bool or type(blocked[i]) is not bool:
            raise ValueError('Static flags must be booleans')
        if blocked[i] and not flag:
            raise ValueError('Blocked frame lacks static evidence')
        if flag:
            c = selected[i]
            if (not ids[i] or c is None or c['instance_token'] != ids[i]
                    or not c.get('annotation_token')):
                raise ValueError('Missing/mismatched selected static identity')
            anchors.add((i, ids[i]))
    return anchors


def anchor_roles(anchors, minimum):
    roles = {k: ['static_selected'] for k in sorted(anchors)}
    if minimum:
        key = (minimum['frame_index'], minimum['instance_token'])
        roles.setdefault(key, []).append('minimum_ttc')
    return roles


def summarize_static(audit, trace):
    prior.timeline(audit)
    anchors = static_anchors(trace)
    flags, selected = trace['static_flags'], trace['selected']
    first = min((i for i, _ in anchors), default=-1)
    heading = audit['ego_yaws'][first] if first >= 0 else 0.
    summary = r.summarize_events(flags, audit['times'])
    distance = min((selected[i]['clearance'] for i, _ in anchors), default=80.)
    shift = r.lateral_shift_after_index(audit['ego_positions'], audit['times'], first, heading, 10.)
    turn = r.net_heading_change_after_index(audit['ego_yaws'], audit['times'], first, heading, 10.)
    strict = r.is_evasive_lane_change(summary.count, shift, turn,
        stationary_max_duration=summary.max_duration, stationary_min_distance=distance)
    return dict(stationary_lead_obstacle_ratio=summary.ratio, stationary_lead_event_count=summary.count,
        stationary_lead_min_dist=distance, ego_evasive_lateral_shift=shift,
        ego_evasive_net_heading_change=turn, ego_evasive_lane_change_flag=int(strict)), summary


def candidate_stages(saved):
    trace = saved['candidate']
    rejected = {tuple(v) for v in saved['rejected']}
    legacy = {(e['frame_index'], e['instance_token']) for e in trace['legacy_postfiltered_events']}
    counts = Counter()
    for i, frame in enumerate(saved['ledger']):
        for c in frame:
            selected = trace['selected'][i]
            if (i, c['instance_token']) in rejected:
                reason = 'v7_preselection_gated'
            elif c['supported'] is not True:
                reason = 'map_unsupported'
            elif c['clearance'] is None:
                reason = 'no_positive_clearance'
            elif selected is None or c['instance_token'] != selected['instance_token']:
                reason = 'not_selected_nearest'
            elif (i, c['instance_token']) in legacy:
                reason = 'legacy_ttc_postfilter'
            elif trace['static_flags'][i]:
                reason = 'selected_static'
            elif trace['temporary_flags'][i]:
                reason = 'selected_temporary_stop'
            else:
                reason = 'selected_not_static'
            counts[reason] += 1
    return dict(counts)


def diagnose(audit, saved, row):
    trace = saved['candidate']
    fields, summary = summarize_static(audit, trace)
    if any(row[k] != v for k, v in fields.items()):
        raise ValueError('Frozen strict-avoidance source reproduction drift')
    anchors = static_anchors(trace)
    minimum = next((e for e in trace['events'] if e['scene_time'] == row['min_ttc_scene_time']
                    and e['annotation_token'] == row['min_ttc_target_annotation_token']), None)
    roles = anchor_roles(anchors, minimum)
    queries = prior.route_queries(audit, set(roles))
    for query in queries:
        query['diagnostic_roles'] = roles[query['index'], query['instance_token']]
        query['scene_time_s'] = audit['times'][query['index']]
    static_rows = []
    for i, instance in sorted(anchors):
        selected = trace['selected'][i]
        candidates = [c for c in saved['ledger'][i] if c['instance_token'] == instance]
        if candidates != [selected]:
            raise ValueError('Selected static candidate differs from bound identity ledger')
        targets = [v for v in audit['vehicle_tracks'][instance] if v['index'] == i]
        if len(targets) != 1:
            raise ValueError('Static target missing/duplicate trajectory frame')
        static_rows.append(dict(index=i, scene_time_s=audit['times'][i],
            instance_token=instance, annotation_token=selected['annotation_token'],
            category=selected['category'], clearance_m=selected['clearance'],
            heading_delta_rad=selected['heading_delta'], target_speed_mps=selected['target_speed'],
            scene_target_max_speed_mps=audit['instance_max_speeds'][instance],
            bounded_stationary=instance in audit['bounded_stationary_instances'],
            target_position=targets[0]['position'], blocked=trace['blocked_flags'][i],
            windows=[prior.motion_window(audit, i, h) for h in prior.WINDOWS]))
    segments = prior.target_episodes(trace['static_flags'], trace['stationary_ids'], audit['times'])
    return dict(scene_name=audit['scene_name'], scene_token=audit['scene_token'],
        reproduced_strict_fields=fields, static_max_legacy_duration_s=summary.max_duration,
        static_target_episodes=segments, static_anchor_count=len(anchors),
        blocked_anchor_count=sum(trace['blocked_flags']), static_anchors=static_rows,
        candidate_stage_counts=candidate_stages(saved), minimum_ttc_event=minimum,
        route_queries=queries, no_static_evidence_means_obstacle_absence=ABSENCE_INFERRED,
        target_identity_human_confirmed=False, causal_acceptance=False, feature_updates=False)


def verify_ancestors():
    prior.load_protocol(PRIOR_SHA)
    if record(prior.SEAL)['sha256'] != PRIOR_SEAL_SHA:
        raise ValueError('Original diagnosis seal required; no refreshed bindings')
    seal = json.loads(prior.SEAL.read_text(encoding='utf-8'))
    verify_records([seal['protocol'], *seal['outputs']])


def inputs():
    return [prior.PROTOCOL, prior.SEAL, parent.PROTOCOL, parent.REPORT, parent.FEATURES,
        parent.EVENTS, parent.legacy.TRACKS, Path(prior.__file__), Path(__file__),
        ROOT/'logs/test_short_static_diagnosis_v2_20261015.py']


def prepare():
    verify_ancestors()
    prior.assert_new_outputs([PROTOCOL, *OUTPUTS])
    write_json(PROTOCOL, dict(version=VERSION, created_at_utc=datetime.now(timezone.utc).isoformat(),
        command=[sys.executable, *sys.argv], focus=FOCUS, prior_sha256=PRIOR_SHA,
        prior_seal_sha256=PRIOR_SEAL_SHA, inputs=[record(p) for p in inputs()],
        runtime=parent.legacy.runtime_record(), outputs=[str(p.resolve()) for p in OUTPUTS],
        diagnostic_only=True, include_brief_static_without_blocked=True, feature_updates=False))
    print('PREPARED original protocol SHA256='+record(PROTOCOL)['sha256'], flush=True)


def load_protocol(expected):
    if not expected or record(PROTOCOL)['sha256'] != expected:
        raise ValueError('Original v2 diagnosis protocol SHA256 required')
    p = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_records(p['inputs'])
    parent.legacy.validate_runtime(p['runtime'])
    verify_ancestors()
    if (p['version'] != VERSION or p['focus'] != FOCUS or p['prior_sha256'] != PRIOR_SHA
            or p['prior_seal_sha256'] != PRIOR_SEAL_SHA
            or p['outputs'] != [str(p.resolve()) for p in OUTPUTS]):
        raise ValueError('Diagnostic contract drift')
    return p


def compute():
    rows = prior.pd.read_csv(parent.FEATURES, float_precision='round_trip')
    prior.assert_development_frame(rows, prior.load_partition())
    audits = json.loads(parent.legacy.TRACKS.read_text(encoding='utf-8'))
    saved = json.loads(parent.EVENTS.read_text(encoding='utf-8'))['scenes']
    p = json.loads(parent.PROTOCOL.read_text(encoding='utf-8'))
    if (rows.shape != (29, 129) or rows.scene_name.tolist() != p['names']
            or rows.scene_token.tolist() != p['tokens']
            or [a['scene_name'] for a in audits] != p['names'] or [a['scene_token'] for a in audits] != p['tokens']
            or [a['scene_name'] for a in saved] != p['names'] or [a['scene_token'] for a in saved] != p['tokens']):
        raise ValueError('Fixed development identity/schema/order drift')
    joined = {a['scene_name']: (a, s, row) for a, s, row in zip(audits, saved, rows.to_dict('records'))}
    return dict(version=VERSION, scope=FOCUS, scenes=[diagnose(*joined[n]) for n in FOCUS],
                feature_updates=False, evaluation_used=False, absence_inferred=False)


def document(result):
    lines = ['# 短暂静态障碍与持续受阻对照', '',
        '2026-10-15。仅诊断既有开发轨迹，不提取新数据、不改保护规则或TTC/特征/评分。'
        '程序选中身份未得到逐目标人工确认，不把场景级避障反馈直接赋给某辆车。', '',
        '| 场景 | 静态选中帧 | blocked帧 | 旧静态最长时长/s | 严格避障 | 同目标片段数 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for s in result['scenes']:
        lines.append(f'| {s["scene_name"]} | {s["static_anchor_count"]} | {s["blocked_anchor_count"]} | '
            f'{s["static_max_legacy_duration_s"]:.3f} | {s["reproduced_strict_fields"]["ego_evasive_lane_change_flag"]} | '
            f'{len(s["static_target_episodes"])} |')
    lines += ['', '## 静态目标与几何查询', '',
        '所有静态选中帧均查询，包括不满足0.8秒blocked门槛的短片段；最低TTC目标单独标角色，不能混用。', '',
        '| 场景 | 时刻/s | 实例/角色 | 几何状态 | 路线下界/m |', '| --- | ---: | --- | --- | ---: |']
    for s in result['scenes']:
        for q in s['route_queries']:
            lines.append(f'| {s["scene_name"]} | {q["scene_time_s"]:.3f} | '
                f'{q["instance_token"]} / {",".join(q["diagnostic_roles"])} | '
                f'{q["relation"]} | {q["spatial_clearance_lower_m"]} |')
    lines += ['', '## 候选经过的计算阶段', '', '| 场景 | 候选数量分解（目标×帧） |', '| --- | --- |']
    lines += [f'| {s["scene_name"]} | {s["candidate_stage_counts"]} |' for s in result['scenes']]
    lines += ['', '## 边界', '',
        '静态时长沿用旧算法的中位帧间隔补偿；单帧不是连续观测了半秒。严格避障的短片段分支是现有规则，'
        '不是本次新加门槛。已观测路线可能正是避让之后的路线，separated不能单独推翻真实避障；'
        'potential不是实际碰撞，unknown不是安全。', '',
        '0042没有选中静态证据，不能据此否定人工观察的两次静止车绕行。'
        '候选阶段分解只能说明已标注候选如何经过当前计算链，不能证明标注完整或检测到所有障碍。'
        '本轮不增添目标标签、不改变阈值，也不把程序选中的truck/motorcycle冒充专家逐目标确认。', '',
        '0669保护改版、0552/0067新目标语义及正式实验选择继续挂起；本结果仅补正例证据边界，不修复或推广v7。', '',
        '[数值证据](F:/Scene_cluster/logs/short_static_diagnosis_v2_evidence_20261015.json) · '
        '[执行与解释](F:/Scene_cluster/logs/short_static_diagnosis_v2_20261015.md)']
    return '\n'.join(lines)+'\n'


def run(expected):
    p = load_protocol(expected)
    prior.assert_new_outputs(OUTPUTS)
    result = compute()
    verify_records(p['inputs'])
    write_json(EVIDENCE, result)
    with DOCUMENT.open('x', encoding='utf-8') as f:
        f.write(document(result))
    verify_records(p['inputs'])
    write_json(SEAL, dict(protocol=record(PROTOCOL), outputs=[record(EVIDENCE), record(DOCUMENT)],
        completed_at_utc=datetime.now(timezone.utc).isoformat(), command=[sys.executable, *sys.argv],
        stage='completed_short_static_diagnosis', feature_updates=False))
    print('COMPLETED diagnostic only: '+','.join(FOCUS), flush=True)


def check(expected):
    p = load_protocol(expected)
    seal = json.loads(SEAL.read_text(encoding='utf-8'))
    verify_records([seal['protocol'], *seal['outputs']])
    if seal['protocol'] != record(PROTOCOL) or seal['outputs'] != [record(EVIDENCE), record(DOCUMENT)]:
        raise ValueError('Unexpected diagnostic binding')
    result = compute()
    if (json.loads(EVIDENCE.read_text(encoding='utf-8')) != result
            or DOCUMENT.read_text(encoding='utf-8') != document(result)):
        raise ValueError('Exact static-target diagnostic replay mismatch')
    verify_records(p['inputs'])
    print('VERIFIED exact short-static diagnosis and original source/runtime/output seals; no feature updates.', flush=True)


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
