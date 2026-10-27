# 第六章开发验证事实稿写作记录

日期：2026-10-16，Asia/Shanghai。前一目标轮完成R10页码修订和0552独立窄审补记，属于实际进展。本轮沿用户持续推进、决定暂挂的要求，补充中文MEM论文的实验/讨论写作素材，不实施新实验。

## 写作范围

采用nature-writing的algorithmic / experiments+discussion / generic框架；按项目要求输出中文，不采用其默认英译格式。核心论点来自现有记录：匹配版本的开发重放能解释计算结果及部分误差来源，但不能替代独立优先级评价或真实路测提效结论。核心证据和边界已明确，未以待确认的作者创新主张启动新论证。

新增 `outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016.md`。它独立于旧骨架稿/方法稿/引文补注件，拓展版本对照、正例保护、0669/0552失败机制和正式评价缺口。章节定位暂按第六章，不是学校格式或作者验收。没有新增论文性能数据、图表绘制、真实150标签、特征/参数/模型选择或KMeans实验。

已核对原方法写作索引ORIGINAL SHA256 `d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9`，并按原始摘要核对v6/v6.1/v7比较报告及其绑定输出后再阅读差异。没有更新旧封印。新稿内部E编号仅作证据定位，不冒充学术参考文献。

## 检查范围

后续证据索引登记新稿与实际使用的来源摘要、版本差异事实及环境/命令。有限机器检查用于身份/摘要、登记计数、局部数值和内部定位；不覆盖每句推论、独立性、公式或作者接受。原20261015写作核验器不覆盖这个新稿，不修改或套用旧核验结果冒充通过。

状态：正文已起草并完成独立事实/版本归因窄审；新稿来源/计数登记已执行，后续仅用原始摘要检查。正式特征/参数/评价及作者决定仍暂挂。

## 新稿专用登记与有限复核

在根目录使用下块。首次登记在最后Python命令追加`--register`，只允许新索引不存在时保存；后续仅用`--expected-index-sha <首次登记摘要>`。不调用旧写作核验器、不重封旧产物、不运行提取或拟合。检查登记计数、少量正文数值片段、内部E定位、来源及稿件摘要；不验证全部正文论断。

