"""Bounded, append-only human target evidence; never a feature/model entry point."""

import argparse
import ast
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "HDBSCAN/tables"
SCRIPTS = ROOT / "HDBSCAN/scripts"
DATA = ROOT / "nuScenes"
STAGE = "development_human_evidence_only"
INVENTORY = ROOT / "logs/vru_evidence_inventory_20261017.json"
INVENTORY_SHA = "506c7ecc9c8bff0b33d2c4366410ba65f2ef727140a6ca482506206dee5c70ad"
CAPABILITY = ROOT / "logs/nuscenes_capability_inventory_20261016.json"
CAPABILITY_SHA = "60bdcd2180bd68e854c7234f080271652b8814ed7ef5755776dd1e3b2fcbbdb0"
PARENT = TABLES / "longitudinal_v7_replay29_protocol_20261015.json"
PARENT_SHA = "ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d"
EXTRACTOR = SCRIPTS / "scene_feature_hdbscan_v5_2.py"
EXTRACTOR_SHA = "a34af552a0bdc396cec210aed1ebf63c5e20d75c0e084f987e51c1d3302e2974"
EVIDENCE = TABLES / "human_evidence29_20261024.json"
REPORT = TABLES / "human_evidence29_20261024_report.json"
CARDS = ROOT / "outputs/人工复核/行人目标证据补充_20261024.md"
HELPERS = {"compute_ann_velocity_xy", "ego_frame_delta", "ego_frame_vector",
           "mapped_actor_lane_geometry", "mapped_vru_lane_relation"}


