'''提取 nuScenes 场景特征的脚本'''
import os
import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from pyquaternion import Quaternion
from nuscenes import NuScenes
from tqdm import tqdm
from nuscenes.map_expansion.map_api import NuScenesMap
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from extraction_audit import ExtractionAudit
from experiment_partition import (
    load_partition, select_development_scenes, assert_new_outputs, provenance_path,
    preflight, write_run_manifest, file_record,
)

from scene_feature_rules import (
    classify_stop_line_controls,
    classify_mapped_vru_lane_relation,
    classify_vehicle_interaction,
    classify_vru_lane_relation,
    events_within_context,
    filter_short_events,
    is_vru_crossing_exposure,
    is_evasive_lane_change,
    is_heading_aligned,
    is_obstacle_induced_route_deviation,
    is_observed_merge_relevant,
    is_observed_vru_relevant,
    is_oncoming_vehicle,
    is_overtaking_exposure,
    is_turning_projection_artifact,
    is_route_deviation_context_supported,
    is_vru_path_conflict,
    lateral_shift_after_index,
    left_turn_cross_traffic_flags,
    local_heading_change_around_index,
    longitudinal_clearance,
    net_heading_change_after_index,
    partition_events_at_time,
    select_lower_ttc_event,
    route_deviation_decision_demand,
    signed_net_heading_change,
    split_stopped_lead_history,
    summarize_motion_decision,
    summarize_events,
    synchronized_path_min_distance,
    synchronized_path_closest_approach,
    wrapped_heading_change,
    is_lane_supported_target,
    is_adjacent_lane_intrusion,
    distance_to_polyline,
    is_side_entry_candidate,
    is_bounded_stationary_track,
)

SCRIPT_DIR = Path(__file__).resolve().parent
HDBSCAN_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = HDBSCAN_ROOT.parent
TABLES_DIR = HDBSCAN_ROOT / "tables"
TABLES_DIR.mkdir(exist_ok=True)

MAX_SCENES = int(os.getenv("SCENE_CLUSTER_MAX_SCENES", "700"))
SCENE_START_INDEX = int(os.getenv("SCENE_CLUSTER_START_INDEX", "0"))
FEATURE_OUTPUT_NAME = os.getenv("SCENE_CLUSTER_FEATURE_OUTPUT", "scene_features_development.csv")
FRONT_MAX_DIST = 80.0
FRONT_LATERAL_LIMIT = 4.0
EGO_TTC_MIN_SPEED = 2.0
CLOSE_FRONT_DIST = 15.0
NEAR_OBJECT_RADIUS = 50.0
DYNAMIC_SPEED_THRESHOLD = 1.0
INTERSECTION_SCENE_DENSITY_THRESHOLD = 0.3
VRU_FRONT_MIN_DIST = -5.0
VRU_FRONT_MAX_DIST = 30.0
VRU_LATERAL_LIMIT = 8.0

# =========================
# 加载 nuScenes
# =========================
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--preflight', action='store_true', help='Validate selection without loading NuScenes or extracting features.')
args = parser.parse_args()
partition = load_partition()
metadata_path = PROJECT_ROOT / 'nuScenes/v1.0-trainval/scene.json'
metadata_scenes = json.loads(metadata_path.read_text(encoding='utf-8'))
selected_scene_records = select_development_scenes(
    metadata_scenes, partition, os.getenv('SCENE_CLUSTER_SCENE_NAMES', ''),
    SCENE_START_INDEX, MAX_SCENES,
)
selection_frame = pd.DataFrame([{'scene_name': scene['name'], 'scene_token': scene['token']}
                                for scene in selected_scene_records])
output_path = TABLES_DIR / FEATURE_OUTPUT_NAME
quality_path = Path(str(output_path) + '.quality.json')
planned_outputs = [output_path, provenance_path(output_path), quality_path]
if os.getenv('SCENE_CLUSTER_AUDIT_OUTPUT'):
    planned_outputs.append(TABLES_DIR / os.environ['SCENE_CLUSTER_AUDIT_OUTPUT'])
resolved_outputs = [os.path.normcase(str(path.resolve())) for path in planned_outputs]
if len(set(resolved_outputs)) != len(resolved_outputs):
    raise ValueError('Colliding extraction output paths')
assert_new_outputs(planned_outputs)
if args.preflight:
    preflight('feature_extraction', selection_frame, partition)
    raise SystemExit(0)
nusc = NuScenes(version='v1.0-trainval', dataroot=str(PROJECT_ROOT / 'nuScenes'), verbose=True)
extraction_audit = ExtractionAudit()


# =========================
# 工具函数
# =========================
def quaternion_yaw(q):
    return Quaternion(q).yaw_pitch_roll[0]


def compute_ann_velocity_xy(nusc, ann, default_dt=0.5):
    """Estimate object planar velocity from adjacent annotations."""
    cur_sample = nusc.get('sample', ann['sample_token'])
    t_cur = cur_sample['timestamp']

    if ann['next'] != "":
        ann_next = nusc.get('sample_annotation', ann['next'])
        nxt_sample = nusc.get('sample', ann_next['sample_token'])
        dt = (nxt_sample['timestamp'] - t_cur) / 1e6
        if dt <= 0:
            dt = default_dt
        return (
            (ann_next['translation'][0] - ann['translation'][0]) / max(dt, 1e-3),
            (ann_next['translation'][1] - ann['translation'][1]) / max(dt, 1e-3),
        )

    if ann['prev'] != "":
        ann_prev = nusc.get('sample_annotation', ann['prev'])
        prv_sample = nusc.get('sample', ann_prev['sample_token'])
        dt = (t_cur - prv_sample['timestamp']) / 1e6
        if dt <= 0:
            dt = default_dt
        return (
            (ann['translation'][0] - ann_prev['translation'][0]) / max(dt, 1e-3),
            (ann['translation'][1] - ann_prev['translation'][1]) / max(dt, 1e-3),
        )

    return 0.0, 0.0


def ego_frame_delta(obj_xy, ego_x, ego_y, ego_yaw):
    """Return object position in ego frame: forward and lateral distance."""
    dx = obj_xy[0] - ego_x
    dy = obj_xy[1] - ego_y
    forward = dx * np.cos(ego_yaw) + dy * np.sin(ego_yaw)
    lateral = -dx * np.sin(ego_yaw) + dy * np.cos(ego_yaw)
    return forward, lateral


def ego_frame_vector(vec_xy, ego_yaw):
    """Project a world-frame vector into ego forward/lateral components."""
    vx, vy = vec_xy
    forward = vx * np.cos(ego_yaw) + vy * np.sin(ego_yaw)
    lateral = -vx * np.sin(ego_yaw) + vy * np.cos(ego_yaw)
    return forward, lateral


def map_intersection_state(nusc_map, x, y, core_radius=5, connector_radius=8):
    """Separate true intersections from broader lane-connector topology."""
    core_records = nusc_map.get_records_in_radius(
        x,
        y,
        core_radius,
        ["road_segment"],
    )

    is_core_intersection = False
    for token in core_records.get("road_segment", []):
        road_segment = nusc_map.get("road_segment", token)
        if road_segment.get("is_intersection", False):
            is_core_intersection = True
            break

    connector_records = nusc_map.get_records_in_radius(
        x,
        y,
        connector_radius,
        ["lane_connector"],
    )
    has_lane_connector = len(connector_records.get("lane_connector", [])) > 0

    return is_core_intersection, has_lane_connector


def mapped_actor_lane_geometry(nusc_map, ego_x, ego_y, obj_xy, lane_cache):
    """Return actor distance and lane heading relative to ego's current lane."""
    lane_token = nusc_map.get_closest_lane(ego_x, ego_y, radius=4)
    if not lane_token:
        return None
    if lane_token not in lane_cache:
        lane_cache[lane_token] = nusc_map.discretize_lanes([lane_token], 1.0)[lane_token]
    poses = lane_cache[lane_token]
    if not poses:
        return None

    pose = min(poses, key=lambda item: (item[0] - obj_xy[0]) ** 2 + (item[1] - obj_xy[1]) ** 2)
    lane_distance = float(np.hypot(obj_xy[0] - pose[0], obj_xy[1] - pose[1]))
    return lane_distance, pose[2]


