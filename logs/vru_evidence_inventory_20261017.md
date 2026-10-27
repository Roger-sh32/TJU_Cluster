# VRU开发证据与类别范围诊断

日期：2026-10-17，Asia/Shanghai。前轮序数评价准备是实际进展。本轮返回特征收敛E2，原计划比较0102/0151隔离候选与真实行人交互；检查发现冻结轨迹没有human轨迹，不能完成该逐目标重放。因此先核实输入证据缺口和类别范围，不以缺数据改写场景语义。

只读使用固定开发29的v5.2轨迹/CSV、v7比较/CSV、已冻结八场景诊断及当前源码。无需nuScenes元数据/图像，不加载SDK，不提取/拟合/评分/导出，不读评价语义，不改任何规则、阈值、字段或旧产物。

第一次查看轨迹结构错误地假定顶层为dict，实际是list，导致AttributeError及过量终端打印；只读命令失败，没有修改文件。后改用明确list结构、只打印选定键/计数。后续配方不输出整条轨迹或访问其他数据。

## 单次诊断配方

仅生成新JSON，拒绝覆盖；以后只读检查原摘要，不重新执行生成。

```powershell
@'
from pathlib import Path
import ast,csv,hashlib,json,math,datetime
root=Path.cwd()
out=root/"logs/vru_evidence_inventory_20261017.json"
assert not out.exists(),"Do not regenerate evidence"
def record(p):
    p=Path(p).resolve();b=p.read_bytes()
    return {"path":str(p),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(Path(p).read_text(encoding="utf8"))
pins={"HDBSCAN/tables/longitudinal_v7_replay29_comparison_20261015.json":"b7df6d51107f04cf3b7fdf9142fcddf24cec1a997e99277555ce3eab4872bdf3","HDBSCAN/tables/crossing_v5_2_regression29_trajectory_20261013.json":"1b8723d72ed3de9f2d90fca91acf59d3716245f343bc5019326a99e972dbfc60","HDBSCAN/tables/scene_features_crossing_v5_2_regression29_20261013.csv":"19108e421555355e82cc4d6ad41defc5f67e075ac8d99bf7db5e253659057333","HDBSCAN/tables/target_diagnosis8_20261012.json":"ca28a0801b7269cd61c91f11e7c9e6a8a2b1a57e4c5077d4f5063c1aa0a57df1","HDBSCAN/scripts/scene_feature_hdbscan_v5_2.py":"a34af552a0bdc396cec210aed1ebf63c5e20d75c0e084f987e51c1d3302e2974","HDBSCAN/scripts/scene_feature_rules.py":"6a21d3d56a08fe7ee60e9143dbb0aa1d3db02f573cfb4206eed17062c92e181d","HDBSCAN/scripts/feature_selection.py":"36cef6e7d7fed0226377555688e749e853faa777622112605d643b1c229103ee","HDBSCAN/scripts/corner_scoring.py":"18c9f88e48087017e5615f0639f13503b54d64335264d94df209fcbc7bbec620"}
for p,sha in pins.items():assert record(root/p)["sha256"]==sha,p
comp=load(root/"HDBSCAN/tables/longitudinal_v7_replay29_comparison_20261015.json")
bound=[comp["protocol"],*comp["outputs"]]
for r in bound:assert record(r["path"])==r
protocol=load(comp["protocol"]["path"])
trajectory=load(root/"HDBSCAN/tables/crossing_v5_2_regression29_trajectory_20261013.json")
assert isinstance(trajectory,list) and len(trajectory)==29
tracks={s["scene_name"]:s for s in trajectory}
def table(p):
    with Path(p).open(encoding="utf8",newline="") as f: rows=list(csv.DictReader(f))
    assert len({r["scene_name"] for r in rows})==len(rows)
    return {r["scene_name"]:r for r in rows}
old=table(root/"HDBSCAN/tables/scene_features_crossing_v5_2_regression29_20261013.csv")
current=table(next(r["path"] for r in comp["outputs"] if r["path"].endswith(".csv")))
assert set(old)==set(current)==set(tracks)==set(protocol["names"])
split_record=next(r for r in protocol["inputs"] if r["path"].endswith("evaluation_split_20260924.csv"))
assert record(split_record["path"])==split_record
partition=table(split_record["path"])
for name,row in current.items():
    assert partition[name]["split"]=="development"
    assert row["scene_token"]==partition[name]["scene_token"]==tracks[name]["scene_token"]
cols=[c for c in next(iter(old.values())) if c.startswith(("vru_","pedestrian_","same_lane_vru","same_direction_vru","obstacle_avoidance_vru","crosswalk_pedestrian"))]
assert len(cols)==22
for name in old:
    for c in cols:assert float(old[name][c])==float(current[name][c]),(name,c)
extractor=root/"HDBSCAN/scripts/scene_feature_hdbscan_v5_2.py"
tree=ast.parse(extractor.read_text(encoding="utf8"))
parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
branch_calls=[]
for n in ast.walk(tree):
    if not (isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="is_vru_path_conflict"):continue
    ancestors=[];x=n
    while x in parents:
        x=parents[x]
        if isinstance(x,ast.If):ancestors.append({"line":x.lineno,"test":ast.unparse(x.test),"in_true_body":any(n in ast.walk(b) for b in x.body)})
    branch_calls.append({"line":n.lineno,"ancestor_ifs":ancestors})
assert len(branch_calls)==1
assert any(r["test"]=="category.startswith('human')" and r["in_true_body"] for r in branch_calls[0]["ancestor_ifs"])
feature_tree=ast.parse((root/"HDBSCAN/scripts/feature_selection.py").read_text(encoding="utf8"))
whitelist=ast.literal_eval(next(n.value for n in feature_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="CLUSTERING_FEATURES" for t in n.targets)))
assert len(whitelist)==52
def count(ratio,n):
    v=float(ratio)*n
    assert math.isfinite(v) and 0<=v<=n and math.isclose(v,round(v),abs_tol=1e-9),v
    return int(round(v))
rows=[]
for name,s in tracks.items():
    values=[r for target in s["vehicle_tracks"].values() for r in target]
    n=len(s["times"])
    assert n>0 and all(b>a for a,b in zip(s["times"],s["times"][1:]))
    assert not any(r["category"].startswith("human") for r in values)
    assert "human_tracks" not in s and "vru_tracks" not in s
    r=current[name]
    rows.append({"scene_name":name,"scene_token":r["scene_token"],"frames":n,"human_track_rows":0,"bicycle_track_rows":sum(x["category"].startswith("vehicle.bicycle") for x in values),"motorcycle_track_rows":sum(x["category"].startswith("vehicle.motorcycle") for x in values),"raw_candidate_frames":count(r["vru_path_conflict_ratio"],n),"observed_relevance_frames":count(r["vru_observed_relevance_ratio"],n),"crosswalk_candidate_frames":count(r["vru_crosswalk_conflict_ratio"],n),"sustained_relevance_frames":count(r["vru_sustained_relevance_ratio"],n),"minimum_observed_distance_m":float(r["vru_observed_min_distance"]),"minimum_observed_time_s":float(r["vru_observed_min_distance_time"]),"complete_human_replay_available":False})
diag=load(root/"HDBSCAN/tables/target_diagnosis8_20261012.json")
human=next(s["vru_candidates"] for s in diag["scenes"] if s["scene_name"]=="scene-0102")
assert len(human)==3 and {r["index"] for r in human}=={8,9,10} and len({r["instance_token"] for r in human})==1
assert next(r["raw_candidate_frames"] for r in rows if r["scene_name"]=="scene-0102")==len(human)
positive=[r for r in rows if r["raw_candidate_frames"]]
assert len(positive)==7 and sum(r["raw_candidate_frames"] for r in rows)==32
assert next(r for r in rows if r["scene_name"]=="scene-0151")["raw_candidate_frames"]==4
before=[record(root/p) for p in pins]+[record(r["path"]) for r in bound]+[record(split_record["path"])]
result={"scope":"Frozen development29 VRU evidence inventory; no human-target reconstruction or new feature semantics","created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"inputs_and_sources":before,"unchanged_vru_columns":cols,"clustering_vru_columns":[c for c in cols if c in whitelist],"vru_prediction_branch":branch_calls,"rows":rows,"positive_raw_scene_count":len(positive),"raw_scene_frame_count":32,"known0102_old_diagnostic_candidates":human,"human_full_trajectories_available":False,"new_extraction":False,"fit":False,"evaluation_semantics":False,"feature_or_rule_change":False}
for r in before:assert record(r["path"])==r
with out.open("x",encoding="utf8") as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({"output":record(out),"rows":len(rows),"unchanged_columns":len(cols),"clustering_vru_columns":result["clustering_vru_columns"],"raw_positive_scenes":len(positive),"raw_candidate_scene_frames":32},ensure_ascii=False))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'VRU_frozen_evidence_inventory','exec'))"
```

