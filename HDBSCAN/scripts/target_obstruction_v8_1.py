"""Identity-local blockage aggregation; preserve legacy duration convention."""
import numpy as np
from HDBSCAN.scripts import scene_feature_rules as rules
from HDBSCAN.scripts.target_obstruction_v8 import obstruction_episodes


def blocked_evidence(target_ids, times):
    episodes = obstruction_episodes(target_ids, times)
    flags = [False]*len(times)
    steps = np.diff(times)
    tail = float(np.median(steps)) if len(steps) else 0.
    for episode in episodes:
        indices = episode['indices']
        duration = episode['observed_duration'] + tail if len(indices) > 1 else 0.
        episode['qualifying_duration'] = duration
        episode['blocked'] = duration >= .8
        if episode['blocked']:
            for i in indices:
                flags[i] = True
    return flags, episodes


def update_blockage(audit, context, fields, trace):
    """Recompute only blockage/deviation dependents, keeping short avoidance."""
    times = audit['times']
    ids = [identity if active else None for identity, active in
           zip(trace['stationary_ids'], trace['static_flags'])]
    if len(ids) != len(times):
        raise ValueError('Static trace/timeline mismatch')
    flags, episodes = blocked_evidence(ids, times)
    raw = False
    for episode in episodes:
        indices = episode['indices']
        episode['raw_deviation'] = False
        if not episode['blocked']:
            continue
        first = indices[0]
        heading = audit['ego_yaws'][first]
        distance = min(trace['selected'][i]['clearance'] for i in indices)
        shift = rules.lateral_shift_after_index(audit['ego_positions'], times, first, heading, horizon=10.)
        turn = rules.net_heading_change_after_index(audit['ego_yaws'], times, first, heading, horizon=10.)
        episode['raw_deviation'] = bool(rules.is_obstacle_induced_route_deviation(
            episode['qualifying_duration'], distance, shift, turn))
        episode.update(minimum_clearance=distance, lateral_shift=shift, net_heading_change=turn)
        raw |= episode['raw_deviation']
    support = rules.is_route_deviation_context_supported(
        context['traffic_light_control_density'], context['crossing_vehicle_exposure_ratio'],
        context['intersection_stop_ratio'], context['left_turn_cross_traffic_interaction_ratio'])
    deviation = bool(raw and support)
    ratio = rules.summarize_events(flags, times).ratio
    result = dict(fields)
    result.update(blocked_path_obstacle_ratio=ratio,
                  obstacle_induced_route_deviation_flag=int(deviation),
                  route_deviation_decision_demand=rules.route_deviation_decision_demand(ratio, deviation))
    return result, dict(blocked_flags=flags, episodes=episodes, raw_deviation=bool(raw))
