# 核心方法引用核验记录

## 范围与实际状态

用户目标为持续推进、需要人工审核或决策的先暂挂。本轮独立完成六条核心方法文献的书目核验、RIS 导出及正文引用位置建议；不代替作者审定、学校格式确认或正式方法批准。日期 2026-10-16（客户端 Asia/Shanghai 日期），响应清单另存主机 UTC 时间。

环境：`F:/Scene_cluster`，PowerShell，`D:/Python/Conda/envs/autodrive-cluster/python.exe`，certifi `2025.08.03`。未安装包或修改环境。流程使用 `nature-academic-search` 的 citation-verification/reference-mgmt；不用仅限 Nature/CNS 的刊物过滤。未发现可用的 academic-search MCP，改用官方网页与经过 TLS 验证的 Crossref/DataCite API。

真实来源：5 份 Crossref JSON、1 份 DataCite JSON、arXiv v1/v3 HTML、CVF HTML、两份 JOSS HTML、Springer HTML、JCU 作者机构馆藏 HTML，共 **13 份原始响应**。分别保存在 `knowledge/sources/参考文献/方法引用元数据_20261016/`，两个检索清单记录请求及最终 URL、实际时间、HTTP 状态/类型、字节数和 SHA256。Springer 重定向 URL 含 cookie 提示，已保存原样；本地响应包含正确标题和卷号，未把 HTTP 200 本身当成全文可用。

产出：

- [六条 RIS](F:/Scene_cluster/outputs/论文初稿/方法原始引用_20261016.ris)：完整作者、唯一 DOI、版本/页码口径备注；新建未覆盖旧引用。
- [引用核验与插入建议](F:/Scene_cluster/outputs/论文初稿/方法原始引用与插入建议_20261016.md)：按事实稿小节映射、核验程度、可支持和不可支持的结论。
- [有限书目检查结果](F:/Scene_cluster/logs/method_reference_validation_20261016.json)：不是论文全面验收报告。

未新增 PDF、媒体下载、数据提取、聚类拟合、排名、真实评价语义访问或 KMeans。未移动原始资料、改动旧核验笔记、改变既有冻结正文/证据索引/实验文件。新书目包不等于替原正文完成了学校格式引用。

## 差异与失败记录

前续探测中，web 工具访问部分 Crossref/CVF 页面失败；ACM 页面拒绝访问。主机 Python 默认 SSL 上下文在加载 Windows 证书库时抛出 `[ASN1: NOT_ENOUGH_DATA]`；PowerShell `Invoke-RestMethod` 返回认证失败。这些失败没有保存假响应，也没有据此判定 DOI 不存在。

本轮明确指定 `ssl.create_default_context(cafile=certifi.where())`，仍启用证书与主机校验，成功取得 API/官方网页原始响应。没有关闭 TLS、修证书库或重建 Conda。ACM 全文没有绕过访问限制；R05 以 Crossref 和作者机构 JCU 元数据/摘要核验，不声称读过全文。

首次离线字段检查 exit 1：把 arXiv v3 HTML 的 `citation_date` 错当成 v3 版本日期。只读查看原始 HTML 后发现 `citation_date=2018/02/09`，`citation_online_date=2020/09/18`；DataCite 另列 v3 提交时间。只修改临时校验命令中的字段假设，RIS 所引 v3 的日期不改，复核后 exit 0。不是忽略断言或将首次年份改成 2020。

重要差异均记录在 RIS 备注及说明：nuScenes 两套页码；UMAP 首发年/所引版本/作者；JOSS 文章号；TKDD Article 5 页前缀；软件引用与理论引用的职责。未猜测差异成因。

## 取数命令

下列为主取数步骤的执行命令。仅生成真实 HTTP 响应和清单，`xb`/`x` 拒绝覆盖；不要对已有目录重复执行。原始响应随服务变化，不以重新下载覆盖本次记录。