## 状态

单次生成exit0，输出23204字节，ORIGINAL SHA256 `506c7ecc9c8bff0b33d2c4366410ba65f2ef727140a6ca482506206dee5c70ad`。29条/22个相关字段v5.2对v7逐值不变，其中9个聚类字段；7条/32个原始候选场景帧。没有人类完整轨迹；0102旧三帧诊断仅有汇总，不是完整坐标序列。15个直接使用源/输入绑定生成前后相同，没有检查整个v7传递链或583MB原始标注。

具体结论见 `outputs/人工复核/VRU类别范围与证据缺口诊断_20261017.md`。新增类别/身份缺口：路径候选仅human分支；0151自行车反馈不能转给四帧未知人类候选。原计划完整正负目标对照未完成；没有用更容易的计数代替成功验收。

独立窄审核JSON原摘要、15直接记录及相关数值/源码后，未发现文稿有根据的P1/P2；没有核完整传递封印、重建人类轨迹或语义验收，也未运行生成/提取/拟合/评分/nuScenes/评价。主线程只读配方exit0：29×22值/9聚类列/7条32帧及8个本地链接核对通过；限定AGENTS/CHANGLOG/HDBSCAN README的git diff --check exit0。没有运行代码测试或完整旧封印递归检查，不能沿用历史330项为本轮测试数。

