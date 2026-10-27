# 公平对照链路只读审计

日期：2026-10-16，Asia/Shanghai。前一目标轮完成入口现状与历史分离，属于实际进展。本轮按收尾E6核查KMeans与主拟合的输入保护和表示可比性，不运行KMeans/UMAP拟合，不修改生产代码、特征或任何已绑定结果。

## 范围

只核对当前两个入口、公共划分/52列检查、主入口提取来源检查和既有KMeans测试；仅使用已见开发29条候选表做两个`--preflight`。不读取评价场景语义、不载入pickle、不执行现有KMeans测试集（其中包含实际合成拟合），不新增或决定正式对照、参数、指标、排序。

工作假设：共用52列白名单并不保证共用提取来源门控，KMeans的预检查可能放行主入口拒绝的候选。另检查支持度过滤/PCA/选K是否意味着比较的不只是聚类器，以及当前输出能否支持固定样本外评价。修复和实验选择均暂挂。

## 本轮实际命令配方

下面是单次诊断生成配方，只在新JSON不存在时执行；拒绝覆写。后续只读JSON与原摘要，不重跑生成。超时只终止本配方新建的对应子进程；不查询或终止其他进程，不据此声称全机器无任务。

```powershell
@'
import ast,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
root=Path.cwd()
output=root/"logs/kmeans_comparison_chain_20261016.json"
assert not output.exists(),"Do not overwrite or regenerate this audit"
def record(p):
    p=Path(p).resolve()
    return {"path":str(p),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
pair=root/"logs/entry_guard_pair_verified_20261016.json"
assert record(pair)["sha256"]=="115ea08753c103ec02836ef7895ce418a35c2536c9f5b4aabeb89f9deb8b7512"
old=json.loads(pair.read_text(encoding="utf8"))
binding=old["rows"][0]["input_binding"]
for key in ["features","manifest"]:
    assert record(binding[key]["path"])["sha256"]==binding[key]["sha256"]
manifest=json.loads(Path(binding["manifest"]["path"]).read_text(encoding="utf8"))
assert binding["stage"]==manifest["stage"]=="candidate_feature_replay"
sources=[root/p for p in ["Kmeans/scripts/kmeans_semantic_baseline.py","Kmeans/tests/test_kmeans_semantic_baseline.py","HDBSCAN/scripts/cluster_umap_hdbscan.py","HDBSCAN/scripts/experiment_partition.py","HDBSCAN/scripts/feature_selection.py","HDBSCAN/scripts/frozen_model.py"]]
before=[record(p) for p in sources]
trees={p.name:ast.parse(p.read_text(encoding="utf8")) for p in sources}
def calls(name,func):
    node=next(n for n in trees[name].body if isinstance(n,ast.FunctionDef) and n.name==func)
    return [{"name":ast.unparse(n.func),"line":n.lineno} for n in ast.walk(node) if isinstance(n,ast.Call)]
kmcalls=calls("kmeans_semantic_baseline.py","run_experiment")
maincalls=calls("cluster_umap_hdbscan.py","main")
assert not any(c["name"]=="require_feature_provenance" for c in kmcalls)
assert any(c["name"]=="require_feature_provenance" for c in maincalls)
prefix="_readonly_chain_audit_20261016"
paths=[root/"Kmeans/tables"/(prefix+"_"+suffix) for suffix in ["metrics.csv","clusters.csv","cluster_sizes.csv","profiles.csv","summary.json","clusters.csv.manifest.json"]]
paths += [root/"Kmeans/pictures"/(prefix+"_pca.png")]
paths += [root/"HDBSCAN/tables"/(prefix+suffix) for suffix in [".csv",".csv.manifest.json",".model"]]
paths += [root/"HDBSCAN/pictures"/(prefix+".png")]
assert not any(p.exists() for p in paths)
env=os.environ.copy()
overrides={k:"1" for k in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMBA_NUM_THREADS","PYTHONDONTWRITEBYTECODE"]}
overrides.update({"MKL_THREADING_LAYER":"SEQUENTIAL","SCENE_CLUSTER_FEATURE_INPUT":Path(binding["features"]["path"]).name,"SCENE_CLUSTER_CLUSTER_OUTPUT":prefix+".csv","SCENE_CLUSTER_CLUSTER_FIGURE":prefix+".png"})
env.update(overrides)
python="D:/Python/Conda/envs/autodrive-cluster/python.exe"
commands=[("main",[python,"-X","utf8","-u","HDBSCAN/scripts/cluster_umap_hdbscan.py","--preflight"]),("kmeans",[python,"-X","utf8","-u","Kmeans/scripts/kmeans_semantic_baseline.py","--input",binding["features"]["path"],"--output-prefix",prefix,"--preflight"])]
rows=[]
for label,command in commands:
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    t=time.monotonic()
    try:
        done=subprocess.run(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf8",timeout=20)
        row={"entry":label,"command":command,"returncode":done.returncode,"stdout":done.stdout,"stderr":done.stderr,"timed_out":False}
    except subprocess.TimeoutExpired as exc:
        def decode(x): return x.decode("utf8",errors="replace") if isinstance(x,bytes) else (x or "")
        row={"entry":label,"command":command,"returncode":None,"stdout":decode(exc.stdout),"stderr":decode(exc.stderr),"timed_out":True}
    row.update({"started_at_utc":started,"elapsed_seconds":time.monotonic()-t,"timeout_seconds":20})
    rows.append(row)
after=[record(p) for p in sources]
assert before==after,"Source changed during audit"
for key in ["features","manifest"]:
    assert record(binding[key]["path"])["sha256"]==binding[key]["sha256"]
assert not any(p.exists() for p in paths),"Unexpected experiment output"
result={"scope":"Read-only comparison-chain audit; two development-only preflights; NO FIT","created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"python":record(python),"parent_pair":record(pair),"sources":before,"input_binding":binding,"split":[record(root/"HDBSCAN/tables"/p) for p in ["evaluation_split_20260924.csv","evaluation_split_20260924_manifest.json"]],"environment_overrides":overrides,"source_calls":{"main":maincalls,"kmeans":kmcalls},"rows":rows,"sources_and_input_unchanged":True,"experiment_outputs_absent":True,"planned_output_paths":[str(p) for p in paths]}
with output.open("x",encoding="utf8") as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({"audit":record(output),"preflight_results":[{k:r[k] for k in ["entry","returncode","timed_out","elapsed_seconds"]} for r in rows],"experiment_outputs_absent":True},ensure_ascii=False))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'kmeans_readonly_chain_audit','exec'))"
```

