# 标准与特征对应审计

## 范围与产出

依用户持续推进、需人工决定先暂挂的要求，核对之前提供的五个官方入口，制作[来源与特征边界](F:/Scene_cluster/knowledge/wiki/标准来源与现有特征映射_20261016.md)及[52字段审阅索引](F:/Scene_cluster/knowledge/wiki/标准特征审阅索引_20261016.json)。七组为文档导航，不是新增模型特征组、正式消融配置或标准符合性清单。论文整体/正式实验目标尚未完成。

本轮没有修改现有源码、阈值、字段、分组评分、数据划分或模型，没有取评价150语义/标签、拟合、重提场景、导出场景GIF或下载nuScenes数据。新增的一份公开规程PDF及两个页面预览是**参考资料**，不是场景媒体、实验成绩或论文图表。本轮未运行HDBSCAN测试套件或旧写作包全依赖核验。

环境：PowerShell；网络及字段核对用 `D:/Python/Conda/envs/autodrive-cluster/python.exe`，TLS显式使用certifi CA并保持证书/主机校验；PDF使用Codex内置依赖 `C:/Users/MSI/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` 中的pypdf/pypdfium2。没有安装依赖或改Conda。日期2026-10-16，取数清单保留实际UTC时间。

## 真实资料与限制

原始目录：`knowledge/sources/标准项目/来源核验_20261016/`。主取数为用户原五网址，补取PEGASUS方法页和i-VISTA2026智能安全规程。共6份真实响应、1次ISO403及2份检索清单。

- PEGASUS首页/方法页：核对场景六层、数据映射、参数空间及高速Highway Chauffeur示例。不把其安全论证另一套分层或本索引七组混入六层。
- ENABLE-S3：仅CORDIS项目结果目录，未下载交付物；D编号/标题只是后续可追踪入口，不代表全文已阅。
- ISO34502：web工具读到官方第1版2022-11书目和公开摘要，含受限通行高速范围；主机403，未保存正文或购买标准。不宣称条款级审阅或城市域直接符合。
- i-VISTA：目录有2026/2023修订等版本，本次不替作者选择正式依据。公开PDF标题和95页数量核对，仅读指定少数条款，非全规程审核。
- C-ICAP：用户原链接实际指2024版管理规则及附录目录，不是C-NCAP主动安全细则。未下载一键ZIP或具体附录，不把目录当正文。

原始文件名S13–S17只是本取数任务局部号，不是冻结写作包S01–S25的证据号。本轮不新建混淆两者的RIS记录。

## 错误、诊断与恢复

初次按UTF8读取 `S17_cicap.html` 失败。检查头字节为 `1f8b0800`，确认为gzip响应体；随后仅在内存 `gzip.decompress(...).decode('utf8')`，核对标题/附录链接。压缩原始字节和摘要保留，不覆写、不重复请求或伪装成已解压文件。清单的Content-Type不足以说明传输体是否压缩，本日志显式补注。

浏览工具两次PEGASUS首页方法链接及C-ICAP“一键下载”解析失败；沿实际首页href取得正确PEGASUS方法页。未因一键下载失败扩大为批量下载。i-VISTA浏览工具截图缓存失败后使用已取得本地PDF渲染，未重下PDF。

pypdf抽取物理第6页时数学字形含孤立surrogate，首次终端输出 `UnicodeEncodeError`。随后仅对诊断打印用backslashreplace保留异常转义，并用pypdfium2原页渲染核对公式，未猜测修补原文。主环境缺fitz/pypdf，故使用已配置的内置运行时，而非安装包。两个PNG在 `exports/source_review_20261016/`，均实际打开目视检查。

首次长here-string直交 `python -` 的离线检查两次在stdin报告非UTF8语法错误。检查发现PowerShell OutputEncoding为UTF8，Console InputEncoding为936；短stdin探针和源码AST单独检查可通过。**未查明长命令失败的完整成因，不据此断言Conda环境损坏或代码编码错误。**改用显式UTF8解码后compile的只读stdin入口，完整字段/来源检查通过；没有修改shell全局配置或环境。失败不作为已通过记录。