```powershell
@'
import argparse, datetime, hashlib, json, re, sys
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument("--register",action="store_true")
parser.add_argument("--expected-index-sha")
args=parser.parse_args()
doc=Path("outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016.md")
index=doc.with_name(doc.stem+"_证据索引.json")
def load(path): return json.loads(Path(path).read_text(encoding="utf8"))
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def record(path):
    p=Path(path)
    return {"path":str(p.resolve()),"bytes":p.stat().st_size,"sha256":digest(p)}
def verify(r):
    assert record(r["path"])==r,r["path"]
old=Path("outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json")
assert digest(old)=="d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9"
original=load(old)
for r in [original["document"],*original["sources"].values()]: verify(r)
for name,sha in (("logs/short_static_diagnosis_v2_seal_20261015.json","c951debde5f186a8269e52c3981c5cc604c777a313837f1521370a658d0ecf0b"),("logs/longitudinal_protection_diagnosis_v1_seal_20261015.json","9678da24c4ff50e2d37dff18354a22cd6926350d7bc9aa98c33d90cbcc50caf5")):
    assert digest(name)==sha
    seal=load(name)
    for r in [seal["protocol"],*seal["outputs"]]: verify(r)
assert digest("logs/partial_bypass_evidence_20261016.json")=="ea0b21f0e5d9970a140bc6173430817fbdef5aecbad3dd4aca400a90e06b2da7"
T="HDBSCAN/tables/"
source_map={
"E01":["knowledge/wiki/独立评价与专家盲评协议.md",T+"evaluation_split_20260924_manifest.json"],
"E02":[original["document"]["path"]],
"E03":["outputs/实验准备/20261016/执行链路审计与恢复顺序.md"],
"E04":[T+"development_fit_summary_20260927.json"],
"E05":[T+"development_candidate700_comparison_20261001.json"],
"E06":[T+"crossing_v6_replay29_comparison_20261014.json"],
"E07":[T+"crossing_v6_1_replay29_comparison_20261015.json"],
"E08":[T+"longitudinal_v7_replay29_comparison_20261015.json",T+"longitudinal_v7_replay29_ledger_20261015.json","HDBSCAN/scripts/longitudinal_candidate_v7.py","logs/longitudinal_v7_replay_20261015.py"],
"E09":[T+"parameter_stability_20260930/summary.json"],
"E10":["logs/development_review_feedback10_20261014.md"],
"E11":["outputs/人工复核/短暂静态障碍与持续受阻对照_20261015.md","logs/short_static_diagnosis_v2_evidence_20261015.json"],
"E12":["outputs/人工复核/0552部分占道绕行根因诊断_20261016.md","logs/partial_bypass_evidence_20261016.json","logs/partial_bypass_review_followup_20261016.md"],
"E13":["outputs/人工复核/纵向绕行保护根因诊断_20261015.md","logs/longitudinal_protection_diagnosis_v1_evidence_20261015.json"],
"E14":["knowledge/wiki/nuScenes数据能力与特征边界_20261016.md"],
"E15":[T+"media_recovery_audit_20261011.json"],
"E16":["logs/experiment_readiness_20261013.md","outputs/实验准备/20261016/专家盲评填写说明_待校准.md","HDBSCAN/scripts/evaluation_metrics.py"]}
sources={k:[record(p) for p in paths] for k,paths in source_map.items()}
compare_pins={"E06":"3b811a32cc26a11a647b9c6acede9759a5f2a569c59a0945b877c85161d4cbbb","E07":"9cc0ff917895087587155ea65611099043ba288a8ec7f64513d1945c92bcc42a","E08":"b7df6d51107f04cf3b7fdf9142fcddf24cec1a997e99277555ce3eab4872bdf3"}
comparisons={}
for key,sha in compare_pins.items():
    p=source_map[key][0];assert digest(p)==sha
    d=load(p)
    for r in [d["protocol"],*d["outputs"]]: verify(r)
    comparisons[key]={"scenes":len(load(d["protocol"]["path"])["names"]),"changed_scenes":len(d["changed_scenes"]),"cells":len(d["changes"]),"clustering_cells":len(d["clustering_changes"])}
split=load(source_map["E01"][1]); fit=load(source_map["E04"][0]); full=load(source_map["E05"][0]); param=load(source_map["E09"][0])
ledger=load(source_map["E08"][1])["scenes"]
partial=next(s for s in load(source_map["E12"][1])["scenes"] if s["scene_name"]=="scene-0552")
facts={"split":split["counts"],"logs":split["log_counts"],"historical_fit":[fit["scene_count"],fit["semantic_feature_count"],fit["cluster_count_excluding_noise"],fit["noise_count"]],
"v4":[full["scene_count"],full["column_count"],full["clustering_feature_count"],full["query_exception_count"]],"comparisons":comparisons,
"historical_parameter_runs":[len(param["configurations"]),len(param["seeds"]),param["successful_runs"]],
"v7_ledger_and_gated":[sum(len(frame) for s in ledger for frame in s["ledger"]),sum(len(s["rejected"]) for s in ledger)],
"v6_1_local_ratio":[load(source_map["E07"][0])["changes"][0]["v6"],load(source_map["E07"][0])["changes"][0]["v6_1"]],
"partial55_shift_turn":[partial["reproduced_fields"]["ego_evasive_lateral_shift"],partial["reproduced_fields"]["ego_evasive_net_heading_change"]],
"partial55_late_window":partial["static_anchor_local_windows_diagnostic_only"][1]}
assert facts["historical_fit"]==[700,52,12,54] and facts["v4"]==[700,129,52,0]
assert facts["split"]=={"development":700,"evaluation":150} and facts["logs"]=={"development":56,"evaluation":12}
assert facts["historical_parameter_runs"]==[4,5,20] and facts["v7_ledger_and_gated"]==[393,13]
assert [list(comparisons[k].values()) for k in ("E06","E07","E08")]==[[29,4,10,1],[29,1,1,1],[29,6,75,13]]
assert [round(v,6) for v in facts["v6_1_local_ratio"]]==[0.230769,0.256410]
assert [round(v,3) for v in facts["partial55_shift_turn"]]==[22.542,0.976]
late=facts["partial55_late_window"]
assert [round(late[k],3) for k in ("existing_shift_function_m","existing_heading_function_rad","available_future_s")]==[2.118,0.160,3.447]
assert late["horizon_complete"] is False and late["window_s_requested"]==10.0
body=doc.read_text(encoding="utf8")
assert set(re.findall(r"【(E\d{2})】",body))==set(source_map)
for snippet in ("开发场景700条、评价场景150条","分别来自56和12个采集日志","12个非噪声簇，54个噪声样本","129列，52个聚类字段","4种配置、5个随机种子，共20次运行","改变4条场景、10格，其中1格为聚类字段","改变6条场景、75格，其中13格为聚类字段","393条","13个目标×帧","0.230769变为0.256410","22.542米","0.976弧度","2.118米","0.160弧度","3.447秒"):
    assert snippet in body,snippet
for target in re.findall(r"\]\((F:/[^)]+)\)",body): assert Path(target).is_file(),target
payload={"stage":"development_experiment_writing_not_formal_results","document":record(doc),"sources":sources,"facts":facts,"original_writing_index":record(old),
"source_binding_count":sum(map(len,sources.values())),"new_experiments":False,"evaluation_semantics_accessed":False,"author_accepted":False,
"check_scope":"Source/document hashes, registered summary values, selected prose snippets and E IDs only; not all prose/formulas/semantics"}
if args.register:
    payload.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.executable,python_version=sys.version,command=sys.argv)
    with index.open("x",encoding="utf8") as stream: json.dump(payload,stream,ensure_ascii=False,indent=2,allow_nan=False)
    print("REGISTERED original index SHA256="+digest(index))
else:
    assert args.expected_index_sha and digest(index)==args.expected_index_sha,"Original new-writing index digest required"
    saved=load(index)
    for key,value in payload.items(): assert saved[key]==value,key
    print("VERIFIED new chapter document/source hashes, selected summary facts and E IDs; no formal results")
print("SOURCE_BINDINGS",payload["source_binding_count"])
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'experiment_chapter_evidence','exec'))"
```