```powershell
@'
import urllib.request, ssl, certifi, json, hashlib, datetime, pathlib
root=pathlib.Path('knowledge/sources/参考文献/方法引用元数据_20261016')
root.mkdir(parents=True,exist_ok=True)
items=[('R01_crossref.json','https://api.crossref.org/works/10.1109/CVPR42600.2020.01164'),('R03_crossref.json','https://api.crossref.org/works/10.21105/joss.00861'),('R04_crossref.json','https://api.crossref.org/works/10.1007/978-3-642-37456-2_14'),('R05_crossref.json','https://api.crossref.org/works/10.1145/2733381'),('R06_crossref.json','https://api.crossref.org/works/10.21105/joss.00205'),('R02_datacite.json','https://api.datacite.org/dois/10.48550/arxiv.1802.03426'),('R02_arxiv_v1.html','https://arxiv.org/abs/1802.03426v1'),('R02_arxiv_v3.html','https://arxiv.org/abs/1802.03426v3'),('R01_cvf.html','https://openaccess.thecvf.com/content_CVPR_2020/html/Caesar_nuScenes_A_Multimodal_Dataset_for_Autonomous_Driving_CVPR_2020_paper.html')]
ctx=ssl.create_default_context(cafile=certifi.where())
records=[]
for name,url in items:
    rec={'file':name,'requested_url':url,'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'TJU-Cluster-reference-audit/1.0'})
        with urllib.request.urlopen(req,context=ctx,timeout=25) as r:
            payload=r.read(); rec.update(final_url=r.geturl(),status=r.status,content_type=r.headers.get('Content-Type'))
        if name.endswith('.json'): json.loads(payload)
        with (root/name).open('xb') as f: f.write(payload)
        rec.update(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),saved=True)
        if 'crossref' in name:
            m=json.loads(payload)['message']; print(name,json.dumps({k:m.get(k) for k in ['DOI','title','author','container-title','published','page','volume','issue','article-number','type']},ensure_ascii=False))
        else: print(name,len(payload),'saved')
    except Exception as e:
        rec.update(saved=False,error=type(e).__name__+': '+str(e)); print(name,rec['error'])
    records.append(rec)
manifest={'client_date':'2026-10-16','scope':'Bibliographic raw metadata only; no dataset/model/evaluation access','tls':'Verified SSL context with explicit certifi CA file; verification enabled','certifi_version':certifi.__version__,'records':records}
with (root/'retrieval_manifest.json').open('x',encoding='utf-8') as f: json.dump(manifest,f,ensure_ascii=False,indent=2)
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -
```

主取数 session `46224` 已退出 0；13 份响应中的其余 4 份由以下补充命令取得，退出 0。

```powershell
@'
import urllib.request, ssl, certifi, json, hashlib, datetime, pathlib
root=pathlib.Path('knowledge/sources/参考文献/方法引用元数据_20261016')
items=[('R03_joss.html','https://joss.theoj.org/papers/10.21105/joss.00861'),('R06_joss.html','https://joss.theoj.org/papers/10.21105/joss.00205'),('R04_springer.html','https://link.springer.com/chapter/10.1007/978-3-642-37456-2_14'),('R05_jcu.html','https://researchonline.jcu.edu.au/47065/')]
ctx=ssl.create_default_context(cafile=certifi.where()); records=[]
for name,url in items:
    rec={'file':name,'requested_url':url,'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TJU-Cluster-reference-audit/1.0'}),context=ctx,timeout=20) as r:
            b=r.read(); rec.update(final_url=r.geturl(),status=r.status,content_type=r.headers.get('Content-Type'))
        with (root/name).open('xb') as f: f.write(b)
        rec.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),saved=True)
    except Exception as e: rec.update(saved=False,error=type(e).__name__+': '+str(e))
    records.append(rec); print(json.dumps(rec,ensure_ascii=False),flush=True)
with (root/'retrieval_supplement.json').open('x',encoding='utf8') as f: json.dump({'client_date':'2026-10-16','tls':'Verified certifi CA, verification enabled','records':records},f,ensure_ascii=False,indent=2)
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -
```

## 核验命令与证据限度

本轮通过的检查：13 份原始响应按清单长度/SHA256 核对；6 条 RIS 起止标记、必需字段、ID 顺序、类型及 DOI 唯一性；5 条与 Crossref 标题/作者/出版年相等，适用项卷期页码相等；arXiv v1/v3 作者与两个日期字段、DataCite DOI/版本/日期交叉核对；CVF 页码、JCU 文章号/页码、Springer 卷号差异单独查验。完整作者数为 `10/3/4/3/4/3`。结果在有限书目检查 JSON 中，状态 `passed_limited_bibliographic_validation`。

这些临时字段断言不是通用 RIS 解析器或工程测试套件，不覆盖所有自由文本、网页语义、原理公式或软件当前行为。独立只读复核另核对引用包和可支持结论，不用断言替代全文审阅。

以下为可重复的离线字段/摘要复查命令，不下载、不覆写检查结果；原始取数清单是本次响应的预期值，不能用更新清单来接受变更。