def file_record(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def verify_records(records):
    for expected in records:
        actual = file_record(expected["path"])
        if actual["sha256"] != expected["sha256"] or (
                "bytes" in expected and actual["bytes"] != expected["bytes"]):
            raise ValueError(f"Source changed: {expected['path']}")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def iter_records(stream, chunk_size=1024 * 1024):
    """Strict JSON-object-array reader with bounded incomplete-record buffering."""
    decoder = json.JSONDecoder()
    buffer, index, eof = "", 0, False

    def fill():
        nonlocal buffer, index, eof
        more = stream.read(chunk_size)
        buffer = buffer[index:] + more
        index = 0
        eof = not more
        return bool(more)

    def nonspace():
        nonlocal index
        while True:
            while index < len(buffer) and buffer[index].isspace():
                index += 1
            if index < len(buffer):
                return True
            if eof or not fill():
                return False

    if not nonspace() or buffer[index] != "[":
        raise ValueError("Expected a JSON array")
    index += 1
    need_value, after_comma = True, False
    while True:
        if not nonspace():
            raise ValueError("Truncated JSON array")
        char = buffer[index]
        if char == "]":
            if after_comma:
                raise ValueError("Trailing comma")
            index += 1
            if nonspace():
                raise ValueError("Trailing content")
            return
        if not need_value:
            if char != ",":
                raise ValueError("Missing comma")
            index += 1
            need_value, after_comma = True, True
            continue
        while True:
            try:
                record, end = decoder.raw_decode(buffer, index)
                break
            except json.JSONDecodeError as error:
                if eof or len(buffer) - index > 8 * 1024 * 1024 or not fill():
                    raise ValueError("Invalid/truncated/oversize metadata record") from error
        if not isinstance(record, dict):
            raise ValueError("Metadata array element is not an object")
        index = end
        need_value, after_comma = False, False
        yield record


def table_records(table):
    with (DATA / "v1.0-trainval" / f"{table}.json").open(encoding="utf8") as handle:
        yield from iter_records(handle)


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_scope(names, rows, partition, expected_size=29):
    if len(names) != expected_size or len(set(names)) != expected_size:
        raise ValueError("Not the approved fixed development membership")
    by_name = {r["scene_name"]: r for r in rows}
    if len(rows) != expected_size or len(by_name) != expected_size or set(by_name) != set(names):
        raise ValueError("Missing, duplicated or additional scene")
    for name in names:
        source = partition[name]
        if source["split"] != "development" or (
                source["scene_token"] != by_name[name]["scene_token"]):
            raise ValueError(f"Non-development or mismatched identity: {name}")
    return list(names)


def select_humans(rows, sample_to_scene, instance_categories):
    selected = {}
    for row in rows:
        if row["sample_token"] not in sample_to_scene:
            continue
        category = instance_categories.get(row["instance_token"])
        if category is None:
            raise ValueError("Missing selected instance/category identity")
        if not category.startswith("human"):
            continue
        if row["token"] in selected:
            raise ValueError("Duplicate human annotation")
        for key, length in (("translation", 3), ("rotation", 4), ("size", 3)):
            if len(row[key]) != length or not all(math.isfinite(float(v)) for v in row[key]):
                raise ValueError(f"Invalid human {key}")
        selected[row["token"]] = dict(row, category_name=category)
    return selected


def validate_human_chains(annotations, samples):
    grouped = {}
    for token, row in annotations.items():
        grouped.setdefault(row["instance_token"], []).append(row)
        sample = samples[row["sample_token"]]
        for direction, reciprocal, sign in (("next", "prev", 1), ("prev", "next", -1)):
            neighbor_token = row[direction]
            if not neighbor_token:
                continue
            neighbor = annotations.get(neighbor_token)
            if neighbor is None:
                raise ValueError(f"Missing human chain link: {token}/{direction}")
            neighbor_sample = samples[neighbor["sample_token"]]
            if (neighbor["instance_token"] != row["instance_token"]
                    or neighbor[reciprocal] != token
                    or neighbor_sample["scene_token"] != sample["scene_token"]
                    or neighbor.get("category_name") != row.get("category_name")
                    or sign * (neighbor_sample["timestamp"] - sample["timestamp"]) <= 0):
                raise ValueError(f"Cross-scene, target-mismatched or unordered human chain: {token}")
    for rows in grouped.values():
        if sum(not row["prev"] for row in rows) != 1 or sum(not row["next"] for row in rows) != 1:
            raise ValueError("Human instance is not a single complete annotation chain")


def future_window(ann, annotations, samples, horizon, ego_end_us):
    start = samples[ann["sample_token"]]["timestamp"] / 1e6
    chain, current = [], ann
    while True:
        chain.append(current)
        if not current["next"]:
            break
        current = annotations[current["next"]]
    times = [samples[a["sample_token"]]["timestamp"] / 1e6 for a in chain]
    used = [a for a, t in zip(chain, times) if t - start <= horizon]
    beyond = next((a for a, t in zip(chain, times) if t - start > horizon), None)
    indices = [samples[a["sample_token"]]["index"] for a in chain]
    return used, {
        "requested_horizon_s": horizon,
        "legacy_observed_span_s": samples[used[-1]["sample_token"]]["timestamp"] / 1e6 - start,
        "ego_available_future_s": ego_end_us / 1e6 - start,
        "target_available_future_s": times[-1] - start,
        "first_beyond_horizon_token": beyond["token"] if beyond else None,
        "first_beyond_horizon_delta_s": (
            samples[beyond["sample_token"]]["timestamp"] / 1e6 - start if beyond else None),
        "remaining_chain_max_gap_s": max((b - a for a, b in zip(times, times[1:])), default=0.0),
        "remaining_chain_missing_sample_count": sum(b - a - 1 for a, b in zip(indices, indices[1:])),
        "extrapolated": False,
        "physical_barrier_evidence": "unknown",
        "future_safety": "not_inferred",
    }


def ensure_new(paths):
    for path in paths:
        if Path(path).exists():
            raise FileExistsError(f"Refusing to overwrite: {path}")


def rules_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import scene_feature_rules
    return scene_feature_rules


def load_helpers():
    import numpy as np
    verify_records([{"path": str(EXTRACTOR), "sha256": EXTRACTOR_SHA}])
    tree = ast.parse(EXTRACTOR.read_text(encoding="utf8"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in HELPERS]
    if {node.name for node in nodes} != HELPERS:
        raise ValueError("Frozen helper definition missing")
    namespace = {"np": np, "classify_mapped_vru_lane_relation":
                 rules_module().classify_mapped_vru_lane_relation}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(EXTRACTOR), "exec"), namespace)
    return namespace


