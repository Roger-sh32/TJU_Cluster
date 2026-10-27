# 当前候选版本开发 700 条重建

## 授权与边界

用户在讨论“冻结候选特征、保留 0552 待验、重建当前来源开发 700 条”后明确回复“好的 那开始吧”。本次执行此方案，不再修改特征算法，不把候选冻结写成全部特征有效。

- 候选版本：`feature_candidate_v4_20261001`。
- 数据：`nuScenes v1.0-trainval`，冻结自定义开发 700 / 评价 150 划分，仅提取开发成员。
- 预期结构：700 行、129 列、52 聚类字段；这是核验目标，不是已完成结果。
- 0552 的新风险下调继续待验；其他新变化同样进入审查，不自动认可改善。
- 不拟合、不选正式参数、不替换模型或排序、不跑 KMeans、不使用评价反馈、不下载媒体、不批量导出轨迹/GIF。

## 固定来源

协议：`HDBSCAN/tables/development_candidate700_protocol_20261001.json`，SHA256 `0da16090e6ccf9475eaaaa0b92922c49a9427b59273cd67d4c74caf7d9ddf0ee`。

协议绑定七个源码模块、700 条场景身份及顺序、聚类字段、实际 Python/包版本、核验脚本和测试、两个比较辅助脚本、历史审计 700 条及当前 33 条/七条控制 CSV/sidecar、匹配历史源码、冻结划分与 scene.json。候选源码和划分的实际副本在 `logs/source_snapshot_candidate_20261001/`。准备及每个执行阶段校验哈希，来源变动则拒绝继续核验。

原始输入的哈希覆盖 scene.json，不覆盖所有 nuScenes 大表及地图；不把现有来源记录夸大为完整原始数据存档。数据集目录不修改。

## 命令和环境

工作目录 `F:\Scene_cluster`，解释器 `D:\Python\Conda\envs\autodrive-cluster\python.exe`。运行配方不导入原生 UMAP，不修改 Conda 环境。

实际执行：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest logs.test_development_candidate700_20261001 -v
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest discover -s HDBSCAN/tests -v
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/development_candidate700_20261001.py prepare
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/development_candidate700_20261001.py run
```

`prepare`/`run` 禁止覆盖已有协议/输出/状态，不要重复执行。`run` 设置协议中的环境变量，顺序执行如下预检查和提取，再在同一运行进程中核验结果：

```powershell
$env:SCENE_CLUSTER_MAX_SCENES = '700'
$env:SCENE_CLUSTER_START_INDEX = '0'
$env:SCENE_CLUSTER_SCENE_NAMES = ''
$env:SCENE_CLUSTER_AUDIT_OUTPUT = ''
$env:SCENE_CLUSTER_FEATURE_OUTPUT = 'scene_features_development_candidate700_20261001.csv'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMBA_NUM_THREADS = '1'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONIOENCODING = 'utf-8'
& D:/Python/Conda/envs/autodrive-cluster/python.exe HDBSCAN/scripts/scene_feature_hdbscan.py --preflight
& D:/Python/Conda/envs/autodrive-cluster/python.exe HDBSCAN/scripts/scene_feature_hdbscan.py
```

提取完成后可只读重验已生成报告，不覆盖：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/development_candidate700_20261001.py check --check-only
```

## 状态与产物

2026-10-01 12:50（北京时间）启动，14:25:42 保存完整特征与 sidecar，14:25:58 完成自动核验，整体约 95 分钟。最初回复时检查到 18/700，属于历史运行中检查点，不是当前进度。启动时 wrapper PID 23700、提取 PID 27408、执行会话 86825，仅保留为运行证据，不据旧 PID 判断当前进程。

真实状态见 `logs/development_candidate700_20261001_status.json`，进度见 `logs/development_candidate700_20261001_console.log`。状态中的 `child_exit_code` 在提取运行时暂保留上一阶段 preflight 的退出码，不能据其中的 0 推断提取已完成；应结合 phase、进程和完成产物。

已完成输出：

- `HDBSCAN/tables/scene_features_development_candidate700_20261001.csv` 和 `.manifest.json` / `.quality.json`。
- `HDBSCAN/tables/development_candidate700_comparison_20261001.json`。
- `HDBSCAN/tables/development_candidate700_risk_20261001.csv`，含各分项新旧值及差值，仅用于开发差异诊断，不是新 corner 排名。

## 核验口径

检查开发身份、顺序、来源与 schema；全部 52 聚类字段必须有限，输出数值必须有限；33 条及七条控制必须逐值精确复现。比较全部 129 列与历史审计 700 条，重算新旧分组风险。风险可能因派生门控变化而上升，不要求单调下降。非预期依赖列、风险上升及除 0151 外的新变化场景列为审查项；0552 始终保留待验。

质量审计列出填值前 NaN/Inf、查询异常及分阶段计数；仅两项诊断距离的正 Inf 可视作已知 sentinel，不能解释为实际测量 30 m。质量异常不能被结构通过掩盖。检查器区分来源/结构通过、原始质量是否清洁以及语义未验收；任务完成不自动启动下一轮模型实验。

## 测试与执行反馈

新增七项核验配方测试先失败后通过，原有 HDBSCAN 182 项测试通过。新增测试最初使用 TemporaryDirectory，在当前 Windows 沙箱中子目录不可访问；改为实际文件哈希与不匹配冻结哈希的对照，不改变生产规则。两个本次创建的空目录已清理。此问题不是特征提取失败或 Conda 依赖故障。

启动时仅配方测试通过；实际 700 条随后完成并通过来源/结构/原始质量检查，仍不是语义验收。应先整理新差异与限制，再决定正式参数/模型等下一步。

## 2026-10-03 只读复核

按上述 `check --check-only` 命令重新核验，退出码 0；保存报告、风险表与重新计算结果完全一致，候选源码及绑定输入未变。完成报告 SHA256 `96ab2e1f8cc99bb5bf2d64ace048d40ec26cb1212d2350a21748fe866a6b515e`，状态为 `completed_requires_review`，不是失败或仍在提取。

- 700 条开发成员及顺序完整，129 列、52 聚类字段齐全，所有输出数值有限；无聚类常量字段。
- 当前 33 条及七条回归控制精确复现；地图可用 700 条，intersection_flag 阳性 586 条。
- 查询异常 0，填值前 NaN/负 Inf 0。1,078 个正 Inf 仅在 merge/VRU 诊断距离，分别 494/584 个，不进入聚类输入，仍不是实测距离。
- 相比历史审计表，691 条全字段不变，9 条共 26 个值变化，均在五个已知派生字段内；没有非预期字段变化。
- **聚类字段有一处真实变化**：scene-0002 的 `left_turn_cross_traffic_interaction_ratio` 从 0.1 到 0。不能把小批回归的“全部聚类值不变”结论推广到全 700 条，也不能直接沿用历史拟合当新版本模型。
- 八条风险值下降、无上升；scene-0816 有特征变化但风险未变。下降不自动代表改善，特别是 scene-0815 的变化仅约 -0.00001713。

待审八条：0002、0093、0102、0453、0552、0669、0815、0816；0151 属已确认开发修正，不在这份待审列表。0552 的媒体缺失限制继续保留。下一步先诊断这些变化，再确认正式参数/拟合；本次只更新状态和文档，没有重提、拟合、评价使用或媒体导出。
