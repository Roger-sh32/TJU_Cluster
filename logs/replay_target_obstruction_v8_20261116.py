"""Bounded development replay of experimental raw-protection release."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from HDBSCAN.scripts import longitudinal_candidate_v7 as legacy
from HDBSCAN.scripts import target_obstruction_v8 as candidate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    tables = ROOT/'HDBSCAN/tables'
    output = ROOT/'logs/target_obstruction_v8_development29_20261116.json'
    if output.exists():
        raise FileExistsError('Preserve existing result')
    report_path = tables/'longitudinal_v7_replay29_comparison_20261015.json'
    if digest(report_path) != 'b7df6d51107f04cf3b7fdf9142fcddf24cec1a997e99277555ce3eab4872bdf3':
        raise ValueError('Original v7 report changed')
    report = json.loads(report_path.read_text(encoding='utf8'))
    bindings = [report['protocol'], *report['outputs']]
    for record in bindings:
        if digest(record['path']) != record['sha256']:
            raise ValueError('Original v7 binding changed: '+record['path'])
    protocol = json.loads(Path(report['protocol']['path']).read_text(encoding='utf8'))
    tracks_path = tables/'crossing_v5_2_regression29_trajectory_20261013.json'
    track_binding = next(r for r in protocol['inputs'] if Path(r['path']) == tracks_path)
    if digest(tracks_path) != track_binding['sha256']:
        raise ValueError('Original tracks changed')
    tracks = json.loads(tracks_path.read_text(encoding='utf8'))
    previous = json.loads((tables/'longitudinal_v7_replay29_ledger_20261015.json').read_text(encoding='utf8'))['scenes']
    frame = pd.read_csv(tables/'scene_features_longitudinal_v7_replay29_20261015.csv', float_precision='round_trip')
    if len(frame) != 29 or frame.scene_name.tolist() != [a['scene_name'] for a in tracks]:
        raise ValueError('Fixed development identities changed')
    if frame.scene_name.tolist() != [a['scene_name'] for a in previous]:
        raise ValueError('Ledger order changed')
    results = []
    for audit, prior, row in zip(tracks, previous, frame.to_dict('records')):
        old_rejected = {tuple(v) for v in prior['rejected']}
        before, trace = legacy.summarize(audit, prior['ledger'], row, old_rejected)
        for key, value in before.items():
            if value != row[key]:
                raise ValueError('v7 baseline mismatch: '+row['scene_name']+'/'+key)
        if trace != prior['candidate']:
            raise ValueError('v7 target trace mismatch')
        ids = [t if active else None for t, active in zip(trace['stationary_ids'], trace['static_flags'])]
        episodes = candidate.obstruction_episodes(ids, audit['times'])
        sustained = {e['instance_token'] for e in episodes if e['observed_duration'] >= .8}
        # Query existing geometry independently of the old scene-wide protection.
        possible, routes = legacy.gate_candidates(audit, prior['ledger'], False)
        route_map = {(r['index'], r['instance_token']): r for r in routes}
        extra, decisions = set(), []
        for i, instance in sorted(possible-old_rejected):
            c = next(c for c in prior['ledger'][i] if c['instance_token'] == instance)
            history = candidate.target_history_evidence(audit, instance, i)
            release = candidate.can_release_raw_protection(
                raw_protected=bool(audit['obstacle_induced_route_deviation_candidate']),
                strict_avoidance=bool(row['ego_evasive_lane_change_flag']),
                supported_deviation=bool(row['obstacle_induced_route_deviation_flag']),
                target_sustained=instance in sustained, history_complete=history['complete'],
                historical_clearance=history['clearance'],
                route_relation=route_map[i, instance]['relation'],
                eligible_static_opposite=legacy.should_reject(c, legacy.geometry.SEPARATED, False))
            if release:
                extra.add((i, instance))
            decisions.append(dict(index=i, instance_token=instance, history=history, release=release))
        after, new_trace = legacy.summarize(audit, prior['ledger'], row, old_rejected | extra)
        if (before['ego_evasive_lane_change_flag'] != after['ego_evasive_lane_change_flag']
                or (before['ego_evasive_lane_change_flag'] and trace['first_static_index'] != new_trace['first_static_index'])):
            raise ValueError('Downstream avoidance dependency changed')
        changes = {key: dict(before=before[key], after=value) for key, value in after.items() if value != before[key]}
        if row['scene_name'] in {'scene-0011', 'scene-0030', 'scene-0026', 'scene-0042'} and (changes or trace != new_trace):
            raise ValueError('Positive control drift')
        results.append(dict(scene_name=row['scene_name'], extra_rejected=sorted(extra),
                            changes=changes, decisions=decisions, episodes=episodes))
    sources = [report_path, tracks_path, Path(__file__), Path(candidate.__file__), Path(legacy.__file__)]
    result = dict(scope='experimental fixed development29; not feature promotion or fit',
                  history_horizon_seconds=1., historical_clearance_margin_m=1.,
                  sustained_observed_span_seconds=.8, positive_controls_unchanged=True,
                  sources=[dict(path=str(p), sha256=digest(p)) for p in sources], scenes=results)
    with output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps([dict(scene=r['scene_name'], rejected=len(r['extra_rejected']), changes=r['changes'])
                      for r in results if r['changes']], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
