"""Pure geometry and temporal rules for scene-level interaction features."""

from typing import NamedTuple, Sequence

import numpy as np


LANE_HALF_WIDTH = 2.5
SAME_PATH_HALF_WIDTH = 1.8
MAX_INTERACTION_HORIZON = 6.0
MIN_MOVING_EGO_SPEED = 2.0


class VehicleInteraction(NamedTuple):
    same_path: bool
    merge_exposure: bool
    merge_conflict: bool
    crossing_exposure: bool
    crossing_conflict: bool


class VruLaneRelation(NamedTuple):
    same_lane: bool
    same_direction: bool


class EventSummary(NamedTuple):
    ratio: float
    count: int
    max_duration: float


class MotionDecisionSummary(NamedTuple):
    initial_avg_speed: float
    initial_stop_ratio: float
    stopped_at_start: bool
    stop_from_motion: bool
    restart_after_stop: bool
    first_stop_time: float


class StopLineControls(NamedTuple):
    traffic_light: bool
    stop_sign: bool
    turn_stop: bool
    non_signalized: bool


class ClosestApproach(NamedTuple):
    distance: float
    relative_time: float


class StoppedLeadSplit(NamedTuple):
    static_flags: list
    temporary_flags: list


class EventPartition(NamedTuple):
    before: list
    after: list


def classify_vehicle_interaction(
    forward_dist,
    lateral_dist,
    obj_forward_speed,
    obj_lateral_speed,
    ego_speed,
    max_horizon=MAX_INTERACTION_HORIZON,
):
    """Classify an actor using predicted entry into the ego driving corridor."""
    same_path = (
        0.0 < forward_dist < 80.0
        and abs(lateral_dist) <= SAME_PATH_HALF_WIDTH
        and obj_forward_speed > -0.5
        and abs(obj_lateral_speed) <= 1.5
    )

    lateral_closing = lateral_dist * obj_lateral_speed < 0.0
    outside_corridor = LANE_HALF_WIDTH < abs(lateral_dist) <= 20.0
    lateral_speed_abs = abs(obj_lateral_speed)

    crossing_exposure = False
    crossing_conflict = False
    merge_exposure = False
    merge_conflict = False

    if outside_corridor and lateral_closing and lateral_speed_abs > 1e-6:
        time_to_corridor = (abs(lateral_dist) - LANE_HALF_WIDTH) / lateral_speed_abs
        within_horizon = 0.0 <= time_to_corridor <= max_horizon
        predicted_object_forward = forward_dist + obj_forward_speed * time_to_corridor
        predicted_ego_forward = ego_speed * time_to_corridor
        predicted_gap = abs(predicted_object_forward - predicted_ego_forward)

        crossing_exposure = (
            lateral_speed_abs >= 1.5
            and within_horizon
            and -10.0 <= predicted_object_forward <= 60.0
        )
        crossing_conflict = (
            crossing_exposure
            and ego_speed >= MIN_MOVING_EGO_SPEED
            and predicted_gap <= 6.0
        )

        forward_dominant = (
            obj_forward_speed >= 0.5
            and abs(obj_forward_speed) >= 0.5 * lateral_speed_abs
        )
        merge_exposure = (
            within_horizon
            and forward_dominant
            and forward_dist > 0.0
            and 0.0 < predicted_object_forward < 60.0
        )
        merge_conflict = merge_exposure and predicted_gap <= 15.0

    return VehicleInteraction(
        same_path=same_path,
        merge_exposure=merge_exposure,
        merge_conflict=merge_conflict,
        crossing_exposure=crossing_exposure,
        crossing_conflict=crossing_conflict,
    )


