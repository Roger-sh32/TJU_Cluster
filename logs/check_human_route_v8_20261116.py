"""Compute observed route evidence for the existing 35 human target anchors."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from HDBSCAN.scripts import human_route_v8 as rules


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    tables = ROOT/'HDBSCAN/tables'
    report = tables/'human_evidence29_20261024_report.json'
    if sha(report) != '9035ce0ea61084e5c4fa1c9f195a2c73a15b29680cb423e90e3a0e5dbdb02e18':
        raise ValueError('Original human report changed')
    record = json.loads(report.read_text(encoding='utf8'))
    human = tables/'human_evidence29_20261024.json'
    tracks = tables/'crossing_v5_2_regression29_trajectory_20261013.json'
    for path in (human, tracks):
        binding = next(r for r in record['inputs']+record['outputs'] if Path(r['path']) == path)
        if sha(path) != binding['sha256']:
            raise ValueError('Bound evidence changed')
    output = ROOT/'logs/human_route_v8_35_20261116.json'
    if output.exists():
        raise FileExistsError('Preserve previous evidence')
    ego = {s['scene_name']: s for s in json.loads(tracks.read_text(encoding='utf8'))}
    results = []
    for scene in json.loads(human.read_text(encoding='utf8'))['scenes']:
        for c in scene['candidate_anchors']:
            evidence = rules.route_evidence(ego[scene['scene_name']], scene['human_tracks'][c['instance_token']], c['index'])
            results.append(dict(scene_name=scene['scene_name'], index=c['index'], instance=c['instance_token'],
                                observed_positive=c['legacy_observed_relevant'], **evidence))
    if len(results) != 35:
        raise ValueError('Expected original 35 target anchors')
    with output.open('x', encoding='utf8') as stream:
        json.dump(dict(scope='geometry evidence only; no feature suppression or barrier inference',
                       sources=[dict(path=str(p), sha256=sha(p)) for p in
                                (report, human, tracks, Path(rules.__file__), Path(__file__))],
                       targets=results), stream, ensure_ascii=False, indent=2, allow_nan=False)
    from collections import Counter
    print(dict(Counter(r['relation'] for r in results)))
    for r in results:
        if r['scene_name'] in ('scene-0102', 'scene-0151') or r['observed_positive']:
            print(r['scene_name'], r['index'], r['relation'], r['clearance_lower_m'], r['observed_positive'])


if __name__ == '__main__':
    main()
