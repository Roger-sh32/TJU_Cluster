# TTC与评价指标引用核验

## 范围

依据持续推进、人工审核或决定先暂挂的要求，本轮补充 R07–R12 六条引用并逐项对照本地实现。上一轮六条方法引用包保持不变，本轮也不改冻结正文、统计模块、特征候选或实验协议。日期 2026-10-16（Asia/Shanghai）；环境 PowerShell、`D:/Python/Conda/envs/autodrive-cluster/python.exe`。

执行 citation-verification/reference-mgmt 工作流；没有可用 academic-search MCP，使用 Crossref、PubMed、作者/出版社及FHWA官方来源。TLS 显式使用 certifi CA，证书和主机名校验开启；没有安装包、更改证书库或关闭验证。

交付：[RIS](F:/Scene_cluster/outputs/论文初稿/TTC与评价补充引用_20261016.ris)、[可复用引用与口径边界](F:/Scene_cluster/knowledge/wiki/TTC与评价指标引用边界_20261016.md)。后者可用于下版正文，但不是新正文或正式指标批准。R10只核验核心书目，页码留空；其余六条的核心字段不等于全文公式已读。

## 实际取得的材料与失败

`knowledge/sources/参考文献/TTC与评价引用元数据_20261016/` 保存12份实际响应：5份Crossref JSON、R07 PubMed XML、R08 Springer HTML、R09作者官网及两节HTML、R12官方登记页及第2章HTML。两份清单另记14次请求的地址、实际UTC时间、状态、长度和SHA256。

两次主机失败明确保留：R09初试URL `evaluation-of-unranked-retrieval-1.html` 返回404，随后沿已读排序页的官方链接定位正确的 `evaluation-of-unranked-retrieval-sets-1.html` 并成功保存；R11 Wiley直连403，无成功文件。浏览工具曾读到Wiley官方摘要，引用高层背景时标注该来源，但不伪造本地全文或以HTTP成功替代内容审核。

PubMed普通网页和Project Euclid页面在浏览工具中只有空/不完整抽取；R07改用NCBI官方efetch XML取得摘要。R10仅有Crossref核心书目，未用二手页码补空，也未声称读过其全文。没有付费访问绕过。TU Delft馆藏搜索中标题末尾截断、把33填在期号；没有采用这些有冲突的字段覆盖Crossref/PubMed。FHWA官方报告日期是June2008，不按二手引用中的May2008。

主取数session `70843` 已退出0，补充取数退出0；无活动取数/实验进程。未下载新PDF、媒体或数据集，未读取真实150评价特征/视频/标签，未拟合模型或运行统计实验。网页文字阅读是有限参考资料核对，不是整篇/整报告审阅。

## 取数复现

以下为两次实际取数的共同执行体；`items`分别使用下列主取数/补充清单，`manifest_name`分别为 `retrieval_manifest.json`/`retrieval_supplement.json`。实际命令通过PowerShell here-string传给环境Python的stdin，主取数同时在终端打印5份Crossref核心字段。这里只保留相同取数与原始摘要步骤，省略不影响原始响应的终端打印展开。**不要在已有目录重跑或覆写清单**；目录已有材料，以离线检查为后续入口。

