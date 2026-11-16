"""Target-local obstruction evidence; does not decide risk or remove protection."""

import math


def target_history_evidence(audit, instance, index, *, horizon=1., ego_width=2.):
    """Bracket a candidate's one-second history; missing observations stay unknown.

    Check actual earlier body clearance and current geometry at both bracketing
    headings. This is a geometric diagnostic, not an inferred intended route.
    """
    times = audit['times']
    obstruction_episodes([None]*len(times), times)
    if not math.isfinite(horizon) or horizon <= 0 or not 0 <= index < len(times):
        raise ValueError('Invalid historical window')
    result = dict(complete=False, clearance=None, reference_indices=[])
    before = [i for i in range(index) if times[i] <= times[index]-horizon]
    if not before:
        return result
    left = before[-1]
    right = left if times[left] == times[index]-horizon else left+1
    references = sorted({left, right})
    track = audit['vehicle_tracks'].get(instance, [])
    rows = {v['index']: v for v in track}
    if len(rows) != len(track):
        raise ValueError('Duplicate target frame')
    if (any(i not in rows for i in range(left, index+1))
            or any(times[i+1]-times[i] > .75 for i in range(left, index))):
        return result
    current = rows[index]
    gaps = []
    for j in references:
        for k in (j, index):
            actor = rows[k]
            delta = [actor['position'][axis]-audit['ego_positions'][k][axis] for axis in (0, 1)]
            evidence = held_heading_clearance(delta, audit['ego_yaws'][j],
                actor['heading_delta']+audit['ego_yaws'][k], actor['width'], actor['length'], ego_width)
            if evidence['forward'] <= 0:
                return result
            gaps.append(evidence['lateral_body_clearance'])
    return dict(complete=True, clearance=min(gaps), reference_indices=references)


def held_heading_clearance(relative_xy, reference_yaw, actor_yaw,
                           actor_width, actor_length, ego_width):
    """Lateral body gap to a held-heading corridor, not a mapped lane boundary."""
    if len(relative_xy) != 2:
        raise ValueError('Expected planar relative position')
    values = [*relative_xy, reference_yaw, actor_yaw, actor_width, actor_length, ego_width]
    if not all(math.isfinite(v) for v in values) or min(actor_width, actor_length, ego_width) <= 0:
        raise ValueError('Invalid body geometry')
    dx, dy = relative_xy
    lateral = -dx * math.sin(reference_yaw) + dy * math.cos(reference_yaw)
    angle = actor_yaw - reference_yaw
    radius = (abs(math.sin(angle))*actor_length + abs(math.cos(angle))*actor_width)/2
    return dict(forward=dx*math.cos(reference_yaw)+dy*math.sin(reference_yaw),
                lateral=lateral, actor_lateral_radius=radius,
                lateral_body_clearance=abs(lateral)-radius-ego_width/2)


def can_release_raw_protection(*, raw_protected, strict_avoidance, supported_deviation,
                               target_sustained, history_complete, historical_clearance,
                               route_relation, eligible_static_opposite):
    """Experimental evidence conjunction; caller must supply target-local facts.

    Existing strict/supported response flags take precedence over route separation.
    A one-metre margin follows the existing route geometry convention.
    """
    flags = [raw_protected, strict_avoidance, supported_deviation, target_sustained,
             history_complete, eligible_static_opposite]
    if any(type(flag) is not bool for flag in flags):
        raise ValueError('Expected explicit evidence booleans')
    return bool(raw_protected and not strict_avoidance and not supported_deviation
                and not target_sustained and history_complete and eligible_static_opposite
                and route_relation == 'separated_observed_route'
                and historical_clearance is not None
                and math.isfinite(historical_clearance) and historical_clearance > 1.)


def obstruction_episodes(target_ids, timestamps, *, maximum_gap=.75):
    """Split selected static targets without joining identities or unseen time.

    A singleton is retained as evidence with zero observed span. That span is
    neither an absence label nor the legacy frame-tail-compensated duration.
    """
    if (isinstance(maximum_gap, bool) or not math.isfinite(maximum_gap)
            or maximum_gap <= 0):
        raise ValueError('Invalid maximum sampling gap')
    if len(target_ids) != len(timestamps):
        raise ValueError('Target/time length mismatch')
    times = [float(t) for t in timestamps]
    if (not all(math.isfinite(t) for t in times)
            or any(b <= a for a, b in zip(times, times[1:]))):
        raise ValueError('Expected finite strictly increasing timestamps')
    if any(t is not None and (not isinstance(t, str) or not t) for t in target_ids):
        raise ValueError('Expected instance token or None')
    episodes = []
    previous = None
    for index, target in enumerate(target_ids):
        if target is None:
            previous = None
            continue
        if (previous is None or previous['instance_token'] != target
                or times[index] - times[index - 1] > maximum_gap):
            previous = dict(instance_token=target, indices=[], start_time=times[index],
                            end_time=times[index], observed_duration=0.)
            episodes.append(previous)
        previous['indices'].append(index)
        previous['end_time'] = times[index]
        previous['observed_duration'] = times[index] - previous['start_time']
    return episodes