## 取数复现入口

实际执行为两次下列取数体，`items`/`manifest`分别使用主、补清单；主取数timeout20s，补取timeout25s且最多读取20MiB+1并校验PDF头。这里保留共同步骤及精确URL，不替换/重下载已存资料。实际请求时间、最终URL、长度、SHA256和错误以两个原始清单为准。

```python
from pathlib import Path
import urllib.request, ssl, certifi, json, datetime, hashlib
root=Path('knowledge/sources/标准项目/来源核验_20261016')
root.mkdir(parents=True,exist_ok=True)
items=[('S13_pegasus.html','https://www.pegasusprojekt.de/en/'),('S14_enable_s3.html','https://cordis.europa.eu/project/id/692455/results'),('S15_iso34502.html','https://www.iso.org/standard/78951.html'),('S16_ivista.html','https://www.i-vista.org/autoindex/index5/'),('S17_cicap.html','https://www.c-ncap.org.cn/cncap-guicheng-detail?id=15')]
manifest='retrieval_manifest.json'
# Second execution:
# items=[('S13_pegasus_method.html','https://www.pegasusprojekt.de/en/pegasus-method'),('S16_ivista_safety_2026.pdf','https://www.i-vista.org/d/file/p/2026-06-08/a3ab8a23847dbf7246da78a99d946fab.pdf')]
# manifest='retrieval_supplement.json'
ctx=ssl.create_default_context(cafile=certifi.where()); rows=[]
for name,url in items:
    a={'file':name,'requested_url':url,'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TJU-Cluster-source-audit/1.0'}),context=ctx,timeout=20) as r:
            b=r.read(); a.update(final_url=r.geturl(),status=r.status,content_type=r.headers.get('Content-Type'))
        with (root/name).open('xb') as f: f.write(b)
        a.update(saved=True,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    except Exception as e: a.update(saved=False,error=type(e).__name__+': '+str(e))
    rows.append(a)
with (root/manifest).open('x',encoding='utf8') as f:
    json.dump({'client_date':'2026-10-16','records':rows},f,ensure_ascii=False,indent=2)
```

两次取数均exit0；失败请求在清单中独立保存。工作均已终止，不存在后台实验任务。不得重跑此取数体覆盖原始摘要。

## 有限离线核验命令

```powershell
@'
from pathlib import Path
import ast,json,hashlib,gzip
root=Path('knowledge/sources/标准项目/来源核验_20261016'); raw=[]; failed=[]
for name in ['retrieval_manifest.json','retrieval_supplement.json']:
    for row in json.loads((root/name).read_text(encoding='utf8'))['records']:
        if not row['saved']:
            failed.append(row['file']); assert not (root/row['file']).exists()
            continue
        b=(root/row['file']).read_bytes()
        assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
        raw.append(row['file'])
assert len(raw)==6 and failed==['S15_iso34502.html']
p=Path('HDBSCAN/scripts/feature_selection.py'); b=p.read_bytes(); tree=ast.parse(b)
fields=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CLUSTERING_FEATURES' for t in n.targets))
m=json.loads(Path('knowledge/wiki/标准特征审阅索引_20261016.json').read_text(encoding='utf8'))
assert hashlib.sha256(b).hexdigest()==m['feature_source_sha256']
flattened=[f for g in m['groups'] for f in g['features']]
assert flattened==fields and len(fields)==len(set(flattened))==m['expected_feature_count']==52
assert m['status']=='reference_audit_only_not_experiment_configuration'
b=(root/'S17_cicap.html').read_bytes()
assert b.startswith(bytes.fromhex('1f8b')) and 'C-ICAP(2024' in gzip.decompress(b).decode('utf8')
assert (root/'S16_ivista_safety_2026.pdf').read_bytes().startswith(b'%PDF-')
print('VERIFIED 52 exact ordered fields / groups',[len(g['features']) for g in m['groups']],'; 6 raw responses / 1 explicit failure')
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; b=sys.stdin.buffer.read(); exec(compile(b.decode('utf8'),'audit_stdin','exec'))"
```