## 执行与审查结果

生成配方exit0；主预检查exit1（来源不匹配，预期拒绝），KMeans预检查exit0（29条/52列），均无超时。六个源/测试及输入绑定未改，11个计划实验输出不存在。JSON为16555字节，ORIGINAL SHA256 `28febdcba1c96b1063fdd5b12074a7a7592f37ef23591970baa699051a12bf82`。

结论与依赖见 `outputs/实验准备/20261016/KMeans公平对照链路审计.md`。已确认KMeans缺主入口来源门控；没有发现或测试评价成员绕过。另静态核查表示/支持度/选K/模型持久化/评分差异，未批准任何新设计。附读corner_scoring.py评分实现，实际SHA256 `18c9f88e48087017e5615f0639f13503b54d64335264d94df209fcbc7bbec620`，没有改动它。曾附读seed_stability/parameter_stability入口作背景，但未运行或据此新增结果；结论表仅基于本轮两个主审入口。

独立窄审确认既有来源门控P2，未发现审计文稿新增的P1/P2；核JSON原摘要及六源字节/SHA、控制流和表示/画像/评分边界。审查只做静态阅读，未重演preflight或实验输出检查，不能据此称独立实验复现。

主线程最终只读检查exit0：JSON原摘要、12项文件记录（解释器/旧成对记录/六源/划分两件/候选两件）和附读评分源码摘要均相符；实际记录主拒绝1/KMeans接受0，无超时，11个实验输出仍不存在。根README21个链接和本轮报告9个链接存在。修改README/AGENTS/CHANGLOG仅作警示与导航，不修改旧KMeans README或任何实验文件。没有运行科学计算测试，不声称完整环境/拟合/公平性验收。

后续可用下列只读配方复核已生成JSON，不再次执行上节生成：

```powershell
@'
from pathlib import Path
import hashlib,json
root=Path.cwd()
p=root/"logs/kmeans_comparison_chain_20261016.json"
assert hashlib.sha256(p.read_bytes()).hexdigest()=="28febdcba1c96b1063fdd5b12074a7a7592f37ef23591970baa699051a12bf82"
d=json.loads(p.read_text(encoding="utf8"))
records=[d["python"],d["parent_pair"],*d["sources"],*d["split"],d["input_binding"]["features"],d["input_binding"]["manifest"]]
for r in records:
    b=Path(r["path"]).read_bytes()
    assert hashlib.sha256(b).hexdigest()==r["sha256"],r["path"]
    if "bytes" in r: assert len(b)==r["bytes"]
assert [r["returncode"] for r in d["rows"]]==[1,0]
assert not any(r["timed_out"] for r in d["rows"])
assert "Feature extraction version/provenance mismatch" in d["rows"][0]["stderr"]
km=json.loads(d["rows"][1]["stdout"])
assert km["preflight_only"] is True and km["scene_count"]==29 and km["semantic_feature_count"]==52
assert not any(Path(p).exists() for p in d["planned_output_paths"])
assert hashlib.sha256((root/"HDBSCAN/scripts/corner_scoring.py").read_bytes()).hexdigest()=="18c9f88e48087017e5615f0639f13503b54d64335264d94df209fcbc7bbec620"
print("VERIFIED original audit,12 bound records,scoring hash,paired exits and11 absent experiment outputs; NO FIT")
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'readonly_kmeans_audit_check','exec'))"
```

本文件是过程记录，不是正式实验协议或修复批准；未提交/推送Git，项目目标仍未完成。