def is_vru_path_conflict(
    forward_dist,
    lateral_dist,
    obj_forward_speed,
    obj_lateral_speed,
    ego_speed,
    corridor_half_width=LANE_HALF_WIDTH,
    max_horizon=8.0,
):
    """Predict whether a moving VRU enters the ego corridor before ego arrives."""
    closing_speed = ego_speed - obj_forward_speed
    if closing_speed <= 0.5 or not 0.0 < forward_dist <= 35.0:
        return False

    time_to_longitudinal_overlap = forward_dist / closing_speed
    if time_to_longitudinal_overlap > max_horizon:
        return False

    predicted_lateral = lateral_dist + obj_lateral_speed * time_to_longitudinal_overlap
    lateral_closing = lateral_dist * obj_lateral_speed < 0.0
    enters_corridor = (
        abs(lateral_dist) <= corridor_half_width
        or abs(predicted_lateral) <= corridor_half_width
        or lateral_dist * predicted_lateral < 0.0
    )
    return lateral_closing and abs(obj_lateral_speed) >= 0.3 and enters_corridor


def is_vru_crossing_exposure(
    forward_dist,
    lateral_dist,
    obj_lateral_speed,
    corridor_half_width=LANE_HALF_WIDTH,
    max_horizon=8.0,
):
    """Detect a VRU moving toward the ego corridor without claiming collision risk."""
    if not 0.0 < forward_dist <= 35.0 or abs(obj_lateral_speed) < 0.3:
        return False
    if abs(lateral_dist) <= corridor_half_width:
        return True
    if lateral_dist * obj_lateral_speed >= 0.0:
        return False
    time_to_corridor = (abs(lateral_dist) - corridor_half_width) / abs(obj_lateral_speed)
    return 0.0 <= time_to_corridor <= max_horizon


def classify_vru_lane_relation(
    forward_dist,
    lateral_dist,
    obj_forward_speed,
    obj_lateral_speed,
    same_lane_half_width=SAME_PATH_HALF_WIDTH,
):
    """Identify VRUs occupying the ego lane without treating them as crossing."""
    same_lane = (
        -5.0 <= forward_dist <= 30.0
        and abs(lateral_dist) <= same_lane_half_width
    )
    same_direction = (
        same_lane
        and obj_forward_speed >= 0.2
        and abs(obj_lateral_speed) <= 0.8
    )
    return VruLaneRelation(same_lane=same_lane, same_direction=same_direction)


def classify_mapped_vru_lane_relation(
    on_walkway,
    lane_lateral_distance,
    obj_lane_forward_speed,
    lane_half_width=SAME_PATH_HALF_WIDTH,
):
    """Classify VRU lane occupancy when map-relative geometry is available."""
    same_lane = not on_walkway and abs(lane_lateral_distance) <= lane_half_width
    return VruLaneRelation(
        same_lane=same_lane,
        same_direction=bool(same_lane and obj_lane_forward_speed >= 0.2),
    )


def filter_short_events(flags, timestamps, minimum_duration=1.0):
    """Remove active runs shorter than minimum_duration."""
    if len(flags) != len(timestamps):
        raise ValueError("flags and timestamps must have the same length")
    filtered = [False] * len(flags)
    start = None
    for index, active in enumerate(flags):
        if active and start is None:
            start = index
        if start is not None and (not active or index == len(flags) - 1):
            end = index if active else index - 1
            if len(timestamps) > 1:
                duration = timestamps[end] - timestamps[start]
                if end == start:
                    duration = 0.0
                else:
                    positive_steps = np.diff(np.asarray(timestamps, dtype=float))
                    positive_steps = positive_steps[positive_steps > 0]
                    duration += float(np.median(positive_steps)) if len(positive_steps) else 0.5
            else:
                duration = 0.0
            if duration >= minimum_duration:
                filtered[start:end + 1] = [True] * (end - start + 1)
            start = None
    return filtered


def is_oncoming_vehicle(
    forward_dist,
    lateral_dist,
    obj_forward_speed,
    maximum_forward_distance=60.0,
    maximum_lateral_distance=8.0,
):
    """Identify an actor approaching ego from the forward road corridor."""
    return bool(
        0.0 < forward_dist <= maximum_forward_distance
        and abs(lateral_dist) <= maximum_lateral_distance
        and obj_forward_speed <= -1.0
    )


