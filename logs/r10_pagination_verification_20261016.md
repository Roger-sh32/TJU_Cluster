# R10 页码补核

日期：2026-10-16，Asia/Shanghai。工作流：`nature-academic-search / citation-verification`。学术检索MCP未挂载；沿原Crossref身份定位期刊档案记录，不使用其他论文参考文献中的二手页码补空。

## 核验结果

R10分类为“书目页码已核验”，范围仅书目。原刊[JSTOR当期目录](https://www.jstor.org/stable/i348796)显示 *The Annals of Statistics*, Vol.7, No.1, Jan.1979，出版机构为Institute of Mathematical Statistics；其中目标题名、B. Efron、页码1–26共同链接至 `https://www.jstor.org/stable/2958830`。与已保存Crossref的题名、作者、年、卷期对应，沿用原DOI `10.1214/aos/1176344552`，不另造文献身份。

因此本次修订为：Efron B. Bootstrap Methods: Another Look at the Jackknife. The Annals of Statistics, 1979, 7(1): 1–26。目录中的“The 1977 Rietz Lecture”是栏目语境，不把论文出版年改成1977。

新增单条[R10元数据修订RIS](F:/Scene_cluster/outputs/论文初稿/R10页码补核修订_20261016.ris)，仅补SP/EP并更新核验说明；其他核心字段沿用旧记录。它用于现有R10的元数据修订，不作为第13篇新文献重复计数，也不代表学校样式或文献管理器导入已经验收。

旧六条RIS、wiki边界说明、20261015事实稿/索引和20261016引文补注件/索引均不编辑、不重封。旧文档“R10页码未核验”保留为当时状态；本记录只取代这个书目缺口，不取代全文/公式核对、作者审定或正式统计设计的待办。下版正文是否集成仍按原流程，不改已封存正文。

## 获取路径与限制

原资料放 `knowledge/sources/参考文献/R10页码补核_20261016/`。

- 主机实际请求原Project Euclid文章页、JSTOR文章页和期目录，共三份HTTP200响应，使用certifi CA/主机名验证、25秒超时、2MiB上限。三份原始HTML保留，地址、时间、字节数和摘要见 `retrieval_manifest.json`。
- Project Euclid返回Incapsula验证壳；两份JSTOR响应为同一Client Challenge壳。`saved=true`仅表示响应字节落盘，不表示论文/目录正文可用。没有执行验证页脚本、绕过访问限制、登录或下载PDF。
- 浏览工具的JSTOR原期目录可以读取，实际返回文本原样UTF-8保存到 `jstor_issue_webtool.txt`，9356字节，SHA256 `24d6225e0c1104db7867e526076b112dc4716533081d88b1e94162738731b48b`。`webtool_capture_manifest.json`明确标注它是工具抽取文本，不是原HTTP HTML；时间为UTC `2026-10-16T12:46:56.685731+00:00`。
- 搜索曾返回其他论文的参考文献、IMS评论和作者资料页；没有将这些二手引文作为页码定案证据，没有读取不相关的PDF全文。工具库中工作流实际文件为`wf2-citation-verification.md`，第一次省略前缀的本地读取失败后按manifest找到正确路径，不影响来源记录。

本轮没有读论文全文、推导或验证公式。R10仍只支持Bootstrap方法归属，不能证明本项目整日志固定排序重采样的适用性、覆盖率、显著性或模型不确定性；也没有新增序数一致性/等级排序指标、特征、拟合、真实评价或媒体。

## 离线复核命令

以下只检查原始响应/工具文本摘要、期目录目标条目、修订RIS核心字段及列出的旧文件。不是全文/全部文句审计或GUI导入检查，不覆写文件。

```powershell
@'
import hashlib, json, re
from pathlib import Path
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ris(path):
    blocks=[]; current=None
    for line in Path(path).read_text(encoding="utf8").splitlines():
        if not line: continue
        assert re.fullmatch(r"[A-Z0-9]{2}  -.*",line),line
        key,value=line[:2],line[6:]
        if key=="TY":
            assert current is None
            current={}
        assert current is not None
        current.setdefault(key,[]).append(value)
        if key=="ER":
            blocks.append(current);current=None
    assert current is None
    return blocks
root=Path("knowledge/sources/参考文献/R10页码补核_20261016")
records=json.loads((root/"retrieval_manifest.json").read_text(encoding="utf8"))["records"]
assert len(records)==3
for record in records:
    path=root/record["file"]
    assert record["saved"] and record["http_status"]==200
    assert path.stat().st_size==record["bytes"] and digest(path)==record["sha256"]
    raw=path.read_text(encoding="utf8")
    assert "Client Challenge" in raw or "Incapsula" in raw
capture=json.loads((root/"webtool_capture_manifest.json").read_text(encoding="utf8"))
text_path=root/capture["file"]
assert digest(text_path)==capture["sha256"]=="24d6225e0c1104db7867e526076b112dc4716533081d88b1e94162738731b48b"
text=text_path.read_text(encoding="utf8")
assert capture["source_url"]=="https://www.jstor.org/stable/i348796"
assert "Vol. 7, No. 1, Jan., 1979 The Annals of Statistics" in text
assert "Published by: Institute of Mathematical Statistics" in text
entry=re.search(r"L32: (.*?)\nL33:.*?\nL34: (.*?)\nL35:.*?\nL36: (.*?)\n",text)
assert entry and entry.groups()==("Bootstrap Methods: Another Look at the Jackknife (pp. 1-26)","B. Efron","https://www.jstor.org/stable/2958830")
old_path=Path("outputs/论文初稿/TTC与评价补充引用_20261016.ris")
assert digest(old_path)=="e79aea95e4a4ddc476db6d701594d366303e98a3064d545ca756fc8c55522f3d"
old=next(r for r in ris(old_path) if r["ID"]==["R10"])
new_records=ris("outputs/论文初稿/R10页码补核修订_20261016.ris")
assert len(new_records)==1
new=new_records[0]
assert "SP" not in old and "EP" not in old
assert new["SP"]==["1"] and new["EP"]==["26"]
assert {k:v for k,v in old.items() if k!="N1"}=={k:v for k,v in new.items() if k not in ("SP","EP","N1")}
crossref=json.loads(Path("knowledge/sources/参考文献/TTC与评价引用元数据_20261016/R10_crossref.json").read_text(encoding="utf8"))["message"]
assert new["DO"][0]==crossref["DOI"] and new["TI"][0]==crossref["title"][0]
assert new["VL"]==[crossref["volume"]] and new["IS"]==[crossref["issue"]]
assert new["PY"]==[str(crossref["published"]["date-parts"][0][0])]
expected={
"knowledge/wiki/TTC与评价指标引用边界_20261016.md":"49c8dd344829ca59d493ce1b052e1d0b62dea70a64889467fb96933bacf92206",
"outputs/论文初稿/方法与开发验证事实稿_20261015.md":"e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536",
"outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json":"d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9",
"outputs/论文初稿/方法与开发验证事实稿_引文补注_20261016.md":"b704476aa4a577aa16d257679dc596fd1af5b3f567f47d01b4e9c676bc6754e6",
"logs/manuscript_citation_integration_20261016.json":"2bc20746226abfad35f4f4b4015d94a712f4536dc1071f515a879a75f0136431",
"HDBSCAN/scripts/evaluation_metrics.py":"1c4f1cf858953a4244cb19d5ed3313a752105c1c109784c4f9a9915f1ebbe7dc"}
for path,sha in expected.items(): assert digest(path)==sha,path
print("PASS: R10 pagination from original issue TOC, RIS-only metadata delta, 3 challenge responses explicit, 7 existing files unchanged")
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'r10_pagination_check','exec'))"
```

## 状态

上述离线块已实际执行exit0：原期目录页码、单条RIS元数据增量、三份验证壳响应与工具文本摘要、七份指定旧文件均符合检查。新RIS初始版本872字节，SHA256 `2818237d2845131bbd9bb3a211ef293b0da826eace41e409f24b9af06463a6b2`。文献管理器导入及学校样式没有GUI验证。

独立静态书目窄审未发现有根据的P1/P2：原期TOC与旧R10身份吻合，RIS仅SP/EP/N1改变，验证壳和实际工具文本已正确区分。审查者未联网、执行离线块或独立核对七份旧文件摘要，不能据其结论扩张为全文或方法验收。主线程随后重跑离线块、检查三份原0552诊断摘要、新日志链接/空白和入口`git diff --check`，均通过。

没有修改任何原始封印或实验结论。专家、候选语义、参数和正式评价决定仍暂挂。
