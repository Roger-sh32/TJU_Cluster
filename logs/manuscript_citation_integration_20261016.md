# 方法稿引文集成记录

## 实际工作

依据持续推进、人工审核/决定先暂挂，本轮将已经核验的两份RIS引用集成到[独立补注件](F:/Scene_cluster/outputs/论文初稿/方法与开发验证事实稿_引文补注_20261016.md)，不改原20261015正文、公式、14行事实表或其原始证据索引。不是新增方法设计、正式规范稿或实验结果。

流程为reference-mgmt/citation-file-mgmt：只复用已有来源内容，不新检索、下载、推测文献字段或替换为其他刊物。书目仍采用本地R01–R12定位，不替作者决定学校最终引用格式；R编号不与S01–S25内部工程来源编号混用。标准版本/条款选择、作者审定、正式结果与实验决策继续暂挂。

新件真实内容：7个可识别的C01–C07补注块、原稿全文、12条全作者书目和版本/缺项限制说明。不是只建立待填空壳。C01用于数据集归属，C02用于TTC背景，C03区分算法与软件来源，C04保留本地组合评分归属，C05区分ARI与标签准确率，C06只给后续评价来源，C07解释原稿历史待补语句及最新执行缺口。

新增内容用`CITATION_ADD`标记；原文在`PARENT_TEXT`区段中。剥离标记块后必须逐字节恢复旧正文，因而原公式、数值、版本说明和内部证据标记未变。原文日期和旧待补句子不被偷偷更新为新结果，当前状态由补注和独立执行审计明确说明。

## 生成与来源

原稿及两份RIS以PowerShell `Get-Content -Raw -Encoding utf8 | ConvertTo-Json -Compress`读取；在工具编排内存中按唯一小节标题插入补注、解析两份RIS并逐条转写全作者/题名/年份/出版字段。文稿和集成索引用`apply_patch`新建，未使用Python写稿、复制覆盖原稿或运行旧seal。随后只修正了新件的R04出版社信息及三个多余句点，未动作者名字或原正文。

原始资料/书目核验已经分别记录在 `logs/method_reference_verification_20261016.md`、`logs/ttc_evaluation_reference_verification_20261016.md`；本次不把重复排版视作又核验了原论文全文。

[本次集成索引](F:/Scene_cluster/logs/manuscript_citation_integration_20261016.json)登记8份输入、7个补注位置、12条RIS核心记录及新件输出摘要；状态`draft_requires_author_and_school_review`。索引记录核验范围，不是自动正式批准，也没有刷新旧写作证据索引。

原稿SHA256 `e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536`；旧写作索引SHA256 `d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9`。新件32988字节，SHA256 `b704476aa4a577aa16d257679dc596fd1af5b3f567f47d01b4e9c676bc6754e6`。

## 独立复核与限界

Confucius只读复核未发现可确认P1/P2：补注没有把论文引用当成700/150划分、工程阈值、组合评分、真实评价成绩或旧网格已修的依据；12条作者、标题、年份、DOI/页码与两份RIS相符，UMAP版本及R10缺页码明确。独立剥离7块后也得到原正文逐字节同一摘要。复核未联网、改文件、跑实验或执行旧verifier；不覆盖本次随后生成的集成索引/日志。后续三个句点的排版调整不改变书目字段。

旧verifier只核验旧稿已登记的事实/来源，不能声称它审核了新补注。以下是本次有限机械检查：来源/输出摘要、原文回退、ID/锚点、RIS核心转写和本地链接；不是引文充分性、全文公式或学校格式验收。

## 只读核验命令

