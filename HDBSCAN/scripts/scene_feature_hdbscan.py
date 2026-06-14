'''提取 nuScenes 场景特征的脚本'''
import numpy as np
import pandas as pd
from pathlib import Path
from pyquaternion import Quaternion
from nuscenes import NuScenes
from tqdm import tqdm
from nuscenes.map_expansion.map_api import NuScenesMap

SCRIPT_DIR = Path(__file__).resolve().parent
HDBSCAN_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = HDBSCAN_ROOT.parent
TABLES_DIR = HDBSCAN_ROOT / "tables"
TABLES_DIR.mkdir(exist_ok=True)

# =========================
# 加载 nuScenes
# =========================
nusc = NuScenes(version='v1.0-trainval', dataroot=str(PROJECT_ROOT / 'nuScenes'), verbose=True)


# =========================
# 工具函数
# =========================
def quaternion_yaw(q):
    return Quaternion(q).yaw_pitch_roll[0]


def compute_ann_speed_with_time(nusc, ann, default_dt=0.5):
    """
    用 prev/next annotation + sample timestamp 估算物体速度 (m/s)。
    兼容 nuScenes v1.0.5: sample_annotation 没有 velocity 字段。
    """
    cur_sample = nusc.get('sample', ann['sample_token'])
    t_cur = cur_sample['timestamp']  # 微秒

    # 优先用 next
    if ann['next'] != "":
        ann_next = nusc.get('sample_annotation', ann['next'])
        nxt_sample = nusc.get('sample', ann_next['sample_token'])
        t_next = nxt_sample['timestamp']
        dt = (t_next - t_cur) / 1e6  # 秒
        if dt <= 0:
            dt = default_dt

        dx = ann_next['translation'][0] - ann['translation'][0]
        dy = ann_next['translation'][1] - ann['translation'][1]
        return np.sqrt(dx * dx + dy * dy) / max(dt, 1e-3)

    # 再用 prev
    if ann['prev'] != "":
        ann_prev = nusc.get('sample_annotation', ann['prev'])
        prv_sample = nusc.get('sample', ann_prev['sample_token'])
        t_prev = prv_sample['timestamp']
        dt = (t_cur - t_prev) / 1e6
        if dt <= 0:
            dt = default_dt

        dx = ann['translation'][0] - ann_prev['translation'][0]
        dy = ann['translation'][1] - ann_prev['translation'][1]
        return np.sqrt(dx * dx + dy * dy) / max(dt, 1e-3)

    # 单帧，没法算
    return 0.0


def is_near_intersection(nusc_map, x, y, radius=10):
    """Detect intersections from nuScenes map topology around ego position."""
    records = nusc_map.get_records_in_radius(
        x,
        y,
        radius,
        ["road_segment", "lane_connector"],
    )

    for token in records.get("road_segment", []):
        road_segment = nusc_map.get("road_segment", token)
        if road_segment.get("is_intersection", False):
            return True

    # lane_connector is a fallback for turning/connecting topology that may not
    # be represented as an intersecting road_segment at the queried point.
    return len(records.get("lane_connector", [])) > 0


scene_features = []

