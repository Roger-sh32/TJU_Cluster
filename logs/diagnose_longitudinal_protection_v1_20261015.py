"""Read-only fixed-development protection diagnosis; no feature or gate updates."""

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
from logs import longitudinal_v7_replay_20261015 as parent
from logs.build_semantic_review_pack_20261001 import record
from logs.diagnose_review8_20261012 import verify_records, write_json
from HDBSCAN.scripts import scene_feature_rules as r
from HDBSCAN.scripts import crossing_candidate_v6 as geometry
from HDBSCAN.scripts.experiment_partition import assert_development_frame, assert_new_outputs, load_partition

VERSION = 'longitudinal_protection_diagnosis_v1_20261015'
PARENT_SHA = 'ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d'
PARENT_REPORT_SHA = 'b7df6d51107f04cf3b7fdf9142fcddf24cec1a997e99277555ce3eab4872bdf3'
FOCUS = ['scene-0669', 'scene-0011', 'scene-0030', 'scene-0074', 'scene-0026']
WINDOWS = [1., 3., 6., 10.]
PROTOCOL = ROOT/'logs/longitudinal_protection_diagnosis_v1_protocol_20261015.json'
EVIDENCE = ROOT/'logs/longitudinal_protection_diagnosis_v1_evidence_20261015.json'
DOCUMENT = ROOT/'outputs/人工复核/纵向绕行保护根因诊断_20261015.md'
SEAL = ROOT/'logs/longitudinal_protection_diagnosis_v1_seal_20261015.json'
OUTPUTS = [EVIDENCE, DOCUMENT, SEAL]


def timeline(audit):
    times, yaws = geometry.parent._timeline(audit['times'], audit['ego_yaws'])
    positions, speeds = np.asarray(audit['ego_positions'], float), np.asarray(audit['ego_speeds'], float)
    if (positions.shape != (len(times), 2) or speeds.shape != times.shape
            or not np.isfinite(positions).all() or not np.isfinite(speeds).all()):
        raise ValueError('Invalid diagnostic trajectory')
    return times, yaws, positions, speeds


def target_episodes(flags, identities, times):
    if len(flags) != len(identities) or len(flags) != len(times):
        raise ValueError('Mismatched episode metadata')
    if any(type(f) is not bool for f in flags) or any(f and not t for f, t in zip(flags, identities)):
        raise ValueError('Active episode lacks strict flag/target identity')
    if not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError('Invalid episode timestamps')
    episodes, own = [], []
    for i, active in enumerate(flags):
        if own and (not active or identities[i] != identities[own[-1]] or times[i]-times[own[-1]] > .75):
            episodes.append(own)
            own = []
        if active:
            own.append(i)
    if own:
        episodes.append(own)
    return episodes


def motion_window(audit, index, horizon):
    times, yaws, positions, speeds = timeline(audit)
    if type(index) is not int or not 0 <= index < len(times) or not np.isfinite(horizon) or horizon <= 0:
        raise ValueError('Invalid diagnostic anchor/window')
    target_time = times[index]+horizon
    bracket = np.flatnonzero(times >= target_time)
    end = int(bracket[0]) if len(bracket) else len(times)-1
    gap = bool(np.any(np.diff(times[index:end+1]) > .75))
    complete = bool(len(bracket) and not gap)
    indices = [i for i in range(index, len(times)) if times[i] <= target_time]
    observed = [i for i in indices if i > 0]
    out = dict(horizon_s=horizon, anchor_index=index, complete_bracket=complete,
        gap_present=gap, sampled_span_s=float(times[indices[-1]]-times[index]),
        observed_speed_count=len(observed),
        observed_speed_min_mps=float(min(speeds[observed])) if observed else None,
        observed_speed_mean_mps=float(np.mean(speeds[observed])) if observed else None,
        anchor_speed_mps=float(speeds[index]) if index > 0 else None,
        lateral_shift_m=None, net_heading_change_rad=None, accumulated_heading_change_rad=None,
        path_length_m=None)
    if gap or len(indices) < 2:
        return out
    delta = positions[indices]-positions[index]
    lateral = -delta[:, 0]*np.sin(yaws[index])+delta[:, 1]*np.cos(yaws[index])
    out.update(lateral_shift_m=float(np.max(np.abs(lateral))),
        net_heading_change_rad=float(abs(np.arctan2(np.sin(yaws[indices[-1]]-yaws[index]),
                                                   np.cos(yaws[indices[-1]]-yaws[index])))),
        accumulated_heading_change_rad=r.wrapped_heading_change(yaws[indices].tolist()),
        path_length_m=float(np.linalg.norm(np.diff(positions[indices], axis=0), axis=1).sum()))
    return out


