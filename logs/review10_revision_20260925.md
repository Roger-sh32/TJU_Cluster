# 对向车方向过滤与停车事件记录（2026-09-25）

## 已确认范围

用户确认：收紧对向车朝向/运动方向，排除横向穿行；0073 按不同目标及停车阶段记录，停车原因证据不足时明确为未确定；不改风险权重。仅使用冻结划分中的开发数据，不运行完整聚类或调整评价集。

## 根因与改动

0030 的误报目标是小汽车 `6f902cccc24d49a2b91d1d7f00047f83`。在约 12.90–13.75 秒，它的前向投影速度为 -2.4 至 -5.48 m/s，但相对车头方向约为 -1.73 至 -2.16 rad，属于斜向横穿而非明确对向。旧规则只要求负前向速度，且事件落在障碍识别后的 10 秒窗口内，误触发了避障期间对向暴露。

本轮 `is_oncoming_vehicle` 保留距离与最低前向接近速度条件，同时要求车头朝向和实际速度方向均在反向轴的 45 度范围内。两项方向证据必须同时提供；非有限值不判为对向。角度阈值是开发启发式，不是行业标准，不等价于地图级对向车道识别。

新增 `audit_interaction_events.py`，从轨迹诊断中生成独立 JSON 和中文 Markdown，不改变 129 列原始特征结构或 52 列聚类白名单。记录包含实例、类别、事件时间、低速停车阶段和停止牌上下文，不将“先发生横向预测、后停车”写成因果结论。

低速停车候选条件为速度 <1 m/s、连续观测跨度 >=0.8 秒，超过 1 秒的采样缺口分段。首帧速度 0 是旧提取占位，排除出停车判定。多个停车段分别编号，横向预测按实例、连续帧和停车阶段分段；末次停车后不等于已经证明主动避险或让行。停止牌字段仅表示该事件时段记录到上下文，未记录不等于不存在。所有停车原因保持 `undetermined`。

## 回归范围与命令

原有 14 条回归之外增加 0042、0067。两条均已核验为开发集，依据此前人工反馈作为真实对向车辆的检查对象；不新增专家评价标签。

工作目录 `F:\Scene_cluster`，解释器 `D:\Python\Conda\envs\autodrive-cluster\python.exe`，源数据 `nuScenes v1.0-trainval`，冻结划分 `HDBSCAN/tables/evaluation_split_20260924.csv`。

```powershell
$env:SCENE_CLUSTER_SCENE_NAMES='scene-0053,scene-0055,scene-0056,scene-0109,scene-0073,scene-0011,scene-0030,scene-0007,scene-0097,scene-0068,scene-0074,scene-0122,scene-0026,scene-0103,scene-0042,scene-0067'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_review10_20260925.csv'
$env:SCENE_CLUSTER_AUDIT_OUTPUT='review10_trajectory_audit_20260925.json'
$env:MKL_THREADING_LAYER='SEQUENTIAL'
D:\Python\Conda\envs\autodrive-cluster\python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py
```

新事件入口要求特征表与诊断文件场景集合完全一致、name/token 对应冻结开发划分，拒绝重复身份、评价样本、无效时序和已有输出文件，支持 `--preflight`。本轮诊断新增 `scene_token`，旧 review9 诊断不能直接冒充符合新版要求的输入。

