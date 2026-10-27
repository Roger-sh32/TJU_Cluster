"""Explain existing human candidates; do not gate, relabel or regenerate features."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "logs/collect_human_evidence_20261024.py"
COLLECTOR_SHA = "f761bce11adcad5c3c00238d10026cb26467e0bfe5b6241192aff16467ad332c"
PARENT_SHA = "9035ce0ea61084e5c4fa1c9f195a2c73a15b29680cb423e90e3a0e5dbdb02e18"
INDEX = ROOT / "HDBSCAN/tables/human_candidate_causes35_20261024.json"
DOCUMENT = ROOT / "outputs/人工复核/行人候选逐目标原因对照_20261024.md"
STAGE = "development_human_candidate_cause_analysis_only"
_CONTRACT = None


def contract():
    global _CONTRACT
    if _CONTRACT is None:
        if hashlib.sha256(COLLECTOR.read_bytes()).hexdigest() != COLLECTOR_SHA:
            raise ValueError("Original collector source changed")
        spec = importlib.util.spec_from_file_location("human_evidence_contract", COLLECTOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CONTRACT = module
    return _CONTRACT


def confirmation_reason(distance, lane_evidence):
    if distance is None or not math.isfinite(distance):
        return "distance_unknown"
    rules = contract().rules_module()
    within_original_limit = rules.is_observed_vru_relevant(distance, True)
    if lane_evidence and within_original_limit:
        return "original_observed_confirmed"
    if lane_evidence:
        return "distance_only_not_met"
    if within_original_limit:
        return "lane_evidence_only_not_met"
    return "both_original_conditions_not_met"


def prediction_details(row):
    closing = row["ego_speed_mps"] - row["forward_speed_mps"]
    nominal_time = row["forward_m"] / closing if closing > 0 and row["forward_m"] > 0 else None
    predicted_lateral = (row["lateral_m"] + row["lateral_speed_mps"] * nominal_time
                         if nominal_time is not None else None)
    formula = contract().rules_module().is_vru_path_conflict(
        row["forward_m"], row["lateral_m"], row["forward_speed_mps"],
        row["lateral_speed_mps"], row["ego_speed_mps"])
    return {"closing_speed_mps": float(closing), "nominal_overlap_time_s": nominal_time,
            "predicted_lateral_m": predicted_lateral, "original_formula_result": bool(formula),
            "model_assumption": "anchor ego heading and relative velocity, not observed future route"}


def analyze_scene(scene):
    flat = [row for track in scene["human_tracks"].values() for row in track]
    rows = {row["token"]: row for row in flat}
    if len(rows) != len(flat):
        raise ValueError("Duplicate human annotation identity")
    result, seen = [], set()
    for anchor in scene["candidate_anchors"]:
        token = anchor["annotation_token"]
        row = rows[token]
        if (token in seen or anchor["instance_token"] != row["instance_token"]
                or anchor["index"] != row["index"] or anchor["time_s"] != row["time_s"]
                or not row["category_name"].startswith("human") or not row["raw_path_candidate"]):
            raise ValueError("Candidate identity/category/raw flag mismatch")
        seen.add(token)
        prediction = prediction_details(row)
        if not prediction["original_formula_result"]:
            raise ValueError("Original prediction does not reproduce")
        front = -5 <= row["forward_m"] <= 30 and abs(row["lateral_m"]) <= 8
        if not front:
            raise ValueError("Original production front band does not reproduce")
        distance = anchor["closest_distance_m"]
        reason = confirmation_reason(distance, anchor["legacy_enters_ego_lane"])
        if (reason == "original_observed_confirmed") != anchor["legacy_observed_relevant"]:
            raise ValueError("Original observed confirmation mismatch")
        future = anchor["future"]
        if (future["physical_barrier_evidence"] != "unknown"
                or future["future_safety"] != "not_inferred" or future["extrapolated"]):
            raise ValueError("Unknown future/isolation was promoted")
        result.append({
            "scene_name": scene["scene_name"], "index": row["index"], "time_s": row["time_s"],
            "annotation_token": token, "instance_token": row["instance_token"],
            "category": row["category_name"], "forward_m": row["forward_m"],
            "lateral_m": row["lateral_m"], "lateral_speed_mps": row["lateral_speed_mps"],
            "prediction": prediction, "closest_distance_m": distance,
            "legacy_enters_ego_lane": anchor["legacy_enters_ego_lane"],
            "legacy_observed_relevant": anchor["legacy_observed_relevant"],
            "original_reason": reason, "point_layers": anchor["current_point_layers"],
            "future": future, "physical_isolation": "unknown", "safety_label_assigned": False,
        })
    if seen != {r["token"] for r in flat if r["raw_path_candidate"]}:
        raise ValueError("Raw candidate annotations dropped or added")
    raw_indices = {r["index"] for r in result}
    observed_indices = {r["index"] for r in result if r["legacy_observed_relevant"]}
    for key, indices in (("path", raw_indices), ("observed", observed_indices)):
        if indices != {i for i, flag in enumerate(scene["frame_flags"][key]) if flag}:
            raise ValueError(f"Original {key} frame aggregation mismatch")
    return result


LABELS = {
    "original_observed_confirmed": "原观测两条件均成立",
    "distance_only_not_met": "原距离条件未满足",
    "lane_evidence_only_not_met": "原程序未获车道进入依据",
    "both_original_conditions_not_met": "原距离和车道依据均未满足",
    "distance_unknown": "原距离未知",
}


def render(rows):
    counts = Counter(row["original_reason"] for row in rows)
    lines = ["# 行人候选逐目标原因对照", "",
             "只读补证侧录：35个目标帧，不是35个独立场景或专家标签。本件不产生新过滤判定。", "",
             "## 原程序条件拆分", "",
             "| 原程序状态 | 目标帧数 |", "| --- | ---: |"]
    for key, label in LABELS.items():
        lines.append(f"| {label} | {counts[key]} |")
    lines += ["", "确认条件沿用原is_observed_vru_relevant：同步中心点距离不超过6m，且原地图查询获得车道进入依据。",
              "“未获依据”不等于实际不进入：原查询有距离/地图/观测窗口限制；这里没有为它补新规则。",
              "", "## 逐目标帧", "",
              "| 场景 | 时刻s | 行人实例前12位 | 原线性重合时间s | 预测横向m | 原最近距离m | 原程序状态 |",
              "| --- | ---: | --- | ---: | ---: | ---: | --- |"]
    for row in rows:
        prediction = row["prediction"]
        fmt = lambda v: f"{v:.3f}" if v is not None else "未知"
        lines.append(f"| {row['scene_name']} | {row['time_s']:.3f} | {row['instance_token'][:12]} | "
                     f"{fmt(prediction['nominal_overlap_time_s'])} | {fmt(prediction['predicted_lateral_m'])} | "
                     f"{fmt(row['closest_distance_m'])} | {LABELS[row['original_reason']]} |")
    lines += ["", "## 怎样使用", "",
              "- 线性重合时间/预测横向位置仅解释原公式；没有跟随自车未来转向，不是预测碰撞的事实。",
              "- 0151包含5个人类目标，不是此前复核的自行车；4候选场景帧中一帧有两名行人。",
              "- 0102三帧指同一walkway上的同一行人；地图位置不是护栏，也不证明实际横穿。",
              "- 0011和0067的原观测确认目标帧原样保留，没有因walkway、未来不足或其他目标而清零。",
              "- 原观测确认属于程序正例，不是逐目标人工确认，更不说明同场景每个人都构成交互。",
              "- 距离较大或原程序未获车道进入依据，均不自动转成安全、无交互或可删除候选。",
              "- 所有35锚点只保留实际标注和窗口界限；未补连续8s轨迹、未推断护栏或片段外安全。",
              "- 对未来路线的占用、历史响应/让行、物理隔离及特征重新分层仍待单独设计，不在本件实现。",
              "", "## 产出与来源", "",
              "[原行人目标证据](行人目标证据补充_20261024.md)",
              "[逐帧明细与来源绑定](../../HDBSCAN/tables/human_candidate_causes35_20261024.json)", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    parser.add_argument("--expected-sha")
    args = parser.parse_args()
    tools = contract()
    if args.check_only:
        if not args.expected_sha:
            raise ValueError("Original analysis index digest required")
        tools.verify_records([{"path": str(INDEX), "sha256": args.expected_sha}])
        index = tools.read_json(INDEX)
        tools.verify_records(index["inputs"] + index["outputs"])
        if index["stage"] != STAGE or index["safety_labels"] or index["rule_change"]:
            raise ValueError("Invalid analysis status")
        print("Analysis original-hash check passed; no extraction or recomputation")
        return
    if args.expected_sha:
        parser.error("--expected-sha requires --check-only")
    tools.ensure_new([INDEX, DOCUMENT])
    tools.verify_records([{"path": str(tools.REPORT), "sha256": PARENT_SHA}])
    parent = tools.read_json(tools.REPORT)
    sources = (parent["inputs"] + parent["outputs"] + [tools.file_record(tools.REPORT),
               tools.file_record(__file__),
               tools.file_record(ROOT / "logs/test_analyze_human_candidates_20261024.py")])
    tools.verify_records(sources)
    evidence = tools.read_json(tools.EVIDENCE)
    if evidence["stage"] != tools.STAGE or len(evidence["scenes"]) != 29:
        raise ValueError("Wrong parent evidence scope")
    rows = [row for scene in evidence["scenes"] for row in analyze_scene(scene)]
    if len(rows) != 35 or len({r["instance_token"] for r in rows}) != 15:
        raise ValueError("Original candidate membership/count mismatch")
    tools.verify_records(sources)
    with DOCUMENT.open("x", encoding="utf8", newline="\n") as handle:
        handle.write(render(rows))
    index = {"stage": STAGE, "created_at_host_utc": datetime.now(timezone.utc).isoformat(),
             "command": sys.argv, "executable": sys.executable, "inputs": sources,
             "outputs": [tools.file_record(DOCUMENT)], "rows": rows,
             "counts": dict(Counter(r["original_reason"] for r in rows)),
             "candidate_target_frames": len(rows), "candidate_instances": 15,
             "safety_labels": False, "rule_change": False, "reextraction": False,
             "fit": False, "evaluation_used": False, "semantic_acceptance": False}
    tools.write_json_new(INDEX, index)
    print({"status": "completed_readonly_cause_analysis", "counts": index["counts"],
           "original_index_sha256": tools.file_record(INDEX)["sha256"]})


if __name__ == "__main__":
    main()
