"""Isolated v5.1 candidate; response protection is not a causal label."""

import math

import numpy as np
from shapely.geometry import Polygon

CANDIDATE_VERSION = 'crossing_candidate_v5_1_20261013'
HORIZON = 6.0
ALIGNMENT_TOLERANCE = .26
EGO_LENGTH = 4.5
EGO_WIDTH = 2.0
CLEARANCE_MARGIN = 1.0


def validate_candidate_selection(names, maximum, allowed):
    if (not 1 <= maximum <= 29 or not 0 < len(names) <= maximum
            or len(names) != len(set(names)) or set(names)-set(allowed)):
        raise ValueError('Candidate selection exceeds fixed development29 scope')


def _timeline(times, yaws):
    times, yaws = np.asarray(times, float), np.asarray(yaws, float)
    if (times.ndim != 1 or not len(times) or yaws.shape != times.shape
            or not np.isfinite(times).all() or not np.isfinite(yaws).all()
            or np.any(np.diff(times) <= 0)):
        raise ValueError('Invalid candidate timeline')
    return times, yaws


def _angle(a, b):
    return abs(math.atan2(math.sin(b-a), math.cos(b-a)))


def _box(position, yaw, width, length):
    c, s = math.cos(yaw), math.sin(yaw)
    return Polygon([(position[0]+c*x-s*y, position[1]+s*x+c*y)
                    for x, y in [(length/2, width/2), (length/2, -width/2),
                                 (-length/2, -width/2), (-length/2, width/2)]])


def _clearances(positions, yaws, rows):
    dimensions = np.asarray([[r.get('width'), r.get('length')] for r in rows], float)
    actor_xy = np.asarray([r['position'] for r in rows], float)
    heading = np.asarray([r.get('heading_delta') for r in rows], float)
    if (dimensions.shape != (len(rows), 2) or actor_xy.shape != (len(rows), 2)
            or not np.isfinite(dimensions).all() or np.any(dimensions <= 0)
            or not np.isfinite(actor_xy).all() or not np.isfinite(heading).all()):
        return None, None
    indices = [r['index'] for r in rows]
    ego_xy, ego_yaw = positions[indices], yaws[indices]
    actor_yaw = ego_yaw + heading
    distances = [float(_box(e, ey, EGO_WIDTH, EGO_LENGTH).distance(_box(a, ay, w, l)))
                 for e, ey, a, ay, (w, l) in zip(ego_xy, ego_yaw, actor_xy, actor_yaw, dimensions)]
    lower = min(distances)
    ego_radius = math.hypot(EGO_WIDTH, EGO_LENGTH)/2
    for j in range(1, len(rows)):
        # Hausdorff motion bound for linearly interpolated centers/sizes/shortest-angle yaws.
        motion = (np.linalg.norm(ego_xy[j]-ego_xy[j-1]) + np.linalg.norm(actor_xy[j]-actor_xy[j-1])
                  + ego_radius*_angle(ego_yaw[j-1], ego_yaw[j])
                  + max(np.linalg.norm(dimensions[j]), np.linalg.norm(dimensions[j-1]))/2
                    *_angle(actor_yaw[j-1], actor_yaw[j])
                  + np.linalg.norm(dimensions[j]-dimensions[j-1])/2)
        interval_lower = max(0., min(distances[j-1], distances[j],
                                    (distances[j-1]+distances[j]-float(motion))/2))
        lower = min(lower, interval_lower)
    return min(distances), float(lower)


def _future(times, index):
    return np.flatnonzero((times >= times[index])
                         & (times <= times[index]+HORIZON+ALIGNMENT_TOLERANCE)).tolist()


def _soft_response(times, speeds, index):
    if index == 0 or speeds[index] < 2:
        return False
    threshold = min(speeds[index]*.5, speeds[index]-2)
    start = previous = None
    for i in _future(times, index):
        if speeds[i] > threshold:
            start = previous = None
            continue
        if previous is None or times[i]-times[previous] > .75:
            start = i
        if times[i]-times[start] >= .8:
            return True
        previous = i
    return False


def _release_end(times, speeds, anchor):
    # Only an observed stop within the response window can bridge to its release.
    stopped = [i for i in _future(times, anchor) if i > 0 and speeds[i] < 1]
    if stopped:
        start = stopped[0]
        for i in range(start+1, len(times)):
            if times[i]-times[i-1] > .75:
                break
            if speeds[i] >= 2:
                return times[i]+HORIZON+ALIGNMENT_TOLERANCE
    return times[anchor]+HORIZON+ALIGNMENT_TOLERANCE


