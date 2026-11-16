"""Recompute eight prediction-dependent columns on the fixed development29."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from HDBSCAN.scripts import human_filter_v8 as rules


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    route_path = ROOT/'logs/human_route_v8_35_20261116.json'
    route = json.loads(route_path.read_text(encoding='utf8'))
    for r in route['sources']:
        if sha(r['path']) != r['sha256']:
            raise ValueError('Route source changed')
    tables = ROOT/'HDBSCAN/tables'
    report_path = tables/'human_evidence29_20261024_report.json'
    if sha(report_path) != '9035ce0ea61084e5c4fa1c9f195a2c73a15b29680cb423e90e3a0e5dbdb02e18':
        raise ValueError('Original human report changed')
    human_path = tables/'human_evidence29_20261024.json'
    track_path = tables/'crossing_v5_2_regression29_trajectory_20261013.json'
    humans = json.loads(human_path.read_text(encoding='utf8'))['scenes']
    tracks = {s['scene_name']: s for s in json.loads(track_path.read_text(encoding='utf8'))}
    evidence = {(r['scene_name'], r['index'], r['instance']): r for r in route['targets']}
    output = ROOT/'logs/human_filter_v8_development29_20261116.json'
    if output.exists():
        raise FileExistsError('Preserve original candidate result')
    results = []
    for scene in humans:
        name = scene['scene_name']
        audit = tracks[name]
        anchors = scene['candidate_anchors']
        original = scene['legacy_vru_reproduction']
        before = rules.aggregate(anchors, audit['times'], scene['frame_flags']['crosswalk'], set())
        if any(abs(value-original[key]) > 1e-8 for key, value in before.items()):
            raise ValueError('Original eight-column baseline mismatch: '+name)
        suppressed, decisions = set(), []
        for anchor in anchors:
            key = (anchor['index'], anchor['instance_token'])
            geometry = evidence[(name,) + key]
            protected = rules.response_protected(audit, key[0], bool(scene['frozen_vehicle_context']['ego_evasive_lane_change_flag']))
            remove = rules.should_suppress(anchor['legacy_observed_relevant'], geometry['relation'], protected)
            if remove:
                suppressed.add(key)
            decisions.append(dict(index=key[0], instance=key[1], response_protected=protected,
                                  relation=geometry['relation'], suppressed=remove))
        after = rules.aggregate(anchors, audit['times'], scene['frame_flags']['crosswalk'], suppressed)
        changes = {k: dict(before=before[k], after=v) for k, v in after.items() if v != before[k]}
        if name in {'scene-0011', 'scene-0067'} and changes:
            raise ValueError('Observed positive control changed')
        results.append(dict(scene_name=name, changes=changes, decisions=decisions))
    if len(results) != 29 or sum(len(r['decisions']) for r in results) != 35:
        raise ValueError('Expected fixed29/35 anchors')
    with output.open('x', encoding='utf8') as stream:
        json.dump(dict(scope='development candidate, no promotion or scoring',
                       baseline_eight_columns_matched=True, scenes=results,
                       sources=[dict(path=str(p), sha256=sha(p)) for p in
                                (route_path, report_path, human_path, track_path, Path(rules.__file__), Path(__file__))]),
                  stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps([r for r in results if r['changes']], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
