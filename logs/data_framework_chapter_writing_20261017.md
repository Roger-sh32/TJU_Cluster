# 第三章研究对象与数据框架事实稿

日期采用任务上下文2026-10-17（Asia/Shanghai）；登记时保留实际主机UTC，不回写时钟。前轮VRU证据缺口诊断是实际进展。本轮推进E10写作，不实施新方法或实验。

## 写作定位

使用nature-writing的algorithmic/method/generic结构，按项目中文MEM要求保留中文，不执行默认英译。核心论点为：已有代码与数据字典支持离线场景复核框架和证据边界，不足以证明真实路测收益。读者为论文导师/作者，侧重研究对象、可信性和适用边界，不提出新的创新主张。沿原骨架第三章定位起草新版本，编号/格式/作者结论仍暂挂。

段落顺序：研究对象/术语，身份与时间，自定义划分，数据能力，缺失/未知，离线未来，总体框架，边界小结。术语沿原方法事实稿统一为scene、开发集/评价集、原始候选/观测相关、复核价值。原始字段名保留但披露VRU实际human-only范围，不改代码字段或作者目标。

新增 `outputs/论文初稿/第三章_研究对象数据证据与总体框架事实稿_20261017.md`。旧骨架、方法稿/索引、引文补注稿和第六章均不覆盖。已有700/150与地点组成来自冻结身份清单，非新评价语义；没有图表绘制、数据集/标准下载、标签、提取、拟合、排名、评分、KMeans或新实验。本章表格为已有元数据/概念说明，不是算法性能结果。

## 原稿保护与核验范围

编辑前原方法索引ORIGINAL SHA `d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9`、原正文及25源核对相同，另核第六章索引/VRU清单/划分两件/媒体报告原摘要。新稿配方进一步核对旧写作/引文原件，不重新登记旧索引。

机器核对仅涵盖本稿身份、23个直接来源、10个内部D定位号、冻结划分计数/地点组成与少量文本片段；不验证所有文字推论、学术原理/引文全文、目标语义、学校格式或作者接受。它是写作专用登记，不是特征/参数/正式评价冻结。无完整传递链、原始场景或媒体重验。

## 新稿登记与只读检查配方

仅首次在最后Python命令末尾加`--register`，拒绝索引已存在；后续加`--expected-index-sha 原摘要`。单独`--sources-only`只核来源/计数，不写文件。禁止更新旧正文/索引或刷新新索引适配后续修稿；写作修改另起版本。

