# 专家一致性与等级排序准备

日期：2026-10-16，Asia/Shanghai。前轮KMeans只读链路审计是实际进展。本轮补查E5/E7尚缺的一致性/等级排序定义，不新增正式统计模块、指标冻结、专家标签或评价访问。

使用nature-academic-search的multi-source-search流程；当前无其学术检索MCP，使用官方网页/作者机构资料回退。manifest给出的workflow实际名为wf1-multi-source-search.md，首次尝试省略wf1前缀导致文件未找到，随后读到正确文件，未修改技能。不是系统文献综述，不声称穷尽检索。

## 本轮获取配方

以下只生成新目录中的实际HTTP响应与索引，拒绝覆写。PDF渲染只用应用自带运行时；主Conda和自带Python都无fitz，自带pypdfium2可用，没有安装/修改环境。网页stable显示1.9.1，本地元数据为1.6.1，故留存1.6官方文档，不将新增的replace_undefined_by参数套到本地。

```powershell
@'
import datetime,hashlib,json,urllib.request
from pathlib import Path
root=Path.cwd()
dest=root/"knowledge/sources/参考文献/序数一致性与等级排序_20261016"
assert not dest.exists(),"Do not replace source responses"
dest.mkdir()
urls=[("alpha.pdf","https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf"),("alpha_portal.html","https://www.asc.upenn.edu/krippendorffs-alpha-reliability"),("kappa_sklearn_1_6.html","https://scikit-learn.org/1.6/modules/generated/sklearn.metrics.cohen_kappa_score.html"),("ndcg_sklearn_1_6.html","https://scikit-learn.org/1.6/modules/generated/sklearn.metrics.ndcg_score.html"),("ir_ranked_evaluation.html","https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html")]
rows=[]
for name,url in urls:
    row={"name":name,"url":url,"requested_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (research source verification)"})
        with urllib.request.urlopen(request,timeout=25) as response:
            data=response.read()
            row.update({"status":response.status,"final_url":response.url,"content_type":response.headers.get("Content-Type","")})
        if name.endswith(".pdf"): assert data.startswith(b"%PDF-"),"Not a PDF response"
        p=dest/name
        with p.open("xb") as stream: stream.write(data)
        row.update({"path":str(p.resolve()),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    except Exception as exc:
        row["error"]=str(exc)
    rows.append(row)
with (dest/"responses.json").open("x",encoding="utf8") as stream:
    json.dump({"scope":"Actual official/author-institution HTTP responses; not a systematic review","rows":rows},stream,ensure_ascii=False,indent=2)
print(json.dumps(rows,ensure_ascii=False))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'ordinal_ranking_source_capture','exec'))"
```

## 状态

首次urllib默认系统信任库在发起HTTP前均报ASN1 NOT_ENOUGH_DATA，未取得五项响应；失败索引已保留，不冒充原文。主环境和应用自带Python均没有requests。本轮不安装库、不关闭TLS验证，以下改用已有pip内置certifi CA，仅对子调用显式传SSLContext；失败索引不覆盖，新响应另存http_verified子目录。

```powershell
@'
from pathlib import Path
import re,ssl
from pip._vendor import certifi
body=Path("logs/ordinal_ranking_preparation_20261016.md").read_text(encoding="utf8")
block=re.search(chr(96)*3+r'powershell\s*\n(.*?)'+chr(96)*3,body,re.S).group(1)
code=block.split("@'\n",1)[1].split("\n'@",1)[0]
code=code.replace('dest.mkdir()', 'dest=dest/"http_verified"\nassert not dest.exists()\ndest.mkdir()').replace('assert not dest.exists(),"Do not replace source responses"','assert dest.is_dir(),"Expected preserved failed-attempt directory"')
code=code.replace('urllib.request.urlopen(request,timeout=25)', 'urllib.request.urlopen(request,timeout=25,context=ssl.create_default_context(cafile=certifi.where()))')
exec(compile(code,"verified_ca_source_capture","exec"))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'source_capture_with_existing_ca','exec'))"
```

## 纯合成定义对照配方

仅用SYN编号，公式演示不接正式API。比较线性/指数增益与本地sklearn1.6.1；原生库导入前仅为本进程设单线程，不拟合任何模型。严格演示函数遇未知或IDCG=0返回None，不代表本轮批准正式实现策略。