def mapped_vru_lane_relation(nusc_map, ego_x, ego_y, obj_xy, obj_velocity, lane_cache):
    """Return a strict VRU lane relation using the ego lane centerline and walkway layer."""
    geometry = mapped_actor_lane_geometry(nusc_map, ego_x, ego_y, obj_xy, lane_cache)
    if geometry is None:
        return None
    lane_distance, lane_heading = geometry
    lane_forward_speed = obj_velocity[0] * np.cos(lane_heading) + obj_velocity[1] * np.sin(lane_heading)
    layers = nusc_map.layers_on_point(obj_xy[0], obj_xy[1], ['walkway'])
    on_walkway = bool(layers.get('walkway'))
    return classify_mapped_vru_lane_relation(
        on_walkway,
        lane_distance,
        lane_forward_speed,
    )


def longitudinal_map_distance(nusc_map, ego_x, ego_y, obj_xy, lane_cache):
    lane = nusc_map.get_closest_lane(ego_x, ego_y, radius=4)
    if not lane:
        return None
    if lane not in lane_cache:
        lane_cache[lane] = nusc_map.discretize_lanes([lane], 1.0)[lane]
    poses = lane_cache[lane]
    if len(poses) < 3:
        return None
    index = min(range(len(poses)), key=lambda i: np.hypot(poses[i][0]-obj_xy[0], poses[i][1]-obj_xy[1]))
    # Endpoint distance includes along-road distance to the next segment.
    if index in (0, len(poses) - 1):
        return None
    return float(np.hypot(poses[index][0]-obj_xy[0], poses[index][1]-obj_xy[1]))


scene_features = []
scene_audits = []
map_cache = {}

