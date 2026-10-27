"""Diagnostic only: compare circular margins with observed oriented footprints."""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

import numpy as np
from shapely.geometry import LineString, Point, Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs.diagnose_review8_20261012 import REPORT, TRAJECTORY, PROTOCOL, verify_records, write_json
from logs.build_semantic_review_pack_20261001 import record
from HDBSCAN.scripts.experiment_partition import assert_new_outputs
from HDBSCAN.scripts.frozen_model import source_hashes

OUTPUT = ROOT / 'HDBSCAN/tables/target_diagnosis8_geometry_20261012.json'


def oriented_footprint(position, yaw, width, length):
    values = np.asarray([*position, yaw, width, length], dtype=float)
    if values.shape != (5,) or not np.isfinite(values).all() or width <= 0 or length <= 0:
        raise ValueError('Unknown or invalid oriented footprint')
    c, s = math.cos(yaw), math.sin(yaw)
    corners = [(length / 2, width / 2), (length / 2, -width / 2),
               (-length / 2, -width / 2), (-length / 2, width / 2)]
    return Polygon([(position[0] + c*x - s*y, position[1] + s*x + c*y) for x, y in corners])


def main():
    assert_new_outputs([OUTPUT])
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_records(protocol['inputs'])
    verify_records([report[k] for k in ('protocol', 'features', 'trajectory', 'quality', 'continuation')])
    verification_path = ROOT / 'HDBSCAN/tables/target_diagnosis8_verification_20261012.json'
    verification = json.loads(verification_path.read_text(encoding='utf-8'))
    verify_records([verification[k] for k in ('script', 'protocol', 'report', 'document')])
    if source_hashes() != protocol['source_hashes'] or report['evaluation_used']:
        raise ValueError('Source or development scope changed')
    audits = {r['scene_name']: r for r in json.loads(TRAJECTORY.read_text(encoding='utf-8'))}
    results = []
    for scene in report['scenes']:
        audit = audits[scene['scene_name']]
        times, positions = audit['times'], audit['ego_positions']
        for candidate in scene['crossing_candidates']:
            index = candidate['index']
            future = [i for i in range(index, len(times)) if times[i]-times[index] <= 6.0]
            track = [r for r in audit['vehicle_tracks'][candidate['instance_token']] if r['index'] in future]
            route = LineString([positions[i] for i in future]) if len(future) > 1 else Point(positions[index])
            center_distance = min(Point(r['position']).distance(route) for r in track)
            np.testing.assert_allclose(center_distance, candidate['minimum_future_route_distance'],
                                       rtol=0, atol=1e-8)
            polygons = [oriented_footprint(r['position'], audit['ego_yaws'][r['index']]+r['heading_delta'],
                                          r['width'], r['length']) for r in track]
            spatial = min(p.distance(route) for p in polygons)
            synchronized = min(p.distance(Point(positions[r['index']])) for p, r in zip(polygons, track))
            first = next(r for r in track if r['index'] == index)
            yaw = audit['ego_yaws'][index]
            vx, vy = first['velocity']
            lateral_speed = -math.sin(yaw)*vx + math.cos(yaw)*vy
            approaching = first['lateral']*lateral_speed < 0
            t_corridor = ((abs(first['lateral'])-2.5)/abs(lateral_speed)
                          if approaching and abs(first['lateral']) > 2.5 else None)
            results.append({'scene_name': scene['scene_name'], 'instance_token': candidate['instance_token'],
                'time_s': times[index], 'retained_by_v4': candidate['retained'],
                'future_complete_by_v4': candidate['future_complete'],
                'ego_observed_future_s': times[future[-1]]-times[index],
                'actor_observed_future_s': times[track[-1]['index']]-times[index],
                'actor_observation_count': len(track),
                'center_to_whole_route_min_m': center_distance,
                'circumscribed_route_threshold_m': 2.5+candidate['actor_bounding_diameter']/2,
                'oriented_box_to_whole_route_min_m': spatial,
                'synchronized_ego_point_to_actor_box_min_m': synchronized,
                'constant_heading_lateral_time_to_corridor_s': t_corridor,
                'current_actor_lateral_speed_mps': lateral_speed,
                'yielding_protection_by_v4': candidate['yielding_response']})
    write_json(OUTPUT, {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'command': [sys.executable, *sys.argv], 'script': record(__file__),
        'tests': record(ROOT / 'logs/test_target_geometry_20261012.py'),
        'inputs': [record(REPORT), record(TRAJECTORY), record(verification_path), record(PROTOCOL)],
        'source_hashes': source_hashes(), 'evaluation_used': False, 'feature_changes': False,
        'semantic_acceptance': False, 'candidates': results,
        'limitations': ['Observed keyframe rectangles only; not a continuous swept-volume test.',
            'Whole-route spatial distance mixes different times; synchronized distances use ego center, not ego body.',
            'No ego footprint, safety buffer, heading uncertainty or annotation uncertainty is subtracted.',
            'Constant-heading corridor arrival is a diagnostic projection, not a collision prediction.',
            'Incomplete futures and yielding may hide a potential conflict; distances do not certify safety.',
            'No rejection, rescoring or feature modification is performed.']})
    print(json.dumps([r for r in results if r['retained_by_v4']], indent=2))


if __name__ == '__main__':
    main()
