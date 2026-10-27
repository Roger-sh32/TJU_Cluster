"""Fixed29 historical episode replay; immutable v6 crossings and geometry."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs import crossing_v6_replay_20261014 as parent
from logs import crossing_v5_2_regression_20261013 as legacy
from logs.build_semantic_review_pack_20261001 import record
from logs.diagnose_review8_20261012 import verify_records, write_json
from HDBSCAN.scripts import crossing_candidate_v6_1 as rules
from HDBSCAN.scripts.experiment_partition import assert_development_frame, assert_new_outputs, load_partition
from HDBSCAN.scripts.feature_selection import CLUSTERING_FEATURES
from HDBSCAN.scripts.frozen_model import require_feature_provenance

PARENT_SHA = 'ae7db74041abe8758746d0819e5afe9fa8df48112d3864b13d1e76e412b9fd23'
TABLES = ROOT / 'HDBSCAN/tables'
PROTOCOL = TABLES / 'crossing_v6_1_replay29_protocol_20261015.json'
FEATURES = TABLES / 'scene_features_crossing_v6_1_replay29_20261015.csv'
MANIFEST = Path(str(FEATURES)+'.manifest.json')
EVENTS = TABLES / 'crossing_v6_1_replay29_events_20261015.json'
REPORT = TABLES / 'crossing_v6_1_replay29_comparison_20261015.json'
DOCUMENT = ROOT / 'outputs/人工复核/横向交互v6_1事件连续性对照_20261015.md'
STATUS = ROOT / 'logs/crossing_v6_1_replay29_20261015_status.json'
OUTPUTS = [FEATURES, MANIFEST, EVENTS, REPORT, DOCUMENT]
ALLOWED = {'left_turn_cross_traffic_interaction_ratio',
           'obstacle_induced_route_deviation_flag', 'route_deviation_decision_demand'}
TRUCK = '727349048e9044d98846cbeeb3a1b5fd'
CAR = '64a805096d9047a6bbc73734b0a90e67'
BOUNDARY_CONTROLS = dict(scene_name='scene-0068', truck=TRUCK, truck_frames=list(range(14, 24)),
                         car=CAR, forbidden_car_frame=24, retained_crossing_frames=[15, 16])


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
                                    v6=old[column], v6_1=new[column]))
    return changes


def check_boundary_controls(diagnostics):
    own = [s for s in diagnostics if s['scene_name'] == 'scene-0068']
    if len(own) != 1:
        raise ValueError('Missing boundary control scene')
    audit = own[0]
    if any(r['instance_token'] == CAR for r in audit['restored']):
        raise ValueError('Unrelated car restored')
    targets = audit['target_flags']
    if TRUCK not in targets or CAR not in targets:
        raise ValueError('Missing protected target audit')
    if any(not targets[TRUCK][i] for i in BOUNDARY_CONTROLS['truck_frames']):
        raise ValueError('Lost same-truck historical episode')
    if any(targets[CAR]) or not audit['flags'][23] or audit['flags'][24]:
        raise ValueError('Truck/car history boundary regression')
    trace = [r for r in audit['restored'] if r['index'] == 23 and r['instance_token'] == TRUCK]
    if len(trace) != 1 or trace[0]['seed_index'] not in (15, 16):
        raise ValueError('Missing same-target retained response seed')
    return dict(boundary=BOUNDARY_CONTROLS, historical_not_current_conflict=True,
                causal_acceptance=False, semantic_acceptance=False)


def input_paths():
    return [parent.PROTOCOL, parent.REPORT, parent.FEATURES, parent.MANIFEST, parent.EVIDENCE,
        legacy.TRACKS, ROOT/'HDBSCAN/tables/evaluation_split_20260924.csv',
        ROOT/'HDBSCAN/tables/evaluation_split_20260924_manifest.json',
        ROOT/'HDBSCAN/scripts/crossing_candidate_v6_1.py',
        ROOT/'HDBSCAN/tests/test_crossing_candidate_v6_1.py', Path(__file__),
        ROOT/'logs/test_crossing_v6_1_replay_20261015.py',
        ROOT/'logs/crossing_v6_boundary_20261015.md',
        ROOT/'logs/crossing_v6_replay_20261014.py']


def prepare():
    parent.check(PARENT_SHA)
    assert_new_outputs([PROTOCOL, STATUS, *OUTPUTS])
    frame = pd.read_csv(parent.FEATURES, float_precision='round_trip')
    assert_development_frame(frame, load_partition())
    write_json(PROTOCOL, dict(version=rules.CANDIDATE_VERSION,
        created_at_utc=datetime.now(timezone.utc).isoformat(), stage='fixed_before_candidate_replay',
        command=[sys.executable, *sys.argv], parent_protocol_sha256=PARENT_SHA,
        inputs=[record(p) for p in input_paths()], runtime=legacy.runtime_record(),
        names=frame.scene_name.tolist(), tokens=frame.scene_token.tolist(),
        allowed_changes=sorted(ALLOWED), boundary_controls=BOUNDARY_CONTROLS,
        outputs=[str(p.resolve()) for p in OUTPUTS],
        semantics='Historical same-target episode only; retained known route-potential response seed; forward<=6s; gap<=.75s',
        geometry_and_current_crossings_changed=False, new_extraction=False,
        fit_allowed=False, evaluation_used=False))
    write_json(STATUS, dict(phase='prepared', protocol=record(PROTOCOL)))
    print('PREPARED original protocol SHA256='+record(PROTOCOL)['sha256'], flush=True)


def load_protocol(expected):
    if not expected or len(expected) != 64:
        raise ValueError('Original expected protocol SHA256 required')
    if record(PROTOCOL)['sha256'] != expected:
        raise ValueError('Original protocol mismatch; no seal refresh')
    status = json.loads(STATUS.read_text(encoding='utf-8'))
    verify_records([status['protocol']])
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_records(protocol['inputs'])
    legacy.validate_runtime(protocol['runtime'])
    parent.check(PARENT_SHA)
    if (protocol['version'] != rules.CANDIDATE_VERSION
            or protocol['parent_protocol_sha256'] != PARENT_SHA
            or protocol['allowed_changes'] != sorted(ALLOWED)
            or protocol['boundary_controls'] != BOUNDARY_CONTROLS
            or protocol['outputs'] != [str(p.resolve()) for p in OUTPUTS]):
        raise ValueError('Frozen replay contract drift')
    return protocol, status


def compute(protocol):
    old = pd.read_csv(parent.FEATURES, float_precision='round_trip')
    assert_development_frame(old, load_partition())
    tracks = json.loads(legacy.TRACKS.read_text(encoding='utf-8'))
    source = json.loads(parent.EVIDENCE.read_text(encoding='utf-8'))['scenes']
    if (old.shape != (29, 129) or old.scene_name.tolist() != protocol['names']
            or old.scene_token.tolist() != protocol['tokens'] or len(tracks) != 29 or len(source) != 29
            or [s['scene_name'] for s in tracks] != protocol['names']
            or [s['scene_name'] for s in source] != protocol['names']
            or [s['scene_token'] for s in tracks] != protocol['tokens']
            or [s['scene_token'] for s in source] != protocol['tokens']):
        raise ValueError('Fixed29/schema/source identity mismatch')
    current, diagnostics = old.copy(), []
    for i, (audit, prior) in enumerate(zip(tracks, source)):
        event = rules.local_left_interaction_audit(audit['times'], audit['ego_yaws'],
            audit['vehicle_tracks'], prior['crossing'], audit['crossing_yield_flags'],
            audit['ego_speeds'], route_evidence=prior['routes'])
        if any(a and not b for a, b in zip(prior['local_left_flags'], event['flags'])):
            raise ValueError('Unexpected loss of existing v6 context')
        updated = {**audit, 'crossing_route_flags': prior['route_flags']}
        values = legacy.recompute_crossing_row(old.iloc[i], updated, prior['conflict_flags'], event['flags'])
        for column, value in values.items():
            if column not in ALLOWED:
                if value != old.iloc[i][column]:
                    raise ValueError('Unchanged crossing replay mismatch')
            else:
                current.at[i, column] = value
        diagnostics.append(dict(scene_name=audit['scene_name'], scene_token=audit['scene_token'], **event))
    changes = compare_frames(current, old)
    controls = parent.check_controls(current, old)
    controls.update(check_boundary_controls(diagnostics))
    return old, current, diagnostics, changes, controls


def document(old, current, diagnostics, changes):
    a, b = old.set_index('scene_name'), current.set_index('scene_name')
    lines = ['# v6.1 同目标事件连续性回归', '',
        '2026-10-15。固定29条开发轨迹重放，不是新提取、正式模型或独立评价。', '',
        f'{len(set(c["scene_name"] for c in changes))}条/{len(changes)}格变化；横向冲突、路线几何、未知状态、TTC/VRU/权重不变。', '',
        '| 场景 | 局部左转 v6 | v6.1 | 恢复的目标帧/响应种子 |', '| --- | ---: | ---: | --- |']
    for s in diagnostics:
        name = s['scene_name']
        detail = '; '.join(f'{r["instance_token"]}: {r["index"]}←{r["seed_index"]}' for r in s['restored']) or '无'
        lines.append(f'| {name} | {a.loc[name,"left_turn_cross_traffic_interaction_ratio"]:.6f} | '
                     f'{b.loc[name,"left_turn_cross_traffic_interaction_ratio"]:.6f} | {detail} |')
    lines += ['', '## 字段变化', '', '| 场景 | 字段 | v6 | v6.1 |', '| --- | --- | ---: | ---: |']
    lines += [f'| {c["scene_name"]} | {c["column"]} | {c["v6"]} | {c["v6_1"]} |' for c in changes]
    lines += ['', '## 边界', '',
        '0068卡车11.551秒的连续曝光历史表示保留，小汽车12.001秒不补回；历史交互不是该帧发生碰撞冲突。'
        '只有同目标已保留、路线潜在相关、未来已知完整的响应锚点才能建立补充；仅在原连续曝光片段、种子之后六秒内，'
        '且原有局部左转逻辑本来成立的帧补充。不能跨目标/缺口/后续事件，未知不能作为新种子；'
        '尾帧如未来未知，保留的也只是历史上下文，原未知状态不清除。', '',
        '没有为命中场景号而修改算法；指定场景和实例只用于冻结回归控制。'
        '保留0453/0073横向过滤、0068原卡车锚点、0552公交程序上下文、0107侵入；'
        '不是对整个事件因果或危险性验收。0067公交身份/语义、0073近1m边界及后续TTC/VRU/部分卡车绕行仍有限。', '',
        '[诊断依据](F:/Scene_cluster/logs/crossing_v6_boundary_20261015.md)，'
        '[执行记录](F:/Scene_cluster/logs/crossing_v6_1_replay_20261015.md)。']
    return '\n'.join(lines)+'\n'


def refuse_formal_fit(frame):
    try:
        require_feature_provenance(FEATURES, frame)
    except ValueError as exc:
        if 'Feature extraction version/provenance mismatch' not in str(exc):
            raise
    else:
        raise ValueError('Formal fitter accepted candidate replay')


def run(expected):
    protocol, status = load_protocol(expected)
    if status['phase'] != 'prepared':
        raise ValueError('Already started; do not repeat or overwrite')
    assert_new_outputs(OUTPUTS)
    write_json(STATUS, dict(phase='replaying', protocol=status['protocol']), False)
    try:
        old, current, diagnostics, changes, controls = compute(protocol)
        verify_records(protocol['inputs'])
        with FEATURES.open('x', encoding='utf-8', newline='') as stream:
            current.to_csv(stream, index=False)
        write_json(EVENTS, dict(version=rules.CANDIDATE_VERSION, protocol=record(PROTOCOL), scenes=diagnostics,
                               current_crossing_source=record(parent.EVIDENCE)))
        manifest = json.loads(parent.MANIFEST.read_text(encoding='utf-8'))
        manifest.update(input=record(parent.FEATURES), output=record(FEATURES), script=record(Path(__file__)),
                        stage='candidate_feature_replay', scene_names=protocol['names'])
        manifest['extra'] = {**manifest['extra'], 'version': rules.CANDIDATE_VERSION,
                             'formal_fit_allowed': False, 'new_extraction': False, 'protocol': record(PROTOCOL)}
        write_json(MANIFEST, manifest)
        refuse_formal_fit(current)
        with DOCUMENT.open('x', encoding='utf-8') as stream:
            stream.write(document(old, current, diagnostics, changes))
        report = dict(version=rules.CANDIDATE_VERSION, protocol=record(PROTOCOL),
            outputs=[record(p) for p in (FEATURES, MANIFEST, EVENTS, DOCUMENT)], changes=changes,
            changed_scenes=sorted(set(c['scene_name'] for c in changes)),
            clustering_changes=[c for c in changes if c['column'] in CLUSTERING_FEATURES],
            controls=controls, restored_target_frames=sum(len(s['restored']) for s in diagnostics),
            current_crossings_and_unknowns_unchanged=True, new_extraction=False,
            formal_fit_refused=True, evaluation_used=False, semantic_acceptance=False)
        write_json(REPORT, report)
        write_json(STATUS, dict(phase='completed_candidate_requires_review', protocol=status['protocol'],
            report=record(REPORT), completed_at_utc=datetime.now(timezone.utc).isoformat()), False)
        print(json.dumps(dict(phase='completed', scenes=29, changed=report['changed_scenes'],
                             cells=len(changes), restored=report['restored_target_frames'])), flush=True)
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
    old, current, diagnostics, changes, controls = compute(protocol)
    saved = pd.read_csv(FEATURES, float_precision='round_trip')
    pd.testing.assert_frame_equal(current, saved, check_dtype=False, rtol=0, atol=0)
    refuse_formal_fit(saved)
    if (json.loads(EVENTS.read_text(encoding='utf-8'))['scenes'] != diagnostics
            or report['changes'] != changes or report['controls'] != controls
            or DOCUMENT.read_text(encoding='utf-8') != document(old, current, diagnostics, changes)):
        raise ValueError('Exact replay mismatch')
    print('VERIFIED original seals, exact29 historical replay and formal fit refusal; no crossing/unknown changes.', flush=True)


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