首次登记在独立窄审及必要修正之后执行，当前不得提前引用不存在的索引。后续文字需要变化应另建版本，不刷新该索引来适配改稿。

## 实际登记与审阅结果

独立静态复核未发现有根据的P1/P2：版本计数与用途未混用，0068局部恢复、0011保护、0669未修和0552各项边界与来源相符。审查者没有运行源封印重验、重放或新稿校验代码，不为新索引自动背书，也不是作者或论文有效性验收。

主线程自审另将“白名单外字段不变”明确为31个纵向允许变更字段之外，避免被误解为52个聚类字段之外；TTC等非聚类诊断字段可以变化。除此之外没有修改旧实现或旧写作。

独立窄审之后单次登记exit0，新索引为 `outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016_证据索引.json`，ORIGINAL SHA256 `4e14e158b4b364fe8c26b444f8064995c8653ebeed90c8c8d99ff72c1f6fb3cd`，16个E定位/26项来源绑定。该索引只用于新写作材料来源追溯，不是正式特征/实验协议或旧包重封。

实际登记通过提取本文第一个PowerShell块中的Python正文、在指定解释器内存执行，逻辑argv为`experiment_chapter_documented_recipe --register`；索引`command`记录该逻辑argv，不是PTY原始命令历史。等价的后续只读执行包装如下，不应再次传`--register`：

```powershell
@'
import re,sys
from pathlib import Path
text=Path("logs/experiment_chapter_writing_20261016.md").read_text(encoding="utf8")
fence=chr(96)*3
block=re.search(fence+r"powershell\n(.*?)\n"+fence,text,re.S).group(1)
code=block.split("@'\n",1)[1].split("\n'@ |",1)[0]
sys.argv=["experiment_chapter_documented_recipe","--expected-index-sha","4e14e158b4b364fe8c26b444f8064995c8653ebeed90c8c8d99ff72c1f6fb3cd"]
exec(compile(code,"experiment_chapter_check","exec"))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'check_new_experiment_chapter','exec'))"
```

登记检查了原写作索引及其25份源/原稿、两个诊断原seal及绑定输出、三个版本比较原摘要及输出，再核对新稿登记事实和链接。不是重新提特征、拟合或读取真实评价语义。本轮未重跑HDBSCAN全套测试，不把既有330项测试冒称新稿验证。

最终以ORIGINAL新索引摘要执行只读检查exit0，26项来源、新稿摘要、所登记计数/数值片段/E定位均一致；新稿/日志链接与空白、入口`git diff --check`通过。稿件17478字节，SHA256 `ff4e7f589edda61ab9592de2e07b0804f2276143f3274454e6ed9a360bd776d4`。这些检查仍不覆盖全部论断或公式。Codex文件展示请求返回queued，不宣称已在界面显示或排版验收。整体论文/正式实验目标未完成。