```powershell
@'
import os
for key in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMBA_NUM_THREADS"]: os.environ[key]="1"
os.environ["MKL_THREADING_LAYER"]="SEQUENTIAL"
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
import hashlib,importlib.metadata,inspect,json,math
from pathlib import Path
from sklearn.metrics import ndcg_score,cohen_kappa_score
root=Path.cwd()
out=root/"logs/ordinal_ranking_synthetic_20261016.json"
assert not out.exists(),"Do not overwrite SYN evidence"
def record(p):
    p=Path(p).resolve();b=p.read_bytes()
    return {"path":str(p),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
preserved={"HDBSCAN/scripts/evaluation_metrics.py":"1c4f1cf858953a4244cb19d5ed3313a752105c1c109784c4f9a9915f1ebbe7dc","outputs/实验准备/20261016/专家盲评填写说明_待校准.md":"0da78f003b276394b4f3680f128c211ea261b7e98e242df13dee427c0b34232a","outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json":"d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9","outputs/论文初稿/第六章_开发验证与误差分析事实稿_20261016_证据索引.json":"4e14e158b4b364fe8c26b444f8064995c8653ebeed90c8c8d99ff72c1f6fb3cd","outputs/实验准备/20261013/manifest.json":"444e398e9feee9f958b5cba941efa4a1aade85e81b28327c017ee472be4986e7"}
for p,sha in preserved.items(): assert record(root/p)["sha256"]==sha
labels={"SYN_1":2,"SYN_2":1,"SYN_3":1,"SYN_4":0,"SYN_5":0}
orders={"A":["SYN_2","SYN_3","SYN_4","SYN_1","SYN_5"],"B":["SYN_4","SYN_1","SYN_5","SYN_2","SYN_3"]}
def demo(order,labels,gain,k=3):
    assert len(order)==len(labels) and set(order)==set(labels)
    if any(v is None for v in labels.values()): return None
    ideal=sum(gain(v)/math.log2(i+2) for i,v in enumerate(sorted(labels.values(),reverse=True)[:k]))
    if ideal==0: return None
    return sum(gain(labels[s])/math.log2(i+2) for i,s in enumerate(order[:k]))/ideal
rows={}
for kind,gain in [("linear",lambda r:r),("exponential",lambda r:2**r-1)]:
    rows[kind]={}
    for name,order in orders.items():
        value=demo(order,labels,gain)
        ids=list(labels)
        scores=[[len(order)-order.index(s) for s in ids]]
        library=float(ndcg_score([[gain(labels[s]) for s in ids]],scores,k=3))
        assert math.isclose(value,library,rel_tol=1e-12,abs_tol=1e-12)
        rows[kind][name]={"manual":value,"sklearn":library}
assert rows["linear"]["A"]["manual"]>rows["linear"]["B"]["manual"]
assert rows["exponential"]["A"]["manual"]<rows["exponential"]["B"]["manual"]
assert demo(list(labels),{s:0 for s in labels},lambda r:r) is None
unknown=dict(labels);unknown["SYN_5"]=None
assert demo(list(labels),unknown,lambda r:r) is None
tie=float(ndcg_score([[2,1]],[[1,1]],k=1))
assert math.isclose(tie,.75)
fixed=[1.0,.5]
assert math.isclose(float(ndcg_score([[2,1]],[fixed],k=1)),1.0)
rating_units=[[0,0,1],[0,0,None],[1,2,None],[2,None,None]]
pairable=[v for values in rating_units if sum(x is not None for x in values)>=2 for v in values if v is not None]
freq={k:pairable.count(k) for k in [0,1,2]}
assert freq=={0:4,1:2,2:1}
def ordinal_distance(c,k):
    if c==k:return 0
    lo,hi=sorted([c,k])
    return (sum(freq[g] for g in range(lo,hi+1))-(freq[lo]+freq[hi])/2)**2
distances={"0-1":ordinal_distance(0,1),"1-2":ordinal_distance(1,2),"0-2":ordinal_distance(0,2)}
assert distances=={"0-1":9.0,"1-2":2.25,"0-2":20.25}
for p,sha in preserved.items(): assert record(root/p)["sha256"]==sha
result={"scope":"SYN formula/API illustration only; NO formal metric choice, no alpha estimation, no data/model access or fit","sklearn_version":importlib.metadata.version("scikit-learn"),"local_library_sources":[record(inspect.getsourcefile(f)) for f in [ndcg_score,cohen_kappa_score]],"signatures":{"ndcg":str(inspect.signature(ndcg_score)),"kappa":str(inspect.signature(cohen_kappa_score))},"labels":labels,"orders":orders,"k":3,"gain_results":rows,"ties":{"averaged_api":tie,"illustrative_fixed_total_order":1.0},"undefined_demo":{"all_zero_IDCG":None,"any_unknown":None},"ordinal_distance_demo":{"rating_units":rating_units,"pairable_frequencies":freq,"squared_distance":distances,"not_alpha":True},"preserved":[record(root/p) for p in preserved]}
with out.open("x",encoding="utf8") as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({"output":record(out),"gain_results":rows,"sklearn_version":result["sklearn_version"],"ordinal_squared_distances":distances},ensure_ascii=False))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'ordinal_ranking_SYN_only','exec'))"
```

