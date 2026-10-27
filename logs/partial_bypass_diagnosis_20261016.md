# 0552 部分占道绕行只读诊断

日期：2026-10-16，Asia/Shanghai。按用户要求继续推进可独立完成的诊断，设计/目标验收继续暂挂。前一目标轮新增数据能力核验材料，属于已完成的证据进展，不是无进展等待。

## 范围与执行

对象是已有人工作答的 `scene-0552` 后段部分占道绕行漏表达。仅从原 v7 冻结台账/特征和 v5.2 冻结轨迹解释当前规则，保留 `scene-0011` 短暂静态避障与 `scene-0669` 原始偏离保护作为已见开发控制。不抽新场景，不把这三条当独立验证样本，也不改变任何规则。

先执行已有 v7 的 `check`，固定 ORIGINAL protocol SHA256 `ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d`：session55177 退出0，父链来源/运行环境/输出封印、原29条精确重放及正式拟合拒绝通过。该旧检查会按既有协议流式核对29条开发成员的官方标注身份，不分析评价语义；不是重复提取或重跑候选 `run`。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/longitudinal_v7_replay_20261015.py check --expected-protocol-sha ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d
```

新诊断主体仅读以下冻结文件及必要代码/反馈。先固定原比较报告摘要，再校验其绑定输出和协议输入；不刷新封印。三个开发成员的31个纵向字段及完整候选轨迹必须与旧结果精确相等才输出证据。静态重车目录包括 truck/trailer/construction 的所有后段可用轨迹，不只挑中想要的目标。

新增的包围框横向投影仅用于说明“中心条件”和“有尺寸物体”不同，使用原 `SAME_PATH_HALF_WIDTH`，不写回特征或用作过滤。它不代表道路车道、计划路线、连续扫掠冲突或风险真值；纵向、时间和因果条件不由这一维投影证明。

## 可复核诊断配方

在根目录运行下面的 PowerShell 块。默认只在新证据文件不存在时保存一次；`--check-only` 在内存重算并核对已保存内容，不覆盖文件。只允许本块定义的3个开发控制，不访问图片、拟合模型或新提特征。

```powershell
@'
import csv, hashlib, inspect, json, math, sys
from pathlib import Path
from HDBSCAN.scripts import longitudinal_candidate_v7 as module
from HDBSCAN.scripts import scene_feature_rules as rules

ROOT = Path.cwd()
FOCUS = ["scene-0552", "scene-0011", "scene-0669"]
REPORT = Path("HDBSCAN/tables/longitudinal_v7_replay29_comparison_20261015.json")
PROTOCOL = Path("HDBSCAN/tables/longitudinal_v7_replay29_protocol_20261015.json")
OUTPUT = Path("logs/partial_bypass_evidence_20261016.json")
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))
def verify(record):
    path = Path(record["path"])
    if path.stat().st_size != record["bytes"] or digest(path) != record["sha256"]:
        raise RuntimeError("Frozen source/output mismatch: " + str(path))
def bind(path):
    path = Path(path)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest(path)}

assert digest(REPORT) == "b7df6d51107f04cf3b7fdf9142fcddf24cec1a997e99277555ce3eab4872bdf3"
assert digest(PROTOCOL) == "ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d"
report, protocol = load(REPORT), load(PROTOCOL)
for record in report["outputs"] + protocol["inputs"]:
    verify(record)
assert set(FOCUS) <= set(protocol["names"])
tracks_path = Path("HDBSCAN/tables/crossing_v5_2_regression29_trajectory_20261013.json")
ledger_path = Path("HDBSCAN/tables/longitudinal_v7_replay29_ledger_20261015.json")
features_path = Path("HDBSCAN/tables/scene_features_longitudinal_v7_replay29_20261015.csv")
tracks = {a["scene_name"]: a for a in load(tracks_path) if a["scene_name"] in FOCUS}
saved = {a["scene_name"]: a for a in load(ledger_path)["scenes"] if a["scene_name"] in FOCUS}
with features_path.open(encoding="utf8", newline="") as stream:
    rows = {row["scene_name"]: row for row in csv.DictReader(stream) if row["scene_name"] in FOCUS}
