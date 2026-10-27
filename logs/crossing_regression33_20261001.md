# 转弯横向投影扩展回归

日期：2026-10-01。目的：将已修正的 0151 横向直行投影规则扩展到历史回归及分散开发样本，检查意外数值变化；不是专家有效性评价，不新增特征或阈值。

## 固定范围与选择

沿用现有元数据提取/质量审计流程。提取前固定 `HDBSCAN/tables/crossing_regression33_protocol_20261001.json`：33 条冻结开发成员、23 个采集日志、四个地点。21 条为上一轮七条与 review11 的并集；新增 12 条为四地点各三条（转弯且旧横穿预测阳性、旧横穿预测阳性且有停车/制动证据、旧横穿预测零）。优先未使用日志，随机种子 `20261001`，不按重跑结果替换成员。

新增场景：0130、0346、0363、0415、0424、0552、0760、0905、0921、1023、1048、1077。这是富集回归样本，不能用于推断全库误报率、Precision@K 或提效百分比。选择用旧预测值作候选分层，不把这些字段当作人工风险标签。

0905 前视媒体缺失，但本轮只处理元数据，不下载或观看它，不将缺失等同低价值。未导出轨迹或 GIF，预期只新增小表与 JSON 质量/来源报告。

## 来源与环境

- 原始元数据：`nuScenes/v1.0-trainval/`，只读。
- 历史比较：`scene_features_development_audit700_20260927.csv`，与 `logs/source_snapshot_20261001_pre_turning_crossing/` 的 script/schema/rules/audit 哈希核对后只读比较。没有为旧表重签当前 manifest。
- 当前控制：`scene_features_semantic_feedback7_20261001_v4.csv`，当前来源校验通过。
- 当前提取：`HDBSCAN/scripts/scene_feature_hdbscan.py`，使用 v4 规则，不修改提取、评分或拟合源码。
- 环境：`D:/Python/Conda/envs/autodrive-cluster/python.exe`，四项计算线程设为 1。新来源及冻结 split 哈希在固定方案内。
- 新表：`HDBSCAN/tables/scene_features_crossing_regression33_20261001.csv` 及质量/来源 sidecar。

## 可复现命令

