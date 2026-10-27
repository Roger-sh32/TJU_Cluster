"""Grouped, physically anchored corner-case scoring."""

import numpy as np
import pandas as pd


# The frozen pipeline requires the current full scoring contract. Legacy helper
# defaults remain available only for historical analyses and small rule tests.
FROZEN_RISK_INPUTS = (
    'adjacent_lane_intrusion_max_duration', 'adjacent_lane_intrusion_ratio',
    'close_following_ratio', 'crossing_conflict_max_duration',
    'crossing_route_conflict_max_duration', 'crossing_route_conflict_ratio',
    'crossing_vehicle_conflict_ratio', 'crossing_vehicle_exposure_ratio',
    'dangerous_ttc_frame_ratio', 'dangerous_ttc_max_duration', 'ego_decel_min',
    'ego_hard_brake_ratio', 'ego_stop_from_motion_flag', 'ego_stopped_at_scene_start',
    'intersection_stop_ratio', 'left_turn_cross_traffic_interaction_ratio',
    'merge_conflict_ratio', 'merge_max_duration', 'merge_observed_relevance_ratio',
    'min_ttc', 'non_signalized_intersection_density', 'route_deviation_decision_demand',
    'side_entry_candidate_ratio', 'stop_sign_stop_candidate', 'traffic_light_control_density',
    'ttc_valid_ratio', 'vru_conflict_max_duration', 'vru_crossing_exposure_ratio',
    'vru_observed_max_duration', 'vru_observed_relevance_ratio', 'vru_path_conflict_ratio',
    'vru_sustained_max_duration', 'vru_sustained_relevance_ratio',
)


def _column(df, name, default=0.0):
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce").fillna(default).to_numpy(dtype=float)
    return np.full(len(df), default, dtype=float)


def _scaled(values, full_scale):
    return np.clip(np.asarray(values, dtype=float) / full_scale, 0.0, 1.0)


def calculate_grouped_risk(df):
    """Return interpretable sub-scores and a fixed-scale total risk in [0, 1]."""
    result = pd.DataFrame(index=df.index)

    min_ttc = _column(df, "min_ttc", 30.0)
    ttc_valid_evidence = _scaled(_column(df, "ttc_valid_ratio"), 0.15)
    ttc_severity = np.clip((3.0 - min_ttc) / 2.5, 0.0, 1.0)
    dangerous_persistence = np.maximum(
        _scaled(_column(df, "dangerous_ttc_frame_ratio"), 0.15),
        _scaled(_column(df, "dangerous_ttc_max_duration"), 2.0),
    )
    close_following = _scaled(_column(df, "close_following_ratio"), 0.25)
    signalized_initial_queue = (
        _scaled(_column(df, "traffic_light_control_density"), 0.50)
        * np.clip(_column(df, "ego_stopped_at_scene_start"), 0.0, 1.0)
    )
    close_following = close_following * (1.0 - 0.90 * signalized_initial_queue)
    result["longitudinal_risk"] = np.clip(
        0.50 * ttc_severity * ttc_valid_evidence
        + 0.35 * dangerous_persistence
        + 0.15 * close_following,
        0.0,
        1.0,
    )

    merge_risk = np.maximum(
        _scaled(_column(df, "merge_conflict_ratio"), 0.25),
        _scaled(_column(df, "merge_max_duration"), 2.0),
    )
    if "merge_observed_relevance_ratio" in df.columns:
        merge_risk = merge_risk * _scaled(
            _column(df, "merge_observed_relevance_ratio"),
            0.10,
        )
    merge_risk = merge_risk * (
        1.0
        - _scaled(
            _column(df, "left_turn_cross_traffic_interaction_ratio"),
            0.10,
        )
    )
    route_evidence_available = 'crossing_route_conflict_ratio' in df.columns
    # Successful yielding can remove realized proximity. Missing future-route
    # conflict is not enough to erase a preceding predicted conflict.
    crossing_ratio = np.maximum(_column(df, 'crossing_vehicle_conflict_ratio'),
                                _column(df, 'crossing_route_conflict_ratio'))
    crossing_duration = np.maximum(_column(df, 'crossing_conflict_max_duration'),
                                   _column(df, 'crossing_route_conflict_max_duration'))
    crossing_risk = np.maximum(_scaled(crossing_ratio, 0.20), _scaled(crossing_duration, 2.0))
    yielding_factor = 1.0 - 0.80 * _scaled(
        _column(df, "intersection_stop_ratio"),
        0.30,
    )
    crossing_risk = crossing_risk * yielding_factor
    intrusion_risk = np.minimum(
        _scaled(_column(df, 'adjacent_lane_intrusion_ratio'), 0.20),
        _scaled(_column(df, 'adjacent_lane_intrusion_max_duration'), 2.0),
    )
    result["interaction_risk"] = np.maximum.reduce([merge_risk, crossing_risk, intrusion_risk])

    if "vru_sustained_relevance_ratio" in df.columns:
        vru_relevance = _column(df, "vru_sustained_relevance_ratio")
        vru_duration = _column(df, "vru_sustained_max_duration")
    elif "vru_observed_relevance_ratio" in df.columns:
        vru_relevance = _column(df, "vru_observed_relevance_ratio")
        vru_duration = _column(df, "vru_observed_max_duration")
    else:
        vru_relevance = _column(df, "vru_path_conflict_ratio")
        vru_duration = _column(df, "vru_conflict_max_duration")
    result["vru_risk"] = np.maximum(
        _scaled(vru_relevance, 0.20),
        _scaled(vru_duration, 2.0),
    ) * yielding_factor

    brake_response = _scaled(_column(df, "ego_hard_brake_ratio"), 0.10)
    decel_response = np.clip((-_column(df, "ego_decel_min") - 3.0) / 3.0, 0.0, 1.0)
    result["ego_response_risk"] = 0.60 * brake_response + 0.40 * decel_response

    result["observed_risk"] = np.clip(
        0.35 * result["longitudinal_risk"]
        + 0.30 * result["interaction_risk"]
        + 0.25 * result["vru_risk"]
        + 0.10 * result["ego_response_risk"],
        0.0,
        1.0,
    )
    non_signalized = _scaled(
        _column(df, "non_signalized_intersection_density"),
        0.30,
    )
    flow_exposure = np.maximum(
        _scaled(_column(df, "crossing_vehicle_exposure_ratio"), 0.40),
        _scaled(_column(df, "vru_crossing_exposure_ratio"), 0.40),
    )
    approach_factor = 0.40 + 0.60 * (
        1.0 - np.clip(_column(df, "ego_stopped_at_scene_start"), 0.0, 1.0)
    )
    approach_factor = np.maximum(
        approach_factor,
        np.clip(_column(df, "ego_stop_from_motion_flag"), 0.0, 1.0),
    )
    signal_suppression = 1.0 - 0.80 * _scaled(
        _column(df, "traffic_light_control_density"),
        0.30,
    )
    intersection_decision_demand = np.clip(
        non_signalized * flow_exposure * approach_factor * signal_suppression,
        0.0,
        1.0,
    )
    # A mapped stop-sign stop has a regulatory explanation. Retain gap-selection
    # demand, and restore full demand when route-relevant traffic is observed.
    if route_evidence_available:
        stop_control = np.clip(_column(df, 'stop_sign_stop_candidate'), 0.0, 1.0)
        relevant_flow = np.maximum.reduce([
            _scaled(_column(df, 'crossing_route_conflict_ratio'), 0.10),
            _scaled(_column(df, 'left_turn_cross_traffic_interaction_ratio'), 0.10),
            _scaled(vru_relevance, 0.10),
        ])
        intersection_decision_demand *= 1.0 - 0.60 * stop_control * (1.0 - relevant_flow)
    result["decision_demand"] = np.maximum.reduce([
        intersection_decision_demand,
        np.clip(_column(df, "route_deviation_decision_demand"), 0.0, 1.0),
        0.30 * _scaled(_column(df, 'side_entry_candidate_ratio'), 0.20),
    ])
    result["risk"] = np.clip(
        result["observed_risk"] + 0.20 * result["decision_demand"],
        0.0,
        1.0,
    )
    return result