def summarize_human_flags(flags, times, minimum, minimum_time, static_flags, evasive):
    rules = rules_module()
    sustained = rules.filter_short_events(flags["observed"], times, minimum_duration=0.8)
    direction = rules.filter_short_events(flags["same_direction"], times, minimum_duration=1.0)
    first_static = next((i for i, value in enumerate(static_flags) if value), None)
    avoidance = rules.events_within_context(sustained, times, first_static if evasive else -1, horizon=10.0)
    groups = {key: rules.summarize_events(flags[key], times)
              for key in ("path", "observed", "crossing", "same_lane", "crosswalk")}
    sustained_summary = rules.summarize_events(sustained, times)
    avoidance_summary = rules.summarize_events(avoidance, times)
    ratio = lambda key: sum(flags[key]) / len(times) if times else 0.0
    return {
        "pedestrian_nearby_ratio": ratio("nearby"),
        "pedestrian_front_ratio": ratio("front"),
        "pedestrian_crossing_risk_ratio": ratio("path"),
        "crosswalk_pedestrian_ratio": ratio("crosswalk_nearby"),
        "vru_path_conflict_ratio": groups["path"].ratio,
        "vru_observed_relevance_ratio": groups["observed"].ratio,
        "vru_observed_event_count": groups["observed"].count,
        "vru_observed_max_duration": groups["observed"].max_duration,
        "vru_sustained_relevance_ratio": sustained_summary.ratio,
        "vru_sustained_max_duration": sustained_summary.max_duration,
        "vru_observed_min_distance": float(minimum) if math.isfinite(minimum) else 30.0,
        "vru_observed_min_distance_time": float(minimum_time),
        "vru_crossing_exposure_ratio": groups["crossing"].ratio,
        "same_lane_vru_exposure_ratio": groups["same_lane"].ratio,
        "same_direction_vru_ratio": rules.summarize_events(direction, times).ratio,
        "vru_crossing_event_count": groups["crossing"].count,
        "vru_conflict_event_count": groups["path"].count,
        "vru_conflict_max_duration": groups["path"].max_duration,
        "vru_crosswalk_conflict_ratio": groups["crosswalk"].ratio,
        "vru_crosswalk_conflict_event_count": groups["crosswalk"].count,
        "obstacle_avoidance_vru_conflict_ratio": avoidance_summary.ratio,
        "obstacle_avoidance_vru_conflict_event_count": avoidance_summary.count,
    }


def prepare():
    verify_records([{"path": str(INVENTORY), "sha256": INVENTORY_SHA},
                    {"path": str(PARENT), "sha256": PARENT_SHA},
                    {"path": str(CAPABILITY), "sha256": CAPABILITY_SHA}])
    inventory, parent = read_json(INVENTORY), read_json(PARENT)
    capability = read_json(CAPABILITY)
    records = {}
    prior_records = (inventory["inputs_and_sources"] + parent["inputs"]
                     + [capability["sdk_source"], capability["category_source"]]
                     + [m["source"] for m in capability["maps"]])
    for record in prior_records:
        path = str(Path(record["path"]).resolve())
        if path in records and records[path]["sha256"] != record["sha256"]:
            raise ValueError("Conflicting original source binding")
        records[path] = dict(record, path=path)
    verify_records(records.values())
    names = [row["scene_name"] for row in inventory["rows"]]
    partition = {row["scene_name"]: row for row in
                 read_csv(TABLES / "evaluation_split_20260924.csv") if row["scene_name"] in names}
    legacy = read_csv(TABLES / "scene_features_crossing_v5_2_regression29_20261013.csv")
    current = read_csv(TABLES / "scene_features_longitudinal_v7_replay29_20261015.csv")
    trajectories = read_json(TABLES / "crossing_v5_2_regression29_trajectory_20261013.json")
    for rows in (legacy, current, trajectories, inventory["rows"]):
        validate_scope(names, rows, partition)
    if parent["names"] != names or parent["tokens"] != [partition[n]["scene_token"] for n in names]:
        raise ValueError("Approved parent order or identity mismatch")
    for path in [INVENTORY, PARENT, CAPABILITY, Path(__file__),
                 ROOT / "logs/test_collect_human_evidence_20261024.py",
                 DATA / "v1.0-trainval/category.json", DATA / "v1.0-trainval/instance.json"]:
        records[str(path.resolve())] = file_record(path)
    for location in sorted({p["log_location"] for p in partition.values()}):
        path = DATA / "maps/expansion" / f"{location}.json"
        records[str(path.resolve())] = file_record(path)
    dist = importlib.metadata.distribution("nuscenes-devkit")
    path = Path(dist.locate_file("nuscenes/map_expansion/map_api.py"))
    records[str(path.resolve())] = file_record(path)
    return inventory, partition, legacy, current, trajectories, list(records.values())