此命令已exit0，组字段数 `7/6/12/6/8/4/9`，总52，无重复且原顺序一致。不导入提取器或加载场景数据；AST只用于读取常量。检查并不证明每个字段与标准条款相符、规则准确或数值有效。

PDF检查/渲染使用 `PdfReader`，确认95页，读取物理第6/30/31/32页；pypdfium2渲染第6/30页、scale1.4，保存为 `ivista_2026_p6.png` 和 `ivista_2026_p30.png`。条款3.15公式与5.2.2.7图文经实际图像查看，不依赖损坏的抽取字形。没有对其余整份规程的表格/评分做核验。

## 后续

独立只读复核（Confucius）先发现一条P2：条款映射中“路线分离只是暴露”的绝对表述可能否定成功让行后的历史交互。主代理核对 `scene_feature_rules.py` 中 `not yielding_response` 的保护条件，**仅修正文档**：区分无实质约束暴露与响应后的路线分离，明确已观测路线不是反事实路线、不能统一关闭保护。复核者定向复查确认P2已消除、无残余同类P1/P2；未改文件、联网或运行实验。ISO摘要没有本地成功响应，独立核验限度保留；也不代表其已审完整PDF或所有公式。

日志内离线检查又从Markdown实际提取执行，exit0；52字段/6原始响应/1失败记录重验通过，本地引用链接可达。另一次独立只读摘要命令确认四份指定模块及原写作正文/证据索引未变：v5.2提取器 `a34af552a0bdc396cec210aed1ebf63c5e20d75c0e084f987e51c1d3302e2974`、rules `6a21d3d56a08fe7ee60e9143dbb0aa1d3db02f573cfb4206eed17062c92e181d`、v7 `33059b93410c70148d161ce7adf94c1d58f1e96167edff31ce0f9157c76c5a3e`、v6.1 `f13e3603aa95b532c04c39d5a03e3df84049b6f6b4a5374ec68a8f2210befc7b`；正文 `e3cd1034ba06ce052db5ed0ef6f129e1090e6ecf412faff40c2cbe675fd6b536`、写作索引 `d7b82321ea70e63293a20668ea88d99763597b8a9692465095a9ccdaf0d18ac9`。这些指定文件检查不扩张成所有历史产物已重验。

交付说明8701字节，SHA256 `1aea1a606787fe921857b5b4d693c90123d62f256d14b1bff8f76f038b99ef99`；审阅JSON4068字节，SHA256 `c45cc0bb6d6e9d9f30cb5c60d22662487bdaa79c92075eebb5277a8da9d56166`。README/CHANGLOG/AGENTS/wiki索引/暂挂导航已加本轮状态。一次JS编排语法失败和一次补丁上下文不匹配没有执行文件改动；检查实际内容后用短上下文成功应用，无重复条目。未提交或推送Git。

当前结论仅推进到“来源身份/适用边界+52字段审阅索引+少数i-VISTA条款”。C-ICAP附录全文、ISO条款及适用域、C-NCAP/Euro NCAP具体协议、ENABLE-S3交付物细节仍需按需核对；本轮不是全部标准条款完成。护栏、遮挡、施工、环境质量和实时控制证据仍是能力缺口，不能把目录检索或字段统计包装为覆盖率。

特征设计、正式规程版本、模型/参数和专家评价决策继续暂挂；不自动扩大实验、不重索已有整场人工反馈。可继续推进有限的原文核对或论文事实/引文整理，不能用这些资料代为通过语义或正式方法审批。
