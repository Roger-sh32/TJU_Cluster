"""Grouped, physically anchored corner-case scoring."""

import numpy as np
import pandas as pd


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
    crossing_risk = np.maximum(
        _scaled(_column(df, "crossing_vehicle_conflict_ratio"), 0.20),
        _scaled(_column(df, "crossing_conflict_max_duration"), 2.0),
    )
    yielding_factor = 1.0 - 0.80 * _scaled(
        _column(df, "intersection_stop_ratio"),
        0.30,
    )
    crossing_risk = crossing_risk * yielding_factor
    result["interaction_risk"] = np.maximum(merge_risk, crossing_risk)

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
    result["decision_demand"] = np.maximum(
        intersection_decision_demand,
        np.clip(_column(df, "route_deviation_decision_demand"), 0.0, 1.0),
    )
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
