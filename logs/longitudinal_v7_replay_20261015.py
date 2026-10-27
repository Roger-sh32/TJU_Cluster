"""Fixed development29 longitudinal ledger, exact baseline gate, then v7 replay."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs import crossing_v6_1_replay_20261015 as parent
from logs import crossing_v5_2_regression_20261013 as legacy
from logs.evaluation_media_audit_20260926 import records
from logs.build_semantic_review_pack_20261001 import record
from logs.diagnose_review8_20261012 import verify_records, write_json
from HDBSCAN.scripts import longitudinal_candidate_v7 as rules
from HDBSCAN.scripts.experiment_partition import assert_development_frame, assert_new_outputs, load_partition
from HDBSCAN.scripts.feature_selection import CLUSTERING_FEATURES
from HDBSCAN.scripts.frozen_model import require_feature_provenance

PARENT_SHA = '51b6be617bb455bfd44a2d8bcf9010b73ee1d16bc7aa9f60963dacc9186c3209'
TABLES = ROOT/'HDBSCAN/tables'
META = ROOT/'nuScenes/v1.0-trainval'
PROTOCOL = TABLES/'longitudinal_v7_replay29_protocol_20261015.json'
BASELINE = TABLES/'longitudinal_v7_replay29_baseline_20261015.json'
FEATURES = TABLES/'scene_features_longitudinal_v7_replay29_20261015.csv'
MANIFEST = Path(str(FEATURES)+'.manifest.json')
EVENTS = TABLES/'longitudinal_v7_replay29_ledger_20261015.json'
REPORT = TABLES/'longitudinal_v7_replay29_comparison_20261015.json'
DOCUMENT = ROOT/'outputs/人工复核/纵向目标v7固定29条对照_20261015.md'
STATUS = ROOT/'logs/longitudinal_v7_replay29_20261015_status.json'
CLAIM = ROOT/'logs/longitudinal_v7_replay29_20261015_claim.json'
OUTPUTS = [BASELINE, FEATURES, MANIFEST, EVENTS, REPORT, DOCUMENT]
ALLOWED = set('''car_following_ratio following_event_count following_max_duration
close_following_ratio front_vehicle_min_dist stopped_lead_ratio stationary_lead_obstacle_ratio
temporarily_stopped_lead_ratio blocked_path_obstacle_ratio stationary_lead_event_count
stationary_lead_min_dist ego_evasive_lateral_shift ego_evasive_net_heading_change
ego_evasive_lane_change_flag obstacle_induced_route_deviation_flag route_deviation_decision_demand
min_ttc min_ttc_scene_time min_ttc_target_annotation_token min_ttc_target_instance_token
min_ttc_target_category min_ttc_target_clearance min_ttc_target_lateral_distance min_ttc_target_speed
min_ttc_target_forward_speed min_ttc_relative_speed min_ttc_target_heading_delta
dangerous_ttc_ratio dangerous_ttc_frame_ratio dangerous_ttc_max_duration ttc_valid_ratio'''.split())


def field_differences(new, old):
    return [dict(column=k, baseline=old[k], replay=v) for k, v in new.items() if v != old[k]]


def require_baseline(result):
    if result.get('passed') is not True:
        raise ValueError('Baseline reproduction failed; no candidate gate permitted')


def check_dependencies(old, new, before, after):
    if (old['ego_evasive_lane_change_flag'] != new['ego_evasive_lane_change_flag']
            or (old['ego_evasive_lane_change_flag'] and
                before['first_static_index'] != after['first_static_index'])):
        raise ValueError('Avoidance/VRU/oncoming dependency drift; stop rather than retain stale context')


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
                    raise ValueError('Unrelated column change: '+column)
                changes.append(dict(scene_name=new['scene_name'], column=column,
                                    v6_1=old[column], v7=new[column]))
    return changes


def annotation_maps(audits):
    """Retain only approved development samples; no evaluation annotation analysis."""
    selected = {a['scene_token']: a for a in audits}
    samples = {s['token']: s for s in records(META/'sample.json') if s['scene_token'] in selected}
    scenes = {s['token']: s for s in records(META/'scene.json') if s['token'] in selected}
    lookup, result, positions = {}, {a['scene_name']: {} for a in audits}, {}
    for token, audit in selected.items():
        scene = scenes[token]
        if scene['name'] != audit['scene_name'] or scene['nbr_samples'] != len(audit['times']):
            raise ValueError('Official metadata scene mismatch')
        sample_token, previous, seen, start = scene['first_sample_token'], '', set(), None
        while sample_token:
            if sample_token in seen or sample_token not in samples:
                raise ValueError('Broken official sample chain')
            s = samples[sample_token]
            i = len(seen)
            if s['scene_token'] != token or s['prev'] != previous:
                raise ValueError('Sample order mismatch')
            if start is None:
                start = s['timestamp']/1e6
            if i >= len(audit['times']) or s['timestamp']/1e6-start != audit['times'][i]:
                raise ValueError('Official sample/trajectory timestamp mismatch')
            lookup[sample_token] = (audit['scene_name'], i)
            seen.add(sample_token)
            previous, sample_token = sample_token, s['next']
        if len(seen) != len(audit['times']) or previous != scene['last_sample_token']:
            raise ValueError('Incomplete official sample chain')
        for instance, track in audit['vehicle_tracks'].items():
            for v in track:
                positions[audit['scene_name'], v['index'], instance] = v
    count = 0
    for ann in records(META/'sample_annotation.json'):
        own = lookup.get(ann['sample_token'])
        if own is None:
            continue
        name, i = own
        instance = ann['instance_token']
        track = positions.get((name, i, instance))
        if track is None:
            continue
        key = (i, instance)
        if key in result[name] or not isinstance(ann['token'], str) or not ann['token']:
            raise ValueError('Duplicate/empty annotation identity')
        if (ann['translation'][:2] != track['position'] or ann['size'][0] != track['width']
                or ann['size'][1] != track['length']):
            raise ValueError('Official annotation geometry mismatch')
        result[name][key] = ann['token']
        count += 1
    if count != len(positions):
        raise ValueError('Incomplete official vehicle annotation identities')
    return result


def inputs():
    return [parent.PROTOCOL, parent.REPORT, parent.FEATURES, parent.MANIFEST, parent.EVENTS,
        legacy.TRACKS, ROOT/'HDBSCAN/tables/evaluation_split_20260924.csv',
        ROOT/'HDBSCAN/tables/evaluation_split_20260924_manifest.json',
        META/'sample.json', META/'sample_annotation.json', META/'scene.json',
        ROOT/'logs/evaluation_media_audit_20260926.py',
        ROOT/'HDBSCAN/scripts/longitudinal_candidate_v7.py',
        ROOT/'HDBSCAN/tests/test_longitudinal_candidate_v7.py', Path(__file__),
        ROOT/'logs/test_longitudinal_v7_replay_20261015.py',
        ROOT/'logs/ttc_scope_diagnosis_20261015.md']


def prepare():
    parent.check(PARENT_SHA)
    assert_new_outputs([PROTOCOL, STATUS, CLAIM, *OUTPUTS])
    old = pd.read_csv(parent.FEATURES, float_precision='round_trip')
    assert_development_frame(old, load_partition())
    write_json(PROTOCOL, dict(version=rules.VERSION, created_at_utc=datetime.now(timezone.utc).isoformat(),
        command=[sys.executable, *sys.argv], parent_sha256=PARENT_SHA,
        stage='fixed_before_baseline_and_candidate_replay', inputs=[record(p) for p in inputs()],
        runtime=legacy.runtime_record(), names=old.scene_name.tolist(), tokens=old.scene_token.tolist(),
        allowed_changes=sorted(ALLOWED), outputs=[str(p.resolve()) for p in OUTPUTS],
        exact_baseline_required=True, new_extraction=False, evaluation_used=False, fit_allowed=False,
        policy='Permanent static, opposing halfplane cos(delta)<0, local turn>=.35, speed<.5, '
        'supported/map known, full6s geometry SEPARATED; existing avoidance/raw deviation protected. '
        'Unknown future never proves separation. Gate before nearest selection; inherited TTC postfilter retained. '
        'TTC formula/clips, v6 geometry/margin, v6.1 crossing, VRU, weights and schema unchanged.'))
    write_json(STATUS, dict(phase='prepared', protocol=record(PROTOCOL)))
    print('PREPARED original protocol SHA256='+record(PROTOCOL)['sha256'], flush=True)


def load_protocol(expected):
    if not expected or len(expected) != 64 or record(PROTOCOL)['sha256'] != expected:
        raise ValueError('Original expected protocol SHA256 required; no seal refresh')
    status = json.loads(STATUS.read_text(encoding='utf-8'))
    verify_records([status['protocol']])
    p = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_records(p['inputs'])
    legacy.validate_runtime(p['runtime'])
    parent.check(PARENT_SHA)
    if (p['version'] != rules.VERSION or p['parent_sha256'] != PARENT_SHA
            or p['allowed_changes'] != sorted(ALLOWED) or p['exact_baseline_required'] is not True
            or p['outputs'] != [str(p.resolve()) for p in OUTPUTS]):
        raise ValueError('Frozen replay contract drift')
    return p, status


def baseline(protocol):
    old = pd.read_csv(parent.FEATURES, float_precision='round_trip')
    assert_development_frame(old, load_partition())
    audits = json.loads(legacy.TRACKS.read_text(encoding='utf-8'))
    if (old.shape != (29, 129) or len(CLUSTERING_FEATURES) != 52
            or old.scene_name.tolist() != protocol['names'] or old.scene_token.tolist() != protocol['tokens']
            or [a['scene_name'] for a in audits] != protocol['names']
            or [a['scene_token'] for a in audits] != protocol['tokens']):
        raise ValueError('Fixed29 identity/schema mismatch')
    if not (old.map_available == 1).all():
        raise ValueError('Unknown map support; bounded replay not authorized to infer it')
    print('Mapping official annotation identities for fixed development29 only...', flush=True)
    identities = annotation_maps(audits)
    replay, mismatches = [], []
    for audit, row in zip(audits, old.to_dict('records')):
        ledger = rules.build_ledger(audit, identities[audit['scene_name']])
        fields, trace = rules.summarize(audit, ledger, row)
        if set(fields) != ALLOWED:
            raise ValueError('Longitudinal field contract mismatch')
        delta = field_differences(fields, row)
        for key, original in [('stationary_ids', 'stationary_lead_instances'),
                              ('static_flags', 'static_obstacle_flags'),
                              ('raw_deviation', 'obstacle_induced_route_deviation_candidate')]:
            if trace[key] != audit[original]:
                delta.append(dict(column=key, baseline=audit[original], replay=trace[key]))
        mismatches += [dict(scene_name=audit['scene_name'], **d) for d in delta]
        replay.append(dict(audit=audit, ledger=ledger, fields=fields, trace=trace))
    result = dict(passed=not mismatches, scenes=29, fields=sorted(ALLOWED), exact_equality=True,
                  static_trace_checked=True, mismatches=mismatches)
    return old, replay, result


def candidate(old, replay, proof):
    require_baseline(proof)
    current, diagnostics = old.copy(), []
    for i, own in enumerate(replay):
        audit, before = own['audit'], own['trace']
        row = old.iloc[i].to_dict()
        protected = bool(row['ego_evasive_lane_change_flag'] or row['obstacle_induced_route_deviation_flag']
                         or audit['obstacle_induced_route_deviation_candidate'])
        rejected, relations = rules.gate_candidates(audit, own['ledger'], protected)
        fields, after = rules.summarize(audit, own['ledger'], row, rejected)
        check_dependencies(row, fields, before, after)
        if protected and (rejected or fields != own['fields']):
            raise ValueError('Protected avoidance context changed')
        for k, v in fields.items():
            current.at[i, k] = v
        diagnostics.append(dict(scene_name=audit['scene_name'], scene_token=audit['scene_token'],
            ledger=own['ledger'], protected_context=protected, rejected=sorted([list(k) for k in rejected]),
            route_relations=relations, baseline=before, candidate=after))
    changes = compare_frames(current, old)
    # Positive control identities are checks, never inputs to the generic gate.
    a, b = old.set_index('scene_name'), current.set_index('scene_name')
    if any(a.loc['scene-0026', k] != b.loc['scene-0026', k] for k in ALLOWED):
        raise ValueError('Protected scene-0026 motorcycle regression')
    for name in ('scene-0011', 'scene-0042'):
        if any(a.loc[name, k] != b.loc[name, k] for k in ALLOWED):
            raise ValueError('Protected forward obstacle/avoidance regression: '+name)
    for d in diagnostics:
        if d['scene_name'] in ('scene-0026', 'scene-0011', 'scene-0042') and d['baseline'] != d['candidate']:
            raise ValueError('Protected target-level trace regression: '+d['scene_name'])
    return current, diagnostics, changes


def document(changes, diagnostics):
    lines = ['# 纵向目标v7固定29条对照', '',
        '2026-10-15。开发轨迹重放候选，非全量实验、正式模型或独立评价。', '',
        '先精确复现31个纵向字段及静止目标/静态障碍/原始偏离台账，再运行目标门控。'
        '只过滤永久静态、朝向处于对向半平面、自车局部转弯、地图支持已知且完整6秒扫掠路线明确分离的目标。'
        '有既存避障/原始绕行上下文的整条场景保守保护。未知不等于安全。', '',
        f'{len(set(c["scene_name"] for c in changes))}条/{len(changes)}格变化。', '',
        '| 场景 | 过滤候选帧数 | 既存避障保护 |', '| --- | ---: | --- |']
    lines += [f'| {d["scene_name"]} | {len(d["rejected"])} | {d["protected_context"]} |' for d in diagnostics]
    lines += ['', '| 场景 | 字段 | v6.1 | v7 |', '| --- | --- | --- | --- |']
    lines += [f'| {c["scene_name"]} | {c["column"]} | {c["v6_1"]} | {c["v7"]} |' for c in changes]
    lines += ['', '## 解释边界', '',
        '门控在最近前车选择之前，之后统一重算TTC、跟随、静止前车、受阻及必要偏离统计。'
        '原来的TTC候选后置转弯过滤仍原样保留，不宣称已全面重构旧逻辑。'
        '对向半平面是新增类别条件，不是把旧角度阈值调到命中0669。几何仍使用已冻结v6的1m间隔及完整未来条件。', '',
        'TTC=30且时间=-1/目标none只表示未测得有效TTC，不代表已验证安全；过滤后的剩余目标也需复核。'
        '0026摩托车及0011/0042前向障碍回归保护通过，v6.1横向/VRU/其余列不变；分数未重算、无模型拟合。'
        '结果变化不等于语义改进或危险性验收。0552本次TTC目标不能借用已确认的公交让行身份；'
        '部分卡车绕行、0102隔离行人、0067语义及0073近边界鲁棒性仍未解决。', '',
        '[完整台账](F:/Scene_cluster/HDBSCAN/tables/longitudinal_v7_replay29_ledger_20261015.json)，'
        '[执行记录](F:/Scene_cluster/logs/longitudinal_v7_replay_20261015.md)。']
    return '\n'.join(lines)+'\n'


def refuse_fit(frame):
    try:
        require_feature_provenance(FEATURES, frame)
    except ValueError as exc:
        if 'Feature extraction version/provenance mismatch' not in str(exc):
            raise
    else:
        raise ValueError('Formal fitter accepted candidate replay')


def claim_run(status):
    # Exclusive creation owns all later status writes; retain claim after failure.
    write_json(CLAIM, dict(protocol=status['protocol'],
                          created_at_utc=datetime.now(timezone.utc).isoformat()))
    return record(CLAIM)


def run(expected):
    protocol, status = load_protocol(expected)
    if status['phase'] != 'prepared':
        raise ValueError('Already started; no implicit resume or overwrite')
    assert_new_outputs(OUTPUTS)
    claim = claim_run(status)
    try:
        write_json(STATUS, dict(phase='baseline_reproduction', protocol=status['protocol'], claim=claim), False)
        old, replay, proof = baseline(protocol)
        write_json(BASELINE, proof)
        require_baseline(proof)
        print('Exact baseline passed; starting conservative preselection gate.', flush=True)
        current, diagnostics, changes = candidate(old, replay, proof)
        verify_records(protocol['inputs'])
        with FEATURES.open('x', encoding='utf-8', newline='') as stream:
            current.to_csv(stream, index=False)
        write_json(EVENTS, dict(version=rules.VERSION, protocol=record(PROTOCOL), scenes=diagnostics))
        manifest = json.loads(parent.MANIFEST.read_text(encoding='utf-8'))
        manifest.update(input=record(parent.FEATURES), output=record(FEATURES), script=record(Path(__file__)),
            stage='candidate_feature_replay', scene_names=protocol['names'])
        manifest['extra'] = {**manifest['extra'], 'version': rules.VERSION, 'formal_fit_allowed': False,
                             'new_extraction': False, 'protocol': record(PROTOCOL)}
        write_json(MANIFEST, manifest)
        refuse_fit(current)
        with DOCUMENT.open('x', encoding='utf-8') as stream:
            stream.write(document(changes, diagnostics))
        report = dict(version=rules.VERSION, protocol=record(PROTOCOL),
            outputs=[record(p) for p in OUTPUTS if p != REPORT], changes=changes,
            changed_scenes=sorted(set(c['scene_name'] for c in changes)),
            clustering_changes=[c for c in changes if c['column'] in CLUSTERING_FEATURES],
            baseline_reproduction_passed=True, unchanged_crossing_vru_and_weights=True,
            formal_fit_refused=True, evaluation_used=False, semantic_acceptance=False)
        write_json(REPORT, report)
        write_json(STATUS, dict(phase='completed_candidate_requires_review', protocol=status['protocol'],
            claim=claim, report=record(REPORT), completed_at_utc=datetime.now(timezone.utc).isoformat()), False)
        print(json.dumps(dict(phase='completed', scenes=29, changed=report['changed_scenes'],
                             cells=len(changes))), flush=True)
    except Exception as exc:
        write_json(STATUS, dict(phase='failed_requires_inspection', protocol=status['protocol'],
                                claim=claim, error=f'{type(exc).__name__}: {exc}'), False)
        raise


def check(expected):
    protocol, status = load_protocol(expected)
    if status['phase'] != 'completed_candidate_requires_review':
        raise ValueError('Replay not completed; do not bypass failed baseline')
    verify_records([status['report'], status['claim']])
    if json.loads(CLAIM.read_text(encoding='utf-8'))['protocol'] != status['protocol']:
        raise ValueError('Run owner protocol mismatch')
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    verify_records([report['protocol'], *report['outputs']])
    old, replay, proof = baseline(protocol)
    current, diagnostics, changes = candidate(old, replay, proof)
    saved = pd.read_csv(FEATURES, float_precision='round_trip')
    pd.testing.assert_frame_equal(current, saved, check_dtype=False, rtol=0, atol=0)
    refuse_fit(saved)
    if (json.loads(BASELINE.read_text(encoding='utf-8')) != proof
            or json.loads(EVENTS.read_text(encoding='utf-8'))['scenes'] != diagnostics
            or report['changes'] != changes or report['baseline_reproduction_passed'] is not True
            or DOCUMENT.read_text(encoding='utf-8') != document(changes, diagnostics)):
        raise ValueError('Exact replay mismatch')
    verify_records(protocol['inputs'])
    print('VERIFIED original seals, exact baseline/candidate29 replay and formal fit refusal.', flush=True)


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