测试命令：

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe -m unittest discover -s HDBSCAN/tests
D:\Python\Conda\envs\autodrive-cluster\python.exe -m unittest discover -s Kmeans/tests
git diff --check
```

先添加失败测试再实现；首轮 HDBSCAN 117 项、KMeans 5 项通过，语法编译通过。KMeans 的 joblib 物理核探测警告未影响测试。

## 实景核验

提取退出码 0：NuScenes 加载 28.591 秒，反向索引 6.1 秒，16 场景处理约 142 秒。输出 16 行、129 列、52 个聚类语义字段，数值有限、身份唯一，全部属于冻结开发集。

- 对比 review9 的原 14 条，只有 0030 两列变化：`oncoming_during_avoidance_ratio` 0.075→0，事件数 1→0。其避障标记保持 1，TTC 1.775 秒与风险 0.194312 均未变。
- 其余 13 条全部特征一致；原 14 条风险分数均一致。没有因本轮规则改变修改风险权重。
- 0042 的真实对向目标 `3db997385db140c9b523ebb0d62dd395` 在约 13.80–15.25 秒有 4 帧通过新方向检查。
- 0067 的 3 个对向候选实例 `abbf722e327a483cb52b5d9f98bddc2a`、`9c16a73b1232441bb108340acfa4051d`、`9a1c0dfb605c4c5287336f69238d2cb3` 仍通过方向检查。这验证没有清空所有实景正例，不代表每个候选均具有风险或逐一人工确认。
- **0042 待修**：其避障标记为 0，与此前人工“避让两次本车道静止车”反馈不符，因而最终 `oncoming_during_avoidance_ratio` 仍为 0。方向识别正确不等于避障事件关联正确。本轮不为恢复该标签再叠加未经诊断的阈值补丁。
- 0042、0067 在 review9 中无对应行，比较表 before 留空，不能拿风险 0 / 0.380261 声称相对改善。

0073 事件记录为：9.50–12.00 秒卡车横向预测、11.50–12.00 秒挂车横向预测、13.00–14.50 秒停止牌上下文低速停车、16.90–17.40 秒小汽车横向预测。四条记录均保留 `stop_reason=undetermined`。该场景风险仍为 0.30，不能声称高估问题已修复。

## 事件与风险产物

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe HDBSCAN/scripts/audit_interaction_events.py --audit HDBSCAN/tables/review10_trajectory_audit_20260925.json --features HDBSCAN/tables/scene_features_review10_20260925.csv --output-prefix HDBSCAN/tables/review10_events_20260925 --preflight
D:\Python\Conda\envs\autodrive-cluster\python.exe HDBSCAN/scripts/audit_interaction_events.py --audit HDBSCAN/tables/review10_trajectory_audit_20260925.json --features HDBSCAN/tables/scene_features_review10_20260925.csv --output-prefix HDBSCAN/tables/review10_events_20260925
D:\Python\Conda\envs\autodrive-cluster\python.exe HDBSCAN/scripts/audit_feature_revision.py --features HDBSCAN/tables/scene_features_review10_20260925.csv --baseline HDBSCAN/tables/scene_features_review9_20260925.csv --output-prefix HDBSCAN/tables/review10_20260925
```

preflight 验证 16 场景、16 条事件且未写文件。正式导出事件 JSON/MD，并再次运行同一前缀验证覆盖被拒绝、原 JSON 哈希不变。事件报告的输入、脚本、划分、Markdown 哈希均复核通过。

风险审计脚本的开发集保护尚未内置，本次在运行前分别通过 `load_development_features`、`assert_development_frame` 验证新旧表。未直接使用未经检查的评价或混合表。

- 原始特征/来源：`HDBSCAN/tables/scene_features_review10_20260925.csv` 及 `.csv.manifest.json`。
- 轨迹诊断：`HDBSCAN/tables/review10_trajectory_audit_20260925.json`。
- 事件证据：`HDBSCAN/tables/review10_events_20260925.json`、`.md`。
- 风险与比较：`HDBSCAN/tables/review10_20260925_risk.csv`、`_comparison.csv`、`_manifest.json`。

## 审查、错误与剩余边界

代码审查发现首帧速度占位虽然被停车检测排除，但仍可能进入横向事件速度统计。已添加先失败后通过的回归测试，排除该占位；没有实测值的事件导出 null。最终 HDBSCAN 118 项、KMeans 5 项测试通过。

一次只读核验命令误用了不存在的 `oncoming_vehicle_ratio` 列，报 KeyError；随后改为检查实际存在的条件暴露字段及逐目标方向证据。此错误未影响提取或文件内容。

事件与特征身份一致，不自动证明来自同一代码运行；当前通过本次明确命令、独立文件名与哈希保存来源，入口尚未强制校验两者的共同运行清单。多个报告文件也不是事务式同时落盘，异常中断时应使用新输出前缀并保留错误记录。旧 review9 审计不能直接用于需要 token 的新入口。

0073 因果归因、0042 避障漏检、0109 侧向候选，以及实际侵入/路线近距的实景正例验收仍需后续处理。固定角度与时间窗口存在局限，不保证所有曲线路段准确。旧表保留，未修改数据集，未进行完整聚类、评价集调参、Git 提交或推送。