# =========================
# 主循环：遍历前 X 个 scene
# =========================
for scene_idx, scene in enumerate(tqdm(nusc.scene[:850], desc="Processing scenes")):
    first_sample = nusc.get('sample', scene['first_sample_token'])

    frame_count = 0

    # ego 相关
    ego_speeds = []
    ego_accs = []
    ego_yaws = []
    prev_ego_pos = None
    prev_ego_speed = None

    # 周围目标统计
    avg_speeds_frame = []
    vehicle_counts = []
    neighbor_speed_std = []
    pedestrian_ratio_frames = []

    # 风险特征
    ttc_list = []
    car_follow_frames = 0
    close_follow_frames = 0

    # 目标类别（truck / bus / bicycle / motorcycle）
    truck_bus_frames = 0
    bicycle_frames = 0
    motorcycle_frames = 0

    # 地图（先占位，地图有问题也不让程序挂）
    map_name = nusc.get('log', scene['log_token'])['location']
    try:
        nusc_map = NuScenesMap(dataroot=nusc.dataroot, map_name=map_name)
        map_available = True
    except Exception:
        nusc_map = None
        map_available = False

    intersection_flag = 0
    intersection_frame_count = 0
    ped_crossing_count = 0

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
        yaw = quaternion_yaw(ego_pose['rotation'])
        ego_yaws.append(yaw)

        # ego 速度/加速度（用位移+固定 0.5s 近似）
        if prev_ego_pos is not None:
            dx = ego_x - prev_ego_pos[0]
            dy = ego_y - prev_ego_pos[1]
            ego_speed = np.sqrt(dx * dx + dy * dy) / 0.5
            ego_speeds.append(ego_speed)

            if prev_ego_speed is not None:
                ego_accs.append((ego_speed - prev_ego_speed) / 0.5)

        prev_ego_pos = (ego_x, ego_y)
        prev_ego_speed = ego_speeds[-1] if len(ego_speeds) > 0 else 0.0

        # -------------------------
        # 周围目标 & 行人
        # -------------------------
        ann_tokens = sample['anns']
        speeds_frame = []
        vehicle_count_this_frame = 0
        pedestrian_here = False

        min_front_dist_for_ttc = np.inf

        has_truck_bus = False
        has_bicycle = False
        has_motorcycle = False

        for ann_token in ann_tokens:
            ann = nusc.get('sample_annotation', ann_token)
            category = ann['category_name']

            # 正确计算目标速度（基于 prev/next）
            obj_speed = compute_ann_speed_with_time(nusc, ann)
            speeds_frame.append(obj_speed)

            # 行人：只有 20m 内算“附近行人”
            if category.startswith('human'):
                dist_to_ego = np.linalg.norm(
                    np.array(ann['translation'][:2]) - np.array([ego_x, ego_y])
                )
                if dist_to_ego < 20:
                    pedestrian_here = True

            # TTC：粗略判断“前方车辆”
            if category.startswith('vehicle'):
                rel_x = ann['translation'][0] - ego_x
                if rel_x > 0:
                    dist = np.linalg.norm(
                        np.array(ann['translation'][:2]) - np.array([ego_x, ego_y])
                    )
                    if dist < min_front_dist_for_ttc:
                        min_front_dist_for_ttc = dist

            # 类别统计
            if category.startswith('vehicle.truck') or category.startswith('vehicle.bus'):
                has_truck_bus = True
            if category.startswith('vehicle.bicycle'):
                has_bicycle = True
            if category.startswith('vehicle.motorcycle'):
                has_motorcycle = True

            if category.startswith('vehicle'):
                vehicle_count_this_frame += 1

        # 每帧邻车统计
        if len(speeds_frame) > 0:
            avg_speeds_frame.append(np.mean(speeds_frame))
            neighbor_speed_std.append(np.std(speeds_frame))
        else:
            avg_speeds_frame.append(0.0)
            neighbor_speed_std.append(0.0)

        vehicle_counts.append(vehicle_count_this_frame)
        pedestrian_ratio_frames.append(1 if pedestrian_here else 0)

        if has_truck_bus:
            truck_bus_frames += 1
        if has_bicycle:
            bicycle_frames += 1
        if has_motorcycle:
            motorcycle_frames += 1

        # -------------------------
        # TTC 计算（加物理约束 + 截断）
        # -------------------------
        if (
            min_front_dist_for_ttc < np.inf
            and len(avg_speeds_frame) > 0
            and len(ego_speeds) > 0
        ):
            car_follow_frames += 1
            if min_front_dist_for_ttc < 15:
                close_follow_frames += 1

            rel_speed = ego_speeds[-1] - avg_speeds_frame[-1]

            # 只有在 ego 明显比前车快、距离不是特别远时才计算 TTC
            if rel_speed > 1.0 and min_front_dist_for_ttc < 80:
                ttc = min_front_dist_for_ttc / rel_speed
                # 截断到 [0, 30] 秒，避免几千秒这种伪值
                ttc = np.clip(ttc, 0, 30)
                ttc_list.append(ttc)

        # -------------------------
        # 地图特征（有就用，报错就跳过，不影响主流程）
        # -------------------------
        if map_available and hasattr(nusc_map, "get_records_in_radius"):
            # 交叉口：优先使用 road_segment.is_intersection，lane_connector 作为补充
            try:
                if is_near_intersection(nusc_map, ego_x, ego_y):
                    intersection_flag = 1
                    intersection_frame_count += 1
            except Exception:
                pass

            # 人行横道
            try:
                rec_pc = nusc_map.get_records_in_radius(ego_x, ego_y, 3, ['ped_crossing'])
                if 'ped_crossing' in rec_pc and len(rec_pc['ped_crossing']) > 0:
                    ped_crossing_count += 1
            except Exception:
                pass

        # 下一帧
        if sample['next'] == "":
            break
        sample = nusc.get('sample', sample['next'])

    # =========================
    # 场景级聚合
    # =========================
    ego_heading_change_total = np.sum(np.abs(np.diff(ego_yaws))) if len(ego_yaws) > 1 else 0.0

    scene_features.append({
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

        # ego 车动态
        'ego_avg_speed': np.mean(ego_speeds) if ego_speeds else 0.0,
        'ego_speed_std': np.std(ego_speeds) if ego_speeds else 0.0,
        'ego_acc_mean': np.mean(ego_accs) if ego_accs else 0.0,
        'ego_acc_std': np.std(ego_accs) if ego_accs else 0.0,
        'ego_hard_brake_ratio': np.mean(np.array(ego_accs) < -3.0) if ego_accs else 0.0,
        'ego_heading_change_total': ego_heading_change_total,

        # 跟车&风险
        'car_following_ratio': car_follow_frames / frame_count if frame_count > 0 else 0.0,
        'close_following_ratio': close_follow_frames / frame_count if frame_count > 0 else 0.0,
        'min_ttc': float(np.min(ttc_list)) if len(ttc_list) > 0 else 30.0,
        'dangerous_ttc_ratio': np.mean(np.array(ttc_list) < 3.0) if len(ttc_list) > 0 else 0.0,

        # 参与者类别
        'truck_bus_ratio': truck_bus_frames / frame_count if frame_count > 0 else 0.0,
        'bicycle_ratio': bicycle_frames / frame_count if frame_count > 0 else 0.0,
        'motorcycle_ratio': motorcycle_frames / frame_count if frame_count > 0 else 0.0,

        # 地图
        'intersection_flag': intersection_flag,
        'intersection_density': intersection_frame_count / frame_count if frame_count > 0 else 0.0,
        'ped_crossing_density': ped_crossing_count / frame_count if frame_count > 0 else 0.0,
    })

# =========================
# 保存场景特征表
# =========================
df = pd.DataFrame(scene_features)
df.replace([np.inf, -np.inf], 30.0, inplace=True)
df = df.fillna(0.0)

output_path = TABLES_DIR / "scene_features.csv"
df.to_csv(output_path, index=False)

print("===== 场景特征表已保存 =====")
print(df.head())
print(f"共 {len(df)} 个场景特征，已保存到: {output_path}")