def calculate_corner_scores(df):
    """Combine cluster rarity, HDBSCAN outlier score, and grouped risk."""
    output = df.copy()
    grouped = calculate_grouped_risk(output)
    for column in grouped.columns:
        output[column] = grouped[column]

    cluster_sizes = output.loc[output["cluster"] >= 0, "cluster"].value_counts()
    total = max(len(output), 1)

    def rarity_for(cluster):
        if cluster < 0:
            return 1.0 - 1.0 / total
        return 1.0 - cluster_sizes.get(cluster, 0) / total

    output["rarity"] = output["cluster"].map(rarity_for)
    output["atypical_norm"] = np.clip(
        _column(output, "cluster_outlier_score"),
        0.0,
        1.0,
    )
    output["corner_score"] = (
        0.20 * output["rarity"]
        + 0.25 * output["atypical_norm"]
        + 0.55 * output["risk"]
    )
    score_min = output["corner_score"].min()
    score_range = output["corner_score"].max() - score_min
    if score_range < 1e-9:
        output["corner_score_norm"] = 0.0
    else:
        output["corner_score_norm"] = (output["corner_score"] - score_min) / score_range
    return output


def fit_score_reference(development_clusters):
    """Capture development-only denominators; callers must validate membership."""
    if development_clusters.empty:
        raise ValueError('Empty scoring reference')
    scored = calculate_corner_scores(development_clusters)
    return {
        'total': len(scored),
        'cluster_sizes': {str(int(k)): int(v) for k, v in
                          scored.loc[scored.cluster >= 0, 'cluster'].value_counts().items()},
        'score_min': float(scored.corner_score.min()),
        'score_max': float(scored.corner_score.max()),
    }


def calculate_frozen_corner_scores(df, reference):
    """Score without estimating rarity or normalization from the query batch."""
    output = df.copy()
    grouped = calculate_grouped_risk(output)
    for column in grouped:
        output[column] = grouped[column]
    total = reference['total']
    if total <= 0:
        raise ValueError('Invalid scoring reference size')
    def rarity(cluster):
        if cluster == -1:
            return 1.0 - 1.0 / total
        key = str(int(cluster))
        if cluster != int(cluster) or key not in reference['cluster_sizes']:
            raise ValueError('Unknown cluster in frozen scoring')
        return 1.0 - reference['cluster_sizes'][key] / total
    output['rarity'] = output.cluster.map(rarity)
    output['atypical_norm'] = pd.to_numeric(output.cluster_outlier_score, errors='raise')
    output['corner_score'] = .20 * output.rarity + .25 * output.atypical_norm + .55 * output.risk
    spread = reference['score_max'] - reference['score_min']
    output['corner_score_norm'] = (0.0 if spread < 1e-9 else
                                   ((output.corner_score - reference['score_min']) / spread).clip(0, 1))
    return output