```python
from pathlib import Path
import urllib.request, ssl, certifi, json, hashlib, datetime
root=Path('knowledge/sources/参考文献/TTC与评价引用元数据_20261016')
root.mkdir(parents=True,exist_ok=True)
# First executed request list (manifest_name='retrieval_manifest.json').
items=[('R07_crossref.json','https://api.crossref.org/works/10.1016/S0001-4575(00)00019-1'),('R08_crossref.json','https://api.crossref.org/works/10.1007/BF01908075'),('R09_crossref.json','https://api.crossref.org/works/10.1017/CBO9780511809071'),('R10_crossref.json','https://api.crossref.org/works/10.1214/aos/1176344552'),('R11_crossref.json','https://api.crossref.org/works/10.1111/j.1467-9868.2007.00593.x'),('R09_stanford.html','https://nlp.stanford.edu/IR-book/'),('R09_ranked.html','https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html'),('R09_unranked.html','https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-1.html'),('R12_fhwa.html','https://www.fhwa.dot.gov/publications/research/safety/08051/')]
manifest_name='retrieval_manifest.json'
# The second execution replaced items and manifest_name with:
# items=[('R07_pubmed.xml','https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=11189125&retmode=xml'),('R08_springer.html','https://link.springer.com/article/10.1007/BF01908075'),('R09_unranked_sets.html','https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-sets-1.html'),('R11_wiley.html','https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-9868.2007.00593.x'),('R12_fhwa_chapter2.html','https://www.fhwa.dot.gov/publications/research/safety/08051/02.cfm')]
# manifest_name='retrieval_supplement.json'
ctx=ssl.create_default_context(cafile=certifi.where()); records=[]
for name,url in items:
    r={'file':name,'requested_url':url,'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TJU-Cluster-reference-audit/1.0'}),context=ctx,timeout=20) as response:
            b=response.read(); r.update(final_url=response.geturl(),status=response.status,content_type=response.headers.get('Content-Type'))
        if name.endswith('.json'): json.loads(b)
        with (root/name).open('xb') as f: f.write(b)
        r.update(saved=True,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    except Exception as e: r.update(saved=False,error=type(e).__name__+': '+str(e))
    records.append(r); print(r)
with (root/manifest_name).open('x',encoding='utf8') as f:
    json.dump({'client_date':'2026-10-16','tls':'Verified certifi CA; hostname and certificate checking enabled','records':records},f,ensure_ascii=False,indent=2)
```

## 有限离线复查

以下检查不联网、不导入模型或评价模块、不执行新实验、不覆写原始材料。检查六条RIS的结构/核心字段与对应原始来源、12份响应摘要、两条失败记录和指定既有文件的原始摘要。它不验证每一句文字、全文公式或本统计方法的覆盖率。

```powershell
@'
from pathlib import Path
import re, json, hashlib, html, xml.etree.ElementTree as E
root=Path('knowledge/sources/参考文献/TTC与评价引用元数据_20261016')
saved=[]; failed=[]
for name in ['retrieval_manifest.json','retrieval_supplement.json']:
    for r in json.loads((root/name).read_text(encoding='utf8'))['records']:
        if not r['saved']:
            assert not (root/r['file']).exists()
            failed.append(r['file']); continue
        b=(root/r['file']).read_bytes()
        assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['file']
        saved.append(r['file'])
assert len(saved)==12 and failed==['R09_unranked.html','R11_wiley.html']
records=[]; cur=None
for line in Path('outputs/论文初稿/TTC与评价补充引用_20261016.ris').read_text(encoding='utf8').splitlines():
    if not line: continue
    assert re.fullmatch(r'[A-Z0-9]{2}  -.*',line),line
    k=line[:2]; v=line[6:]
    if k=='TY': assert cur is None; cur={}
    assert cur is not None
    cur.setdefault(k,[]).append(v)
    if k=='ER': records.append(cur); cur=None
assert cur is None and [r['ID'][0] for r in records]==['R07','R08','R09','R10','R11','R12']
assert [r['TY'][0] for r in records]==['JOUR','JOUR','BOOK','JOUR','JOUR','RPRT']
old=Path('outputs/论文初稿/方法原始引用_20261016.ris').read_text(encoding='utf8')
dois=re.findall(r'^DO  - (.+)$',old,flags=re.M)+[r['DO'][0] for r in records if 'DO' in r]
assert len(dois)==11 and len(set(d.lower() for d in dois))==11
for r in records:
    for field in ['TY','ID','AU','TI','PY','UR','N1']: assert r.get(field),(r,field)
    rid=r['ID'][0]
    if rid=='R12': continue
    m=json.loads((root/(rid+'_crossref.json')).read_text(encoding='utf8'))['message']
    assert r['DO'][0].lower()==m['DOI'].lower() and r['TI'][0]==html.unescape(m['title'][0])
    assert r['AU']==[a['family']+', '+a['given'] for a in m['author']]
    assert r['PY']==[str(m['published']['date-parts'][0][0])]
    if rid=='R09': assert r['SN'][0] in m['ISBN']; continue
    assert r['VL']==[m['volume']] and r['IS']==[m['issue']]
    assert r['JO']==[html.unescape(m['container-title'][0])]
    if rid=='R10': assert not m.get('page') and 'SP' not in r and 'EP' not in r
    else: assert r['SP'][0]+'-'+r['EP'][0]==m['page']
xml=E.fromstring((root/'R07_pubmed.xml').read_bytes())
assert xml.findtext('.//PMID')=='11189125'
assert ''.join(xml.find('.//ArticleTitle').itertext()).rstrip('.')==records[0]['TI'][0]
assert any(x.text.lower()==records[0]['DO'][0].lower() for x in xml.findall('.//ArticleId') if x.get('IdType')=='doi')
fhwa=html.unescape((root/'R12_fhwa.html').read_text(encoding='utf8'))
for value in ['Douglas Gettman','Lili Pu','Tarek Sayed','Steve Shelby','FHWA-HRT-08-051','June 2008']: assert value in fhwa,value
assert 'DO' not in records[-1] and records[-1]['M1']==['FHWA-HRT-08-051'] and records[-1]['DA']==['2008/06']
chapter=html.unescape((root/'R12_fhwa_chapter2.html').read_text(encoding='utf8'))
assert '1.5' in chapter and 'PET' in chapter and 'TTC' in chapter
expected={'HDBSCAN/scripts/evaluation_metrics.py':'1c4f1cf858953a4244cb19d5ed3313a752105c1c109784c4f9a9915f1ebbe7dc','HDBSCAN/scripts/seed_stability.py':'96f7886d3522b8bcbce82c9e6bb2bbc516ee3fb235c5d6d77acf4fe405f8ff9d','HDBSCAN/scripts/scene_feature_hdbscan_v5_2.py':'a34af552a0bdc396cec210aed1ebf63c5e20d75c0e084f987e51c1d3302e2974','HDBSCAN/scripts/longitudinal_candidate_v7.py':'33059b93410c70148d161ce7adf94c1d58f1e96167edff31ce0f9157c76c5a3e','outputs/论文初稿/方法与开发验证事实稿_20261015.md':'e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536','outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json':'d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9','outputs/论文初稿/方法原始引用_20261016.ris':'e73c12bf2d39a567ce061c4f0096c3fb9b1fb8364dbff876a17fe2cb6b8524eb','outputs/论文初稿/方法原始引用与插入建议_20261016.md':'c1efd2c7ae0f9efe3947dd77189641073991cf255e51ab5bdc698a89387b7a58'}
for p,h in expected.items(): assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
print('VERIFIED 6 reference core records, 12 raw responses, 2 explicit failures, 8 preserved files; R10 pagination unverified')
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -
```