def selected_metadata(partition, trajectories):
    scenes = {row["token"]: row for row in table_records("scene")
              if row["token"] in {p["scene_token"] for p in partition.values()}}
    samples = {row["token"]: row for row in table_records("sample") if row["scene_token"] in scenes}
    for track in trajectories:
        scene = scenes[track["scene_token"]]
        part = partition[track["scene_name"]]
        if scene["name"] != track["scene_name"] or scene["log_token"] != part["log_token"]:
            raise ValueError("Raw scene identity/log mismatch")
        token, seen, ordered = scene["first_sample_token"], set(), []
        while token:
            if token in seen or token not in samples or samples[token]["scene_token"] != scene["token"]:
                raise ValueError("Invalid selected sample chain")
            seen.add(token)
            sample = samples[token]
            if sample["prev"] != (ordered[-1]["token"] if ordered else ""):
                raise ValueError("Sample chain is not reciprocal")
            sample["index"] = len(ordered)
            ordered.append(sample)
            token = sample["next"]
        if (len(ordered) != scene["nbr_samples"] or len(ordered) != len(track["times"])
                or ordered[-1]["token"] != scene["last_sample_token"]):
            raise ValueError("Selected sample chain count/end mismatch")
        times = [s["timestamp"] / 1e6 - ordered[0]["timestamp"] / 1e6 for s in ordered]
        if times != track["times"]:
            raise ValueError("Frozen/source sample time mismatch")
        if not all(len(track[key]) == len(times) for key in
                   ("ego_positions", "ego_yaws", "ego_speeds", "static_obstacle_flags")):
            raise ValueError("Incomplete frozen ego/context arrays")
    if len(samples) != sum(len(t["times"]) for t in trajectories):
        raise ValueError("Selected scene contains samples outside its frozen chain")
    # Decode shared records, but gate sample membership before retaining target data.
    selected = [row for row in table_records("sample_annotation") if row["sample_token"] in samples]
    wanted_instances = {row["instance_token"] for row in selected}
    categories = {row["token"]: row["name"] for row in table_records("category")}
    instances = {row["token"]: row for row in table_records("instance")
                 if row["token"] in wanted_instances}
    instance_categories = {token: categories[row["category_token"]] for token, row in instances.items()}
    humans = select_humans(selected, {k: v["scene_token"] for k, v in samples.items()}, instance_categories)
    validate_human_chains(humans, samples)
    grouped = {}
    for row in humans.values():
        grouped.setdefault(row["instance_token"], []).append(row)
    for token, rows in grouped.items():
        identity = instances[token]
        if (identity["nbr_annotations"] != len(rows)
                or identity["first_annotation_token"] not in humans
                or identity["last_annotation_token"] not in humans
                or humans[identity["first_annotation_token"]]["instance_token"] != token
                or humans[identity["last_annotation_token"]]["instance_token"] != token
                or humans[identity["first_annotation_token"]]["prev"]
                or humans[identity["last_annotation_token"]]["next"]):
            raise ValueError("Raw instance identity/count/chain endpoints mismatch")
    return samples, humans, {token: instances[token] for token in grouped}


