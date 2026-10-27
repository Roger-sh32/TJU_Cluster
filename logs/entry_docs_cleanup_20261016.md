# 项目入口现状与历史分离

日期：2026-10-16，Asia/Shanghai。前一目标轮补查旧网格绑定，属于实际进展。本轮修正当前入口中的过期陈述和可误执行历史命令，不修改生产代码、结果、封印或环境。

## 发现与处理

根README的长时间线与底部现状冲突：后续记录已说明限定媒体恢复，底部仍写150条媒体缺失/暂缓下载；环境段仍把历史卡顿整体称作当前未修复，流程把旧33条回归当当前表，并重复保留R10页码未核验。另有直接用environment.yml重装/`--prune`的操作说明，容易与冻结运行环境要求混淆。

HDBSCAN README保留了两处旧网格命令，其中一处是完整参数搜索而不是preflight，还同时将850条旧表/V2状态称作“当前”。本轮不抹去这些历史内容，而是标明历史日期与不执行边界，旧命令改为text留痕，取消当前推荐的含义。

具体编辑：

- 根 `README.md` 缩为当前状态、任务导航、目录约定、两条只读检查、来源/历史和Git边界；不再附长时间线，逐次内容由CHANGLOG/日志及原样快照保留。
- `HDBSCAN/README.md` 给旧评价准备与早期目录/执行顺序加历史警示，六段早期PowerShell命令及旧preflight留为不可执行推荐的text示例；保留原数值、批次表和说明。
- `docs/development_environment.md` 仅追加历史初始化提示，原2026-06-27内容保留，不重新验证或改变其中机器级配置。

新入口区分：限定恢复不等于全库/盲评包验收；主环境小矩阵探针不等于完整UMAP就绪；v4完整700不等于v6.1/v7全量；旧模型/TopK不等于当前正式成绩；作者和实验决定仍暂挂。

## 原样快照与绑定边界

编辑前，用PowerShell `Copy-Item -LiteralPath` 逐份复制到新建 `logs/entry_docs_before_20261016/`，拒绝覆盖已有目录；每份原文件与副本SHA256相同后才编辑。快照仅追溯旧文字，不作为当前指南。

| 快照 | 原字节数 | SHA256 |
| --- | ---: | --- |
| `root_README.md` | 18273 | `ad6d969ea1cd172cfb90d6a4c2e6e1b73aae21a9858489541871c30b4b0e43f3` |
| `HDBSCAN_README.md` | 50920 | `01e04f61fff38a11a15a6a2bd5fd7b10625d0115e5163f7aad0414f438bf846b` |
| `development_environment.md` | 9285 | `bad61b34ae0ef0ffb2b68a3f57c7cc18d0c81236f4bc87776c2c94f0d4a03508` |

编辑前只读查询既有180份可读JSON清单中path/sha256记录，未发现三份入口文件的直接文件记录绑定。此检查不覆盖拒读、排除区域或不同格式的间接关系，不据此声称全局无绑定；本轮也不编辑那些既有JSON/实验文件。原媒体恢复报告摘要 `ec708a4c29f1320a2b585b25ccef82efd95d63fb098af1e6c8f1fd6c3f7add3f` 及completed状态绑定另查相符，未打开图像。

一次初始apply_patch尝试因同一补丁对README同时Delete/Add而被拒绝，未修改任何文件。随后确认根README仍与原样快照相同，改为单次Update整段替换，再处理其余入口；没有删除数据或回滚用户内容。

## 实际只读命令检查

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -c "import sys; print(sys.executable)"
& D:/Python/Conda/envs/autodrive-cluster/python.exe HDBSCAN/scripts/review_nuscenes_scenes.py --help
```

两条已实际执行exit0，前者输出 `D:\Python\Conda\envs\autodrive-cluster\python.exe`，后者显示回看CLI选项。没有nuScenes表加载、场景提取、图像读取/导出或拟合；这不是完整依赖或UMAP性能测试。

## 实际复核结果

只读内存检查exit0：21项预先给定SHA256全部相同，包含三份原样快照、原方法稿/索引、引文补注稿/索引、第六章稿/索引、十个关键生产模块、媒体恢复报告及网格绑定清单。未改这些文件或刷新摘要。根README的20个本地Markdown链接全部存在；其PowerShell块为1个，HDBSCAN README为0个，旧grid命令仅留在text历史块。没有声称历史HDBSCAN所有旧路径均有效。

环境文档移除新增提示后，文本与原样快照完全相同；三个快照同时进行了字节SHA验证。根README已取消过期媒体缺失、旧回归“当前”、R10缺页码及Conda重装指令；此前OpenCV无GUI是历史观察，本轮未重新验GUI。

另按第六章登记配方执行只读检查（未传register），没有任何提取或拟合。实际命令：

```powershell
@'
from pathlib import Path
import re,sys
text=Path("logs/experiment_chapter_writing_20261016.md").read_text(encoding="utf8")
block=re.search(chr(96)*3+r'powershell\s*\n(.*?)'+chr(96)*3,text,re.S).group(1)
code=block.split("@'\n",1)[1].split("\n'@",1)[0]
sys.argv=["experiment_chapter_documented_recipe","--expected-index-sha","4e14e158b4b364fe8c26b444f8064995c8653ebeed90c8c8d99ff72c1f6fb3cd"]
exec(compile(code,"experiment_chapter_documented_recipe","exec"))
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'readonly_chapter_check','exec'))"
```

第六章检查实际exit0，输出 `VERIFIED new chapter document/source hashes, selected summary facts and E IDs; no formal results`、`SOURCE_BINDINGS 26`。这仅覆盖原配方限定范围。

独立窄审仅比较指定入口和三份快照文本，未发现有根据的P1/P2；未执行命令、核源码或评价语义，链接/SHA由主线程另查，不能称环境/语义/评价验收。复核后将根README的GUI断言进一步限定为历史观察，并更新AGENTS/CHANGLOG导航。最终导航/20个链接/日志围栏检查exit0；限定六个本轮编辑文件的 `git diff --check -- README.md HDBSCAN/README.md docs/development_environment.md AGENTS.md CHANGLOG.md logs/entry_docs_cleanup_20261016.md` exit0（未跟踪新日志由围栏/文本检查另覆盖）。没有运行代码测试或全仓库完整性检查。

未提交或推送Git，未实施任何暂挂修复。正式实验及作者/专家决定仍待处理，本项目目标未完成。