def crossing_candidate_audit(positions, times, yaws, speeds, vehicle_tracks, legacy_evidence):
    """Separate unresolved predictions from protected, observed and contradicted ones."""
    times, yaws = _timeline(times, yaws)
    positions, speeds = np.asarray(positions, float), np.asarray(speeds, float)
    if (positions.shape != (len(times), 2) or speeds.shape != times.shape
            or not np.isfinite(positions).all() or not np.isfinite(speeds).all()):
        raise ValueError('Invalid candidate ego geometry')
    result = []
    identities = set()
    for old in legacy_evidence:
        index, instance = old['index'], old['instance_token']
        if not isinstance(index, int) or not 0 <= index < len(times) or (index, instance) in identities:
            raise ValueError('Invalid or duplicate crossing identity')
        identities.add((index, instance))
        future = _future(times, index)
        rows = [r for r in vehicle_tracks[instance] if r['index'] in future]
        indices = [r['index'] for r in rows]
        if not rows or indices != sorted(set(indices)) or index not in indices:
            raise ValueError('Invalid crossing target timeline')
        complete = bool(times[future[-1]]-times[index] >= HORIZON
                        and indices == future and not np.any(np.diff(times[future]) > .75))
        minimum, lower = _clearances(positions, yaws, rows)
        soft_response = _soft_response(times, speeds, index)
        if old['yielding_response'] or soft_response:
            state = 'response_protected_prediction'
        elif minimum is None:
            state = 'unknown_geometry'
        elif minimum <= CLEARANCE_MARGIN:
            state = 'observed_proximity'
        elif not complete:
            state = 'unknown_future'
        elif old['heading_change'] > .35 and lower > CLEARANCE_MARGIN:
            state = ('contradicted_turning_projection' if old['rejected_turning_projection']
                     else 'contradicted_synchronized_turn')
        else:
            state = 'prediction_only'
        unresolved = not complete or minimum is None
        contradicted = state.startswith('contradicted_')
        result.append({'index': index, 'instance_token': instance,
            'time_s': float(times[index]-times[0]), 'state': state,
            'effective_conflict': state in {'response_protected_prediction', 'observed_proximity', 'prediction_only'},
            'unresolved': unresolved, 'contradicted': contradicted,
            'future_complete': complete, 'available_future_s': float(times[future[-1]]-times[index]),
            'geometry_known': minimum is not None,
            'synchronized_box_clearance_m': minimum, 'modeled_clearance_lower_m': lower,
            'yielding_response': bool(old['yielding_response']),
            'soft_deceleration_response': soft_response,
            'v4_projection_rejected': bool(old['rejected_turning_projection'])})
    return result


def local_left_interaction_flags(times, yaws, tracks, evidence, yield_flags, speeds=None):
    """Anchor local exposure to the same target, never whole-scene traffic exposure."""
    times, yaws = _timeline(times, yaws)
    if len(yield_flags) != len(times):
        raise ValueError('Invalid yield timeline')
    if speeds is not None:
        speeds = np.asarray(speeds, float)
        if speeds.shape != times.shape or not np.isfinite(speeds).all() or np.any(speeds < 0):
            raise ValueError('Invalid response speed timeline')
    anchors = {}
    for item in evidence:
        if item['effective_conflict']:
            anchors.setdefault(item['instance_token'], set()).add(item['index'])
    result = [False]*len(times)
    for instance, track in tracks.items():
        exposed = sorted(r['index'] for r in track if r['crossing_exposure'])
        response_anchors = {i for i in exposed if i > 0 and yield_flags[i]}
        if speeds is not None:
            response_anchors |= {i for i in exposed if _soft_response(times, speeds, i)}
        target_anchors = anchors.get(instance, set()) | response_anchors
        episodes, episode = [], []
        for i in exposed:
            if episode and times[i]-times[episode[-1]] > .75:
                episodes.append(episode)
                episode = []
            episode.append(i)
        if episode:
            episodes.append(episode)
        for episode in episodes:
            for anchor in target_anchors.intersection(episode):
                local = [i for i in episode if abs(times[i]-times[anchor]) <= HORIZON]
                end = times[anchor]+HORIZON+ALIGNMENT_TOLERANCE
                if speeds is not None and anchor in response_anchors:
                    end = _release_end(times, speeds, anchor)
                turn_window = np.flatnonzero((times >= times[anchor]-HORIZON-ALIGNMENT_TOLERANCE)
                                            & (times <= end))
                headings = np.unwrap(yaws[turn_window])
                if headings[-1]-headings[0] > .35:
                    for i in local:
                        result[i] = True
    return result
