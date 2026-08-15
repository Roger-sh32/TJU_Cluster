"""Feature groups used to cluster scenario semantics rather than outcomes."""


CLUSTERING_FEATURES = [
    "avg_speed",
    "speed_std",
    "avg_vehicle_count",
    "neighbor_density_std",
    "neighbor_speed_std",
    "pedestrian_nearby_ratio",
    "pedestrian_front_ratio",
    "ego_avg_speed",
    "ego_speed_std",
    "ego_heading_change_total",
    "ego_stopped_at_scene_start",
    "ego_stop_from_motion_flag",
    "ego_restart_after_stop_flag",
    "car_following_ratio",
    "following_max_duration",
    "merge_exposure_ratio",
    "merge_observed_relevance_ratio",
    "merge_lane_entry_relevance_ratio",
    "overtaking_exposure_ratio",
    "crossing_vehicle_exposure_ratio",
    "left_turn_crossing_yield_ratio",
    "left_turn_cross_traffic_interaction_ratio",
    "vru_crossing_exposure_ratio",
    "same_lane_vru_exposure_ratio",
    "same_direction_vru_ratio",
    "vru_path_conflict_ratio",
    "vru_observed_relevance_ratio",
    "vru_crosswalk_conflict_ratio",
    "obstacle_avoidance_vru_conflict_ratio",
    "oncoming_during_avoidance_ratio",
    "stationary_lead_obstacle_ratio",
    "temporarily_stopped_lead_ratio",
    "blocked_path_obstacle_ratio",
    "obstacle_induced_route_deviation_flag",
    "route_deviation_decision_demand",
    "ego_evasive_lane_change_flag",
    "truck_bus_dynamic_ratio",
    "bicycle_ratio",
    "motorcycle_ratio",
    "two_wheeler_dynamic_ratio",
    "intersection_density",
    "lane_connector_density",
    "ped_crossing_density",
    "intersection_stop_ratio",
    "traffic_light_control_density",
    "stop_sign_control_density",
    "turn_stop_control_density",
    "non_signalized_intersection_density",
]


def select_clustering_features(df):
    """Return available semantic features in a stable, explicit order."""
    available = [column for column in CLUSTERING_FEATURES if column in df.columns]
    if not available:
        raise ValueError("No supported clustering features are present in the input table.")
    return df[available].copy()