日期使用当前任务上下文的2026-10-17，JSON created_at_utc保留实际工具主机时钟值，不回写或推定二者一致。项目仍未完成，补证据/正式规则/实验选择保持暂挂。

## 只读核验配方

后续只运行此块，不重跑生成，也不更新原摘要：

```powershell
@'
from pathlib import Path
import csv,hashlib,json,re
root=Path.cwd()
p=root/"logs/vru_evidence_inventory_20261017.json"
assert hashlib.sha256(p.read_bytes()).hexdigest()=="506c7ecc9c8bff0b33d2c4366410ba65f2ef727140a6ca482506206dee5c70ad"
d=json.loads(p.read_text(encoding="utf8"))
for r in d["inputs_and_sources"]:
    b=Path(r["path"]).read_bytes()
    assert len(b)==r["bytes"] and hashlib.sha256(b).hexdigest()==r["sha256"],r["path"]
assert len(d["rows"])==29 and len(d["unchanged_vru_columns"])==22 and len(d["clustering_vru_columns"])==9
assert sum(r["raw_candidate_frames"]>0 for r in d["rows"])==7
assert sum(r["raw_candidate_frames"] for r in d["rows"])==32
assert not any(r["human_track_rows"] or r["complete_human_replay_available"] for r in d["rows"])
assert not any(d[k] for k in ["new_extraction","fit","evaluation_semantics","feature_or_rule_change"])
tables={}
for label,name in [("v5.2","scene_features_crossing_v5_2_regression29_20261013.csv"),("v7","scene_features_longitudinal_v7_replay29_20261015.csv")]:
    with (root/"HDBSCAN/tables"/name).open(encoding="utf8",newline="") as f:tables[label]={r["scene_name"]:r for r in csv.DictReader(f)}
assert set(tables["v5.2"])==set(tables["v7"])=={r["scene_name"] for r in d["rows"]}
for name in tables["v7"]:
    for c in d["unchanged_vru_columns"]:assert float(tables["v5.2"][name][c])==float(tables["v7"][name][c])
file=root/"outputs/人工复核/VRU类别范围与证据缺口诊断_20261017.md"
local=[u for u in re.findall(r'\[[^\]]*\]\(([^)]+)\)',file.read_text(encoding="utf8")) if "://" not in u and not u.startswith("#")]
for u in local:assert (file.parent/u.split("#")[0]).exists()
print("VERIFIED original JSON,15 records,29x22 unchanged values,9 clustering fields,7 scenes/32 scene-frames; no human replay; local links",len(local))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'readonly_VRU_evidence_check','exec'))"
```

没有把缺轨迹当作目标不存在，没有把自行车反馈转移给未知行人；没有申请重复整场人工复核或自动启动补提取。
