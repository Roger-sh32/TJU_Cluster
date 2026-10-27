"""Export development-only temporal evidence without inferring stop causality."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

try:
    from .experiment_partition import (
        assert_development_frame, assert_new_outputs, file_record,
        load_development_features,
    )
except ImportError:
    from experiment_partition import (
        assert_development_frame, assert_new_outputs, file_record,
        load_development_features,
    )


def _runs(indices, times):
    runs = []
    for i in indices:
        if not runs or i != runs[-1][-1] + 1 or times[i] - times[runs[-1][-1]] > 1.0:
            runs.append([])
        runs[-1].append(i)
    return runs


def scene_events(scene):
    times = np.asarray(scene['times'], dtype=float)
    speeds = np.asarray(scene['ego_speeds'], dtype=float)
    signs = scene['stop_sign_stop_flags']
    if (times.ndim != 1 or len(times) == 0 or speeds.shape != times.shape
            or len(signs) != len(times) or not np.isfinite(times).all()
            or not np.isfinite(speeds).all() or np.any(np.diff(times) <= 0)
            or np.any(speeds < 0) or not all(isinstance(x, bool) for x in signs)):
        raise ValueError('Invalid event timeline')
    # Frame zero speed is an extraction placeholder, not a stopped observation.
    stops = [run for run in _runs([i for i in range(1, len(times)) if speeds[i] < 1.0], times)
             if times[run[-1]] - times[run[0]] >= 0.8]

    def phase(i):
        if not stops:
            return 'no_stop_observed', None
        for number, run in enumerate(stops, 1):
            if run[0] <= i <= run[-1]:
                return 'during_stop', number
            if i < run[0]:
                return ('before_first_stop', number) if number == 1 else ('between_stops', number - 1)
        return 'after_last_stop', len(stops)

    def record(run, event_type, instance='', category=''):
        stage, stop_id = phase(run[0])
        measured = [i for i in run if i > 0]
        return {
            'scene_name': scene['scene_name'], 'scene_token': scene['scene_token'],
            'event_type': event_type, 'instance_token': instance, 'category': category,
            'start_s': float(times[run[0]]), 'end_s': float(times[run[-1]]),
            'observed_span_s': float(times[run[-1]] - times[run[0]]),
            'frame_count': len(run), 'phase': stage, 'related_stop_id': stop_id,
            'ego_speed_min': float(np.min(speeds[measured])) if measured else None,
            'ego_speed_max': float(np.max(speeds[measured])) if measured else None,
            'stop_sign_context_observed': any(signs[i] for i in run),
            'stop_reason': 'undetermined',
        }

    events = [record(run, 'low_speed_stop') for run in stops]
    for instance, track in scene['vehicle_tracks'].items():
        indices = [r['index'] for r in track]
        if (not isinstance(instance, str) or not instance
                or any(type(i) is not int or not 0 <= i < len(times) for i in indices)
                or any(a >= b for a, b in zip(indices, indices[1:]))
                or any(not isinstance(r.get('crossing_conflict'), bool) for r in track)):
            raise ValueError('Invalid actor event evidence')
        candidates = [r['index'] for r in track if r['crossing_conflict']]
        for run in _runs(candidates, times):
            segments = []
            for i in run:
                if not segments or phase(i) != phase(segments[-1][-1]):
                    segments.append([])
                segments[-1].append(i)
            events.extend(record(segment, 'predicted_crossing', instance, track[0]['category'])
                          for segment in segments)
    return sorted(events, key=lambda e: (e['start_s'], e['event_type'], e['instance_token']))


def build_report(audits, features, partition):
    identities = pd.DataFrame([{'scene_name': s['scene_name'], 'scene_token': s['scene_token']}
                               for s in audits])
    assert_development_frame(identities, partition)
    if set(identities.scene_name) != set(features.scene_name):
        raise ValueError('Audit and feature scenes must match exactly')
    return {s['scene_name']: scene_events(s) for s in audits}


def render_markdown(report):
    lines = ['# 交互事件审查记录', '',
             '仅限开发集。以下是时间与目标证据，不是碰撞事实，也不是停车原因标签。',
             '低速停车候选要求速度 <1 m/s、连续观测跨度至少 0.8 秒；首帧速度占位不参与。',
             '停止牌上下文与横向预测可以共存，停车原因均保留为“未确定”。', '',
             '时间为场景起点后的秒数；单帧事件跨度为 0，不外推持续时间。', '']
    phases = {'before_first_stop': '首次停车前', 'during_stop': '低速停车中',
              'between_stops': '两次停车之间', 'after_last_stop': '末次停车后',
              'no_stop_observed': '未观测到持续停车'}
    for name, events in report.items():
        lines.extend([f'## {name}', '', '| 时间/s | 事件 | 阶段 | 目标实例 | 停止牌上下文 |',
                      '| --- | --- | --- | --- | --- |'])
        for event in events:
            kind = '低速停车候选' if event['event_type'] == 'low_speed_stop' else f"横向预测：{event['category']}"
            sign = '有' if event['stop_sign_context_observed'] else '未记录（不等于无）'
            lines.append(f"| {event['start_s']:.2f}–{event['end_s']:.2f} | {kind} | "
                         f"{phases[event['phase']]} | {event['instance_token'] or '自车'} | {sign} |")
        if not events:
            lines.append('| - | 未提取到上述事件 | - | - | - |')
        lines.extend(['', '停车原因：未确定；不能根据先后顺序认定为某辆车让行。', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--features', type=Path, required=True)
    parser.add_argument('--output-prefix', type=Path, required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    features, _, partition = load_development_features(args.features)
    audits = json.loads(args.audit.read_text(encoding='utf-8'))
    report = build_report(audits, features, partition)
    output = Path(str(args.output_prefix) + '.json')
    markdown = Path(str(args.output_prefix) + '.md')
    assert_new_outputs([output, markdown])
    count = sum(len(events) for events in report.values())
    if args.preflight:
        print(f'development-only preflight: {len(report)} scenes, {count} events; no writes')
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with markdown.open('x', encoding='utf-8') as stream:
        stream.write(render_markdown(report))
    with output.open('x', encoding='utf-8') as stream:
        json.dump({
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'python': sys.executable, 'command': [sys.executable, *sys.argv],
            'scope': 'development', 'partition': partition['file'],
            'inputs': [file_record(args.features), file_record(args.audit)],
            'script': file_record(__file__),
            'markdown': file_record(markdown), 'scenes': report,
            'note': 'Temporal evidence only; stop reason undetermined. No score changes.',
        }, stream, ensure_ascii=False, indent=2)
    print(f'{len(report)} development scenes, {count} events: {markdown}')


if __name__ == '__main__':
    main()
