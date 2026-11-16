# UMAP原文与项目实现边界核对

## 2026-11-15续办结果

第二通道已于2026-10-27成功结束：HTML 41013字节、PDF 7880321字节，均HTTP200。本次PDF实算SHA256为45ca6cfcd08d5808ab20b5cf53364d2b2d5ab19dca95a594f54af515a15421c3，与原记录一致。显式使用既有certifi CA解决了该次获取，未关闭TLS验证；这不表示整个环境证书问题已永久修复。

本轮无需重下载。用Codex bundled native/poppler/Library/bin/pdftoppm.exe渲染并查看物理页15/20/49。命令形式：pdftoppm.exe -f PAGE -l PAGE -singlefile -scale-to 1500 -png PDF logs/umap_pages_20261115/page_PAGE。PDF为explicit_certifi_ca目录中的原件，输出三张PNG。

新增knowledge/wiki/UMAP原文与项目实现边界_20261115.md。本轮未执行拟合、场景提取或参数修改；仅定向页面检查，无全文证明审查或独立审稿结论。

日期：2026-10-27，Asia/Shanghai。继续补第二章理论依据，不替作者选择方法/正式参数。
上一轮连续阅读版已实际构建并检查，是有效进展；本轮不复跑该构建或修改原稿/索引。

本轮使用academic-search的citation-verification路线。可用工具中没有arXiv/Crossref学术MCP，
因此对已知R02标识直接使用官方arXiv网页/PDF，不用二手博客替代，也不重新做主题检索/书目导出。
既有R02记录为arXiv:1802.03426v3，三作者，版本提交2020-09-18；PDF封面显示2020-09-21，两种日期分别记录，不改旧RIS。

## 范围

- 保存本次实际HTTP响应及取得情况，原始资料只放knowledge/sources。
- 定向阅读PDF计算说明/图构造/交叉熵/局限章节，公式须查看页面图像，不凭损坏的抽取字符抄式。
- 另写简短wiki，区分原文主张、项目代码事实与未实证推论，不新增理论正确性/效果结论。
- 不读评价语义、不提取或拟合、不修改特征、评分或参数；旧章节、来源索引和连续阅读版保留。
- 不声称全63页精读、范畴论证明验收或当前软件与论文完全等价；未取得的HDBSCAN R04/R05全文仍不升级。

浏览工具已能读取v3页面及63页PDF文字；两张公式截图返回引用但未实际显示给本代理，
第49物理页截图另报Cache miss。因此当前不能说已完成视觉核对，需要本地实际下载/渲染后再判定。
浏览页面中的原英文只作定位；新说明以短中文转述和必要数学定义为主，不复制原论文长段落。

## 单次原始资料获取命令

下列代码只向两个固定官方URL请求；每份原始响应独占写入，已有目标时拒绝。
非PDF的成功/失败响应保留为response，不伪装PDF；超时只记录错误，不自动重试。
取得记录生成后保留，不重跑本段覆盖原件。

```powershell
@'
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
folder=Path('knowledge/sources/参考文献/UMAP原理核验_20261027')
if folder.exists():
    raise FileExistsError('Acquisition folder exists; preserve original responses')
folder.mkdir()
requests=[
    ('https://arxiv.org/abs/1802.03426v3','arxiv_v3.html',False),
    ('https://arxiv.org/pdf/1802.03426v3','UMAP_1802.03426v3.pdf',True),
]
records=[]
for url,name,is_pdf in requests:
    started=datetime.now(timezone.utc).isoformat()
    row=dict(url=url,started_at_utc=started)
    try:
        try:
            response=urlopen(Request(url,headers={'User-Agent':'TJU-Cluster source verification'}),timeout=60)
        except HTTPError as error:
            response=error
        with response:
            raw=response.read(20*1024*1024+1)
            row.update(status=response.status,final_url=response.geturl(),headers=dict(response.headers.items()))
        if len(raw)>20*1024*1024:
            raise ValueError('Response exceeded acquisition size limit')
        valid_pdf=bool(raw.startswith(b'%PDF-'))
        target=folder/(name if not is_pdf or valid_pdf else name+'.response')
        with target.open('xb') as stream:
            stream.write(raw)
        row.update(path=target.as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                   pdf_magic=valid_pdf,accepted=bool(row['status']==200 and (not is_pdf or valid_pdf)))
    except Exception as error:
        row.update(accepted=False,error_type=type(error).__name__,error=str(error))
    row['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    records.append(row)
    time.sleep(3.2)
with (folder/'http_acquisition_20261027.json').open('x',encoding='utf8') as stream:
    json.dump(dict(scope='official arXiv raw acquisition only',records=records),stream,ensure_ascii=False,indent=2)
print(json.dumps([{k:r.get(k) for k in ('url','status','path','bytes','sha256','accepted','error_type')} for r in records],ensure_ascii=False))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'umap-source-acquisition','exec'))"
```

