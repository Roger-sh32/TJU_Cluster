"""Pure frozen-track longitudinal replay and conservative preselection gate."""

import numpy as np

from HDBSCAN.scripts import scene_feature_rules as r
from HDBSCAN.scripts import crossing_candidate_v6 as geometry

VERSION = 'longitudinal_candidate_v7_20261015'


def select_nearest(candidates, rejected):
    best = None
    for c in candidates:
        if (c['instance_token'] in rejected or c['supported'] is not True
                or c['clearance'] is None):
            continue
        if best is None or c['clearance'] < best['clearance']:
            best = c
    return best


def should_reject(c, relation, protected_context):
    if type(protected_context) is not bool or type(c['permanent_static']) is not bool:
        raise ValueError('Expected boolean context/static evidence')
    numbers = [c['target_speed'], c['heading_delta'], c['local_turn']]
    if not np.isfinite(numbers).all():
        raise ValueError('Invalid longitudinal candidate geometry')
    return bool(not protected_context and c['supported'] is True and c['on_surface'] is True
                and c['clearance'] is not None and c['permanent_static']
                and c['target_speed'] < .5 and np.cos(c['heading_delta']) < 0
                and c['local_turn'] >= .35 and relation == geometry.SEPARATED)


def build_ledger(audit, annotation_tokens):
    times, yaws = geometry.parent._timeline(audit['times'], audit['ego_yaws'])
    speeds = np.asarray(audit['ego_speeds'], float)
    if speeds.shape != times.shape or not np.isfinite(speeds).all():
        raise ValueError('Invalid ego speeds')
    tracks = {}
    expected = set()
    for instance, track in audit['vehicle_tracks'].items():
        indices = [v['index'] for v in track]
        if indices != sorted(set(indices)):
            raise ValueError('Duplicate/unsorted vehicle track')
        for v in track:
            i = v['index']
            if type(i) is not int or not 0 <= i < len(times):
                raise ValueError('Invalid vehicle frame')
            vx, vy = v['velocity']
            vf = vx*np.cos(yaws[i])+vy*np.sin(yaws[i])
            vl = -vx*np.sin(yaws[i])+vy*np.cos(yaws[i])
            speed = float(np.sqrt(vx*vx+vy*vy))
            if r.classify_vehicle_interaction(v['forward'], v['lateral'], vf, vl, speeds[i]).same_path:
                expected.add((i, instance))
            tracks[i, instance] = (v, speed, float(vf))
    ledger, seen = [[] for _ in times], set()
    for support in audit['lane_targets']:
        i, instance = support['index'], support['instance']
        key = (i, instance)
        if key in seen or key not in expected or key not in annotation_tokens:
            raise ValueError('Missing/duplicate candidate annotation identity')
        seen.add(key)
        v, speed, vf = tracks[key]
        permanent = bool(audit['instance_max_speeds'][instance] <= .5
            or (instance in audit['bounded_stationary_instances'] and audit['instance_max_speeds'][instance] < 1.))
        ledger[i].append(dict(index=i, instance_token=instance, annotation_token=annotation_tokens[key],
            category=v['category'], clearance=r.longitudinal_clearance(v['forward'], v['length']),
            supported=support['supported'], on_surface=support['on_surface'],
            target_speed=speed, target_forward_speed=vf, heading_delta=v['heading_delta'],
            lateral_distance=v['lateral'], local_turn=r.local_heading_change_around_index(yaws, times, i),
            permanent_static=permanent))
    if seen != expected:
        raise ValueError('Candidate ledger incomplete; do not approximate missing map support')
    return ledger


def gate_candidates(audit, ledger, protected_context):
    eligible = {(c['index'], c['instance_token']) for frame in ledger for c in frame
                if should_reject(c, geometry.SEPARATED, protected_context)}
    if not eligible:
        return set(), []
    tracks = {instance: [{**v, 'crossing_exposure': (v['index'], instance) in eligible,
        'crossing_conflict': False, 'raw_crossing_conflict': False} for v in track]
        for instance, track in audit['vehicle_tracks'].items()
        if any((v['index'], instance) in eligible for v in track)}
    relations = geometry.audit_route_relations(audit['ego_positions'], audit['times'], audit['ego_yaws'], tracks)
    rejected = {(v['index'], v['instance_token']) for v in relations if v['relation'] == geometry.SEPARATED}
    return rejected, relations


