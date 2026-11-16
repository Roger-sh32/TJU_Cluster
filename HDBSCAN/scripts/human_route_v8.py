"""Human body/observed route evidence; no physical-barrier inference."""
import math
import numpy as np
from HDBSCAN.scripts.crossing_candidate_v6 import swept_envelope
from HDBSCAN.scripts import crossing_candidate_v5_2 as geometry


def route_evidence(ego, human_track, index, horizon=8.):
    times, yaws = geometry._timeline(ego['times'], ego['ego_yaws'])
    positions = np.asarray(ego['ego_positions'], float)
    if positions.shape != (len(times), 2) or not np.isfinite(positions).all():
        raise ValueError('Invalid ego geometry')
    if type(index) is not int or not 0 <= index < len(times) or not math.isfinite(horizon) or horizon <= 0:
        raise ValueError('Invalid anchor/horizon')
    result = dict(relation='unknown', complete=False, clearance_lower_m=None, passage_observed=False)
    ends = np.flatnonzero(times >= times[index]+horizon)
    if not len(ends):
        return result
    end = int(ends[0])
    rows = {r['index']: r for r in human_track}
    if len(rows) != len(human_track):
        raise ValueError('Duplicate human annotation index')
    indices = list(range(index, end+1))
    if any(i not in rows for i in indices) or np.any(np.diff(times[index:]) > .75):
        return result
    actor_yaws = []
    for i in indices:
        q = np.asarray(rows[i]['rotation'], float)
        if q.shape != (4,) or not np.isfinite(q).all() or np.linalg.norm(q) == 0:
            raise ValueError('Invalid actor rotation')
        w, x, y, z = q/np.linalg.norm(q)
        actor_yaws.append(math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z)))
    actor = swept_envelope([rows[i]['translation'][:2] for i in indices], actor_yaws,
                           [rows[i]['size'][:2] for i in indices])
    route = swept_envelope(positions[index:], yaws[index:],
                           [[geometry.EGO_WIDTH, geometry.EGO_LENGTH]]*(len(times)-index))
    clearance = float(actor.distance(route))
    result.update(complete=True, clearance_lower_m=clearance, last_target_index=end)
    if clearance <= geometry.CLEARANCE_MARGIN:
        result['relation'] = 'potential_route_overlap'
        return result
    distances = [float(geometry._box(p, a, geometry.EGO_WIDTH, geometry.EGO_LENGTH).distance(actor))
                 for p, a in zip(positions[index:], yaws[index:])]
    nearest = int(np.argmin(distances))+index
    travel = float(np.linalg.norm(np.diff(positions[nearest:], axis=0), axis=1).sum())
    passage = travel >= geometry.EGO_LENGTH and distances[-1]-min(distances) >= geometry.EGO_LENGTH
    result['passage_observed'] = bool(passage)
    if passage:
        result['relation'] = 'separated_observed_route'
    return result