固定方案只创建一次，已有文件时拒绝覆盖：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/crossing_regression33_20261001.py prepare
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMBA_NUM_THREADS='1'
$protocol=Get-Content -Raw HDBSCAN/tables/crossing_regression33_protocol_20261001.json | ConvertFrom-Json
$env:SCENE_CLUSTER_SCENE_NAMES=$protocol.scene_names -join ','
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_crossing_regression33_20261001.csv'
Remove-Item Env:SCENE_CLUSTER_AUDIT_OUTPUT -ErrorAction SilentlyContinue
& D:/Python/Conda/envs/autodrive-cluster/python.exe HDBSCAN/scripts/scene_feature_hdbscan.py --preflight
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py 2>&1 | Tee-Object -FilePath logs/crossing_regression33_extraction_20261001_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/crossing_regression33_20261001.py freeze-check
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/crossing_regression33_20261001.py check
```

已通过 preflight：33 条全部为冻结开发成员。最终核验需等待实际提取完成：核对 129 列、身份、52 聚类字段、原始质量审计、七条控制复现、新旧逐值差异和各风险分项。发生异常或不符合预期的变化时不自动重拟合、调整规则或将结果认定有效。

核验产物：`crossing_regression33_comparison_20261001.json`、`crossing_regression33_risk_20261001.csv`。后续 `check --check-only` 重算核对既有产物，不覆盖。没有拟合模型、选择最终参数、改旧排序、使用评价数据或启动 KMeans。

## 执行状态

提取已正常结束（退出码 0），33 条、129 列；七条 v4 控制精确复现，当前来源检查通过。对比已完成，全部 52 聚类字段不变；31 条全部数值不变，只 0151/0552 的六个横向派生单元变化。**计算/来源核验完成，语义仍需要复核 0552**，不能将结构检查写成准确性通过。

## 检查器审查与方案补充

独立审查发现比较配方的三个问题，均发生在分析检查器而不是提取/评分源码：风险总分不保证单调下降（移除左转交互门控可能恢复 merge 风险）；左转交互变化可联动路线绕行标记/决策需求，原允许字段漏列；原方案记录了配方哈希但核验没有强制检查且未绑定导入的比较 helper。

在读取新提取数值前，保留原配方逐字节副本 `logs/crossing_regression33_20261001_pre_review.py`，SHA256 `51c8cc4a6f0436163768a91f19480096f7331ce2fb57499029e50f1eee049244`，与未改写的原方案一致。四项分析检查测试先失败后通过；修订配方现在保存变化/审查标记，不因合法联动拒绝整份结果，新增变化场景仍需语义复核。

`crossing_regression33_verification_protocol_20261001.json` 在首次新旧比较前固定原方案、原配方、修订检查器及 helper 哈希。它是公开的审查补充，不是回写原方案或基于结果选参；抽样成员、提取来源、阈值、评分权重全未变。由于保存了原配方，原方案内 script 路径的当前版本不同，应使用副本核对原哈希，不假称原文件字节未变。

分析测试命令：`python -m unittest logs.test_crossing_regression33_checks_20261001 -v`，4 项通过。HDBSCAN 套件在本轮重新运行，182 项通过（4.684 秒）；测试控制台 `logs/crossing_regression33_tests_20261001_console.log`。

独立修订复查未发现新增可执行问题；四项测试及核验补充的四处哈希不匹配探针均能在读输出表之前拒绝。复查不替代主进程实际输出核验，也未宣布 0552 语义通过。

## 最终比较

- 唯一标识及冻结开发身份完整；四地点数量 16/11/3/3，23 个采集日志。
- 捕获查询异常 0；填值前 44 个正 Inf 只属于 merge 最小诊断距离（17）和 VRU 最小诊断距离（27）；没有 NaN、负 Inf 或非有限聚类输入。
- 0151 与七条 v4 结果一致：风险 0.160460 → 0.010417；三项横向冲突证据归零。
- 新增 0552：横向冲突比例 0.048780 → 0、停后横向冲突比例 0.048780 → 0、最长横向冲突约 0.999750 秒 → 0；风险 0.349963 → 0.200000，决策需求仍为 1。
- 没有风险上升或不在既知依赖关系内的字段变化；`requires_review=true`，因为 0552 未经过本轮用户验收。其变化不能自动当作改善，更不能统计为新增真阴性。
- 33 条聚类输入完全相同不代表其余 667 条相同，也不使旧 700 条 manifest 恢复当前身份。

CSV SHA256：`0591b1ac43f3161e0b4900e738c38a640765fd0e29cb11e0d1e99184bbd4507f`。比较 JSON/Risk CSV 已落盘，核验控制台 `logs/crossing_regression33_verification_20261001_console.log`。没有新聚类标签、稀有分、综合 corner 排名或专家效果指标。

0552 的单条轨迹定位已完成，单独输出 `scene_features_crossing_case0552_20261001.csv` 和 `crossing_case0552_trajectory_20261001.json`；全部 129 列精确复现 33 条中的该行，当前来源通过，异常 0、正 Inf 诊断 2。这是发现新变化后的显式诊断，不属于改写原 33 条抽样。无批量轨迹、GIF 或下载。

被过滤目标为同一辆 `vehicle.car`，instance `661bbc09751c415a879050c906308a6d`，候选索引 27/28；六秒未来与实际路线中心最小距离约 8.46/7.70 m，目标外接圆直径约 4.76 m，自车航向变化约 1.17/0.98 rad，未来完整、无低速/强制动响应证据。原始候选保留。这与转弯直行投影误报机制相符，但不能凭轨迹距离单独证明没有更早的让行/避险决策。

nuScenes 描述为弯折公交车、校车、停车场、左转、停着的公交车、超越卡车；该描述不能当目标级冲突真值。候选实际场景时间约 13.398/13.898 秒，自车速度约 4.00/3.85 m/s。

单条来源/精确复现和媒体元数据路径检查完成：**0552 的 41 张 CAM_FRONT 关键帧全部缺失**（0/41 存在），不能播放或人工验收，不下载、不补造。未检查 sweeps 或解码其他相机。机器证据 `HDBSCAN/tables/crossing_case0552_diagnosis_20261001.json`，配方 `logs/check_crossing_case0552_20261001.py`，控制台 `logs/crossing_case0552_verification_20261001_console.log`。

单条诊断复现命令（已完成，重复运行会拒绝覆盖原输出）：

```powershell
$env:SCENE_CLUSTER_SCENE_NAMES='scene-0552'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_crossing_case0552_20261001.csv'
$env:SCENE_CLUSTER_AUDIT_OUTPUT='crossing_case0552_trajectory_20261001.json'
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py 2>&1 | Tee-Object -FilePath logs/crossing_case0552_extraction_20261001_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/check_crossing_case0552_20261001.py 2>&1 | Tee-Object -FilePath logs/crossing_case0552_verification_20261001_console.log
```

## 需要确认的下一步

已向用户提出：是否将当前特征冻结为**候选版**并重提完整 700 条同版本开发表，0552 仍保留待验、不计入已修正误报；不加入施工视觉识别，不下载、不用评价场景、不自动选择正式聚类参数。也可继续有限小批回归。候选版冻结不是特征语义全部验收；本轮没有默认为用户批准完整重提，尚未启动新 700 条任务。