class SelectedTables:
    def __init__(self, samples, humans):
        self.tables = {"sample": samples, "sample_annotation": humans}

    def get(self, table, token):
        return self.tables[table][token]


def collect_scene(track, baseline, samples, humans, map_obj, helpers):
    import numpy as np
    rules = rules_module()
    ordered = sorted((s for s in samples.values() if s["scene_token"] == track["scene_token"]),
                     key=lambda s: s["index"])
    timestamps = [s["timestamp"] / 1e6 for s in ordered]
    by_sample = {s["token"]: [] for s in ordered}
    for ann in humans.values():
        if ann["sample_token"] in by_sample:
            by_sample[ann["sample_token"]].append(ann)
    flags = {key: [False] * len(ordered) for key in
             ("nearby", "front", "path", "crossing", "same_lane",
              "same_direction", "observed", "crosswalk", "crosswalk_nearby")}
    cache, target_tracks, candidates = {}, {}, []
    adapter = SelectedTables(samples, humans)
    minimum, minimum_time, minimum_anchor = float("inf"), -1.0, None
    for index, sample in enumerate(ordered):
        x, y = track["ego_positions"][index]
        yaw, ego_speed = track["ego_yaws"][index], track["ego_speeds"][index]
        near_crosswalk = bool(map_obj.get_records_in_radius(x, y, 8, ["ped_crossing"])["ped_crossing"])
        for ann in by_sample[sample["token"]]:
            position = ann["translation"][:2]
            vx, vy = helpers["compute_ann_velocity_xy"](adapter, ann)
            forward, lateral = helpers["ego_frame_delta"](position, x, y, yaw)
            vf, vl = helpers["ego_frame_vector"]((vx, vy), yaw)
            relation = rules.classify_vru_lane_relation(forward, lateral, vf, vl)
            mapped_used = False
            if relation.same_lane:
                mapped = helpers["mapped_vru_lane_relation"](map_obj, x, y, position, (vx, vy), cache)
                if mapped is not None:
                    relation, mapped_used = mapped, True
            front = -5.0 <= forward <= 30.0 and abs(lateral) <= 8.0
            path = bool(front and rules.is_vru_path_conflict(forward, lateral, vf, vl, ego_speed))
            crossing = bool(front and rules.is_vru_crossing_exposure(forward, lateral, vl))
            nearby = float(np.hypot(position[0] - x, position[1] - y)) < 20.0
            for key, value in (("nearby", nearby), ("front", front), ("path", path),
                               ("crossing", crossing), ("same_lane", relation.same_lane),
                               ("same_direction", relation.same_direction)):
                flags[key][index] |= bool(value)
            row = {key: ann.get(key) for key in
                   ("token", "sample_token", "instance_token", "category_name", "prev", "next",
                    "translation", "rotation", "size", "visibility_token", "attribute_tokens")}
            row.update(index=index, timestamp_us=sample["timestamp"], time_s=track["times"][index],
                       velocity_xy=[float(vx), float(vy)],
                       velocity_method="next" if ann["next"] else "prev" if ann["prev"] else "zero_no_neighbor",
                       forward_m=float(forward), lateral_m=float(lateral),
                       forward_speed_mps=float(vf), lateral_speed_mps=float(vl),
                       ego_speed_mps=float(ego_speed), front_band=bool(front),
                       raw_path_candidate=path, crossing_exposure=crossing,
                       mapped_lane_relation_used=mapped_used, same_lane=bool(relation.same_lane),
                       same_direction=bool(relation.same_direction))
            target_tracks.setdefault(ann["instance_token"], []).append(row)
            if path:
                candidates.append({"index": index, "annotation_token": ann["token"],
                                   "instance_token": ann["instance_token"], "time_s": track["times"][index]})
        flags["crosswalk"][index] = near_crosswalk and flags["path"][index]
        flags["crosswalk_nearby"][index] = near_crosswalk and flags["nearby"][index]
    for candidate in candidates:
        index = candidate["index"]
        ann = humans[candidate["annotation_token"]]
        future, facts = future_window(ann, humans, samples, 8.0, ordered[-1]["timestamp"])
        positions = [a["translation"][:2] for a in future]
        times = [samples[a["sample_token"]]["timestamp"] / 1e6 for a in future]
        closest = rules.synchronized_path_closest_approach(
            track["ego_positions"], timestamps, positions, times, timestamps[index], horizon=8.0)
        distance = float(closest.distance)
        if distance < minimum:
            minimum = distance
            minimum_time = timestamps[index] - timestamps[0] + closest.relative_time
            minimum_anchor = ann["token"]
        lane_checks, enters_lane = [], False
        for actor, time in zip(future, times):
            ego_index = int(np.argmin(np.abs(np.asarray(timestamps) - time)))
            ego_position = track["ego_positions"][ego_index]
            position = actor["translation"][:2]
            if np.linalg.norm(np.asarray(ego_position) - np.asarray(position)) > 10.0:
                continue
            geometry = helpers["mapped_actor_lane_geometry"](
                map_obj, *ego_position, position, cache)
            relation = helpers["mapped_vru_lane_relation"](
                map_obj, *ego_position, position, (0.0, 0.0), cache)
            lane_checks.append({"annotation_token": actor["token"], "ego_index": ego_index,
                                "ego_lane_center_distance_m": float(geometry[0]) if geometry else None,
                                "same_lane": bool(relation.same_lane) if relation is not None else None})
            if relation is not None and relation.same_lane:
                enters_lane = True
                break
        relevant = bool(rules.is_observed_vru_relevant(distance, enters_lane))
        flags["observed"][index] |= relevant
        point_layers = map_obj.layers_on_point(*ann["translation"][:2],
                                              ["walkway", "ped_crossing", "lane", "road_segment"])
        candidate.update(
            category=ann["category_name"], future_annotation_tokens=[a["token"] for a in future],
            future=facts, closest_distance_m=distance if math.isfinite(distance) else None,
            closest_relative_time_s=float(closest.relative_time),
            legacy_enters_ego_lane=enters_lane, legacy_observed_relevant=relevant,
            lane_checks_until_first_entry=lane_checks, current_point_layers=point_layers,
            lane_connector_point_query="not_queried", physical_isolation="unknown")
    values = summarize_human_flags(
        flags, timestamps, minimum, minimum_time, track["static_obstacle_flags"],
        bool(int(baseline["ego_evasive_lane_change_flag"])))
    return {"scene_name": track["scene_name"], "scene_token": track["scene_token"],
            "frame_count": len(ordered), "human_tracks": target_tracks,
            "candidate_anchors": candidates, "frame_flags": flags,
            "legacy_vru_reproduction": values, "minimum_distance_anchor": minimum_anchor,
            "minimum_is_no_candidate_fill": not math.isfinite(minimum),
            "frozen_vehicle_context": {"ego_evasive_lane_change_flag":
                                      int(baseline["ego_evasive_lane_change_flag"]),
                                      "static_obstacle_flags": track["static_obstacle_flags"]}}