def is_observed_vru_relevant(minimum_distance, enters_ego_lane, maximum_distance=6.0):
    """Require observed proximity and actual entry into the ego lane."""
    return bool(enters_ego_lane and minimum_distance <= maximum_distance)


def is_observed_merge_relevant(minimum_distance, enters_ego_lane, maximum_distance=15.0):
    """Require a nearby actor to actually enter the ego lane before calling it a merge."""
    return bool(enters_ego_lane and minimum_distance <= maximum_distance)


def is_overtaking_exposure(
    forward_dist,
    lateral_dist,
    obj_forward_speed,
    ego_speed,
    heading_aligned,
):
    """Identify a faster aligned vehicle passing beside ego without claiming lane entry."""
    return bool(
        heading_aligned
        and -15.0 <= forward_dist <= 30.0
        and 2.5 <= abs(lateral_dist) <= 8.0
        and obj_forward_speed >= ego_speed + 1.0
    )


def is_heading_aligned(actor_heading, ego_heading, minimum_cosine=0.0):
    """Reject actors whose annotated orientation opposes ego travel direction."""
    return bool(np.cos(actor_heading - ego_heading) > minimum_cosine)


def select_scene_batch(scenes, start_index, count):
    """Return a reproducible bounded scene batch."""
    if start_index < 0 or count < 0:
        raise ValueError("start_index and count must be non-negative")
    return scenes[start_index:start_index + count]


def split_stopped_lead_history(
    frame_instance_tokens,
    instance_max_speeds,
    static_speed_threshold=0.5,
    dynamic_speed_threshold=1.0,
):
    """Separate permanently static obstacles from actors that move elsewhere in the scene."""
    static_flags = []
    temporary_flags = []
    for token in frame_instance_tokens:
        max_speed = instance_max_speeds.get(token, 0.0) if token else 0.0
        static_flags.append(bool(token and max_speed <= static_speed_threshold))
        temporary_flags.append(bool(token and max_speed >= dynamic_speed_threshold))
    return StoppedLeadSplit(static_flags, temporary_flags)


def partition_events_at_time(flags, timestamps, cutoff_time):
    """Partition event evidence into frames at/before and after a cutoff."""
    if len(flags) != len(timestamps):
        raise ValueError("flags and timestamps must have the same length")
    before = [bool(flag and timestamp <= cutoff_time) for flag, timestamp in zip(flags, timestamps)]
    after = [bool(flag and timestamp > cutoff_time) for flag, timestamp in zip(flags, timestamps)]
    return EventPartition(before, after)


def signed_net_heading_change(yaws):
    """Return signed net heading change with angle wrapping removed."""
    if len(yaws) < 2:
        return 0.0
    unwrapped = np.unwrap(np.asarray(yaws, dtype=float))
    return float(unwrapped[-1] - unwrapped[0])


def select_lower_ttc_event(current, candidate):
    """Keep the lower-TTC event together with its provenance fields."""
    if current is None or candidate["ttc"] < current["ttc"]:
        return candidate
    return current


def left_turn_cross_traffic_flags(exposure_flags, left_turn, has_conflict_or_yield):
    """Keep cross-traffic exposure when it forms part of a left-turn interaction."""
    active = left_turn and has_conflict_or_yield
    return [bool(flag and active) for flag in exposure_flags]


def events_within_context(flags, timestamps, start_index, horizon=10.0):
    """Keep event flags only within a bounded context beginning at start_index."""
    if len(flags) != len(timestamps):
        raise ValueError("flags and timestamps must have the same length")
    if start_index is None or start_index < 0 or start_index >= len(flags):
        return [False] * len(flags)

    start_time = timestamps[start_index]
    return [
        bool(active and start_time <= timestamp <= start_time + horizon)
        for active, timestamp in zip(flags, timestamps)
    ]


