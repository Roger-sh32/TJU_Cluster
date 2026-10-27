"""Same-target historical episode continuity; v6 geometry/crossings unchanged."""

import numpy as np

from HDBSCAN.scripts import crossing_candidate_v6 as parent
from HDBSCAN.scripts import crossing_candidate_v5_2 as legacy

CANDIDATE_VERSION = 'crossing_candidate_v6_1_replay_20261015'
crossing_candidate_audit = parent.crossing_candidate_audit
audit_route_relations = parent.audit_route_relations


def local_left_interaction_audit(times, yaws, tracks, evidence, yield_flags, speeds,
                                  *, route_evidence):
    """Extend historical context only, never current conflict or causal certainty."""
    times, yaws = legacy._timeline(times, yaws)
    speeds = np.asarray(speeds, float)
    if (len(yield_flags) != len(times) or speeds.shape != times.shape
            or not np.isfinite(speeds).all() or np.any(speeds < 0)):
        raise ValueError('Invalid response timeline')
    for rows in (evidence, route_evidence):
        for row in rows:
            index, instance = row.get('index'), row.get('instance_token')
            if (type(index) is not int or not 0 <= index < len(times)
                    or type(instance) is not str or not instance or instance not in tracks):
                raise ValueError('Invalid evidence identity')
            for key in ('effective_conflict', 'future_complete', 'unresolved',
                        'yielding_response', 'soft_deceleration_response'):
                if key in row and type(row[key]) is not bool:
                    raise ValueError('Non-boolean evidence status')
    routes = {(r['index'], r['instance_token']): r for r in route_evidence}
    identities = [(r['index'], r['instance_token']) for r in evidence]
    if len(routes) != len(route_evidence) or len(identities) != len(set(identities)):
        raise ValueError('Duplicate target evidence')
    flags, targets, restored = [False]*len(times), {}, []
    for instance, track in tracks.items():
        indices = [r['index'] for r in track]
        if (any(type(i) is not int or not 0 <= i < len(times) for i in indices)
                or indices != sorted(set(indices))):
            raise ValueError('Invalid target timeline')
        exposed = [r['index'] for r in track if r.get('crossing_exposure')]
        if not exposed:
            continue
        own_evidence = [r for r in evidence if r['instance_token'] == instance]
        own_routes = [r for r in route_evidence if r['instance_token'] == instance]
        current = parent.local_left_interaction_flags(times, yaws, {instance: track},
            own_evidence, yield_flags, speeds, route_evidence=own_routes)
        original = legacy.local_left_interaction_flags(times, yaws,
            {instance: track}, own_evidence, yield_flags, speeds)
        seeds = set()
        for item in own_evidence:
            index = item['index']
            route = routes.get((index, instance), {})
            if (index in exposed and item.get('effective_conflict')
                    and item.get('state') == 'response_protected_prediction'
                    and item.get('future_complete') and not item.get('unresolved', True)
                    and item.get('route_relation') == 'potential_route_overlap'
                    and route.get('relation') == 'potential_route_overlap'
                    and route.get('future_complete')
                    and (item.get('yielding_response') or item.get('soft_deceleration_response'))):
                seeds.add(index)
        episodes, episode = [], []
        for index in exposed:
            if episode and times[index]-times[episode[-1]] > .75:
                episodes.append(episode)
                episode = []
            episode.append(index)
        if episode:
            episodes.append(episode)
        for episode in episodes:
            own_seeds = sorted(seeds.intersection(episode))
            for index in episode:
                eligible = [seed for seed in own_seeds
                            if 0 <= times[index]-times[seed] <= legacy.HORIZON]
                if original[index] and not current[index] and eligible:
                    current[index] = True
                    restored.append(dict(index=index, instance_token=instance,
                        seed_index=eligible[0], kind='historical_response_episode'))
        targets[instance] = current
        flags = [a or b for a, b in zip(flags, current)]
    return dict(flags=flags, target_flags=targets, restored=restored)


def local_left_interaction_flags(times, yaws, tracks, evidence, yield_flags, speeds,
                                 *, route_evidence):
    return local_left_interaction_audit(times, yaws, tracks, evidence, yield_flags,
                                       speeds, route_evidence=route_evidence)['flags']