```powershell
@'
from pathlib import Path
import argparse,collections,csv,datetime,hashlib,json,re,sys
parser=argparse.ArgumentParser()
group=parser.add_mutually_exclusive_group(required=True)
group.add_argument("--register",action="store_true")
group.add_argument("--sources-only",action="store_true")
group.add_argument("--expected-index-sha")
args=parser.parse_args()
root=Path.cwd()
doc=root/"outputs/论文初稿/第三章_研究对象数据证据与总体框架事实稿_20261017.md"
index=doc.with_name(doc.stem+"_证据索引.json")
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding="utf8"))
def record(p):
    p=Path(p).resolve();return {"path":str(p),"bytes":p.stat().st_size,"sha256":digest(p)}
def verify(r):assert record(r["path"])==r,r["path"]
pins={"outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json":"d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9","outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016_证据索引.json":"4e14e158b4b364fe8c26b444f8064995c8653ebeed90c8c8d99ff72c1f6fb3cd","outputs/论文初稿/方法与开发验证事实稿_引文补注_20261016.md":"b704476aa4a577aa16d257679dc596fd1af5b3f567f47d01b4e9c676bc6754e6","logs/manuscript_citation_integration_20261016.json":"2bc20746226abfad35f4f4b4015d94a712f4536dc1071f515a879a75f0136431","logs/vru_evidence_inventory_20261017.json":"506c7ecc9c8bff0b33d2c4366410ba65f2ef727140a6ca482506206dee5c70ad","logs/kmeans_comparison_chain_20261016.json":"28febdcba1c96b1063fdd5b12074a7a7592f37ef23591970baa699051a12bf82","logs/nuscenes_capability_inventory_20261016.json":"60bdcd2180bd68e854c7234f080271652b8814ed7ef5755776dd1e3b2fcbbdb0","logs/nuscenes_capability_nested_20261016.json":"1e0acc8b039587bf5428ae2c5344f2629e0e986f10c7adcd9dfce77595f21009","HDBSCAN/tables/media_recovery_audit_20261011.json":"ec708a4c29f1320a2b585b25ccef82efd95d63fb098af1e6c8f1fd6c3f7add3f"}
for p,sha in pins.items():assert digest(root/p)==sha,p
old=load(root/"outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json")
for r in [old["document"],*old["sources"].values()]:verify(r)
six=load(root/"outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016_证据索引.json")
verify(six["document"])
for records in six["sources"].values():
    for r in records:verify(r)
source_paths={
"D01":["outputs/论文初稿/方法原始引用_20261016.ris","outputs/论文初稿/方法原始引用与插入建议_20261016.md"],
"D02":["knowledge/sources/数据说明/nuScenes能力核验_20261016/schema_nuscenes_master.md","knowledge/wiki/nuScenes数据能力与特征边界_20261016.md","logs/nuscenes_capability_inventory_20261016.json","logs/nuscenes_capability_nested_20261016.json"],
"D03":["HDBSCAN/tables/evaluation_split_20260924.csv","HDBSCAN/tables/evaluation_split_20260924_manifest.json","knowledge/wiki/独立评价与专家盲评协议.md"],
"D04":["HDBSCAN/scripts/scene_feature_hdbscan_v5_2.py","HDBSCAN/scripts/scene_feature_rules.py","HDBSCAN/scripts/feature_selection.py"],
"D05":["outputs/论文初稿/方法与开发验证事实稿_20261015.md","outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json"],
"D06":["outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016.md","outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016_证据索引.json"],
"D07":["HDBSCAN/tables/media_recovery_audit_20261011.json"],
"D08":["logs/vru_evidence_inventory_20261017.json","outputs/人工复核/VRU类别范围与证据缺口诊断_20261017.md"],
"D09":["HDBSCAN/scripts/evaluation_metrics.py","outputs/实验准备/20261016/专家盲评填写说明_待校准.md"],
"D10":["logs/kmeans_comparison_chain_20261016.json","outputs/实验准备/20261016/KMeans公平对照链路审计.md"]}
sources={key:[record(root/p) for p in paths] for key,paths in source_paths.items()}
assert sum(map(len,sources.values()))==23
split=load(root/source_paths["D03"][1])
with (root/source_paths["D03"][0]).open(encoding="utf8",newline="") as f:members=list(csv.DictReader(f))
assert len(members)==850 and len({r["scene_token"] for r in members})==len({r["scene_name"] for r in members})==850
counts=dict(collections.Counter(r["split"] for r in members))
logs={role:{r["log_token"] for r in members if r["split"]==role} for role in counts}
locations={role:dict(collections.Counter(r["log_location"] for r in members if r["split"]==role)) for role in counts}
assert counts==split["counts"]=={"development":700,"evaluation":150}
assert not logs["development"] & logs["evaluation"]
assert {k:len(v) for k,v in logs.items()}==split["log_counts"]=={"development":56,"evaluation":12}
assert locations==split["location_counts"]
assert locations["development"]=={"boston-seaport":384,"singapore-onenorth":151,"singapore-queenstown":95,"singapore-hollandvillage":70}
assert locations["evaluation"]=={"boston-seaport":83,"singapore-onenorth":32,"singapore-queenstown":20,"singapore-hollandvillage":15}
inv=load(root/source_paths["D02"][2]);assert inv["sdk_version"]=="1.2.0" and len(inv["maps"])==4 and {r["version"] for r in inv["maps"]}=={"1.3"}
vru=load(root/source_paths["D08"][0]);assert len(vru["rows"])==29 and not vru["human_full_trajectories_available"]
media=load(root/source_paths["D07"][0]);assert media["evaluation_scene_count"]==150 and media["development_scene_count"]==8 and media["all_selected_media_present_and_required_decode_checks_passed"]
body=doc.read_text(encoding="utf8")
assert set(re.findall(r'【(D\d{2})】',body))==set(source_paths)
assert re.findall(r'^## (3\.\d+) ',body,re.M)==["3."+str(i) for i in range(1,9)]
assert all(s in body for s in ["不是nuScenes官方train/val","没有完整human轨迹","不报告新的实验成绩","学校样式及最终编号未审定"])
ris=(root/source_paths["D01"][0]).read_text(encoding="utf8")
r01=next(b for b in ris.split("ER  -") if "ID  - R01" in b)
assert len(re.findall(r'^AU  - ',r01,re.M))==10 and "10.1109/CVPR42600.2020.01164" in r01 and "11618" in r01 and "11628" in r01
facts={"counts":counts,"log_counts":{k:len(v) for k,v in logs.items()},"locations":locations,"logs_disjoint":True,"sdk_version":"1.2.0","static_map_versions":["1.3"],"vru_replay_scene_count":29,"media_scope":{"evaluation":150,"development":8}}
if args.register:
    assert not index.exists(),"Do not reseal writing"
    with index.open("x",encoding="utf8") as f:json.dump({"stage":"data_framework_writing_not_formal_results","task_date":"2026-10-17","registered_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"document":record(doc),"sources":sources,"facts":facts,"checks":"Identity/hash,selected counts and identifiers only; not prose/formula/semantic/author acceptance","new_extraction_or_fit":False,"evaluation_semantics":False},f,ensure_ascii=False,indent=2)
    print("REGISTERED ORIGINAL index SHA256",digest(index))
elif args.expected_index_sha:
    assert digest(index)==args.expected_index_sha,"Original writing index mismatch"
    saved=load(index);verify(saved["document"])
    assert saved["sources"]==sources and saved["facts"]==facts
    print("VERIFIED registered document,23 source bindings and selected facts; NOT formal acceptance")
else:print("SOURCES_ONLY passed; no writing registration")
print("D_IDS",len(source_paths),"SOURCE_BINDINGS",sum(map(len,sources.values())),"OLD_WRITING_PRESERVED")
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'data_framework_writing_recipe','exec'))"
```