## 实际结果与来源限制

CA限定恢复取得四份HTTP200：Alpha原PDF443314字节、Kappa1.6文档、NDCG1.6文档、IR正文；作者机构门户403明确保留。初次五项只是本机TLS解析错误，无HTTP原文。索引ORIGINAL SHA：失败索引 `546eba312cd3a69d42f2e4965902b44d6ee59c9eaf31a7b7edc5d46551a814ea`；恢复索引 `5fa58e39a97756e2f18683beaa8332dbe29b518921db83b16ade776195db6797`。不覆写索引或失败记录，不将一个403扩展为PDF不可访问。

SYN配方exit0，输出3499字节，ORIGINAL SHA `29f3a3746847851dd11b86755acf0c20dd8f2243f6cb908eeaefdd756e39e36a`。四次手算与API值在1e-12内相符；A/B在线性增益下0.520909/0.403030，指数下0.394809/0.458199，顺序反转。并列平均0.75与演示总顺序1区分；未知/零IDCG严格演示返回None。序数距离9/2.25/20.25只演示距离，没算Alpha，没选正式规则。

发现原SYN配方inspect.getsourcefile记录了sklearn验证装饰器，不是实际指标定义；原JSON不改、不重复生成。另存 `logs/ordinal_ranking_library_sources_20261016.json`（906字节，ORIGINAL SHA `ce72cc4fd23d90df3401ef9c3e5f2bc91cb75f19e08c1ebdee1f20e1c4d48abb`）补AST定位的两个实际模块。此补充不声称封印全部传递依赖；原配方/输出的限制显式保留。

补充文件实际生成命令：

```powershell
@'
from pathlib import Path
import ast,hashlib,json
root=Path.cwd()
p=root/"logs/ordinal_ranking_synthetic_20261016.json"
assert hashlib.sha256(p.read_bytes()).hexdigest()=="29f3a3746847851dd11b86755acf0c20dd8f2243f6cb908eeaefdd756e39e36a"
library=Path("D:/Python/Conda/envs/autodrive-cluster/Lib/site-packages/sklearn/metrics")
records=[]
for name,function in [("_ranking.py","ndcg_score"),("_classification.py","cohen_kappa_score")]:
    f=library/name
    tree=ast.parse(f.read_text(encoding="utf8"))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==function)
    b=f.read_bytes()
    records.append({"path":str(f),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"definition":function,"line":node.lineno})
out=root/"logs/ordinal_ranking_library_sources_20261016.json"
with out.open("x",encoding="utf8") as s:
    json.dump({"parent_synthetic_sha256":"29f3a3746847851dd11b86755acf0c20dd8f2243f6cb908eeaefdd756e39e36a","scope":"Supplement actual metric module records; original inspect.getsourcefile records are decorator validation wrapper only, not metric definitions; no rerun or edits","actual_metric_modules":records},s,ensure_ascii=False,indent=2)
print(out,len(out.read_bytes()),hashlib.sha256(out.read_bytes()).hexdigest())
print(json.dumps(records))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'metric_source_binding_supplement','exec'))"
```

选页渲染命令如下，实际exit0（10页文档，生成1/5/6页PNG），三图已目视核对日期/基本式、单人条目不成对及序数/区间差异。不称读完全部PDF。

```powershell
@'
from pathlib import Path
import pypdfium2 as pdfium
src=Path("knowledge/sources/参考文献/序数一致性与等级排序_20261016/http_verified/alpha.pdf")
out=Path("logs/ordinal_ranking_pdf_pages_20261016")
assert not out.exists()
out.mkdir()
doc=pdfium.PdfDocument(src)
print("pages",len(doc))
for p in [0,4,5]:
    target=out/("alpha_p%02d.png"%(p+1))
    doc[p].render(scale=1.5).to_pil().save(target)
    print(target)
'@ | & 'C:/Users/MSI/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'alpha_selected_pages_render','exec'))"
```