# =========================
# 主循环：遍历前 X 个 scene
# =========================
scene_batch = selected_scene_records
for scene_idx, scene in enumerate(tqdm(scene_batch, desc="Processing scenes")):
    first_sample = nusc.get('sample', scene['first_sample_token'])

    frame_count = 0

    # ego 相关
    ego_speeds = []
    ego_accs = []
    ego_yaws = []
    ego_positions = []
    scene_timestamps = []
    prev_ego_pos = None
    prev_ego_speed = None
    prev_timestamp = None

    # 周围目标统计
    avg_speeds_frame = []
    vehicle_counts = []
    neighbor_speed_std = []
    pedestrian_ratio_frames = []
    pedestrian_front_frames = 0
    pedestrian_crossing_risk_frames = 0
    crosswalk_pedestrian_frames = 0

    # 风险特征
    ttc_list = []
    ttc_candidate_events = []
    front_vehicle_distances = []
    car_follow_frames = 0
    close_follow_frames = 0
    valid_ttc_frames = 0
    path_conflict_vehicle_frames = 0
    dangerous_ttc_flags = []
    following_flags = []
    merge_exposure_flags = []
    merge_conflict_flags = []
    overtaking_exposure_flags = []
    crossing_exposure_flags = []
    crossing_conflict_flags = []
    vru_conflict_flags = []
    vru_crossing_exposure_flags = []
    same_lane_vru_flags = []
    same_direction_vru_flags = []
    vru_crosswalk_conflict_flags = []
    oncoming_vehicle_flags = []
    intersection_stop_flags = []
    stationary_lead_flags = []
    stationary_lead_instance_tokens = []
    stationary_lead_distances_by_frame = []
    stationary_lead_distances = []
    first_stationary_lead_index = None
    first_stationary_lead_heading = None
    merge_exposure_candidates = []
    vru_observed_candidates = []
    lane_cache = {}
    instance_max_speeds = {}
    minimum_ttc_event = None
    crossing_yield_flags = []
    vehicle_tracks = {}
    crossing_candidates = []
    stop_sign_stop_flags = []
    rejected_lane_targets = 0
    lane_target_map_unknown_count = 0
    lane_target_audit = []
    side_entry_flags = []
    side_entry_instances = set()

    # 目标类别（truck / bus / bicycle / motorcycle）
    truck_bus_frames = 0
    truck_bus_dynamic_frames = 0
    truck_bus_path_conflict_frames = 0
    truck_bus_merge_exposure_frames = 0
    bicycle_frames = 0
    motorcycle_frames = 0
    two_wheeler_dynamic_frames = 0

    # 地图（先占位，地图有问题也不让程序挂）
    map_name = nusc.get('log', scene['log_token'])['location']
    try:
        if map_name not in map_cache:
            loaded_map = NuScenesMap(dataroot=nusc.dataroot, map_name=map_name)
            polygons = [loaded_map.extract_polygon(token)
                        for area in loaded_map.drivable_area for token in area['polygon_tokens']]
            map_cache[map_name] = (loaded_map, prep(unary_union(polygons)))
        nusc_map, drivable_surface = map_cache[map_name]
        map_available = True
    except Exception as exc:
        extraction_audit.record_error(scene, 'map_load', exc)
        nusc_map = None
        map_available = False

    intersection_flag = 0
    intersection_frame_count = 0
    lane_connector_frame_count = 0
    ped_crossing_count = 0
    traffic_light_control_frames = 0
    stop_sign_control_frames = 0
    turn_stop_control_frames = 0
    non_signalized_intersection_frames = 0

    sample = first_sample

    # =========================
    # 遍历该 scene 的所有帧
    # =========================
    while True:
        frame_count += 1

        # ego pose
        lidar_data = nusc.get('sample_data', sample['data']['LIDAR_TOP'])
        ego_pose = nusc.get('ego_pose', lidar_data['ego_pose_token'])

        ego_x, ego_y = ego_pose['translation'][:2]
        ego_positions.append((ego_x, ego_y))
        yaw = quaternion_yaw(ego_pose['rotation'])
        ego_yaws.append(yaw)
        timestamp = sample['timestamp'] / 1e6
        scene_timestamps.append(timestamp)

        if prev_ego_pos is not None:
            dx = ego_x - prev_ego_pos[0]
            dy = ego_y - prev_ego_pos[1]
            dt = timestamp - prev_timestamp
            if dt <= 0:
                dt = 0.5
            ego_speed = np.sqrt(dx * dx + dy * dy) / dt
            ego_speeds.append(ego_speed)

            if prev_ego_speed is not None:
                ego_accs.append((ego_speed - prev_ego_speed) / dt)
            prev_ego_speed = ego_speed

        prev_ego_pos = (ego_x, ego_y)
        prev_timestamp = timestamp

        # -------------------------
        # 周围目标 & 行人
        # -------------------------
        ann_tokens = sample['anns']
        speeds_frame = []
        vehicle_count_this_frame = 0
        pedestrian_here = False
        pedestrian_front_here = False
        pedestrian_crossing_risk_here = False
        ped_crossing_here = False
        is_core_intersection_here = False
        traffic_light_control_here = False
        stop_sign_control_here = False
        turn_stop_control_here = False
        stop_sign_stop_here = False
        ego_speed_current = ego_speeds[-1] if len(ego_speeds) > 0 else 0.0

        min_front_dist_for_ttc = np.inf
        nearest_front_forward_speed = None
        nearest_front_obj_speed = None
        nearest_front_ann_token = None
        nearest_front_instance_token = None
        nearest_front_category = None
        nearest_front_lateral_dist = None
        nearest_front_heading_delta = None

        has_truck_bus = False
        has_dynamic_truck_bus = False
        has_path_conflict_truck_bus = False
        has_merge_exposure_truck_bus = False
        has_path_conflict_vehicle = False
        has_merge_exposure_vehicle = False
        has_merge_conflict_vehicle = False
        has_overtaking_exposure = False
        has_crossing_exposure_vehicle = False
        has_crossing_conflict_vehicle = False
        has_vru_path_conflict = False
        has_vru_crossing_exposure = False
        has_same_lane_vru = False
        has_same_direction_vru = False
        has_oncoming_vehicle = False
        has_bicycle = False
        has_motorcycle = False
        has_side_entry = False
        has_dynamic_two_wheeler = False

        for ann_token in ann_tokens:
            ann = nusc.get('sample_annotation', ann_token)
            category = ann['category_name']

            # 正确计算目标速度（基于 prev/next）
            obj_vx, obj_vy = compute_ann_velocity_xy(nusc, ann)
            obj_speed = np.sqrt(obj_vx * obj_vx + obj_vy * obj_vy)
            instance_token = ann.get('instance_token')
            if instance_token:
                instance_max_speeds[instance_token] = max(
                    instance_max_speeds.get(instance_token, 0.0),
                    float(obj_speed),
                )
            obj_xy = ann['translation'][:2]
            dist_to_ego = np.linalg.norm(
                np.array(obj_xy) - np.array([ego_x, ego_y])
            )
            forward_dist, lateral_dist = ego_frame_delta(obj_xy, ego_x, ego_y, yaw)
            obj_forward_speed, lateral_speed = ego_frame_vector((obj_vx, obj_vy), yaw)

            # 行人暴露与路径冲突分开，近距离本身不等于横穿风险。
            if category.startswith('human'):
                vru_lane_relation = classify_vru_lane_relation(
                    forward_dist,
                    lateral_dist,
                    obj_forward_speed,
                    lateral_speed,
                )
                if map_available and vru_lane_relation.same_lane:
                    try:
                        mapped_relation = mapped_vru_lane_relation(
                            nusc_map,
                            ego_x,
                            ego_y,
                            obj_xy,
                            (obj_vx, obj_vy),
                            lane_cache,
                        )
                        if mapped_relation is not None:
                            vru_lane_relation = mapped_relation
                    except Exception as exc:
                        extraction_audit.record_error(scene, 'vru_lane_relation', exc, frame_count - 1)
                has_same_lane_vru |= vru_lane_relation.same_lane
                has_same_direction_vru |= vru_lane_relation.same_direction
                if dist_to_ego < 20:
                    pedestrian_here = True
                if (
                    VRU_FRONT_MIN_DIST <= forward_dist <= VRU_FRONT_MAX_DIST
                    and abs(lateral_dist) <= VRU_LATERAL_LIMIT
                ):
                    pedestrian_front_here = True
                    if is_vru_crossing_exposure(
                        forward_dist,
                        lateral_dist,
                        lateral_speed,
                    ):
                        has_vru_crossing_exposure = True
                    if is_vru_path_conflict(
                        forward_dist,
                        lateral_dist,
                        obj_forward_speed,
                        lateral_speed,
                        ego_speed_current,
                    ):
                        pedestrian_crossing_risk_here = True
                        has_vru_path_conflict = True
                        vru_observed_candidates.append((frame_count - 1, ann_token))

            # 同车道、合流、横向暴露和横向冲突分别记录。
            if category.startswith('vehicle'):
                if dist_to_ego <= NEAR_OBJECT_RADIUS:
                    speeds_frame.append(obj_speed)
                    vehicle_count_this_frame += 1

                interaction = classify_vehicle_interaction(
                    forward_dist,
                    lateral_dist,
                    obj_forward_speed,
                    lateral_speed,
                    ego_speed_current,
                )
                actor_heading_aligned = is_heading_aligned(
                    quaternion_yaw(ann['rotation']),
                    yaw,
                )
                vehicle_tracks.setdefault(instance_token, []).append({
                    'index': frame_count - 1, 'position': tuple(obj_xy),
                    'forward': float(forward_dist), 'lateral': float(lateral_dist),
                    'aligned': actor_heading_aligned, 'length': ann['size'][1],
                    'width': ann['size'][0],
                    'heading_delta': float(np.arctan2(np.sin(quaternion_yaw(ann['rotation']) - yaw),
                                                      np.cos(quaternion_yaw(ann['rotation']) - yaw))),
                    'category': category,
                    'velocity': [float(obj_vx), float(obj_vy)],
                    'crossing_conflict': interaction.crossing_conflict,
                    'crossing_exposure': interaction.crossing_exposure,
                })
                actor_delta = vehicle_tracks[instance_token][-1]['heading_delta']
                if is_side_entry_candidate(forward_dist, lateral_dist, actor_delta, obj_speed):
                    has_side_entry = True
                    side_entry_instances.add(instance_token)
                merge_exposure = interaction.merge_exposure and actor_heading_aligned
                merge_conflict = interaction.merge_conflict and actor_heading_aligned
                has_merge_conflict_vehicle |= merge_conflict
                has_merge_exposure_vehicle |= merge_exposure
                overtaking_exposure = is_overtaking_exposure(
                    forward_dist,
                    lateral_dist,
                    obj_forward_speed,
                    ego_speed_current,
                    actor_heading_aligned,
                )
                has_overtaking_exposure |= overtaking_exposure
                if merge_exposure:
                    is_heavy = category.startswith('vehicle.truck') or category.startswith('vehicle.bus')
                    merge_exposure_candidates.append(
                        (frame_count - 1, ann_token, is_heavy, overtaking_exposure)
                    )
                has_crossing_exposure_vehicle |= interaction.crossing_exposure
                has_crossing_conflict_vehicle |= interaction.crossing_conflict
                if interaction.crossing_conflict:
                    crossing_candidates.append((frame_count - 1, ann_token))
                has_oncoming_vehicle |= is_oncoming_vehicle(
                    forward_dist,
                    lateral_dist,
                    obj_forward_speed,
                    obj_lateral_speed=lateral_speed,
                    heading_delta=actor_delta,
                )
                if interaction.same_path or merge_conflict or interaction.crossing_conflict:
                    has_path_conflict_vehicle = True
                if interaction.same_path:
                    supported = True
                    if map_available:
                        try:
                            actor_yaw = quaternion_yaw(ann['rotation'])
                            half_width, half_length = np.asarray(ann['size'][:2]) / 2
                            footprint = Polygon([
                                (obj_xy[0] + x*np.cos(actor_yaw) - y*np.sin(actor_yaw),
                                 obj_xy[1] + x*np.sin(actor_yaw) + y*np.cos(actor_yaw))
                                for x, y in [(-half_length, -half_width), (half_length, -half_width),
                                             (half_length, half_width), (-half_length, half_width)]])
                            on_surface = bool(drivable_surface.intersects(footprint))
                            lane_distance = longitudinal_map_distance(
                                nusc_map, ego_x, ego_y, obj_xy, lane_cache)
                            # Current-lane distance is diagnostic only: ego may
                            # already be steering away from a blocked lane.
                            supported = is_lane_supported_target(on_surface)
                            lane_target_audit.append({'index': frame_count - 1, 'instance': instance_token,
                                'category': category, 'on_surface': on_surface,
                                'lane_distance': lane_distance, 'supported': supported,
                                'forward': float(forward_dist), 'lateral': float(lateral_dist)})
                        except Exception as exc:
                            extraction_audit.record_error(scene, 'vehicle_lane_support', exc, frame_count - 1)
                            lane_target_map_unknown_count += 1
                    else:
                        lane_target_map_unknown_count += 1
                    if not supported:
                        rejected_lane_targets += 1
                    clearance = longitudinal_clearance(
                        forward_dist,
                        ann.get('size', [0.0, 4.0, 0.0])[1],
                    ) if supported else None
                    if clearance is not None and clearance < min_front_dist_for_ttc:
                        min_front_dist_for_ttc = clearance
                        nearest_front_forward_speed = obj_forward_speed
                        nearest_front_obj_speed = obj_speed
                        nearest_front_ann_token = ann_token
                        nearest_front_instance_token = instance_token
                        nearest_front_category = category
                        nearest_front_lateral_dist = lateral_dist
                        nearest_front_heading_delta = float(
                            np.arctan2(
                                np.sin(quaternion_yaw(ann['rotation']) - yaw),
                                np.cos(quaternion_yaw(ann['rotation']) - yaw),
                            )
                        )

            # 类别统计
            if category.startswith('vehicle.truck') or category.startswith('vehicle.bus'):
                is_relevant_heavy_vehicle = (
                    dist_to_ego <= NEAR_OBJECT_RADIUS
                    or (
                        0 < forward_dist < FRONT_MAX_DIST
                        and abs(lateral_dist) <= FRONT_LATERAL_LIMIT * 2
                    )
                )
                if is_relevant_heavy_vehicle:
                    has_truck_bus = True
                if is_relevant_heavy_vehicle and obj_speed > DYNAMIC_SPEED_THRESHOLD:
                    has_dynamic_truck_bus = True
                if (
                    obj_speed > DYNAMIC_SPEED_THRESHOLD
                    and (interaction.same_path or merge_conflict or interaction.crossing_conflict)
                ):
                    has_path_conflict_truck_bus = True
                if obj_speed > DYNAMIC_SPEED_THRESHOLD and merge_exposure:
                    has_merge_exposure_truck_bus = True
            if category.startswith('vehicle.bicycle'):
                if dist_to_ego <= NEAR_OBJECT_RADIUS:
                    has_bicycle = True
                    if obj_speed > DYNAMIC_SPEED_THRESHOLD:
                        has_dynamic_two_wheeler = True
            if category.startswith('vehicle.motorcycle'):
                if dist_to_ego <= NEAR_OBJECT_RADIUS:
                    has_motorcycle = True
                    if obj_speed > DYNAMIC_SPEED_THRESHOLD:
                        has_dynamic_two_wheeler = True

        # 每帧邻车统计
        if len(speeds_frame) > 0:
            avg_speeds_frame.append(np.mean(speeds_frame))
            neighbor_speed_std.append(np.std(speeds_frame))
        else:
            avg_speeds_frame.append(0.0)
            neighbor_speed_std.append(0.0)

        vehicle_counts.append(vehicle_count_this_frame)
        pedestrian_ratio_frames.append(1 if pedestrian_here else 0)
        if has_path_conflict_vehicle:
            path_conflict_vehicle_frames += 1
        following_flags.append(nearest_front_forward_speed is not None)
        side_entry_flags.append(has_side_entry)
        merge_exposure_flags.append(has_merge_exposure_vehicle)
        merge_conflict_flags.append(has_merge_conflict_vehicle)
        overtaking_exposure_flags.append(has_overtaking_exposure)
        crossing_exposure_flags.append(has_crossing_exposure_vehicle)
        crossing_conflict_flags.append(has_crossing_conflict_vehicle)
        vru_conflict_flags.append(has_vru_path_conflict)
        vru_crossing_exposure_flags.append(has_vru_crossing_exposure)
        same_lane_vru_flags.append(has_same_lane_vru)
        same_direction_vru_flags.append(has_same_direction_vru)
        oncoming_vehicle_flags.append(has_oncoming_vehicle)
        stationary_lead_here = bool(
            nearest_front_obj_speed is not None
            and nearest_front_obj_speed < 0.5
            and min_front_dist_for_ttc < 40.0
        )
        stationary_lead_flags.append(stationary_lead_here)
        stationary_lead_instance_tokens.append(
            nearest_front_instance_token if stationary_lead_here else None
        )
        stationary_lead_distances_by_frame.append(
            min_front_dist_for_ttc if stationary_lead_here else float("inf")
        )
        if stationary_lead_here:
            stationary_lead_distances.append(min_front_dist_for_ttc)
            if first_stationary_lead_index is None:
                first_stationary_lead_index = frame_count - 1
                first_stationary_lead_heading = yaw
        if pedestrian_front_here:
            pedestrian_front_frames += 1
        if pedestrian_crossing_risk_here:
            pedestrian_crossing_risk_frames += 1

        if has_truck_bus:
            truck_bus_frames += 1
        if has_dynamic_truck_bus:
            truck_bus_dynamic_frames += 1
        if has_path_conflict_truck_bus:
            truck_bus_path_conflict_frames += 1
        if has_merge_exposure_truck_bus:
            truck_bus_merge_exposure_frames += 1
        if has_bicycle:
            bicycle_frames += 1
        if has_motorcycle:
            motorcycle_frames += 1
        if has_dynamic_two_wheeler:
            two_wheeler_dynamic_frames += 1

        # -------------------------
        # TTC 计算（加物理约束 + 截断）
        # -------------------------
        dangerous_ttc_here = False
        if (
            min_front_dist_for_ttc < np.inf
            and len(avg_speeds_frame) > 0
            and len(ego_speeds) > 0
            and nearest_front_forward_speed is not None
        ):
            car_follow_frames += 1
            front_vehicle_distances.append(min_front_dist_for_ttc)
            if min_front_dist_for_ttc < CLOSE_FRONT_DIST:
                close_follow_frames += 1

            rel_speed = ego_speeds[-1] - nearest_front_forward_speed

            # 只有在 ego 明显比前车快、距离不是特别远时才计算 TTC
            if (
                ego_speeds[-1] >= EGO_TTC_MIN_SPEED
                and rel_speed > 1.0
                and min_front_dist_for_ttc < FRONT_MAX_DIST
            ):
                ttc = min_front_dist_for_ttc / rel_speed
                # 截断到 [0, 30] 秒，避免几千秒这种伪值
                ttc = np.clip(ttc, 0, 30)
                ttc_candidate_events.append(
                    {
                        'frame_index': frame_count - 1,
                        'ttc': float(ttc),
                        'scene_time': float(timestamp - scene_timestamps[0]),
                        'annotation_token': nearest_front_ann_token or '',
                        'instance_token': nearest_front_instance_token or '',
                        'category': nearest_front_category or '',
                        'clearance': float(min_front_dist_for_ttc),
                        'lateral_distance': float(nearest_front_lateral_dist or 0.0),
                        'target_speed': float(nearest_front_obj_speed or 0.0),
                        'target_forward_speed': float(nearest_front_forward_speed),
                        'relative_speed': float(rel_speed),
                        'heading_delta': float(nearest_front_heading_delta or 0.0),
                    }
                )
        dangerous_ttc_flags.append(dangerous_ttc_here)

        # -------------------------
        # 地图特征（有就用，报错就跳过，不影响主流程）
        # -------------------------
        if map_available and hasattr(nusc_map, "get_records_in_radius"):
            # 交叉口：核心路口与 lane connector 分开记录，避免把连接段都当成路口
            try:
                is_core_intersection, has_lane_connector = map_intersection_state(nusc_map, ego_x, ego_y)
                is_core_intersection_here = is_core_intersection
                if is_core_intersection:
                    intersection_flag = 1
                    intersection_frame_count += 1
                if has_lane_connector:
                    lane_connector_frame_count += 1
            except Exception as exc:
                extraction_audit.record_error(scene, 'intersection', exc, frame_count - 1)

            # Traffic-light phase is unavailable, but map stop-line types
            # distinguish signalized, stop-sign, and turn-stop infrastructure.
            try:
                stop_line_records = nusc_map.get_records_in_radius(
                    ego_x,
                    ego_y,
                    20,
                    ['stop_line'],
                )
                stop_line_types = [
                    nusc_map.get('stop_line', token).get('stop_line_type', '')
                    for token in stop_line_records.get('stop_line', [])
                ]
                controls = classify_stop_line_controls(stop_line_types)
                traffic_light_control_here = controls.traffic_light
                stop_sign_control_here = controls.stop_sign
                turn_stop_control_here = controls.turn_stop
                if ego_speed_current < 1.0 and controls.stop_sign:
                    approach = LineString([
                        (ego_x - 3 * np.cos(yaw), ego_y - 3 * np.sin(yaw)),
                        (ego_x + 10 * np.cos(yaw), ego_y + 10 * np.sin(yaw)),
                    ])
                    for token in stop_line_records.get('stop_line', []):
                        record = nusc_map.get('stop_line', token)
                        if record.get('stop_line_type') == 'STOP_SIGN':
                            polygon = nusc_map.extract_polygon(record['polygon_token'])
                            if polygon.distance(Point(ego_x, ego_y)) <= 8.0 and polygon.intersects(approach):
                                stop_sign_stop_here = True
            except Exception as exc:
                extraction_audit.record_error(scene, 'stop_line_controls', exc, frame_count - 1)

            # 人行横道
            try:
                rec_pc = nusc_map.get_records_in_radius(ego_x, ego_y, 8, ['ped_crossing'])
                if 'ped_crossing' in rec_pc and len(rec_pc['ped_crossing']) > 0:
                    ped_crossing_here = True
                    ped_crossing_count += 1
            except Exception as exc:
                extraction_audit.record_error(scene, 'pedestrian_crossing', exc, frame_count - 1)

        if ped_crossing_here and pedestrian_here:
            crosswalk_pedestrian_frames += 1
        if traffic_light_control_here:
            traffic_light_control_frames += 1
        if stop_sign_control_here:
            stop_sign_control_frames += 1
        if turn_stop_control_here:
            turn_stop_control_frames += 1
        if is_core_intersection_here and not traffic_light_control_here:
            non_signalized_intersection_frames += 1
        vru_crosswalk_conflict_flags.append(
            bool(ped_crossing_here and has_vru_path_conflict)
        )
        intersection_stop_flags.append(
            bool(is_core_intersection_here and len(ego_speeds) > 0 and ego_speed_current < 1.0)
        )
        crossing_yield_flags.append(
            bool(has_crossing_exposure_vehicle and ego_speed_current < 1.0)
        )
        stop_sign_stop_flags.append(stop_sign_stop_here)

        # 下一帧
        if sample['next'] == "":
            break
        sample = nusc.get('sample', sample['next'])

    # =========================
    # 场景级聚合
    # =========================
    ego_heading_change_total = wrapped_heading_change(ego_yaws)
    turning_projection_flags = [False] * frame_count
    for candidate in ttc_candidate_events:
        frame_index = candidate['frame_index']
        local_heading_change = local_heading_change_around_index(
            ego_yaws,
            scene_timestamps,
            frame_index,
        )
        if is_turning_projection_artifact(
            candidate['target_speed'],
            candidate['heading_delta'],
            local_heading_change,
        ):
            turning_projection_flags[frame_index] = True
            continue
        valid_ttc_frames += 1
        ttc_list.append(candidate['ttc'])
        dangerous_ttc_flags[frame_index] = candidate['ttc'] < 3.0
        minimum_ttc_event = select_lower_ttc_event(minimum_ttc_event, candidate)

    for index, is_artifact in enumerate(turning_projection_flags):
        if not is_artifact:
            continue
        stationary_lead_flags[index] = False
        stationary_lead_instance_tokens[index] = None
        stationary_lead_distances_by_frame[index] = float("inf")

    intersection_density = intersection_frame_count / frame_count if frame_count > 0 else 0.0
    ego_decision = summarize_motion_decision(
        ego_speeds,
        scene_timestamps[1:],
    )
    stopped_lead_summary = summarize_events(stationary_lead_flags, scene_timestamps)
    bounded_stationary_instances = {
        instance for instance, track in vehicle_tracks.items()
        if is_bounded_stationary_track(
            [row['position'] for row in track],
            [scene_timestamps[row['index']] for row in track])
    }
    stopped_lead_split = split_stopped_lead_history(
        stationary_lead_instance_tokens,
        instance_max_speeds,
        bounded_stationary_instances=bounded_stationary_instances,
    )
    stationary_lead_summary = summarize_events(
        stopped_lead_split.static_flags,
        scene_timestamps,
    )
    blocked_path_flags = filter_short_events(
        stopped_lead_split.static_flags,
        scene_timestamps,
        minimum_duration=0.8,
    )
    blocked_path_summary = summarize_events(blocked_path_flags, scene_timestamps)
    temporarily_stopped_lead_summary = summarize_events(
        stopped_lead_split.temporary_flags,
        scene_timestamps,
    )
    static_indices = [
        index for index, active in enumerate(stopped_lead_split.static_flags) if active
    ]
    blocked_indices = [
        index for index, active in enumerate(blocked_path_flags) if active
    ]
    first_stationary_lead_index = static_indices[0] if static_indices else None
    first_stationary_lead_heading = (
        ego_yaws[first_stationary_lead_index]
        if first_stationary_lead_index is not None
        else None
    )
    static_stationary_distances = [
        stationary_lead_distances_by_frame[index] for index in static_indices
    ]
    blocked_stationary_distances = [
        stationary_lead_distances_by_frame[index] for index in blocked_indices
    ]
    ego_evasive_lateral_shift = lateral_shift_after_index(
        ego_positions,
        scene_timestamps,
        first_stationary_lead_index if first_stationary_lead_index is not None else -1,
        first_stationary_lead_heading if first_stationary_lead_heading is not None else 0.0,
        horizon=10.0,
    )
    ego_evasive_net_heading_change = net_heading_change_after_index(
        ego_yaws,
        scene_timestamps,
        first_stationary_lead_index if first_stationary_lead_index is not None else -1,
        first_stationary_lead_heading if first_stationary_lead_heading is not None else 0.0,
        horizon=10.0,
    )
    ego_evasive_lane_change = is_evasive_lane_change(
        stationary_lead_summary.count,
        ego_evasive_lateral_shift,
        ego_evasive_net_heading_change,
        stationary_max_duration=stationary_lead_summary.max_duration,
        stationary_min_distance=(
            float(np.min(static_stationary_distances))
            if static_stationary_distances
            else 80.0
        ),
    )
    first_blocked_index = blocked_indices[0] if blocked_indices else None
    first_blocked_heading = (
        ego_yaws[first_blocked_index] if first_blocked_index is not None else None
    )
    route_lateral_shift = lateral_shift_after_index(
        ego_positions,
        scene_timestamps,
        first_blocked_index if first_blocked_index is not None else -1,
        first_blocked_heading if first_blocked_heading is not None else 0.0,
        horizon=10.0,
    )
    route_net_heading_change = net_heading_change_after_index(
        ego_yaws,
        scene_timestamps,
        first_blocked_index if first_blocked_index is not None else -1,
        first_blocked_heading if first_blocked_heading is not None else 0.0,
        horizon=10.0,
    )
    obstacle_induced_route_deviation_candidate = is_obstacle_induced_route_deviation(
        blocked_path_summary.max_duration,
        (
            float(np.min(blocked_stationary_distances))
            if blocked_stationary_distances
            else 80.0
        ),
        route_lateral_shift,
        route_net_heading_change,
    )
    oncoming_during_avoidance_flags = events_within_context(
        oncoming_vehicle_flags,
        scene_timestamps,
        first_stationary_lead_index if ego_evasive_lane_change else -1,
        horizon=10.0,
    )

    # Offline scene mining can use the recorded future paths to reject actors
    # that would only intersect a constant-heading extrapolation of ego.
    merge_observed_flags = [False] * frame_count
    merge_lane_entry_flags = [False] * frame_count
    heavy_merge_observed_flags = [False] * frame_count
    vru_observed_flags = [False] * frame_count
    merge_observed_min_distance = float("inf")
    vru_observed_min_distance = float("inf")
    vru_observed_min_distance_time = -1.0
    intrusion_flags = [False] * frame_count
    intrusion_instances = set()
    for instance, track in vehicle_tracks.items():
        for start_at, start in enumerate(track):
            i = start['index']
            for end in track[start_at + 1:]:
                j = end['index']
                duration = scene_timestamps[j] - scene_timestamps[i]
                if duration > 4.0:
                    break
                _, actor_lateral_move = ego_frame_vector(
                    np.asarray(end['position']) - np.asarray(start['position']), ego_yaws[i])
                clearance = end['forward'] - 2.25 - end['length'] / 2
                if is_adjacent_lane_intrusion(
                    start['lateral'], end['lateral'], actor_lateral_move,
                    clearance, duration, start['aligned'] and end['aligned'],
                ):
                    # Strong turns alter the reference frame; retain these as
                    # exposure until lane-relative evidence is available.
                    if wrapped_heading_change(ego_yaws[i:j + 1]) > 0.35:
                        continue
                    if abs(start['heading_delta']) > 0.6 or abs(end['heading_delta']) > 0.6:
                        continue
                    intrusion_flags[i:j + 1] = [True] * (j - i + 1)
                    intrusion_instances.add(instance)

    crossing_route_flags = [False] * frame_count
    for frame_index, ann_token in crossing_candidates:
        start_time = scene_timestamps[frame_index]
        future_indices = [i for i in range(frame_index, frame_count)
                          if scene_timestamps[i] - start_time <= 6.0]
        route = [ego_positions[i] for i in future_indices]
        ann = nusc.get('sample_annotation', ann_token)
        while True:
            actor_time = nusc.get('sample', ann['sample_token'])['timestamp'] / 1e6
            if actor_time - start_time > 6.0:
                break
            actor_position = ann['translation'][:2]
            ego_index = int(np.argmin(np.abs(np.asarray(scene_timestamps) - actor_time)))
            near_in_time = abs(scene_timestamps[ego_index] - actor_time) <= 0.26
            if (near_in_time and distance_to_polyline(actor_position, route) <= 2.5
                    and np.linalg.norm(np.asarray(actor_position) - ego_positions[ego_index]) <= 10.0):
                crossing_route_flags[frame_index] = True
                break
            if not ann['next']:
                break
            ann = nusc.get('sample_annotation', ann['next'])
    for frame_index, ann_token, is_heavy, was_overtaking in merge_exposure_candidates:
        ann = nusc.get('sample_annotation', ann_token)
        start_time = scene_timestamps[frame_index]
        actor_positions = []
        actor_timestamps = []
        while True:
            ann_sample = nusc.get('sample', ann['sample_token'])
            ann_time = ann_sample['timestamp'] / 1e6
            if ann_time - start_time > 6.0:
                break
            actor_positions.append(tuple(ann['translation'][:2]))
            actor_timestamps.append(ann_time)
            if ann['next'] == "":
                break
            ann = nusc.get('sample_annotation', ann['next'])

        observed_distance = synchronized_path_min_distance(
            ego_positions,
            scene_timestamps,
            actor_positions,
            actor_timestamps,
            start_time,
        )
        merge_observed_min_distance = min(merge_observed_min_distance, observed_distance)
        enters_ego_lane = not map_available
        if map_available:
            for actor_position, actor_time in zip(actor_positions, actor_timestamps):
                ego_index = int(np.argmin(np.abs(np.asarray(scene_timestamps) - actor_time)))
                try:
                    geometry = mapped_actor_lane_geometry(
                        nusc_map,
                        ego_positions[ego_index][0],
                        ego_positions[ego_index][1],
                        actor_position,
                        lane_cache,
                    )
                    if geometry is not None and geometry[0] <= 1.8:
                        enters_ego_lane = True
                        break
                except Exception as exc:
                    extraction_audit.record_error(scene, 'merge_observed_lane', exc, ego_index)
        if observed_distance <= 15.0 and (not was_overtaking or enters_ego_lane):
            merge_observed_flags[frame_index] = True
            if is_heavy:
                heavy_merge_observed_flags[frame_index] = True
        if is_observed_merge_relevant(observed_distance, enters_ego_lane):
            merge_lane_entry_flags[frame_index] = True

    for frame_index, ann_token in vru_observed_candidates:
        ann = nusc.get('sample_annotation', ann_token)
        start_time = scene_timestamps[frame_index]
        actor_positions = []
        actor_timestamps = []
        while True:
            ann_sample = nusc.get('sample', ann['sample_token'])
            ann_time = ann_sample['timestamp'] / 1e6
            if ann_time - start_time > 8.0:
                break
            actor_positions.append(tuple(ann['translation'][:2]))
            actor_timestamps.append(ann_time)
            if ann['next'] == "":
                break
            ann = nusc.get('sample_annotation', ann['next'])
        closest_approach = synchronized_path_closest_approach(
            ego_positions,
            scene_timestamps,
            actor_positions,
            actor_timestamps,
            start_time,
            horizon=8.0,
        )
        observed_distance = closest_approach.distance
        if observed_distance < vru_observed_min_distance:
            vru_observed_min_distance_time = (
                start_time - scene_timestamps[0] + closest_approach.relative_time
            )
        vru_observed_min_distance = min(vru_observed_min_distance, observed_distance)
        enters_ego_lane = not map_available
        if map_available:
            for actor_position, actor_time in zip(actor_positions, actor_timestamps):
                ego_index = int(np.argmin(np.abs(np.asarray(scene_timestamps) - actor_time)))
                if np.linalg.norm(
                    np.asarray(ego_positions[ego_index]) - np.asarray(actor_position)
                ) > 10.0:
                    continue
                try:
                    relation = mapped_vru_lane_relation(
                        nusc_map,
                        ego_positions[ego_index][0],
                        ego_positions[ego_index][1],
                        actor_position,
                        (0.0, 0.0),
                        lane_cache,
                    )
                    if relation is not None and relation.same_lane:
                        enters_ego_lane = True
                        break
                except Exception as exc:
                    extraction_audit.record_error(scene, 'vru_observed_lane', exc, ego_index)
        if is_observed_vru_relevant(observed_distance, enters_ego_lane):
            vru_observed_flags[frame_index] = True

    vru_sustained_flags = filter_short_events(
        vru_observed_flags,
        scene_timestamps,
        minimum_duration=0.8,
    )
    obstacle_avoidance_vru_flags = events_within_context(
        vru_sustained_flags,
        scene_timestamps,
        first_stationary_lead_index if ego_evasive_lane_change else -1,
        horizon=10.0,
    )
    same_direction_vru_flags = filter_short_events(
        same_direction_vru_flags,
        scene_timestamps,
        minimum_duration=1.0,
    )
    crossing_conflict_partition = partition_events_at_time(
        crossing_conflict_flags,
        scene_timestamps,
        (
            scene_timestamps[0] + ego_decision.first_stop_time
            if ego_decision.first_stop_time >= 0.0
            else float("inf")
        ),
    )
    signed_heading_change = signed_net_heading_change(ego_yaws)
    left_turn_flag = signed_heading_change > 0.35
    left_turn_crossing_yield_flags = (
        crossing_yield_flags if left_turn_flag else [False] * frame_count
    )
    left_turn_cross_traffic_interaction_flags = left_turn_cross_traffic_flags(
        crossing_exposure_flags,
        left_turn_flag,
        any(crossing_conflict_flags) or any(crossing_yield_flags),
    )
    merge_exposure_flags = filter_short_events(
        merge_exposure_flags,
        scene_timestamps,
        minimum_duration=1.0,
    )
    merge_conflict_flags = filter_short_events(
        merge_conflict_flags,
        scene_timestamps,
        minimum_duration=1.0,
    )
    overtaking_exposure_flags = filter_short_events(
        overtaking_exposure_flags,
        scene_timestamps,
        minimum_duration=1.0,
    )
    merge_observed_flags = filter_short_events(
        merge_observed_flags,
        scene_timestamps,
        minimum_duration=1.0,
    )
    merge_lane_entry_flags = filter_short_events(
        merge_lane_entry_flags,
        scene_timestamps,
        minimum_duration=1.0,
    )
    heavy_merge_observed_flags = filter_short_events(
        heavy_merge_observed_flags,
        scene_timestamps,
        minimum_duration=1.0,
    )

    following_summary = summarize_events(following_flags, scene_timestamps)
    merge_exposure_summary = summarize_events(merge_exposure_flags, scene_timestamps)
    merge_summary = summarize_events(merge_conflict_flags, scene_timestamps)
    overtaking_exposure_summary = summarize_events(overtaking_exposure_flags, scene_timestamps)
    crossing_exposure_summary = summarize_events(crossing_exposure_flags, scene_timestamps)
    crossing_conflict_summary = summarize_events(crossing_conflict_flags, scene_timestamps)
    crossing_pre_stop_summary = summarize_events(
        crossing_conflict_partition.before,
        scene_timestamps,
    )
    crossing_post_stop_summary = summarize_events(
        crossing_conflict_partition.after,
        scene_timestamps,
    )
    left_turn_crossing_yield_summary = summarize_events(
        left_turn_crossing_yield_flags,
        scene_timestamps,
    )
    left_turn_cross_traffic_interaction_summary = summarize_events(
        left_turn_cross_traffic_interaction_flags,
        scene_timestamps,
    )
    vru_conflict_summary = summarize_events(vru_conflict_flags, scene_timestamps)
    vru_observed_summary = summarize_events(vru_observed_flags, scene_timestamps)
    vru_sustained_summary = summarize_events(vru_sustained_flags, scene_timestamps)
    vru_crossing_exposure_summary = summarize_events(vru_crossing_exposure_flags, scene_timestamps)
    same_lane_vru_summary = summarize_events(same_lane_vru_flags, scene_timestamps)
    same_direction_vru_summary = summarize_events(same_direction_vru_flags, scene_timestamps)
    obstacle_avoidance_vru_summary = summarize_events(obstacle_avoidance_vru_flags, scene_timestamps)
    oncoming_during_avoidance_summary = summarize_events(oncoming_during_avoidance_flags, scene_timestamps)
    vru_crosswalk_conflict_summary = summarize_events(vru_crosswalk_conflict_flags, scene_timestamps)
    merge_observed_summary = summarize_events(merge_observed_flags, scene_timestamps)
    merge_lane_entry_summary = summarize_events(merge_lane_entry_flags, scene_timestamps)
    heavy_merge_observed_summary = summarize_events(heavy_merge_observed_flags, scene_timestamps)
    dangerous_ttc_summary = summarize_events(dangerous_ttc_flags, scene_timestamps)
    intrusion_summary = summarize_events(intrusion_flags, scene_timestamps)
    side_entry_summary = summarize_events(filter_short_events(
        side_entry_flags, scene_timestamps, minimum_duration=0.8), scene_timestamps)
    crossing_route_summary = summarize_events(crossing_route_flags, scene_timestamps)
    stop_sign_stop_summary = summarize_events(stop_sign_stop_flags, scene_timestamps)
    intersection_stop_summary = summarize_events(intersection_stop_flags, scene_timestamps)
    route_deviation_context_supported = is_route_deviation_context_supported(
        traffic_light_control_frames / frame_count if frame_count > 0 else 0.0,
        crossing_exposure_summary.ratio,
        intersection_stop_summary.ratio,
        left_turn_cross_traffic_interaction_summary.ratio,
    )
    obstacle_induced_route_deviation = bool(
        obstacle_induced_route_deviation_candidate
        and route_deviation_context_supported
    )
    route_deviation_demand = route_deviation_decision_demand(
        blocked_path_summary.ratio,
        obstacle_induced_route_deviation,
    )

    if os.getenv('SCENE_CLUSTER_AUDIT_OUTPUT'):
        scene_audits.append({'scene_name': scene['name'],
            'scene_token': scene['token'],
            'times': [t - scene_timestamps[0] for t in scene_timestamps],
            'ego_positions': ego_positions, 'ego_yaws': ego_yaws,
            'vehicle_tracks': vehicle_tracks, 'lane_targets': lane_target_audit,
            'ego_speeds': [0.0] + ego_speeds,
            'stationary_lead_instances': stationary_lead_instance_tokens,
            'static_obstacle_flags': stopped_lead_split.static_flags,
            'instance_max_speeds': instance_max_speeds,
            'bounded_stationary_instances': sorted(bounded_stationary_instances),
            'crossing_conflict_flags': crossing_conflict_flags,
            'crossing_exposure_flags': crossing_exposure_flags,
            'crossing_yield_flags': crossing_yield_flags,
            'stop_sign_stop_flags': stop_sign_stop_flags,
            'crossing_route_flags': crossing_route_flags})
    scene_features.append({
        'scene_name': scene['name'],
        'scene_token': scene['token'],
        'adjacent_lane_intrusion_ratio': intrusion_summary.ratio,
        'side_entry_candidate_ratio': side_entry_summary.ratio,
        'side_entry_candidate_instances': '|'.join(sorted(side_entry_instances)) or 'none',
        'adjacent_lane_intrusion_max_duration': intrusion_summary.max_duration,
        'adjacent_lane_intrusion_instances': '|'.join(sorted(intrusion_instances)) or 'none',
        'crossing_route_conflict_ratio': crossing_route_summary.ratio,
        'crossing_route_conflict_max_duration': crossing_route_summary.max_duration,
        'stop_sign_stop_candidate': int(stop_sign_stop_summary.max_duration >= 0.8),
        'stop_sign_stop_ratio': stop_sign_stop_summary.ratio,
        'rejected_lane_target_count': rejected_lane_targets,
        'lane_target_map_unknown_count': lane_target_map_unknown_count,
        'log_location': map_name,
        'frame_count': frame_count,

        # 周围车辆速度/密度特征
        'avg_speed': np.mean(avg_speeds_frame) if avg_speeds_frame else 0.0,
        'max_speed': np.max(avg_speeds_frame) if avg_speeds_frame else 0.0,
        'speed_std': np.std(avg_speeds_frame) if avg_speeds_frame else 0.0,

        'avg_vehicle_count': np.mean(vehicle_counts) if vehicle_counts else 0.0,
        'max_vehicle_count': np.max(vehicle_counts) if vehicle_counts else 0.0,
        'neighbor_density_std': np.std(vehicle_counts) if vehicle_counts else 0.0,
        'neighbor_speed_std': np.mean(neighbor_speed_std) if neighbor_speed_std else 0.0,

        # 行人：20m 内行人出现比例
        'pedestrian_nearby_ratio': np.mean(pedestrian_ratio_frames) if pedestrian_ratio_frames else 0.0,
        'pedestrian_front_ratio': pedestrian_front_frames / frame_count if frame_count > 0 else 0.0,
        'pedestrian_crossing_risk_ratio': pedestrian_crossing_risk_frames / frame_count if frame_count > 0 else 0.0,
        'crosswalk_pedestrian_ratio': crosswalk_pedestrian_frames / frame_count if frame_count > 0 else 0.0,

        # ego 车动态
        'ego_avg_speed': np.mean(ego_speeds) if ego_speeds else 0.0,
        'ego_speed_std': np.std(ego_speeds) if ego_speeds else 0.0,
        'ego_acc_mean': np.mean(ego_accs) if ego_accs else 0.0,
        'ego_acc_std': np.std(ego_accs) if ego_accs else 0.0,
        'ego_decel_min': np.min(ego_accs) if ego_accs else 0.0,
        'ego_hard_brake_ratio': np.mean(np.array(ego_accs) < -3.0) if ego_accs else 0.0,
        'ego_hard_accel_ratio': np.mean(np.array(ego_accs) > 3.0) if ego_accs else 0.0,
        'ego_heading_change_total': ego_heading_change_total,
        'ego_signed_heading_change': signed_heading_change,
        'ego_left_turn_flag': int(left_turn_flag),
        'ego_initial_avg_speed': ego_decision.initial_avg_speed,
        'ego_initial_stop_ratio': ego_decision.initial_stop_ratio,
        'ego_stopped_at_scene_start': int(ego_decision.stopped_at_start),
        'ego_stop_from_motion_flag': int(ego_decision.stop_from_motion),
        'ego_restart_after_stop_flag': int(ego_decision.restart_after_stop),
        'ego_first_stop_time': ego_decision.first_stop_time,

        # 跟车&风险
        'path_conflict_vehicle_ratio': path_conflict_vehicle_frames / frame_count if frame_count > 0 else 0.0,
        'car_following_ratio': car_follow_frames / frame_count if frame_count > 0 else 0.0,
        'following_event_count': following_summary.count,
        'following_max_duration': following_summary.max_duration,
        'merge_exposure_ratio': merge_exposure_summary.ratio,
        'merge_conflict_ratio': merge_summary.ratio,
        'overtaking_exposure_ratio': overtaking_exposure_summary.ratio,
        'overtaking_event_count': overtaking_exposure_summary.count,
        'overtaking_max_duration': overtaking_exposure_summary.max_duration,
        'merge_observed_relevance_ratio': merge_observed_summary.ratio,
        'merge_lane_entry_relevance_ratio': merge_lane_entry_summary.ratio,
        'merge_observed_min_distance': merge_observed_min_distance,
        'merge_event_count': merge_summary.count,
        'merge_max_duration': merge_summary.max_duration,
        'crossing_vehicle_exposure_ratio': crossing_exposure_summary.ratio,
        'crossing_vehicle_conflict_ratio': crossing_conflict_summary.ratio,
        'crossing_conflict_pre_stop_ratio': crossing_pre_stop_summary.ratio,
        'crossing_conflict_post_stop_ratio': crossing_post_stop_summary.ratio,
        'left_turn_crossing_yield_ratio': left_turn_crossing_yield_summary.ratio,
        'left_turn_cross_traffic_interaction_ratio': left_turn_cross_traffic_interaction_summary.ratio,
        'crossing_conflict_max_duration': crossing_conflict_summary.max_duration,
        'vru_path_conflict_ratio': vru_conflict_summary.ratio,
        'vru_observed_relevance_ratio': vru_observed_summary.ratio,
        'vru_observed_event_count': vru_observed_summary.count,
        'vru_observed_max_duration': vru_observed_summary.max_duration,
        'vru_sustained_relevance_ratio': vru_sustained_summary.ratio,
        'vru_sustained_max_duration': vru_sustained_summary.max_duration,
        'vru_observed_min_distance': vru_observed_min_distance,
        'vru_observed_min_distance_time': vru_observed_min_distance_time,
        'vru_crossing_exposure_ratio': vru_crossing_exposure_summary.ratio,
        'same_lane_vru_exposure_ratio': same_lane_vru_summary.ratio,
        'same_direction_vru_ratio': same_direction_vru_summary.ratio,
        'vru_crossing_event_count': vru_crossing_exposure_summary.count,
        'vru_conflict_event_count': vru_conflict_summary.count,
        'vru_conflict_max_duration': vru_conflict_summary.max_duration,
        'vru_crosswalk_conflict_ratio': vru_crosswalk_conflict_summary.ratio,
        'vru_crosswalk_conflict_event_count': vru_crosswalk_conflict_summary.count,
        'obstacle_avoidance_vru_conflict_ratio': obstacle_avoidance_vru_summary.ratio,
        'obstacle_avoidance_vru_conflict_event_count': obstacle_avoidance_vru_summary.count,
        'oncoming_during_avoidance_ratio': oncoming_during_avoidance_summary.ratio,
        'oncoming_during_avoidance_event_count': oncoming_during_avoidance_summary.count,
        'stopped_lead_ratio': stopped_lead_summary.ratio,
        'stationary_lead_obstacle_ratio': stationary_lead_summary.ratio,
        'temporarily_stopped_lead_ratio': temporarily_stopped_lead_summary.ratio,
        'blocked_path_obstacle_ratio': blocked_path_summary.ratio,
        'obstacle_induced_route_deviation_flag': int(obstacle_induced_route_deviation),
        'route_deviation_decision_demand': route_deviation_demand,
        'stationary_lead_event_count': stationary_lead_summary.count,
        'stationary_lead_min_dist': float(np.min(static_stationary_distances)) if static_stationary_distances else 80.0,
        'ego_evasive_lateral_shift': ego_evasive_lateral_shift,
        'ego_evasive_net_heading_change': ego_evasive_net_heading_change,
        'ego_evasive_lane_change_flag': int(ego_evasive_lane_change),
        'close_following_ratio': close_follow_frames / frame_count if frame_count > 0 else 0.0,
        'front_vehicle_min_dist': float(np.min(front_vehicle_distances)) if len(front_vehicle_distances) > 0 else 80.0,
        'min_ttc': float(np.min(ttc_list)) if len(ttc_list) > 0 else 30.0,
        'min_ttc_scene_time': minimum_ttc_event['scene_time'] if minimum_ttc_event else -1.0,
        'min_ttc_target_annotation_token': minimum_ttc_event['annotation_token'] if minimum_ttc_event else 'none',
        'min_ttc_target_instance_token': minimum_ttc_event['instance_token'] if minimum_ttc_event else 'none',
        'min_ttc_target_category': minimum_ttc_event['category'] if minimum_ttc_event else 'none',
        'min_ttc_target_clearance': minimum_ttc_event['clearance'] if minimum_ttc_event else 80.0,
        'min_ttc_target_lateral_distance': minimum_ttc_event['lateral_distance'] if minimum_ttc_event else 0.0,
        'min_ttc_target_speed': minimum_ttc_event['target_speed'] if minimum_ttc_event else 0.0,
        'min_ttc_target_forward_speed': minimum_ttc_event['target_forward_speed'] if minimum_ttc_event else 0.0,
        'min_ttc_relative_speed': minimum_ttc_event['relative_speed'] if minimum_ttc_event else 0.0,
        'min_ttc_target_heading_delta': minimum_ttc_event['heading_delta'] if minimum_ttc_event else 0.0,
        'dangerous_ttc_ratio': np.mean(np.array(ttc_list) < 3.0) if len(ttc_list) > 0 else 0.0,
        'dangerous_ttc_frame_ratio': dangerous_ttc_summary.ratio,
        'dangerous_ttc_max_duration': dangerous_ttc_summary.max_duration,
        'ttc_valid_ratio': valid_ttc_frames / frame_count if frame_count > 0 else 0.0,

        # 参与者类别
        'truck_bus_ratio': truck_bus_frames / frame_count if frame_count > 0 else 0.0,
        'truck_bus_dynamic_ratio': truck_bus_dynamic_frames / frame_count if frame_count > 0 else 0.0,
        'truck_bus_path_conflict_ratio': truck_bus_path_conflict_frames / frame_count if frame_count > 0 else 0.0,
        'truck_bus_merge_exposure_ratio': truck_bus_merge_exposure_frames / frame_count if frame_count > 0 else 0.0,
        'truck_bus_merge_observed_relevance_ratio': heavy_merge_observed_summary.ratio,
        'bicycle_ratio': bicycle_frames / frame_count if frame_count > 0 else 0.0,
        'motorcycle_ratio': motorcycle_frames / frame_count if frame_count > 0 else 0.0,
        'two_wheeler_dynamic_ratio': two_wheeler_dynamic_frames / frame_count if frame_count > 0 else 0.0,

        # 地图
        'intersection_flag': int(intersection_density >= INTERSECTION_SCENE_DENSITY_THRESHOLD),
        'intersection_density': intersection_density,
        'lane_connector_density': lane_connector_frame_count / frame_count if frame_count > 0 else 0.0,
        'ped_crossing_density': ped_crossing_count / frame_count if frame_count > 0 else 0.0,
        'intersection_stop_ratio': intersection_stop_summary.ratio,
        'traffic_light_control_density': traffic_light_control_frames / frame_count if frame_count > 0 else 0.0,
        'stop_sign_control_density': stop_sign_control_frames / frame_count if frame_count > 0 else 0.0,
        'turn_stop_control_density': turn_stop_control_frames / frame_count if frame_count > 0 else 0.0,
        'non_signalized_intersection_density': non_signalized_intersection_frames / frame_count if frame_count > 0 else 0.0,
        'map_available': int(map_available),
    })