def summarize_events(flags: Sequence[bool], timestamps: Sequence[float]):
    """Summarize frame flags as exposure ratio, event count, and max duration."""
    if len(flags) != len(timestamps):
        raise ValueError("flags and timestamps must have the same length")
    if not flags:
        return EventSummary(0.0, 0, 0.0)

    if len(timestamps) > 1:
        positive_steps = np.diff(np.asarray(timestamps, dtype=float))
        positive_steps = positive_steps[positive_steps > 0]
        default_step = float(np.median(positive_steps)) if len(positive_steps) else 0.5
    else:
        default_step = 0.5

    event_count = 0
    current_start = None
    max_duration = 0.0
    for index, active in enumerate(flags):
        if active and current_start is None:
            current_start = index
            event_count += 1
        if current_start is not None and (not active or index == len(flags) - 1):
            last_active = index if active else index - 1
            duration = timestamps[last_active] - timestamps[current_start] + default_step
            max_duration = max(max_duration, float(duration))
            current_start = None

    return EventSummary(
        ratio=float(np.mean(np.asarray(flags, dtype=bool))),
        count=event_count,
        max_duration=max_duration,
    )


def wrapped_heading_change(yaws: Sequence[float]):
    """Return total absolute heading change without +/-pi discontinuities."""
    if len(yaws) < 2:
        return 0.0
    return float(np.sum(np.abs(np.diff(np.unwrap(np.asarray(yaws, dtype=float))))))


def local_heading_change_around_index(
    yaws: Sequence[float],
    timestamps: Sequence[float],
    event_index: int,
    window=1.5,
):
    """Return accumulated heading change near an event, excluding distant turns."""
    if event_index < 0 or event_index >= len(yaws) or len(yaws) != len(timestamps):
        return 0.0
    event_time = timestamps[event_index]
    local_yaws = [
        yaw
        for yaw, timestamp in zip(yaws, timestamps)
        if abs(timestamp - event_time) <= window
    ]
    return wrapped_heading_change(local_yaws)


def longitudinal_clearance(forward_dist, object_length, ego_length=4.5, minimum_clearance=0.5):
    """Convert center distance to bumper clearance and reject overlapping boxes."""
    clearance = float(forward_dist - 0.5 * object_length - 0.5 * ego_length)
    if clearance <= minimum_clearance:
        return None
    return clearance


def summarize_motion_decision(
    speeds,
    timestamps,
    initial_window=3.0,
    stop_threshold=1.0,
    moving_threshold=2.0,
    minimum_stop_duration=1.0,
):
    """Separate initial stopping, stopping from motion, and restart behavior."""
    if len(speeds) != len(timestamps):
        raise ValueError("speeds and timestamps must have the same length")
    if not speeds:
        return MotionDecisionSummary(0.0, 0.0, False, False, False, -1.0)

    speed_values = np.asarray(speeds, dtype=float)
    time_values = np.asarray(timestamps, dtype=float)
    relative_times = time_values - time_values[0]
    initial_mask = relative_times <= initial_window
    initial_speeds = speed_values[initial_mask]
    initial_avg_speed = float(np.mean(initial_speeds))
    initial_stop_ratio = float(np.mean(initial_speeds < stop_threshold))
    stopped_at_start = initial_stop_ratio >= 0.8

    stop_flags = speed_values < stop_threshold
    stop_runs = []
    run_start = None
    positive_steps = np.diff(time_values)
    positive_steps = positive_steps[positive_steps > 0]
    default_step = float(np.median(positive_steps)) if len(positive_steps) else 0.5
    for index, stopped in enumerate(stop_flags):
        if stopped and run_start is None:
            run_start = index
        if run_start is not None and (not stopped or index == len(stop_flags) - 1):
            run_end = index if stopped else index - 1
            duration = time_values[run_end] - time_values[run_start] + default_step
            if duration >= minimum_stop_duration:
                stop_runs.append((run_start, run_end))
            run_start = None

    first_stop_time = -1.0
    stop_from_motion = False
    restart_after_stop = False
    if stop_runs:
        first_start, first_end = stop_runs[0]
        first_stop_time = float(relative_times[first_start])
        had_prior_motion = bool(np.any(speed_values[:first_start] >= moving_threshold))
        stop_from_motion = had_prior_motion and not stopped_at_start
        restart_after_stop = bool(np.any(speed_values[first_end + 1:] >= moving_threshold))

    return MotionDecisionSummary(
        initial_avg_speed=initial_avg_speed,
        initial_stop_ratio=initial_stop_ratio,
        stopped_at_start=stopped_at_start,
        stop_from_motion=stop_from_motion,
        restart_after_stop=restart_after_stop,
        first_stop_time=first_stop_time,
    )