```powershell
@'
from pathlib import Path
import json, hashlib, re, html
root=Path('knowledge/sources/参考文献/方法引用元数据_20261016')
checked=[]
for n in ['retrieval_manifest.json','retrieval_supplement.json']:
    for r in json.loads((root/n).read_text(encoding='utf8'))['records']:
        assert r['saved'], r
        b=(root/r['file']).read_bytes()
        assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'], r['file']
        checked.append(r['file'])
records=[]; cur=None
for line in Path('outputs/论文初稿/方法原始引用_20261016.ris').read_text(encoding='utf8').splitlines():
    if not line: continue
    assert re.fullmatch(r'[A-Z0-9]{2}  -.*',line), line
    k=line[:2]; v=line[6:]
    if k=='TY': assert cur is None; cur={}
    assert cur is not None
    cur.setdefault(k,[]).append(v)
    if k=='ER': records.append(cur); cur=None
assert cur is None and len(records)==6
assert [r['ID'][0] for r in records]==['R01','R02','R03','R04','R05','R06']
assert [r['TY'][0] for r in records]==['CONF','GEN','JOUR','CHAP','JOUR','JOUR']
assert len({r['DO'][0].lower() for r in records})==6
for r in records:
    for field in ['TY','ID','AU','TI','PY','DO','UR','N1']: assert r.get(field),(r,field)
    rid=r['ID'][0]
    if rid=='R02': continue
    s=json.loads((root/(rid+'_crossref.json')).read_text(encoding='utf8'))['message']
    assert r['DO'][0].lower()==s['DOI'].lower() and r['TI'][0]==s['title'][0]
    assert r['AU']==[a['family']+', '+a['given'] for a in s['author']]
    assert r['PY']==[str(s['published']['date-parts'][0][0])]
    if rid in ['R03','R05','R06']: assert r['VL']==[s['volume']] and r['IS']==[s['issue']]
    if rid in ['R01','R04']: assert r['SP'][0]+'-'+r['EP'][0]==s['page']
    if rid in ['R03','R06']: assert r['SP']==[s['page']] and 'EP' not in r
def meta(s,k): return re.findall(r'<meta\s+name="'+re.escape(k)+r'"\s+content="([^"]+)"',s)
r2=records[1]; v1=(root/'R02_arxiv_v1.html').read_text(encoding='utf8'); v3=(root/'R02_arxiv_v3.html').read_text(encoding='utf8')
assert meta(v1,'citation_author')==['McInnes, Leland','Healy, John']
assert meta(v3,'citation_author')==r2['AU'] and meta(v3,'citation_title')==r2['TI']
assert meta(v3,'citation_date')==['2018/02/09']
assert meta(v3,'citation_online_date')==r2['DA']==['2020/09/18'] and r2['PY']==['2020']
a=json.loads((root/'R02_datacite.json').read_text(encoding='utf8'))['data']['attributes']
assert a['publicationYear']==2018 and a['version']=='3' and a['doi'].lower()==r2['DO'][0].lower()
assert [x['name'] for x in a['creators']]==r2['AU']
assert any(d['date'].startswith('2020-09-18') and d.get('dateInformation')=='v3' for d in a['dates'])
cvf=(root/'R01_cvf.html').read_text(encoding='utf8')
assert meta(cvf,'citation_firstpage')==['11621'] and meta(cvf,'citation_lastpage')==['11631']
jcu=html.unescape((root/'R05_jcu.html').read_text(encoding='utf8'))
assert '5:1' in jcu and '5:51' in jcu and records[4]['C7']==['5']
assert records[4]['SP']==['5:1'] and records[4]['EP']==['5:51']
assert '7819' in (root/'R04_springer.html').read_text(encoding='utf8') and records[3]['VL']==['7819']
expected={'outputs/论文初稿/方法与开发验证事实稿_20261015.md':'e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536','outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json':'d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9'}
for p,h in expected.items(): assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
print('VERIFIED limited bibliographic fields: 6 records,',len(checked),'raw responses; original manuscript unchanged')
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -
```

旧写作包只读核验命令：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/verify_manuscript_facts_20261015.py --expected-index-sha d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9
```

session `34702` 退出 0：14 行登记事实、25 个来源、原正文/核验器摘要及其依赖来源封印核对通过。该只读命令内部有既有合成统计/固定29重放检查，不是重新提取、拟合或访问真实150评价语义；不要把这次检查写成新实验成绩。

保持原始摘要：正文 `e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536`；证据索引 `d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9`。

本轮没有重跑 HDBSCAN 测试套件，不能把之前 330 项通过表述为本轮新增运行。没有进行 EndNote/Zotero GUI 导入、GB/T 7714 学校样式排版、付费章节全文或逐式审阅。

独立只读复核（Confucius）已结束：对本次两份引用产出及本地 JSON/HTML 检查，未发现可复现的 P1/P2 书目或归因问题，13 份原始响应长度/摘要匹配。复核未联网、未读评价语义、未编辑文件或运行实验；不覆盖全文公式、管理器兼容性或学校格式。主代理随后从本日志提取并实际执行上面的第三个代码块，exit 0，输出 `VERIFIED limited bibliographic fields: 6 records, 13 raw responses; original manuscript unchanged`。

交付时 RIS SHA256：`e73c12bf2d39a567ce061c4f0096c3fb9b1fb8364dbff876a17fe2cb6b8524eb`；引用说明 SHA256：`c1efd2c7ae0f9efe3947dd77189641073991cf255e51ab5bdc698a89387b7a58`。新引用包的实际原始资料目录含 13 份响应和 2 份取数清单，共 558661 字节；不以文件数推断全文读取程度。所有本轮取数/核验句柄已终止，无活动实验任务，未提交或推送 Git。

## 后续安全推进

六条核心文献从“尚未核验”推进为“身份/书目信息已核验，导入及插入建议已准备”；冻结正文中的历史待办原话不改。其余 TTC/交通冲突、标准映射、ARI/排名统计引用仍需补核；作者/学校格式、语义设计和正式实验批准仍暂挂。没有新增要求用户重复观看整场景的任务，目标仍未全部完成。