# =========================
# 保存场景特征表
# =========================
df = pd.DataFrame(scene_features)
quality_report = extraction_audit.report(df)
quality_report.update({'input': file_record(metadata_path), 'partition': partition['file'],
                       'script': file_record(__file__),
                       'audit_code': file_record(SCRIPT_DIR / 'extraction_audit.py')})
with quality_path.open('x', encoding='utf-8') as stream:
    json.dump(quality_report, stream, ensure_ascii=False, indent=2, allow_nan=False)
df.replace([np.inf, -np.inf], 30.0, inplace=True)
df = df.fillna(0.0)

output_path = TABLES_DIR / FEATURE_OUTPUT_NAME
df.to_csv(output_path, index=False)
manifest_extra = {'feature_rules': file_record(SCRIPT_DIR / 'scene_feature_rules.py'),
                  'extraction_audit_code': file_record(SCRIPT_DIR / 'extraction_audit.py'),
                  'quality_audit': file_record(quality_path)}
if os.getenv('SCENE_CLUSTER_AUDIT_OUTPUT'):
    audit_path = TABLES_DIR / os.environ['SCENE_CLUSTER_AUDIT_OUTPUT']
    with audit_path.open('x', encoding='utf-8') as stream:
        json.dump(scene_audits, stream, ensure_ascii=False, default=lambda v: v.item())
    manifest_extra['trajectory_audit'] = file_record(audit_path)
write_run_manifest(output_path, 'feature_extraction', metadata_path, df, partition, __file__,
                   extra=manifest_extra)

print("===== 场景特征表已保存 =====")
print(df.head())
print(f"共 {len(df)} 个场景特征，已保存到: {output_path}")
print(f"Pre-fill nonfinite cells: {quality_report['nonfinite_cell_count']}; "
      f"caught query exceptions: {quality_report['query_exception_count']}; audit: {quality_path}")