def route_queries(audit, anchors):
    tracks = {}
    for instance, track in audit['vehicle_tracks'].items():
        if any((v['index'], instance) in anchors for v in track):
            tracks[instance] = [{**v, 'crossing_exposure': (v['index'], instance) in anchors,
                                'crossing_conflict': False, 'raw_crossing_conflict': False} for v in track]
    result = geometry.audit_route_relations(audit['ego_positions'], audit['times'], audit['ego_yaws'], tracks)
    if {(q['index'], q['instance_token']) for q in result} != anchors:
        raise ValueError('Incomplete target diagnostic geometry')
    return result


def diagnose_scene(audit, saved, row):
    times, _, _, speeds = timeline(audit)
    trace = saved['candidate']
    flags, identities = trace['blocked_flags'], trace['stationary_ids']
    segments = target_episodes(flags, identities, times.tolist())
    indices = [i for i, f in enumerate(flags) if f]
    selected = trace['selected']
    first = indices[0] if indices else -1
    shift = r.lateral_shift_after_index(audit['ego_positions'], audit['times'], first,
                                     audit['ego_yaws'][first] if first >= 0 else 0., horizon=10.)
    turn = r.net_heading_change_after_index(audit['ego_yaws'], audit['times'], first,
                                          audit['ego_yaws'][first] if first >= 0 else 0., horizon=10.)
    duration = r.summarize_events(flags, audit['times']).max_duration
    distance = min((selected[i]['clearance'] for i in indices), default=80.)
    raw = r.is_obstacle_induced_route_deviation(duration, distance, shift, turn)
    if raw != trace['raw_deviation'] or raw != audit['obstacle_induced_route_deviation_candidate']:
        raise ValueError('Frozen raw-protection driver reproduction mismatch')
    episodes = []
    anchors = {(i, identities[i]) for i in indices}
    for own in segments:
        k = own[0]
        inst = identities[k]
        local_flags = [i in own for i in range(len(times))]
        event_duration = r.summarize_events(local_flags, audit['times']).max_duration
        local_distance = min(selected[i]['clearance'] for i in own)
        windows = [motion_window(audit, k, h) for h in WINDOWS]
        before = [i for i in range(1, k+1) if times[k]-times[i] <= 3.]
        episodes.append(dict(instance_token=inst, category=selected[k]['category'], indices=own,
            start_time_s=float(times[k]), end_time_s=float(times[own[-1]]),
            observed_span_s=float(times[own[-1]]-times[k]), legacy_duration_with_median_tail_s=event_duration,
            minimum_clearance_m=local_distance, anchor_heading_delta_rad=selected[k]['heading_delta'],
            anchor_target_speed_mps=selected[k]['target_speed'], windows=windows,
            observed_speed_before_count=len(before),
            observed_speed_before_mean_mps=float(np.mean(speeds[before])) if before else None,
            frozen_rule_per_episode=r.is_obstacle_induced_route_deviation(event_duration, local_distance,
                r.lateral_shift_after_index(audit['ego_positions'], audit['times'], k, audit['ego_yaws'][k], 10.),
                r.net_heading_change_after_index(audit['ego_yaws'], audit['times'], k, audit['ego_yaws'][k], 10.))))
    minimum = next((e for e in trace['events'] if e['scene_time'] == row['min_ttc_scene_time']
                    and e['annotation_token'] == row['min_ttc_target_annotation_token']), None)
    if minimum:
        anchors.add((minimum['frame_index'], minimum['instance_token']))
    relations = route_queries(audit, anchors)
    # Geometry is observed only. Never call gate_candidates or publish changed features.
    causes = dict(strict_evasion=bool(row['ego_evasive_lane_change_flag']),
        supported_deviation=bool(row['obstacle_induced_route_deviation_flag']), raw_deviation=bool(raw))
    if bool(any(causes.values())) != saved['protected_context']:
        raise ValueError('Protection branch reproduction mismatch')
    return dict(scene_name=audit['scene_name'], scene_token=audit['scene_token'], protection_causes=causes,
        protected_context=saved['protected_context'], episodes=episodes, route_queries=relations,
        minimum_ttc_event=minimum,
        minimum_event_window=motion_window(audit, minimum['frame_index'], 6.) if minimum else None,
        global_raw_inputs=dict(first_blocked_index=first, max_blocked_duration_s=duration,
            min_clearance_m=distance, ten_second_lateral_shift_m=shift, ten_second_net_heading_rad=turn),
        route_state_counts=dict(Counter(q['relation'] for q in relations)),
        causal_acceptance=False, feature_updates=False)