```powershell
@'
from pathlib import Path
import json,hashlib,re
idx=json.loads(Path('logs/manuscript_citation_integration_20261016.json').read_text(encoding='utf8'))
assert idx['kind']=='citation_annotation_only' and idx['status']=='draft_requires_author_and_school_review'
assert len(idx['source_records'])==8 and len(idx['annotations'])==7 and len(idx['bibliographic_core'])==12
for rec in idx['source_records']+[idx['output']]:
    raw=Path(rec['path']).read_bytes()
    assert len(raw)==rec['bytes'] and hashlib.sha256(raw).hexdigest()==rec['sha256'],rec['path']
assert idx['parent_expected_sha256']=='e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536'
assert idx['parent_index_expected_sha256']=='d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9'
p=Path('outputs/论文初稿/方法与开发验证事实稿_20261015.md').read_bytes()
assert hashlib.sha256(p).hexdigest()==idx['parent_expected_sha256']
assert hashlib.sha256(Path('outputs/论文初稿/方法与开发验证事实稿_20261015_证据索引.json').read_bytes()).hexdigest()==idx['parent_index_expected_sha256']
d=Path(idx['output']['path']).read_text(encoding='utf8')
assert d.count('<!-- PARENT_TEXT_BEGIN -->')==d.count('<!-- PARENT_TEXT_END -->')==1
body=d.split('<!-- PARENT_TEXT_BEGIN -->\n',1)[1].split('<!-- PARENT_TEXT_END -->',1)[0]
pat=r'<!-- CITATION_ADD_BEGIN (C\d+) -->\n.*?<!-- CITATION_ADD_END \1 -->\n\n'
assert re.findall(pat,body,re.S)==[a['id'] for a in idx['annotations']]
assert re.sub(pat,'',body,flags=re.S).encode('utf8')==p
expected={f'R{i:02}' for i in range(1,13)}
assert set(re.findall(r'\[(R\d{2})\]\(#ref-r\d{2}\)',body))==expected
assert set(re.findall(r'^\*\*(R\d{2})\*\*\.',d,flags=re.M))==expected
assert len(re.findall(r'<a id="ref-r\d{2}"></a>',d))==12
for a in idx['annotations']:
    text=re.search(r'<!-- CITATION_ADD_BEGIN '+a['id']+r' -->\n(.*?)<!-- CITATION_ADD_END '+a['id']+r' -->',body,re.S).group(1)
    assert set(re.findall(r'\[(R\d{2})\]',text))==set(a['reference_ids'])
ris=[]
for name in ['方法原始引用_20261016.ris','TTC与评价补充引用_20261016.ris']:
    text=Path('outputs/论文初稿',name).read_text(encoding='utf8')
    for b in re.split(r'\nER  -\s*(?:\n|$)',text.strip()):
        if not b.strip(): continue
        r={}
        for line in b.strip().splitlines():
            m=re.fullmatch(r'([A-Z0-9]{2})  - (.*)',line)
            if m: r.setdefault(m[1],[]).append(m[2])
        ris.append(r)
assert len(ris)==12
for r,core in zip(ris,idx['bibliographic_core']):
    assert all(core[k]==r[k] for k in core)
    rid=r['ID'][0]
    entry=re.search(r'^\*\*'+rid+r'\*\*\..*$',d,re.M).group(0)
    for value in r['AU']+r['TI']+r['PY']+r.get('DO',[])+r.get('UR',[]): assert value in entry,(rid,value)
    if 'SP' in r: assert r['SP'][0] in entry
    if 'EP' in r: assert r['EP'][0] in entry
    if rid=='R10': assert ': 1–26' not in entry and 'SP' not in core and 'EP' not in core
for link in re.findall(r'\]\((F:/Scene_cluster/[^)]+)\)',d): assert Path(link).exists(),link
print('VERIFIED 8 inputs, exact original-body rollback, 7 annotation blocks, 12 references and local links; no experiment')
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'citation_integration_check','exec'))"
```

此命令不会重跑原实验或取数，不修改任何来源/输出；发现摘要差异时应检查实际版本，不刷新旧或新索引来消除失配。

## 未完成

有限核验命令已从本日志实际提取执行，exit0，确认8份来源/新件摘要、精确原文回退、7补注块、12条引文及本地链接；不调用旧verifier或运行任何实验。集成索引SHA256 `2bc20746226abfad35f4f4b4015d94a712f4536dc1071f515a879a75f0136431`，新件SHA256仍为 `b704476aa4a577aa16d257679dc596fd1af5b3f567f47d01b4e9c676bc6754e6`。README/CHANGLOG/AGENTS/HDBSCAN说明已登记本版。Codex文件面板打开请求返回queued，仅说明已排队，不声称当前窗口已显示或已渲染审查。未提交/推送Git。

新件仍待作者判断补注是否进入正文、学校样式及章节/公式编号。R10页码、标准全文细节、正式特征/参数/对照方案、同源全量结果和独立专家评价都没有因加引用而完成。旧网格P2仍未修复，v7仍为固定29重放；本轮不做新提取、拟合、排序、媒体或评价，不要求重复人工看场景。整体目标保持未完成。
