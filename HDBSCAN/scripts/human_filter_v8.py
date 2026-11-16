"""Experimental target-level human prediction suppression with response guards."""
import numpy as np
from HDBSCAN.scripts import scene_feature_rules as rules
from HDBSCAN.scripts import crossing_candidate_v5_2 as response


def response_protected(audit, index, evasive):
    times, _ = response._timeline(audit['times'], [0.]*len(audit['times']))
    speeds = np.asarray(audit['ego_speeds'], float)
    if speeds.shape != times.shape or not np.isfinite(speeds).all() or np.any(speeds < 0):
        raise ValueError('Invalid speed observations')
    if type(index) is not int or not 0 <= index < len(times):
        raise ValueError('Invalid anchor')
    # Preserve missing history and whole-scene avoidance conservatively.
    before = np.flatnonzero(times <= times[index]-2.)
    after = np.flatnonzero(times >= times[index]+8.)
    if evasive or not len(before) or not len(after):
        return True
    start, end = int(before[-1]), int(after[0])
    if start == 0 or np.any(np.diff(times[start:end+1]) > .75):
        return True
    if np.any(speeds[start:end+1] < 1.):
        return True
    return any(response._soft_response(times, speeds, i) for i in range(start, index+1))


def should_suppress(observed_positive, relation, protected):
    if type(observed_positive) is not bool or type(protected) is not bool:
        raise ValueError('Expected explicit evidence flags')
    return not observed_positive and not protected and relation == 'separated_observed_route'


def aggregate(anchors, times, original_crosswalk_flags, suppressed):
    if not times or len(original_crosswalk_flags) != len(times):
        raise ValueError('Invalid aggregate timeline')
    retained = [c for c in anchors if (c['index'], c['instance_token']) not in suppressed]
    path = [False]*len(times)
    for c in retained:
        path[c['index']] = True
    crosswalk = [p and original for p, original in zip(path, original_crosswalk_flags)]
    p, c = rules.summarize_events(path, times), rules.summarize_events(crosswalk, times)
    finite = [a for a in retained if a['closest_distance_m'] is not None and np.isfinite(a['closest_distance_m'])]
    closest = min(finite, key=lambda a: a['closest_distance_m']) if finite else None
    return dict(pedestrian_crossing_risk_ratio=p.ratio, vru_path_conflict_ratio=p.ratio,
                vru_conflict_event_count=p.count, vru_conflict_max_duration=p.max_duration,
                vru_crosswalk_conflict_ratio=c.ratio, vru_crosswalk_conflict_event_count=c.count,
                vru_observed_min_distance=closest['closest_distance_m'] if closest else 30.,
                vru_observed_min_distance_time=closest['time_s']+closest['closest_relative_time_s'] if closest else -1.)