def verify_parent():
    _, status = parent.load_protocol(PARENT_SHA)
    if status['phase'] != 'completed_candidate_requires_review':
        raise ValueError('Parent incomplete')
    if record(parent.REPORT)['sha256'] != PARENT_REPORT_SHA:
        raise ValueError('Original parent report digest required; no refreshed output bindings')
    verify_records([status['report'], status['claim']])
    report = json.loads(parent.REPORT.read_text(encoding='utf-8'))
    verify_records([report['protocol'], *report['outputs']])


def inputs():
    return [parent.PROTOCOL, parent.REPORT, parent.FEATURES, parent.MANIFEST, parent.EVENTS,
        parent.legacy.TRACKS, ROOT/'HDBSCAN/scripts/scene_feature_rules.py',
        ROOT/'HDBSCAN/scripts/crossing_candidate_v6.py', Path(__file__),
        ROOT/'logs/test_longitudinal_protection_diagnosis_v1_20261015.py']


def prepare():
    verify_parent()
    assert_new_outputs([PROTOCOL, *OUTPUTS])
    write_json(PROTOCOL, dict(version=VERSION, command=[sys.executable, *sys.argv],
        created_at_utc=datetime.now(timezone.utc).isoformat(), parent_sha256=PARENT_SHA,
        parent_report_sha256=PARENT_REPORT_SHA,
        focus=FOCUS, diagnostic_windows_s=WINDOWS, inputs=[record(p) for p in inputs()],
        runtime=parent.legacy.runtime_record(), outputs=[str(p.resolve()) for p in OUTPUTS],
        stage='diagnosis_only_no_feature_updates', new_thresholds_or_filter=False,
        feature_updates=False, evaluation_used=False, model_used=False))
    print('PREPARED original protocol SHA256='+record(PROTOCOL)['sha256'], flush=True)


def load_protocol(expected):
    if not expected or record(PROTOCOL)['sha256'] != expected:
        raise ValueError('Original diagnosis protocol SHA256 required; no seal refresh')
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_records(protocol['inputs'])
    parent.legacy.validate_runtime(protocol['runtime'])
    verify_parent()
    if (protocol['version'] != VERSION or protocol['parent_sha256'] != PARENT_SHA
            or protocol['parent_report_sha256'] != PARENT_REPORT_SHA
            or protocol['focus'] != FOCUS or protocol['diagnostic_windows_s'] != WINDOWS
            or protocol['outputs'] != [str(p.resolve()) for p in OUTPUTS]):
        raise ValueError('Diagnosis contract drift')
    return protocol


def compute():
    rows = pd.read_csv(parent.FEATURES, float_precision='round_trip')
    assert_development_frame(rows, load_partition())
    audits = json.loads(parent.legacy.TRACKS.read_text(encoding='utf-8'))
    saved = json.loads(parent.EVENTS.read_text(encoding='utf-8'))['scenes']
    protocol = json.loads(parent.PROTOCOL.read_text(encoding='utf-8'))
    if (rows.shape != (29, 129) or rows.scene_name.tolist() != protocol['names']
            or rows.scene_token.tolist() != protocol['tokens']
            or [a['scene_name'] for a in audits] != protocol['names']
            or [a['scene_token'] for a in audits] != protocol['tokens']
            or [a['scene_name'] for a in saved] != protocol['names']
            or [a['scene_token'] for a in saved] != protocol['tokens']):
        raise ValueError('Fixed development29 identity/order drift')
    joined = {a['scene_name']: (a, s, row) for a, s, row in zip(audits, saved, rows.to_dict('records'))}
    protected = [s['scene_name'] for s in saved if s['protected_context']]
    if set(protected)-set(FOCUS):
        raise ValueError('Unexamined protected scene; revise separate diagnosis before freezing')
    return dict(version=VERSION, scene_scope=FOCUS, parent_protected_scenes=protected,
        scenes=[diagnose_scene(*joined[name]) for name in FOCUS],
        new_features=False, causal_acceptance=False, evaluation_used=False)