def summarize(audit, ledger, context, rejected=()):
    times = audit['times']
    n = len(times)
    if not n or len(ledger) != n:
        raise ValueError('Invalid ledger timeline')
    following, stationary, stationary_ids, distances = [], [], [], []
    dangerous, events, selected, legacy_rejected = [False]*n, [], [], []
    front, close_count, following_count = [], 0, 0
    for i, candidates in enumerate(ledger):
        excluded = {instance for index, instance in rejected if index == i}
        c = select_nearest(candidates, excluded)
        selected.append(c)
        following.append(c is not None)
        stopped = bool(c is not None and c['target_speed'] < .5 and c['clearance'] < 40.)
        stationary.append(stopped)
        stationary_ids.append(c['instance_token'] if stopped else None)
        distances.append(c['clearance'] if stopped else float('inf'))
        if c is None or i == 0:
            continue
        following_count += 1
        front.append(c['clearance'])
        close_count += c['clearance'] < 15.
        relative = audit['ego_speeds'][i]-c['target_forward_speed']
        if audit['ego_speeds'][i] >= 2. and relative > 1. and c['clearance'] < 80.:
            event = dict(frame_index=i, scene_time=times[i], ttc=float(np.clip(c['clearance']/relative, 0, 30)),
                annotation_token=c['annotation_token'], instance_token=c['instance_token'], category=c['category'],
                clearance=c['clearance'], lateral_distance=c['lateral_distance'], target_speed=c['target_speed'],
                target_forward_speed=c['target_forward_speed'], relative_speed=relative, heading_delta=c['heading_delta'])
            if r.is_turning_projection_artifact(c['target_speed'], c['heading_delta'], c['local_turn']):
                legacy_rejected.append(event)
                stationary[i], stationary_ids[i], distances[i] = False, None, float('inf')
            else:
                events.append(event)
                dangerous[i] = event['ttc'] < 3.
    minimum = None
    for event in events:
        minimum = r.select_lower_ttc_event(minimum, event)
    split = r.split_stopped_lead_history(stationary_ids, audit['instance_max_speeds'],
                                        bounded_stationary_instances=audit['bounded_stationary_instances'])
    stopped, static, temporary, follow, danger = (r.summarize_events(flags, times)
        for flags in (stationary, split.static_flags, split.temporary_flags, following, dangerous))
    blocked_flags = r.filter_short_events(split.static_flags, times, minimum_duration=.8)
    blocked = r.summarize_events(blocked_flags, times)
    indices = [i for i, active in enumerate(split.static_flags) if active]
    blocked_indices = [i for i, active in enumerate(blocked_flags) if active]
    first = indices[0] if indices else -1
    first_block = blocked_indices[0] if blocked_indices else -1
    heading = audit['ego_yaws'][first] if first >= 0 else 0.
    bh = audit['ego_yaws'][first_block] if first_block >= 0 else 0.
    shift = r.lateral_shift_after_index(audit['ego_positions'], times, first, heading, horizon=10.)
    turn = r.net_heading_change_after_index(audit['ego_yaws'], times, first, heading, horizon=10.)
    minimum_static = min((distances[i] for i in indices), default=80.)
    evasive = r.is_evasive_lane_change(static.count, shift, turn,
        stationary_max_duration=static.max_duration, stationary_min_distance=minimum_static)
    bshift = r.lateral_shift_after_index(audit['ego_positions'], times, first_block, bh, horizon=10.)
    bturn = r.net_heading_change_after_index(audit['ego_yaws'], times, first_block, bh, horizon=10.)
    raw_deviation = r.is_obstacle_induced_route_deviation(blocked.max_duration,
        min((distances[i] for i in blocked_indices), default=80.), bshift, bturn)
    supported = r.is_route_deviation_context_supported(context.get('traffic_light_control_density', 0.),
        context.get('crossing_vehicle_exposure_ratio', 0.), context.get('intersection_stop_ratio', 0.),
        context.get('left_turn_cross_traffic_interaction_ratio', 0.))
    deviation = bool(raw_deviation and supported)
    fields = dict(car_following_ratio=following_count/n, following_event_count=follow.count,
        following_max_duration=follow.max_duration, close_following_ratio=float(close_count/n),
        front_vehicle_min_dist=min(front, default=80.), stopped_lead_ratio=stopped.ratio,
        stationary_lead_obstacle_ratio=static.ratio, temporarily_stopped_lead_ratio=temporary.ratio,
        blocked_path_obstacle_ratio=blocked.ratio, stationary_lead_event_count=static.count,
        stationary_lead_min_dist=minimum_static, ego_evasive_lateral_shift=shift,
        ego_evasive_net_heading_change=turn, ego_evasive_lane_change_flag=int(evasive),
        obstacle_induced_route_deviation_flag=int(deviation),
        route_deviation_decision_demand=r.route_deviation_decision_demand(blocked.ratio, deviation),
        min_ttc=min((v['ttc'] for v in events), default=30.),
        min_ttc_scene_time=minimum['scene_time'] if minimum else -1.,
        min_ttc_target_annotation_token=minimum['annotation_token'] if minimum else 'none',
        min_ttc_target_instance_token=minimum['instance_token'] if minimum else 'none',
        min_ttc_target_category=minimum['category'] if minimum else 'none',
        min_ttc_target_clearance=minimum['clearance'] if minimum else 80.,
        min_ttc_target_lateral_distance=minimum['lateral_distance'] if minimum else 0.,
        min_ttc_target_speed=minimum['target_speed'] if minimum else 0.,
        min_ttc_target_forward_speed=minimum['target_forward_speed'] if minimum else 0.,
        min_ttc_relative_speed=minimum['relative_speed'] if minimum else 0.,
        min_ttc_target_heading_delta=minimum['heading_delta'] if minimum else 0.,
        dangerous_ttc_ratio=float(np.mean([e['ttc'] < 3. for e in events])) if events else 0.,
        dangerous_ttc_frame_ratio=danger.ratio, dangerous_ttc_max_duration=danger.max_duration,
        ttc_valid_ratio=len(events)/n)
    trace = dict(selected=selected, events=events, legacy_postfiltered_events=legacy_rejected,
        following_flags=following, stationary_flags=stationary, stationary_ids=stationary_ids,
        static_flags=split.static_flags, temporary_flags=split.temporary_flags,
        blocked_flags=blocked_flags, dangerous_flags=dangerous,
        first_static_index=first, raw_deviation=bool(raw_deviation))
    return fields, trace
