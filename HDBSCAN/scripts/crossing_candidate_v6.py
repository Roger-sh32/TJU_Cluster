"""Observed-route relevance before response protection; replay-only v6 candidate."""

import math

import numpy as np
from shapely.ops import unary_union

from HDBSCAN.scripts import crossing_candidate_v5_2 as parent

CANDIDATE_VERSION = 'crossing_candidate_v6_replay_20261014'
SEPARATED = 'separated_observed_route'


def swept_envelope(positions, yaws, dimensions):
    """Contain piecewise-linear centers/sizes and shortest-angle rotating boxes."""
    positions, yaws, dimensions = (np.asarray(value, float)
                                  for value in (positions, yaws, dimensions))
    n = yaws.size
    if (not n or yaws.shape != (n,) or positions.shape != (n, 2) or dimensions.shape != (n, 2)
            or not all(np.isfinite(a).all() for a in (positions, yaws, dimensions))
            or np.any(dimensions <= 0)):
        raise ValueError('Invalid swept-body geometry')
    boxes = [parent._box(p, a, w, l) for p, a, (w, l)
             in zip(positions, yaws, dimensions)]
    shapes = list(boxes)
    for i in range(1, n):
        angle = parent._angle(yaws[i-1], yaws[i])
        radius = max(np.linalg.norm(dimensions[i-1]), np.linalg.norm(dimensions[i])) / 2
        # Linear interpolation error <= sup|corner second derivative|/8.
        error = radius * angle**2 / 8 + angle * np.linalg.norm(dimensions[i]-dimensions[i-1]) / 8
        hull = boxes[i-1].union(boxes[i]).convex_hull
        # GEOS round buffers are inscribed polygons: enlarge to contain the disk.
        padding = max(error, 1e-9 * (1 + np.max(np.abs(positions[i-1:i+1]))
                                    + np.max(dimensions[i-1:i+1])))
        expanded = hull.buffer(padding / math.cos(math.pi/64), resolution=16)
        # Tiny GEOS buffers can be empty; never drop the connecting hull.
        shapes.append(hull.union(expanded))
    return unary_union(shapes)


def audit_route_relations(positions, times, yaws, tracks):
    """Audit exposure anchors, not lane identity or video-external intended routes."""
    times, yaws = parent._timeline(times, yaws)
    positions = np.asarray(positions, float)
    if positions.shape != (len(times), 2) or not np.isfinite(positions).all():
        raise ValueError('Invalid route positions')
    result = []
    for instance, track in tracks.items():
        indices = [r['index'] for r in track]
        if (any(type(i) is not int or not 0 <= i < len(times) for i in indices)
                or indices != sorted(set(indices))):
            raise ValueError('Invalid target timeline')
        for row in track:
            if not (row.get('crossing_exposure') or row.get('raw_crossing_conflict')
                    or row.get('crossing_conflict')):
                continue
            k = row['index']
            future = parent._geometry_future(times, k)
            rows = [r for r in track if r['index'] in future]
            complete = (times[future[-1]]-times[k] >= parent.HORIZON
                        and [r['index'] for r in rows] == future
                        and not np.any(np.diff(times[k:]) > .75))
            item = dict(index=k, instance_token=instance, relation='unknown',
                        future_complete=bool(complete), spatial_clearance_lower_m=None,
                        passage_observed=False)
            if not complete:
                result.append(item)
                continue
            try:
                actor = swept_envelope([r['position'] for r in rows],
                    [yaws[r['index']] + r.get('heading_delta', float('nan')) for r in rows],
                    [[r.get('width'), r.get('length')] for r in rows])
                route = swept_envelope(positions[k:], yaws[k:],
                                      [[parent.EGO_WIDTH, parent.EGO_LENGTH]]*(len(times)-k))
            except (TypeError, ValueError):
                result.append(item)
                continue
            lower = float(actor.distance(route))
            item['spatial_clearance_lower_m'] = lower
            if lower <= parent.CLEARANCE_MARGIN:
                # Envelope overlap is only potential relevance, never actual conflict.
                item['relation'] = 'potential_route_overlap'
            else:
                sampled = [parent._box(p, yaw, parent.EGO_WIDTH, parent.EGO_LENGTH).distance(actor)
                           for p, yaw in zip(positions[k:], yaws[k:])]
                nearest = int(np.argmin(sampled)) + k
                travel = float(np.linalg.norm(np.diff(positions[nearest:], axis=0), axis=1).sum())
                passage = (travel >= parent.EGO_LENGTH
                           and sampled[-1]-min(sampled) >= parent.EGO_LENGTH)
                item['passage_observed'] = bool(passage)
                if passage:
                    item['relation'] = SEPARATED
            result.append(item)
    return result


def crossing_candidate_audit(positions, times, yaws, speeds, tracks, legacy_evidence):
    evidence = parent.crossing_candidate_audit(positions, times, yaws, speeds, tracks, legacy_evidence)
    routes = {(r['index'], r['instance_token']): r
              for r in audit_route_relations(positions, times, yaws, tracks)}
    for item in evidence:
        route = routes.get((item['index'], item['instance_token']))
        if route is None:
            raise ValueError('Crossing anchor missing route audit')
        item['parent_state'] = item['state']
        item['route_relation'] = route['relation']
        item['route_clearance_lower_m'] = route['spatial_clearance_lower_m']
        item['route_unresolved'] = route['relation'] == 'unknown'
        item['unresolved'] |= item['route_unresolved']
        if (route['relation'] == SEPARATED and item['future_complete']
                and item['observed_horizon_box_clearance_m'] is not None
                and item['observed_horizon_box_clearance_m'] > parent.CLEARANCE_MARGIN):
            item.update(state='contradicted_observed_route', effective_conflict=False, contradicted=True)
    return evidence


def local_left_interaction_flags(times, yaws, tracks, evidence, yield_flags, speeds,
                                 *, route_evidence):
    """Apply the same gate to raw response anchors; never re-add rejected targets."""
    routes = {(r['index'], r['instance_token']): r['relation'] for r in route_evidence}
    if len(routes) != len(route_evidence):
        raise ValueError('Duplicate route identity')
    filtered = {}
    for instance, track in tracks.items():
        filtered[instance] = []
        for row in track:
            exposed = bool(row.get('crossing_exposure'))
            if exposed:
                key = (row['index'], instance)
                if key not in routes:
                    raise ValueError('Exposure anchor missing route audit')
                exposed &= routes[key] != SEPARATED
            filtered[instance].append({**row, 'crossing_exposure': exposed})
    filtered_evidence = [{**r, 'effective_conflict': r['effective_conflict']
        and routes.get((r['index'], r['instance_token'])) != SEPARATED} for r in evidence]
    return parent.local_left_interaction_flags(times, yaws, filtered, filtered_evidence, yield_flags, speeds)