evidence = []
for name in FOCUS:
    audit, prior = tracks[name], saved[name]
    context = {k: float(rows[name][k]) for k in ("traffic_light_control_density", "crossing_vehicle_exposure_ratio", "intersection_stop_ratio", "left_turn_cross_traffic_interaction_ratio")}
    fields, trace = module.summarize(audit, prior["ledger"], context, prior["rejected"])
    for key, value in fields.items():
        expected = rows[name][key] if isinstance(value, str) else float(rows[name][key])
        assert value == expected, (name, key, value, expected)
    assert trace == prior["candidate"], name
    assert audit["scene_token"] == prior["scene_token"] == rows[name]["scene_token"]
    times = audit["times"]
    static = rules.summarize_events(trace["static_flags"], times)
    blocked = rules.summarize_events(trace["blocked_flags"], times)
    anchors = [{"index": i, "scene_time_s": times[i], "selected": trace["selected"][i]} for i, flag in enumerate(trace["static_flags"]) if flag]
    first = trace["first_static_index"]
    blocked_indices = [i for i, flag in enumerate(trace["blocked_flags"]) if flag]
    first_block = blocked_indices[0] if blocked_indices else -1
    defaults = inspect.signature(rules.is_evasive_lane_change).parameters
    shift, turn = fields["ego_evasive_lateral_shift"], fields["ego_evasive_net_heading_change"]
    strict_components = {
        "positive_static_event_count": static.count > 0,
        "sustained_static_branch": static.max_duration >= defaults["minimum_stationary_duration"].default,
        "brief_shift_branch": 4.0 <= shift <= defaults["maximum_brief_lateral_shift"].default,
        "brief_heading_branch": turn <= 0.10,
        "brief_distance_branch": fields["stationary_lead_min_dist"] <= defaults["maximum_brief_obstacle_distance"].default,
        "shift_in_strict_range": defaults["minimum_lateral_shift"].default <= shift <= defaults["maximum_lateral_shift"].default,
        "heading_in_strict_range": turn <= defaults["maximum_net_heading_change"].default,
    }
    recombined = strict_components["positive_static_event_count"] and (strict_components["sustained_static_branch"] or all(strict_components[k] for k in ("brief_shift_branch", "brief_heading_branch", "brief_distance_branch"))) and strict_components["shift_in_strict_range"] and strict_components["heading_in_strict_range"]
    assert int(recombined) == fields["ego_evasive_lane_change_flag"]
    target_rows = []
    for instance, track in sorted(audit["vehicle_tracks"].items()):
        if name != "scene-0552" or track[0]["category"] not in ("vehicle.truck", "vehicle.trailer", "vehicle.construction"):
            continue
        maximum = audit["instance_max_speeds"][instance]
        permanent = maximum <= 0.5 or (instance in audit["bounded_stationary_instances"] and maximum < 1.0)
        frames = []
        for point in track:
            i = point["index"]
            if times[i] < 14.0:
                continue
            vx, vy = point["velocity"]
            vf = vx*math.cos(audit["ego_yaws"][i]) + vy*math.sin(audit["ego_yaws"][i])
            vl = -vx*math.sin(audit["ego_yaws"][i]) + vy*math.cos(audit["ego_yaws"][i])
            interaction = rules.classify_vehicle_interaction(point["forward"], point["lateral"], vf, vl, audit["ego_speeds"][i])
            conditions = {"forward_window": 0.0 < point["forward"] < 80.0,
                          "center_lateral": abs(point["lateral"]) <= rules.SAME_PATH_HALF_WIDTH,
                          "forward_velocity": vf > -0.5, "lateral_velocity": abs(vl) <= 1.5}
            assert bool(interaction.same_path) == all(conditions.values())
            candidates = [c for c in prior["ledger"][i] if c["instance_token"] == instance]
            assert len(candidates) == int(interaction.same_path)
            selected = trace["selected"][i]
            half_extent = (abs(math.cos(point["heading_delta"]))*point["width"] + abs(math.sin(point["heading_delta"]))*point["length"])/2
            low, high = point["lateral"] - half_extent, point["lateral"] + half_extent
            frames.append({"index": i, "scene_time_s": times[i], "forward_m": point["forward"], "center_lateral_m": point["lateral"],
                "length_m": point["length"], "width_m": point["width"], "heading_delta_rad": point["heading_delta"],
                "speed_mps": math.hypot(vx, vy), "ego_speed_mps": audit["ego_speeds"][i],
                "same_path_components": conditions, "same_path": bool(interaction.same_path), "ledger_candidate": candidates[0] if candidates else None,
                "selected": bool(selected is not None and selected["instance_token"] == instance),
                "static_selected": bool(trace["static_flags"][i] and selected is not None and selected["instance_token"] == instance),
                "body_lateral_projection_m": [low, high],
                "body_projection_intersects_lateral_strip_only": bool(low <= rules.SAME_PATH_HALF_WIDTH and high >= -rules.SAME_PATH_HALF_WIDTH)})
        if frames:
            target_rows.append({"instance_token": instance, "category": track[0]["category"], "max_scene_speed_mps": maximum,
                "bounded_stationary": instance in audit["bounded_stationary_instances"], "permanent_static_by_existing_rule": bool(permanent), "frames": frames,
                "human_blocking_truck_identity_confirmed": False})
    local = []
    for anchor in anchors:
        i = anchor["index"]
        local.append({"index": i, "instance_token": anchor["selected"]["instance_token"], "available_future_s": times[-1]-times[i],
            "window_s_requested": 10.0, "horizon_complete": times[-1]-times[i] >= 10.0,
            "existing_shift_function_m": rules.lateral_shift_after_index(audit["ego_positions"], times, i, audit["ego_yaws"][i], 10.0),
            "existing_heading_function_rad": rules.net_heading_change_after_index(audit["ego_yaws"], times, i, audit["ego_yaws"][i], 10.0)})
    evidence.append({"scene_name": name, "scene_token": audit["scene_token"], "reproduced_field_count": len(fields), "reproduced_fields": fields,
        "static_summary": static._asdict(), "blocked_summary": blocked._asdict(), "static_anchors": anchors,
        "strict_condition_components": strict_components, "first_static_index": first, "first_blocked_index": first_block,
        "existing_raw_deviation": trace["raw_deviation"], "existing_context_supported": rules.is_route_deviation_context_supported(**{
            "traffic_light_density": context["traffic_light_control_density"], "crossing_exposure_ratio": context["crossing_vehicle_exposure_ratio"],
            "intersection_stop_ratio": context["intersection_stop_ratio"], "left_turn_cross_traffic_ratio": context["left_turn_cross_traffic_interaction_ratio"]}),
        "existing_v7_scene_protection": prior["protected_context"], "static_anchor_local_windows_diagnostic_only": local,
        "heavy_tracks_after14s": target_rows})