## 状态

来源模式先执行exit0；独立局部事实/归因窄审未发现有根据的P1/P2，未核完整传递链或本章索引，不构成作者/学校验收，也不表示旧核验器覆盖新章。

首次登记实际exit0，输出D_IDS10/SOURCE_BINDINGS23/OLD_WRITING_PRESERVED。新索引ORIGINAL SHA256 `c3409b17854416de29bc045a6e9cf139cee04d36dac9a03fca3bb53d89d6e295`；正文SHA256 `f537a66ce07ac2fd8fda50155c8b393288aaa8edece01fa7cf2a21e613deb209`。此后正文/索引及本次已绑定来源不原地改写，后续写作另起版本。

实际登记是在根目录用下列包装器执行第一块中同一Python代码；来源预查仅将sys.argv改为sources-only，后续原摘要检查按下方命令：

```powershell
@'
from pathlib import Path
import re,sys
body=Path("logs/data_framework_chapter_writing_20261017.md").read_text(encoding="utf8")
block=re.search(chr(96)*3+r'powershell\s*\n(.*?)'+chr(96)*3,body,re.S).group(1)
sys.argv=["data_framework_writing_recipe","--expected-index-sha","c3409b17854416de29bc045a6e9cf139cee04d36dac9a03fca3bb53d89d6e295"]
exec(compile(block.split("@'\n",1)[1].split("\n'@",1)[0],"data_framework_writing_recipe","exec"))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'data_chapter_original_check','exec'))"
```

原登记包装器的唯一参数差别为 `sys.argv=["data_framework_writing_recipe","--register"]`，执行名data_chapter_registration；它已完成，不再重跑登记。不填正式优越性、提效、专家成绩或作者创新结论；不要求现在确认，正式实验/学校/作者决定继续暂挂。

最终原摘要检查exit0：正文14040字节、索引6851字节、10个D定位/23直接来源及限定事实通过，旧方法/第六章/引文原件和骨架保留。错误索引摘要、对已存在索引再次登记两项内存拒绝探针均按预期拒绝，无新产物写入或索引刷新；不是实验代码测试。README22个链接存在，新两份Markdown无外链/本地链接，围栏/尾空白通过；限定README/AGENTS/CHANGLOG的git diff --check exit0。

一次组合检查包装器共用exec命名空间，使局部Path变量被配方的字符串循环变量覆盖，出现AttributeError；该次原摘要检查本身通过，但组合命令exit1且未跑到拒绝探针，没有写文件。随后为每次exec隔离命名空间，原检查与两项探针均exit0。此故障不在正文、数据或已登记配方中，不修改封印来消除它。

实际最终组合检查命令：

```powershell
@'
from pathlib import Path
import re,sys,hashlib
text=Path("logs/data_framework_chapter_writing_20261017.md").read_text(encoding="utf8")
blocks=re.findall(chr(96)*3+r'powershell\s*\n(.*?)'+chr(96)*3,text,re.S)
exec(compile(blocks[1].split("@'\n",1)[1].split("\n'@",1)[0],"data_chapter_original_check","exec"),{"__name__":"__main__"})
recipe=blocks[0].split("@'\n",1)[1].split("\n'@",1)[0]
for flags,message in [(["--expected-index-sha","0"*64],"Original writing index mismatch"),(["--register"],"Do not reseal writing")]:
    sys.argv=["data_framework_writing_recipe",*flags]
    try:exec(compile(recipe,"data_framework_negative_check","exec"),{"__name__":"__main__"})
    except AssertionError as exc:
        assert str(exc)==message,str(exc)
        print("EXPECTED_REFUSAL",message)
    else:raise AssertionError("Guard did not refuse")
assert hashlib.sha256(Path("outputs/论文初稿/基于聚类的自动驾驶路测关键场景识别研究_导师审查骨架稿.md").read_bytes()).hexdigest()=="69e801dbc82bfc81fabeee0866aae86ec4daffd6a0c244b63c5e2196a1eb7561"
for rel in ["README.md","outputs/论文初稿/第三章_研究对象数据证据与总体框架事实稿_20261017.md","logs/data_framework_chapter_writing_20261017.md"]:
    file=Path(rel);s=file.read_text(encoding="utf8")
    assert s.count(chr(96)*3)%2==0
    assert all(line==line.rstrip() for line in s.splitlines())
    links=re.findall(r'\[[^\]]*\]\(([^)]+)\)',s)
    local=[u for u in links if "://" not in u and not u.startswith("#")]
    for u in local:assert (file.parent/u.split("#")[0]).exists(),u
    print("DOC_LINKS",rel,len(local))
print("Old skeleton preserved; guards and text checks passed")
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'isolated_data_chapter_checks','exec'))"
```

未新运行HDBSCAN全套测试、原场景提取/评分/拟合或真实评价。正文事实窄审与登记检查不代表学校格式、作者/专家接受或正式实验冻结。未提交Git，项目目标仍未完成。