def compare_baseline(scene, old, current, columns):
    mismatches = []
    if set(scene["legacy_vru_reproduction"]) != set(columns):
        raise ValueError("VRU reproduction field set mismatch")
    for column in columns:
        actual = scene["legacy_vru_reproduction"][column]
        for label, row in (("v5.2", old), ("v7", current)):
            expected = float(row[column])
            if not math.isfinite(expected) or not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12):
                mismatches.append({"scene": scene["scene_name"], "field": column,
                                   "baseline": label, "expected": expected, "actual": actual})
    return mismatches


def render_cards(evidence):
    scenes = evidence["scenes"]
    lines = ["# 行人目标证据补充（固定开发29条）", "",
             "任务日期：2026-10-24。本件是目标身份与原逻辑复现，不是新特征、准确率或安全标签。", "",
             f"- 保存{sum(len(s['human_tracks']) for s in scenes)}个行人标注实例，"
             f"{sum(len(t) for s in scenes for t in s['human_tracks'].values())}条标注记录。",
             f"- 原始预测候选覆盖{sum(any(s['frame_flags']['path']) for s in scenes)}场景/"
             f"{sum(sum(s['frame_flags']['path']) for s in scenes)}场景帧；"
             f"共{sum(len(s['candidate_anchors']) for s in scenes)}个目标帧，不混同独立样本。",
             "- 22个相关字段按原规则、冻结自车与车辆上下文条件复现；与v5.2/v7逐列对照。",
             "- 全链指片段内已有标注链，不是连续真值、完整视野或片段外轨迹。", "",
             "## 原规则候选身份与时段", "",
             "| 场景 | 行人实例（前12位） | 原候选时刻s | 原观测相关目标帧数 |",
             "| --- | --- | --- | --- |"]
    for scene in scenes:
        groups = {}
        for anchor in scene["candidate_anchors"]:
            groups.setdefault(anchor["instance_token"], []).append(anchor)
        for instance, anchors in groups.items():
            lines.append(f"| {scene['scene_name']} | {instance[:12]} | "
                         + ", ".join(f"{a['time_s']:.3f}" for a in anchors)
                         + f" | {sum(a['legacy_observed_relevant'] for a in anchors)} |")
    lines += ["", "## 必须保留的解释边界", "",
              "- 0151本次列出的都是human目标，不能把此前自行车/护栏反馈自动移给它们。",
              "- 0102可按目标与时刻比对旧三帧诊断；walkway位置不等于护栏识别或实际横穿。",
              "- 原crosswalk冲突是自车8m半径横道与预测候选同帧，并不保证目标在横道内。",
              "- 最近距离是同步中心点距离；原观测进入车道是有限地图几何，不是路线占用/因果/危险证明。",
              "- future记录实际窗口跨度、片段剩余时间、目标链剩余时间、下一括界样本及间隔缺帧数。",
              "- 原规则仍可能使用不足8s窗口；没有把缺口、护栏未知或片段结束当成安全。",
              "- 原持续性/场景汇总可能跨目标合并；本件保留目标帧，不据此修改既有数值。",
              "- 未输出图像或目标框，新增目标身份不是人工视觉确认；后续可仅复核具体目标时段。",
              "- 未做700条完整提取、聚类/评分/排名、评价集语义处理或正式评测。", "",
              "## 机器证据", "",
              "[完整目标链与候选](../../HDBSCAN/tables/human_evidence29_20261024.json)",
              "[来源与复现核验](../../HDBSCAN/tables/human_evidence29_20261024_report.json)", ""]
    return "\n".join(lines)


