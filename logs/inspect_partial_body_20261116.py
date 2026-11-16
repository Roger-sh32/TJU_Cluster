"""Geometric footprint candidates on frozen development tracks, not risk labels."""
import hashlib
import json
import math
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shapely.geometry import box
from HDBSCAN.scripts import crossing_candidate_v5_2 as geometry
from HDBSCAN.scripts import scene_feature_rules as rules


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    path = ROOT/'HDBSCAN/tables/crossing_v5_2_regression29_trajectory_20261013.json'
    report = ROOT/'HDBSCAN/tables/human_evidence29_20261024_report.json'
    if sha(report) != '9035ce0ea61084e5c4fa1c9f195a2c73a15b29680cb423e90e3a0e5dbdb02e18':
        raise ValueError('Original report changed')
    binding = next(r for r in json.loads(report.read_text(encoding='utf8'))['inputs'] if Path(r['path']) == path)
    if sha(path) != binding['sha256']:
        raise ValueError('Original tracks changed')
    output = ROOT/'logs/partial_body_development29_20261116.json'
    if output.exists():
        raise FileExistsError('Preserve previous diagnostic')
    corridor = box(geometry.EGO_LENGTH/2, -1.8, 80., 1.8)
    scenes = []
    for a in json.loads(path.read_text(encoding='utf8')):
        targets = []
        for instance, track in a['vehicle_tracks'].items():
            speed = a['instance_max_speeds'][instance]
            static = speed <= .5 or (instance in a['bounded_stationary_instances'] and speed < 1.)
            if not static:
                continue
            frames = []
            for v in track:
                if math.cos(v['heading_delta']) <= .3:
                    continue
                footprint = geometry._box([v['forward'], v['lateral']], v['heading_delta'], v['width'], v['length'])
                area = footprint.intersection(corridor).area
                if area > 0:
                    frames.append(dict(index=v['index'], time=a['times'][v['index']],
                                       center_outside=abs(v['lateral']) > 1.8, overlap_area=float(area)))
            if not frames:
                continue
            i = frames[0]['index']
            available = a['times'][-1]-a['times'][i]
            targets.append(dict(instance=instance, category=track[0]['category'], frames=frames,
                available_ego_future_seconds=available, ten_second_future_available=available >= 10.,
                observed_lateral_shift=rules.lateral_shift_after_index(a['ego_positions'], a['times'], i, a['ego_yaws'][i], horizon=10.),
                observed_net_turn=rules.net_heading_change_after_index(a['ego_yaws'], a['times'], i, a['ego_yaws'][i], horizon=10.)))
        scenes.append(dict(scene_name=a['scene_name'], targets=targets))
    with output.open('x', encoding='utf8') as stream:
        json.dump(dict(scope='body intersection with heading-aligned strip, not lane occupancy or causal response',
                       sources=[dict(path=str(p), sha256=sha(p)) for p in (path, report, Path(__file__))], scenes=scenes),
                  stream, ensure_ascii=False, indent=2, allow_nan=False)
    for s in scenes:
        if s['scene_name'] == 'scene-0552':
            print(json.dumps(s, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