inputs = [REPORT, PROTOCOL, tracks_path, ledger_path, features_path, Path(module.__file__), Path(rules.__file__), Path("logs/development_review_feedback10_20261014.md")]
result = {"version": "partial_bypass_readonly_20261016", "focus": FOCUS, "input_bindings": [bind(p) for p in inputs],
          "scope": "Frozen development replay diagnosis; body projection is one-dimensional debugging, not lane occupancy or conflict",
          "feature_updates": False, "threshold_updates": False, "human_target_acceptance": False, "evaluation_used": False, "scenes": evidence}
if "--check-only" in sys.argv:
    assert digest(OUTPUT) == "ea0b21f0e5d9970a140bc6173430817fbdef5aecbad3dd4aca400a90e06b2da7", "Original diagnostic evidence digest required"
    assert load(OUTPUT) == result, "Saved diagnostic evidence drift"
    print("CHECKED: 3 scenes x 31 fields and full selected traces exact; saved diagnosis identical")
else:
    with OUTPUT.open("x", encoding="utf8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print("SAVED: " + str(OUTPUT) + "; 3 scenes x 31 fields and full selected traces exact")
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'partial_bypass_diagnosis','exec'))"
```

执行主块将生成新诊断证据；仅检查时，在最后 Python 命令末尾追加 `--check-only`，或从本块提取 Python 原文后用同解释器 `-X utf8 -c <code> --check-only`。不运行旧版本的 `prepare/run`，不覆盖新旧输出。

## 状态与限制

本块已单次执行exit0，保存 `logs/partial_bypass_evidence_20261016.json`，75356字节，SHA256 `ea0b21f0e5d9970a140bc6173430817fbdef5aecbad3dd4aca400a90e06b2da7`。三条各31字段及完整候选轨迹精确重现。0552共5个类别符合目录范围的后段重车实例、52条可用目标帧；两程序静态大车均仅16.401s进入same_path，只有trailer被选中；本轮没有完成它们与人工卡车的身份绑定。

发现单帧static汇总约0.500s而blocked过滤使用0s，以及13.898s car首锚点跨入后续转向，产生22.542m固定朝向横移/0.976rad净转角。后段trailer重锚点运动查询仅作诊断，未来不满10s，不回写成新特征；上下文False也不是raw候选False的唯一原因。

读者报告：[0552部分占道绕行根因诊断](F:/Scene_cluster/outputs/人工复核/0552部分占道绕行根因诊断_20261016.md)。`--check-only`在内存精确重现已保存诊断，exit0；另以两个内存负例分别改变0552单字段与轨迹raw偏离位，均在写输出前按预期拒绝，证据文件摘要未变。这只验证诊断配方的相等性门控，不验证特征语义或归因。

独立窄审工具返回额度限制错误，未产生审查结果，不计作独立复核通过；本轮仅有主线程源码/数值/文档核查。该审查缺口留待工具可用时补齐，不自动换工具绕过限制，也不要求用户现在再次审核整场景。原HDBSCAN全套测试未在本轮重跑；生产实现没有改动。

阈值、特征、版本、模型、排序及评价设计均未改动，设计决定仍暂挂。新诊断为只读证据，不得因此推广候选或启动正式实验。

最终加入原始诊断摘要检查后，`--check-only`再次exit0；新报告/日志的本地链接、空白及本轮入口文档的`git diff --check`通过。原方法事实稿/证据索引、引文补注件/集成索引和原执行链路索引及其19项源/证据摘要均与已登记值相同。这不是全部历史文件或语义的重新验收。