def lateral_shift_after_index(
    positions,
    timestamps,
    start_index,
    start_heading,
    horizon=6.0,
):
    """Measure maximum lateral displacement in the frozen ego frame."""
    if len(positions) != len(timestamps):
        raise ValueError("positions and timestamps must have the same length")
    if not positions or start_index < 0 or start_index >= len(positions):
        return 0.0

    origin = np.asarray(positions[start_index], dtype=float)
    start_time = timestamps[start_index]
    lateral_values = []
    for position, timestamp in zip(positions[start_index:], timestamps[start_index:]):
        if timestamp - start_time > horizon:
            break
        delta = np.asarray(position, dtype=float) - origin
        lateral = -delta[0] * np.sin(start_heading) + delta[1] * np.cos(start_heading)
        lateral_values.append(abs(float(lateral)))
    return max(lateral_values, default=0.0)


def net_heading_change_after_index(
    yaws,
    timestamps,
    start_index,
    start_heading,
    horizon=10.0,
):
    """Return absolute net heading change, distinguishing turns from lane changes."""
    if len(yaws) != len(timestamps):
        raise ValueError("yaws and timestamps must have the same length")
    if not yaws or start_index < 0 or start_index >= len(yaws):
        return 0.0

    start_time = timestamps[start_index]
    end_heading = yaws[start_index]
    for yaw, timestamp in zip(yaws[start_index:], timestamps[start_index:]):
        if timestamp - start_time > horizon:
            break
        end_heading = yaw
    wrapped_delta = np.arctan2(
        np.sin(end_heading - start_heading),
        np.cos(end_heading - start_heading),
    )
    return abs(float(wrapped_delta))


def synchronized_path_min_distance(
    ego_positions,
    ego_timestamps,
    actor_positions,
    actor_timestamps,
    start_time,
    horizon=6.0,
    timestamp_tolerance=0.26,
):
    """Measure observed ego-actor distance at approximately synchronized times."""
    return synchronized_path_closest_approach(
        ego_positions,
        ego_timestamps,
        actor_positions,
        actor_timestamps,
        start_time,
        horizon,
        timestamp_tolerance,
    ).distance


def synchronized_path_closest_approach(
    ego_positions,
    ego_timestamps,
    actor_positions,
    actor_timestamps,
    start_time,
    horizon=6.0,
    timestamp_tolerance=0.26,
):
    """Return synchronized minimum distance and its time relative to start_time."""
    if not ego_positions or not actor_positions:
        return ClosestApproach(float("inf"), -1.0)

    ego_times = np.asarray(ego_timestamps, dtype=float)
    actor_times = np.asarray(actor_timestamps, dtype=float)
    minimum = float("inf")
    closest_time = -1.0
    for actor_position, actor_time in zip(actor_positions, actor_times):
        if actor_time < start_time or actor_time - start_time > horizon:
            continue
        ego_index = int(np.argmin(np.abs(ego_times - actor_time)))
        if abs(ego_times[ego_index] - actor_time) > timestamp_tolerance:
            continue
        distance = np.linalg.norm(
            np.asarray(ego_positions[ego_index], dtype=float)
            - np.asarray(actor_position, dtype=float)
        )
        if distance < minimum:
            minimum = float(distance)
            closest_time = float(actor_time - start_time)
    return ClosestApproach(minimum, closest_time)


