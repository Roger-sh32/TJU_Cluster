"""Read-only checks of the bounded replay, then publish a human diagnosis table."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs.diagnose_review8_20261012 import (NAMES, REPORT, PROTOCOL, TRAJECTORY, FEATURES,
    BASELINE, projection_blockers, exact_rows, verify_records, write_json)
from logs.build_semantic_review_pack_20261001 import record
from HDBSCAN.scripts.experiment_partition import load_partition, assert_development_frame, assert_new_outputs
from HDBSCAN.scripts.frozen_model import require_feature_provenance, source_hashes
from HDBSCAN.scripts.scene_feature_rules import turning_crossing_projection_audit

DOCUMENT = ROOT / 'outputs/人工复核/八场景逐目标诊断_20261012.md'
VERIFICATION = ROOT / 'HDBSCAN/tables/target_diagnosis8_verification_20261012.json'
REASONS = {'incomplete_future': '未来不足或断档', 'low_speed_or_braking_response': '低速/强刹保护',
           'nonfinite_geometry': '几何未知', 'turn_below_threshold': '局部转角不足',
           'invalid_actor_size': '尺寸无效', 'within_footprint_route_margin': '落入车身路线边界'}


def main():
    assert_new_outputs([DOCUMENT, VERIFICATION])
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_records(protocol['inputs'])
    verify_records([report[k] for k in ('protocol', 'features', 'trajectory', 'quality')])
    if 'continuation' in report:
        verify_records([report['continuation']])
        amendment = json.loads(Path(report['continuation']['path']).read_text(encoding='utf-8'))
        verify_records(amendment['inputs'])
        verify_records([amendment['parent_protocol']])
        if amendment['source_hashes'] != protocol['source_hashes']:
            raise ValueError('Continuation changed production source bindings')
    if source_hashes() != protocol['source_hashes']:
        raise ValueError('Production source drift')
    frame = pd.read_csv(FEATURES, float_precision='round_trip')
    reference = pd.read_csv(BASELINE, float_precision='round_trip')
    exact_rows(frame, reference)
    require_feature_provenance(FEATURES, frame)
    assert_development_frame(frame, load_partition())
    if set(frame.scene_name) != set(NAMES) or len(frame) != 8 or report['evaluation_used']:
        raise ValueError('Diagnostic scope changed')
    quality = json.loads(Path(report['quality']['path']).read_text(encoding='utf-8'))
    if quality['query_exception_count'] or report['query_exception_count']:
        raise ValueError('Query errors remain')
    audits = {r['scene_name']: r for r in json.loads(TRAJECTORY.read_text(encoding='utf-8'))}
    if set(audits) != set(NAMES) or {r['scene_name'] for r in report['scenes']} != set(NAMES):
        raise ValueError('Target coverage mismatch')
    features = frame.set_index('scene_name')
    lines = ['# 八场景逐目标诊断', '', '日期：2026-10-12。未经修改的 v4 提取器重放八条开发场景，'
        '与冻结 700 表对应行逐列精确一致。本表定位候选来源，不是修复后结果或专家有效性验证。', '',
        '只分析开发集；没有拟合、改规则、调权重或生成新 GIF。原始人工意见见 '
        '[反馈记录](F:/Scene_cluster/logs/development_review_feedback_20261012.md)。', '',
        '横向“保留原因”是阻止现有过滤器删除候选的条件，不等于真实让行已成立。'
        '路线距离为未来目标点到自车路线折线的空间最小距离，不等于同步碰撞距离。'
        '完整未来是现有六秒规则，保守未删不能当作已确认风险。', '']
    for scene in report['scenes']:
        name = scene['scene_name']
        audit = audits[name]
        if scene['scene_token'] != features.loc[name, 'scene_token'] or audit['scene_token'] != scene['scene_token']:
            raise ValueError('Scene identity mismatch')
        # Recompute from retained raw candidates, since the saved track flags are post-filter.
        raw_tracks = {key: [{**row, 'crossing_conflict': row['raw_crossing_conflict']} for row in track]
                      for key, track in audit['vehicle_tracks'].items()}
        raw = turning_crossing_projection_audit(audit['ego_positions'], audit['times'], audit['ego_yaws'],
                                                audit['ego_speeds'], raw_tracks)
        if len(raw) != len(scene['crossing_candidates']):
            raise ValueError('Raw target count mismatch')
        for expected, actual in zip(raw, scene['crossing_candidates']):
            for key, value in expected.items():
                if isinstance(value, (float, int)) and not isinstance(value, bool):
                    np.testing.assert_allclose(value, actual[key], rtol=0, atol=0, equal_nan=True)
                elif value != actual[key]:
                    raise ValueError('Projection evidence mismatch')
            if projection_blockers(actual) != actual['rejection_blockers']:
                raise ValueError('Projection reason mismatch')
        indices = {r['index'] for r in scene['vru_candidates']}
        if len(indices) / len(audit['times']) != features.loc[name, 'vru_path_conflict_ratio']:
            raise ValueError('VRU summary mismatch')
        lines.extend([f'## {name}', '',
            f'[原始带时间动图](F:/Scene_cluster/exports/development_review_20261012/{name}_CAM_FRONT_timestamped.gif)', '',
            '| 数据时间/s | 横向目标实例 | 类别 | 现有处理 | 保留原因 | 未来路线距离/m |',
            '| --- | --- | --- | --- | --- | ---: |'])
        for item in scene['crossing_candidates']:
            reasons = '、'.join(REASONS[r] for r in item['rejection_blockers']) or '-'
            state = '保留候选' if item['retained'] else '已过滤'
            lines.append(f'| {item["time_s"]:.3f} | {item["instance_token"]} | {item["category"]} | '
                         f'{state} | {reasons} | {item["minimum_future_route_distance"]:.3f} |')
        if not scene['crossing_candidates']:
            lines.append('| - | - | 无原始横向冲突候选 | - | - | - |')
        ttc = scene['minimum_ttc']
        if ttc:
            lane = ttc['ego_lane_center_distance_m']
            lane_text = '未知' if lane is None else f'{lane:.3f} m'
            lines += ['', f'最低 TTC：t={ttc["time_s"]:.3f}s，TTC={ttc["ttc_s"]:.3f}s，'
                f'{ttc["category"]}，实例 `{ttc["instance_token"]}`。目标速度 '
                f'{ttc["target_speed_mps"]:.3f} m/s，朝向差 {np.degrees(ttc["heading_delta_rad"]):.2f}°，'
                f'局部转角 {np.degrees(ttc["local_heading_change_rad"]):.2f}°，'
                f'自车当前车道中心距离 {lane_text}。当前转弯过滤未删除该最低 TTC；未来空间路线距离 '
                f'{ttc["future_actor_to_ego_route_min_distance_m"]:.3f} m，仅诊断，不保证未来完整或同时间冲突。']
        else:
            lines += ['', '无有效最低 TTC 目标记录；填充值不当作实测。']
        if scene['vru_candidates']:
            lines += ['', '| 时间/s | VRU 实例 | 人行道地图证据 | 当前车道中心距离/m | 同步最近距/m |',
                      '| --- | --- | --- | ---: | ---: |']
            for item in scene['vru_candidates']:
                lane = item['ego_lane_center_distance_m']
                distance = item['observed_closest_distance_m']
                lines.append(f'| {item["time_s"]:.3f} | {item["instance_token"]} | '
                    f'{"有" if item["on_walkway"] else "未记录，不等于没有"} | '
                    f'{lane if lane is not None else "未知"} | {distance if distance is not None else "未知"} |')
            lines += ['', '护栏物理隔离仍来自人工观察；地图未自动验证护栏。lane_connector 无点内多边形查询，'
                       '诊断明确记为未知，不当作不存在。']
        static = scene['static_obstacle_frames']
        if static:
            lines += ['', '静止障碍候选（非已确认占道）：' + '；'.join(
                f't={r["time_s"]:.3f}s / `{r["instance_token"]}`' for r in static) + '。']
        events = scene['temporal_events']
        stops = [e for e in events if e['event_type'] == 'low_speed_stop']
        lines += ['', '低速持续停车候选：' + ('；'.join(f'{e["start_s"]:.3f}–{e["end_s"]:.3f}s' for e in stops)
                  if stops else '未提取到') + '。停车原因未自动确定。', '']
    lines += ['## 来源与限制', '', f'[原始诊断 JSON]({REPORT.as_posix()})，'
              f'[执行记录](F:/Scene_cluster/logs/review8_target_diagnosis_20261012.md)。', '',
              '所有数值仍为 v4。没有把反馈变成场景级真值或独立评价成绩，'
              '未来不足、地图未知或保守响应保护均不能证明目标有风险或无风险。']
    with DOCUMENT.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(lines) + '\n')
    write_json(VERIFICATION, {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'command': [sys.executable, *sys.argv], 'script': record(__file__), 'protocol': record(PROTOCOL),
        'report': record(REPORT), 'document': record(DOCUMENT), 'exact_eight_rows': True,
        'raw_projection_evidence_recomputed': True, 'frozen_sources_unchanged': True,
        'evaluation_used': False, 'semantic_acceptance': False})
    print('VERIFIED AND PUBLISHED: ' + str(DOCUMENT))


if __name__ == '__main__':
    main()