## 结论与未完成项

本日志中的离线复查代码块已实际执行两次，均exit0：六条核心书目、12份真实响应及两条失败记录相符，指定八文件摘要未变。另只读确认冻结划分清单 `log_counts.evaluation=12`，说明文件全部本地链接可达。原始目录实际14文件（12响应+2清单），合计517639字节；没有把失败请求算成已存原文。

独立只读复核（Confucius）未发现可确认P1/P2：六条书目与可用本地来源一致；TTC/ARI/名单重合、条数预算、未知边界及固定排序区间的说明与四份指定代码相符。复核未独立核验Wiley浏览工具访问过程、全文公式或导入兼容性，未编辑、联网、运行实验或访问评价语义。主代理随后补了“统计分组不是HDBSCAN簇”的解释及冻结划分清单链接，并复查链接、日志数量和交付文件摘要；没有扩展为方法语义验收。

本轮交付RIS SHA256 `e79aea95e4a4ddc476db6d701594d366303e98a3064d545ca756fc8c55522f3d`（3786字节）；wiki说明 SHA256 `49c8dd344829ca59d493ce1b052e1d0b62dea70a64889467fb96933bacf92206`（10793字节）。README、CHANGLOG、AGENTS、wiki索引和暂挂导航仅增加本轮状态；旧方法引用包/写作包及四份代码保持原摘要。未提交或推送Git。

本轮只补安全/评价引用与实现边界，不把SSAM默认值移植为规则，不更改已封印模块，不把ARI/名单重合、场景数预算、合成统计或有限开发反馈写成独立安全精度、时间/里程收益或显著性结论。

R10页码/原文、标准条款映射、专家序数一致性和正式指标/参数冻结仍未完成。需要作者/专家决策的继续暂挂；已有人工作答的整场景不重复索取。没有运行HDBSCAN测试套件、真实统计或旧写作包全依赖核验；本轮指定八文件摘要检查不能扩张为所有历史产物均已验证。整体目标继续保持未完成。