def classify_stop_line_controls(stop_line_types):
    """Normalize nuScenes stop-line types into traffic-control features."""
    normalized = {str(value).upper() for value in stop_line_types}
    traffic_light = "TRAFFIC_LIGHT" in normalized
    return StopLineControls(
        traffic_light=traffic_light,
        stop_sign="STOP_SIGN" in normalized,
        turn_stop="TURN_STOP" in normalized,
        non_signalized=not traffic_light,
    )


def is_evasive_lane_change(
    stationary_event_count,
    lateral_shift,
    net_heading_change,
    minimum_lateral_shift=1.5,
    maximum_net_heading_change=0.35,
    stationary_max_duration=float("inf"),
    stationary_min_distance=0.0,
    minimum_stationary_duration=1.0,
    maximum_brief_obstacle_distance=20.0,
):
    """Identify obstacle avoidance while excluding ordinary turning maneuvers."""
    obstacle_evidence = stationary_max_duration >= minimum_stationary_duration
    return bool(
        stationary_event_count > 0
        and obstacle_evidence
        and lateral_shift >= minimum_lateral_shift
        and net_heading_change <= maximum_net_heading_change
    )


def is_turning_projection_artifact(
    target_speed,
    heading_delta,
    local_heading_change,
    maximum_static_speed=0.5,
    minimum_opposing_heading=2.35,
    minimum_turn_change=0.35,
):
    """Reject static opposing actors briefly projected ahead during a turn."""
    wrapped_heading = abs(
        np.arctan2(np.sin(heading_delta), np.cos(heading_delta))
    )
    return bool(
        target_speed < maximum_static_speed
        and wrapped_heading >= minimum_opposing_heading
        and local_heading_change >= minimum_turn_change
    )


def is_obstacle_induced_route_deviation(
    stationary_max_duration,
    stationary_min_distance,
    lateral_shift,
    net_heading_change,
    minimum_stationary_duration=0.8,
    maximum_obstacle_distance=25.0,
    minimum_lateral_shift=4.0,
    minimum_heading_change=0.35,
):
    """Identify a sustained path blockage followed by a route-level maneuver."""
    has_blockage = (
        stationary_max_duration >= minimum_stationary_duration
        and stationary_min_distance <= maximum_obstacle_distance
    )
    has_route_change = (
        lateral_shift >= minimum_lateral_shift
        or abs(net_heading_change) >= minimum_heading_change
    )
    return bool(has_blockage and has_route_change)


def route_deviation_decision_demand(
    blocked_path_obstacle_ratio,
    route_deviation_flag,
    full_scale_ratio=0.15,
):
    """Scale sustained blockage into decision demand only when ego deviates."""
    if not route_deviation_flag:
        return 0.0
    return float(np.clip(blocked_path_obstacle_ratio / full_scale_ratio, 0.0, 1.0))


def is_route_deviation_context_supported(
    traffic_light_density,
    crossing_exposure_ratio,
    intersection_stop_ratio,
    left_turn_cross_traffic_ratio,
    maximum_traffic_light_density=0.3,
    crossing_exposure_threshold=0.1,
    intersection_stop_threshold=0.1,
):
    """Reject ordinary signalized turns and cross-traffic yielding decisions."""
    if traffic_light_density >= maximum_traffic_light_density:
        return False
    if left_turn_cross_traffic_ratio > 0.0:
        return False
    is_cross_traffic_yield = (
        crossing_exposure_ratio >= crossing_exposure_threshold
        and intersection_stop_ratio >= intersection_stop_threshold
    )
    return not is_cross_traffic_yield