## 后续记录

实际获取、页面核对和写作/来源摘要结果在本文件后补；上面的计划/浏览成功不等于本地主机也已取得PDF。

### 获取通道诊断

首次命令退出0只表示写出了失败记录，不表示取得文献：两个Conda请求均在默认TLS上下文触发
`ASN1: NOT_ENOUGH_DATA`，未收到HTTP响应/正文。另一个bundled Python的只读探针报
`CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate`，也未保存任何PDF。
Conda显式加载既有certifi CA可成功建立CERT_REQUIRED且check_hostname=True的上下文；
这只隔离默认信任加载问题，尚不能证明网络握手/全文成功，也不修复整个环境。
当前元数据查询得到umap-learn 0.5.5，仅查包版本，没有导入UMAP或拟合。

以下是分开的、有原因的第二条获取通道，保留第一次记录；不关闭证书/主机名校验、不安装依赖。
保存实际CA文件哈希，不泛称环境修好了。输出路径独占，不覆盖原始失败记录。

```powershell
@'
from pathlib import Path
from datetime import datetime, timezone
import certifi, hashlib, json, ssl, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
folder=Path('knowledge/sources/参考文献/UMAP原理核验_20261027/explicit_certifi_ca')
folder.mkdir()
ca=Path(certifi.where())
context=ssl.create_default_context(cafile=str(ca))
assert context.verify_mode==ssl.CERT_REQUIRED and context.check_hostname
records=[]
for url,name,is_pdf in [
    ('https://arxiv.org/abs/1802.03426v3','arxiv_v3.html',False),
    ('https://arxiv.org/pdf/1802.03426v3','UMAP_1802.03426v3.pdf',True),
]:
    row=dict(url=url,started_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        try:
            response=urlopen(Request(url,headers={'User-Agent':'TJU-Cluster source verification'}),context=context,timeout=60)
        except HTTPError as error:
            response=error
        with response:
            raw=response.read(20*1024*1024+1)
            row.update(status=response.status,final_url=response.geturl(),headers=dict(response.headers.items()))
        if len(raw)>20*1024*1024:
            raise ValueError('Response exceeded acquisition size limit')
        valid_pdf=raw.startswith(b'%PDF-')
        target=folder/(name if not is_pdf or valid_pdf else name+'.response')
        with target.open('xb') as stream:
            stream.write(raw)
        row.update(path=target.as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                   pdf_magic=valid_pdf,accepted=bool(row['status']==200 and (not is_pdf or valid_pdf)))
    except Exception as error:
        row.update(accepted=False,error_type=type(error).__name__,error=str(error))
    row['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    records.append(row)
    time.sleep(3.2)
receipt=dict(scope='official arXiv acquisition with existing explicit CA; TLS verification enabled',
             ca_path=str(ca),ca_sha256=hashlib.sha256(ca.read_bytes()).hexdigest(),
             verify_mode=int(context.verify_mode),check_hostname=context.check_hostname,records=records)
with (folder/'http_acquisition_20261027.json').open('x',encoding='utf8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2)
print(json.dumps([{k:r.get(k) for k in ('url','status','path','bytes','sha256','accepted','error_type')} for r in records],ensure_ascii=False))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'umap-explicit-ca-acquisition','exec'))"
```