def write_json_new(path, value):
    with Path(path).open("x", encoding="utf8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def check_only(expected_sha):
    if not expected_sha:
        raise ValueError("Original --expected-report-sha is required")
    verify_records([{"path": str(REPORT), "sha256": expected_sha}])
    report = read_json(REPORT)
    verify_records(report["inputs"] + report["outputs"])
    evidence = read_json(EVIDENCE)
    if report["stage"] != STAGE or evidence["stage"] != STAGE or report["mismatches"]:
        raise ValueError("Wrong stage or failed reproduction")
    print(json.dumps({"check_only": "passed", "report_sha256": expected_sha,
                      "scenes": len(evidence["scenes"]), "fit": False}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    parser.add_argument("--expected-report-sha")
    args = parser.parse_args()
    if args.check_only:
        check_only(args.expected_report_sha)
        return
    if args.expected_report_sha:
        parser.error("--expected-report-sha is only valid with --check-only")
    inventory, partition, legacy, current, trajectories, sources = prepare()
    print(f"Preflight: frozen29/source bindings verified; stage={STAGE}", flush=True)
    if args.preflight:
        return
    ensure_new([EVIDENCE, REPORT, CARDS])
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    print("Reading selected sample/human metadata; no image/ego-pose/full SDK load", flush=True)
    samples, humans, instances = selected_metadata(partition, trajectories)
    from nuscenes.map_expansion.map_api import NuScenesMap
    maps = {}
    helpers = load_helpers()
    by_old = {r["scene_name"]: r for r in legacy}
    by_current = {r["scene_name"]: r for r in current}
    expected_rows = {r["scene_name"]: r for r in inventory["rows"]}
    results, mismatches = [], []
    for track in trajectories:
        name = track["scene_name"]
        location = partition[name]["log_location"]
        if location not in maps:
            maps[location] = NuScenesMap(dataroot=str(DATA), map_name=location)
        scene = collect_scene(track, by_old[name], samples, humans, maps[location], helpers)
        scene["human_instance_sources"] = {token: instances[token] for token in scene["human_tracks"]}
        errors = compare_baseline(scene, by_old[name], by_current[name], inventory["unchanged_vru_columns"])
        if sum(scene["frame_flags"]["path"]) != expected_rows[name]["raw_candidate_frames"]:
            errors.append({"scene": name, "field": "raw_candidate_frames", "mismatch": True})
        mismatches.extend(errors)
        results.append(scene)
        print(f"{len(results):02d}/29 {name}: humans={len(scene['human_tracks'])}, "
              f"raw_frames={sum(scene['frame_flags']['path'])}, "
              f"target_anchors={len(scene['candidate_anchors'])}, mismatches={len(errors)}", flush=True)
    if mismatches:
        print(json.dumps(mismatches, ensure_ascii=False, indent=2))
        raise ValueError("Legacy reproduction failed; final evidence files not written")
    verify_records(sources)
    evidence = {"stage": STAGE, "authorization": "2026-10-24 同意先补行人目标证据",
                "human_scope": "category_name.startswith('human'); bicycles excluded",
                "full_feature_extraction": False, "fit_allowed": False, "evaluation_used": False,
                "map_locations_from": "frozen development partition",
                "scenes": results}
    write_json_new(EVIDENCE, evidence)
    with CARDS.open("x", encoding="utf8", newline="\n") as handle:
        handle.write(render_cards(evidence))
    report = {"stage": STAGE, "created_at_host_utc": datetime.now(timezone.utc).isoformat(),
              "task_date_as_supplied": "2026-10-24 Asia/Shanghai", "command": sys.argv,
              "inputs": sources, "outputs": [file_record(EVIDENCE), file_record(CARDS)],
              "runtime": {"executable": sys.executable, "python": sys.version,
                          "packages": {name: importlib.metadata.version(name) for name in
                                       ("numpy", "nuscenes-devkit", "Shapely")},
                          "threads": {k: os.environ.get(k) for k in
                                      ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}},
              "scene_count": len(results), "columns": inventory["unchanged_vru_columns"],
              "comparisons": len(results) * len(inventory["unchanged_vru_columns"]) * 2,
              "comparison_abs_tolerance": 1e-12, "comparison_rel_tolerance": 0,
              "mismatches": mismatches, "old_inputs_unchanged": True,
              "new_human_metadata_extraction": True, "full_feature_extraction": False,
              "feature_rule_score_change": False, "fit": False, "evaluation_used": False,
              "semantic_acceptance": False,
              "shared_metadata_scan_disclosure": "Shared JSON bytes decoded sequentially; only approved "
              "29 sample annotations retained; only human geometry computed/output. No evaluation "
              "features, labels, media or scene-level evaluation semantics used."}
    write_json_new(REPORT, report)
    print(json.dumps({"status": "completed_evidence_requires_target_review",
                      "comparisons": report["comparisons"], "mismatches": 0,
                      "report_sha256": file_record(REPORT)["sha256"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