def document(evidence):
    lines = ['# 纵向绕行保护根因诊断', '',
        '2026-10-15。只读固定开发轨迹；无新特征、门控变化、阈值调优或风险标签。'
        'v7四条受保护场景全部检查，另保留0026末帧摩托车控制；不读取评价语义或媒体。', '',
        '| 场景 | 保护分支：严格避障/支持绕行/原始绕行 | 原始受阻时长/s | 净距离/m | 10秒侧移/m | 10秒转角/rad | 几何查询状态 |',
        '| --- | --- | ---: | ---: | ---: | ---: | --- |']
    for s in evidence['scenes']:
        p, g = s['protection_causes'], s['global_raw_inputs']
        lines.append(f'| {s["scene_name"]} | {int(p["strict_evasion"])}/{int(p["supported_deviation"])}/{int(p["raw_deviation"])} | '
            f'{g["max_blocked_duration_s"]:.3f} | {g["min_clearance_m"]:.3f} | '
            f'{g["ten_second_lateral_shift_m"]:.3f} | {g["ten_second_net_heading_rad"]:.3f} | {s["route_state_counts"]} |')
    lines += ['', '## 同目标片段与短时观测', '',
        '下表3秒侧移/转角是已有离散观测，不插值；只有存在真实括界且无>0.75秒缺口才称窗口完整。'
        '片段时长沿用旧算法的中位帧间隔尾部补偿，并不证明目标持续存在到补偿时刻。'
        '末帧无运动跨度记未知，不记成安全的0；初帧速度占位0不作为停车证据。', '',
        '| 场景 | 实例/类别 | 静态受阻观测时段/s | 旧判据按同目标片段成立 | 3秒侧移/m | 3秒净转角/rad | 3秒窗口完整 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for s in evidence['scenes']:
        for e in s['episodes']:
            w = next(w for w in e['windows'] if w['horizon_s'] == 3.)
            lines.append(f'| {s["scene_name"]} | {e["instance_token"]} / {e["category"]} | '
                f'{e["start_time_s"]:.3f}–{e["end_time_s"]:.3f} | {e["frozen_rule_per_episode"]} | '
                f'{w["lateral_shift_m"]} | {w["net_heading_change_rad"]} | {w["complete_bracket"]} |')
    lines += ['', '## 解释边界', '',
        '旧判据只需要持续静态前车与随后侧移/转角，并没有同目标路线占用或因果响应检验。'
        '因此正常转弯也可以满足原始绕行候选，继而触发v7整场保护；最终支持绕行flag为0并不会关闭原始分支。'
        '按目标拆片段只用于定位混合来源，并不能自动证明是否真实绕行。', '',
        '几何查询在受保护目标上独立记录完整观测路线相关性，没有调用目标门控、重新选前车或发布任何变更字段。'
        '已观测路线可能是成功避障之后的路线；几何分离、没有明显制动或大转角均不能单独证明目标无关。'
        'potential只是潜在空间相关，unknown不是安全，separated也不是不曾影响决策的因果证明。', '',
        '需要人工/设计确认的保护改版继续挂起：不直接取消原始保护，不调整角度/1m裕度，不为0669硬编码。'
        '优先补同目标局部占用/响应证据后另起候选，并用真实避障和摩托车控制回归。'
        '0552/0067新目标的语义复核与0102隔离VRU仍挂起，正式700/150/拟合不开启。', '',
        '[数值证据与源码绑定](F:/Scene_cluster/logs/longitudinal_protection_diagnosis_v1_evidence_20261015.json) · '
        '[执行记录](F:/Scene_cluster/logs/longitudinal_protection_diagnosis_v1_20261015.md)']
    return '\n'.join(lines)+'\n'


def run(expected):
    protocol = load_protocol(expected)
    assert_new_outputs(OUTPUTS)
    result = compute()
    verify_records(protocol['inputs'])
    write_json(EVIDENCE, result)
    with DOCUMENT.open('x', encoding='utf-8') as stream:
        stream.write(document(result))
    write_json(SEAL, dict(protocol=record(PROTOCOL), outputs=[record(EVIDENCE), record(DOCUMENT)],
        completed_at_utc=datetime.now(timezone.utc).isoformat(), stage='completed_diagnosis_requires_design',
        command=[sys.executable, *sys.argv], feature_updates=False))
    print(json.dumps(dict(stage='completed_diagnosis_requires_design', focus=FOCUS)), flush=True)


def check(expected):
    protocol = load_protocol(expected)
    seal = json.loads(SEAL.read_text(encoding='utf-8'))
    verify_records([seal['protocol'], *seal['outputs']])
    if seal['protocol'] != record(PROTOCOL) or seal['outputs'] != [record(EVIDENCE), record(DOCUMENT)]:
        raise ValueError('Unexpected diagnostic output binding')
    result = compute()
    if (json.loads(EVIDENCE.read_text(encoding='utf-8')) != result
            or DOCUMENT.read_text(encoding='utf-8') != document(result)):
        raise ValueError('Exact diagnosis replay mismatch')
    verify_records(protocol['inputs'])
    print('VERIFIED exact diagnosis, original parent/source/runtime/output seals; no feature updates.', flush=True)


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
