"""Development-only roadside passing diagnostics; never a risk or clustering input."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

try:
    from .experiment_partition import (load_development_features, assert_development_frame,
        assert_new_outputs, file_record, provenance_path)
    from .scene_feature_rules import is_bounded_stationary_track, wrapped_heading_change
except ImportError:
    from experiment_partition import (load_development_features, assert_development_frame,
        assert_new_outputs, file_record, provenance_path)
    from scene_feature_rules import is_bounded_stationary_track, wrapped_heading_change


PARAMETERS = {'ego_width_m': 1.85, 'ego_length_m': 4.5, 'maximum_forward_m': 30,
              'maximum_lateral_m': 6, 'maximum_clearance_m': 3,
              'maximum_sample_gap_s': 1, 'minimum_pass_span_s': 1,
              'minimum_ego_travel_m': 5,
              'low_speed_limit_mps': 1, 'lateral_motion_m': 1.5,
              'curved_heading_change_rad': .35}


def find_passages(scene, map_context):
    times = np.asarray(scene['times'], dtype=float)
    ego = np.asarray(scene['ego_positions'], dtype=float)
    yaws = np.asarray(scene['ego_yaws'], dtype=float)
    if (times.ndim != 1 or not len(times) or ego.shape != (len(times), 2)
            or yaws.shape != times.shape or not np.isfinite(times).all()
            or not np.isfinite(ego).all() or not np.isfinite(yaws).all()
            or np.any(np.diff(times) <= 0)):
        raise ValueError('Invalid scene trajectory')
    result = {'candidates': [], 'excluded': []}
    for instance, track in scene['vehicle_tracks'].items():
        previous = -1
        for row in track:
            i = row['index']
            try:
                values = np.asarray([row['forward'], row['lateral'], row['heading_delta'],
                                     row['width'], row['length'], *row['position'], *row['velocity']], dtype=float)
                valid = (values.shape == (9,) and np.isfinite(values).all()
                         and values[3] > 0 and values[4] > 0)
            except (TypeError, ValueError):
                valid = False
            if type(i) is not int or not previous < i < len(times) or not valid:
                raise ValueError(f'Invalid actor geometry: {instance}')
            previous = i
        if not track:
            continue
        whole_peak_speed = max(np.linalg.norm(r['velocity']) for r in track)
        positions = np.asarray([r['position'] for r in track])
        diameter = float(np.max(np.linalg.norm(positions[:, None] - positions[None, :], axis=2)))
        runs = []
        for row in track:
            if (abs(row['forward']) > PARAMETERS['maximum_forward_m']
                    or abs(row['lateral']) > PARAMETERS['maximum_lateral_m']):
                continue
            if (not runs or row['index'] != runs[-1][-1]['index'] + 1
                    or times[row['index']] - times[runs[-1][-1]['index']] > PARAMETERS['maximum_sample_gap_s']):
                runs.append([])
            runs[-1].append(row)
        for run in runs:
            start, end = run[0], run[-1]
            def extent(row):
                return (PARAMETERS['ego_length_m'] / 2
                        + abs(np.cos(row['heading_delta'])) * row['length'] / 2
                        + abs(np.sin(row['heading_delta'])) * row['width'] / 2)
            if not (start['forward'] > extent(start) and end['forward'] < -extent(end)):
                continue
            indices = [r['index'] for r in run]
            peak_speed = max(np.linalg.norm(r['velocity']) for r in run)
            if peak_speed >= PARAMETERS['low_speed_limit_mps']:
                continue
            bounded = is_bounded_stationary_track(
                [r['position'] for r in run], [times[i] for i in indices])
            motion = 'static_supported' if bounded else 'low_speed_uncertain'
            if times[indices[-1]] - times[indices[0]] < PARAMETERS['minimum_pass_span_s']:
                continue
            travel = float(np.sum(np.linalg.norm(np.diff(ego[indices], axis=0), axis=1)))
            if travel < PARAMETERS['minimum_ego_travel_m']:
                continue
            closest = min(run, key=lambda r: abs(r['forward']))
            delta = closest['heading_delta']
            clearance = (abs(closest['lateral']) - PARAMETERS['ego_width_m'] / 2
                         - abs(np.cos(delta)) * closest['width'] / 2
                         - abs(np.sin(delta)) * closest['length'] / 2)
            if clearance > PARAMETERS['maximum_clearance_m']:
                continue
            local_delta = ego[indices] - ego[indices[0]]
            normal = np.array([-np.sin(yaws[indices[0]]), np.cos(yaws[indices[0]])])
            lateral_range = float(np.ptp(local_delta @ normal))
            heading_change = wrapped_heading_change(yaws[indices])
            path = ('curved_path_uncertain' if heading_change > PARAMETERS['curved_heading_change_rad']
                    else 'lateral_motion_observed' if lateral_range >= PARAMETERS['lateral_motion_m']
                    else 'no_clear_lateral_maneuver')
            context = map_context(scene, closest)
            event = {'instance_token': instance, 'category': closest['category'],
                     'start_s': float(times[indices[0]]), 'end_s': float(times[indices[-1]]),
                     'pass_sample_s': float(times[closest['index']]), 'frame_count': len(run),
                     'motion_status': motion, 'passage_peak_speed_mps': float(peak_speed),
                     'whole_track_peak_speed_mps': float(whole_peak_speed),
                     'motion_elsewhere_observed': bool(whole_peak_speed >= PARAMETERS['low_speed_limit_mps']),
                     'whole_track_diameter_m': diameter, 'lateral_clearance_m': float(clearance),
                     'clearance_note': 'Approximate body projection at nearest longitudinal keyframe, not minimum swept clearance.',
                     'ego_lateral_range_m': lateral_range, 'ego_heading_change_rad': float(heading_change),
                     'path_evidence': path, 'map_context': context,
                     'avoidance_cause': 'undetermined', 'diagnostic_only': True}
            if not context.get('available'):
                event['exclusion'] = 'map_unknown'
            elif not context.get('on_drivable'):
                event['exclusion'] = 'off_drivable_surface'
            elif not (context.get('same_lane') or context.get('same_road')):
                event['exclusion'] = 'road_relation_not_supported'
            if 'exclusion' in event:
                result['excluded'].append(event)
            else:
                result['candidates'].append(event)
    return result


class MapContext:
    def __init__(self, dataroot, locations):
        self.dataroot = dataroot
        self.locations = locations
        self.maps = {}
        self.sources = {}

    def __call__(self, scene, row):
        from nuscenes.map_expansion.map_api import NuScenesMap
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        from shapely.prepared import prep
        name = self.locations[scene['scene_name']]
        try:
            if name not in self.maps:
                m = NuScenesMap(dataroot=str(self.dataroot), map_name=name)
                polygons = [m.extract_polygon(t) for r in m.drivable_area for t in r['polygon_tokens']]
                self.maps[name] = (m, prep(unary_union(polygons)))
                self.sources[name] = file_record(self.dataroot / 'maps/expansion' / (name + '.json'))
            m, surface = self.maps[name]
            i = row['index']
            angle = scene['ego_yaws'][i] + row['heading_delta']
            x, y = row['position']
            footprint = Polygon([(x + a*np.cos(angle) - b*np.sin(angle),
                                  y + a*np.sin(angle) + b*np.cos(angle))
                                 for a,b in [(-row['length']/2,-row['width']/2),
                                             (row['length']/2,-row['width']/2),
                                             (row['length']/2,row['width']/2),
                                             (-row['length']/2,row['width']/2)]])
            actor = m.layers_on_point(x, y, ['lane', 'road_segment'])
            ego = m.layers_on_point(*scene['ego_positions'][i], ['lane', 'road_segment'])
            return {'available': True, 'on_drivable': bool(surface.intersects(footprint)),
                    'same_lane': bool(actor['lane'] and actor['lane'] == ego['lane']),
                    'same_road': bool(actor['road_segment'] and actor['road_segment'] == ego['road_segment']),
                    'actor_layers': actor, 'ego_layers': ego}
        except Exception as exc:
            return {'available': False, 'error': f'{type(exc).__name__}: {exc}'}


def validate_pair(feature_path, audit_path):
    manifest = json.loads(provenance_path(feature_path).read_text(encoding='utf-8'))
    if (manifest.get('stage') != 'feature_extraction'
            or manifest.get('output', {}).get('sha256') != file_record(feature_path)['sha256']
            or manifest.get('extra', {}).get('trajectory_audit', {}).get('sha256') != file_record(audit_path)['sha256']):
        raise ValueError('Features and trajectory audit lack matching extraction provenance')


def render_markdown(report):
    lines = ['# 静止/低速车辆旁通过候选', '',
             '仅作开发诊断，不进入风险评分或聚类。通过候选不等于占道事实、避障换道或真实冲突。',
             '间隙为最近纵向关键帧处的近似车身横向投影间距，非连续最小间距；负值也不是碰撞证明。',
             '横移仅为观测几何，不证明因目标让行；静止性未确认、弯道及地图未知均单独保留。', '']
    for name, result in report.items():
        lines += [f'## {name}', '', '| 经过时刻/s | 目标实例 | 静止证据 | 车道/道路关系 | 近似间隙/m | 路径证据 |',
                  '| --- | --- | --- | --- | --- | --- |']
        for e in result['candidates']:
            state = '有静止证据' if e['motion_status'] == 'static_supported' else '低速，静止性未确认'
            relation = '同一车道多边形' if e['map_context']['same_lane'] else '同一道路区域（车道关系未确认）'
            path = {'no_clear_lateral_maneuver':'未观察到明确横向动作',
                    'lateral_motion_observed':'存在横移，因果未确定', 'curved_path_uncertain':'弯曲路径，尚不能归因'}[e['path_evidence']]
            lines.append(f"| {e['pass_sample_s']:.2f} | {e['instance_token']} | {state} | {relation} | {e['lateral_clearance_m']:.2f} | {path} |")
        if not result['candidates']:
            lines.append('| - | 无满足条件的候选 | - | - | - | - |')
        lines += ['', f"未纳入候选的地图证据记录：{len(result['excluded'])} 条，原因见 JSON。", '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output-prefix', type=Path, required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    features, _, partition = load_development_features(args.features)
    validate_pair(args.features, args.audit)
    scenes = json.loads(args.audit.read_text(encoding='utf-8'))
    identities = pd.DataFrame([{'scene_name':s['scene_name'], 'scene_token':s['scene_token']} for s in scenes])
    assert_development_frame(identities, partition)
    if set(identities.scene_name) != set(features.scene_name):
        raise ValueError('Scene sets must match')
    output, markdown = Path(str(args.output_prefix)+'.json'), Path(str(args.output_prefix)+'.md')
    assert_new_outputs([output, markdown])
    if args.preflight:
        for scene in scenes:
            find_passages(scene, lambda s,r: {'available': False, 'error':'preflight skips maps'})
        print(f'{len(scenes)} development scenes; paired provenance valid; no maps loaded or files written')
        return
    context = MapContext(Path(__file__).resolve().parents[2] / 'nuScenes',
                         dict(zip(features.scene_name, features.log_location)))
    report = {s['scene_name']: find_passages(s, context) for s in scenes}
    output.parent.mkdir(parents=True, exist_ok=True)
    with markdown.open('x', encoding='utf-8') as stream:
        stream.write(render_markdown(report))
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'created_at_utc':datetime.now(timezone.utc).isoformat(),
                   'scope':'development_diagnostic_only', 'python':sys.executable,
                   'command':[sys.executable,*sys.argv], 'parameters':PARAMETERS,
                   'partition':partition['file'], 'inputs':[file_record(args.features),file_record(args.audit),
                                                          file_record(provenance_path(args.features))],
                   'scripts':[file_record(__file__), file_record(Path(__file__).with_name('scene_feature_rules.py'))],
                   'maps':context.sources, 'markdown':file_record(markdown), 'scenes':report},
                  stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'{len(scenes)} scenes; {sum(len(r["candidates"]) for r in report.values())} candidates; {markdown}')


if __name__ == '__main__':
    main()