独立窄审未发现文稿有根据的P1/P2，核SYN原摘要、序数距离/增益反转/并列及定义与正式规则的界限。补充索引核实际模块当前字节/摘要，但**它是事后源码快照，不能追溯证明SYN执行时两个模块未变**；不升级为完整运行时封印。审查未重跑生成/下载/拟合/评价，也未计算Alpha。

只读核验配方（不重新生成任何已存响应/SYN文件）：

```powershell
@'
from pathlib import Path
import hashlib,json,math,re
root=Path.cwd()
base=root/"knowledge/sources/参考文献/序数一致性与等级排序_20261016"
pins={base/"responses.json":"546eba312cd3a69d42f2e4965902b44d6ee59c9eaf31a7b7edc5d46551a814ea",base/"http_verified/responses.json":"5fa58e39a97756e2f18683beaa8332dbe29b518921db83b16ade776195db6797",root/"logs/ordinal_ranking_synthetic_20261016.json":"29f3a3746847851dd11b86755acf0c20dd8f2243f6cb908eeaefdd756e39e36a",root/"logs/ordinal_ranking_library_sources_20261016.json":"ce72cc4fd23d90df3401ef9c3e5f2bc91cb75f19e08c1ebdee1f20e1c4d48abb"}
for p,sha in pins.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
load=lambda p:json.loads(Path(p).read_text(encoding="utf8"))
assert sum("error" in r for r in load(base/"responses.json")["rows"])==5
responses=load(base/"http_verified/responses.json")["rows"]
assert sum(r.get("status")==200 for r in responses)==4
assert sum("403" in r.get("error","") for r in responses)==1
syn=load(root/"logs/ordinal_ranking_synthetic_20261016.json")
supp=load(root/"logs/ordinal_ranking_library_sources_20261016.json")
records=[r for r in responses if "path" in r]+syn["local_library_sources"]+syn["preserved"]+supp["actual_metric_modules"]
for r in records:
    b=Path(r["path"]).read_bytes()
    assert hashlib.sha256(b).hexdigest()==r["sha256"] and len(b)==r["bytes"]
assert (base/"http_verified/alpha.pdf").read_bytes().startswith(b"%PDF-")
for name,marker in [("kappa_sklearn_1_6.html","Weighting type"),("ndcg_sklearn_1_6.html","by default ties are averaged"),("ir_ranked_evaluation.html","NDCG")]:
    assert marker in (base/"http_verified"/name).read_text(encoding="utf8")
for mode,gain in [("linear",lambda v:v),("exponential",lambda v:2**v-1)]:
    denom=sum(gain(v)/math.log2(i+2) for i,v in enumerate([2,1,1]))
    for name,order in syn["orders"].items():
        value=sum(gain(syn["labels"][s])/math.log2(i+2) for i,s in enumerate(order[:3]))/denom
        assert math.isclose(value,syn["gain_results"][mode][name]["manual"],abs_tol=1e-12)
file=root/"knowledge/wiki/专家序数一致性与等级排序边界_20261016.md"
links=re.findall(r'\[[^\]]*\]\(([^)]+)\)',file.read_text(encoding="utf8"))
local=[u for u in links if "://" not in u and not u.startswith("#")]
for u in local:assert (file.parent/u.split("#")[0]).exists()
print("VERIFIED4 pinned JSONs,4 raw responses,5 preserved records,2 current metric modules+wrapper; SYN formulas; local links",len(local))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'readonly_ordinal_ranking_check','exec'))"
```

可复用定义见 `knowledge/wiki/专家序数一致性与等级排序边界_20261016.md`。最终只读配方exit0：4个固定JSON摘要、4份原始响应、5项既有记录、两个实际指标模块和装饰器相符，SYN公式复算及5个本地链接检查通过。AGENTS/CHANGLOG/wiki入口限定 `git diff --check` exit0；新文档围栏/链接按本轮配方检查，未作全仓库测试或完整冻结审计。

本轮没有编辑既有统计模块、专家说明、正文/索引或统计包；正式选择继续暂挂，不创建指标导入器/标签/真实评价/模型或拟合实验，不提交Git。项目目标仍未完成。
