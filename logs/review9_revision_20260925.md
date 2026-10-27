# 开发回归：静止目标抖动与停车归因（2026-09-25）

## 范围与设计

仅复跑既有 14 条开发回归场景，冻结划分沿用 `HDBSCAN/tables/evaluation_split_20260924.csv`。不读取评价样本反馈调参，不进行 UMAP/HDBSCAN 或 KMeans 拟合，不覆盖旧表。本轮不修改风险权重、地图过滤和 52 列聚类白名单。

目标是核验 0030 避障漏检根因，并补齐 0073 的事件级诊断。先检查已有视频、轨迹和规则，再添加失败测试、实现最小修正、重提特征。

## 根因

0030 旧避障目标 `1462e9f27d254a5bb0b570fc87db040c` 是道路外摩托车，仍应过滤。但另一个道路内目标 `4bcbde94a9884756aa02d3097d84e3d7` 不应被遗漏：已有诊断轨迹跨越约 18.10 秒，两点最大距离仅 0.464 m，中位速度约 0.007 m/s；第 34 帧附近的单步标注变化产生约 0.579 m/s 峰值。

旧 `split_stopped_lead_history` 用全场最大速度 <=0.5 m/s 判断永久静止，0.5–1.0 m/s 之间既不是静止，也不是明确动态。道路外目标被正确排除后，道路内近乎静止的目标又落入这个空档，导致真实避障证据丢失。并非需要取消道路外过滤。

## 修正与边界

- 在原判定之外增加完整轨迹的有限抖动证据：至少 5 点、跨度 >=2 秒、采样间隔 (0,1] 秒、任意两点距离 <=0.5 m、速度 90% 分位 <=0.5 m/s、峰值 <1 m/s。
- 该证据只补足静止分类，不覆盖 >=1 m/s 的明确运动证据，也不改变 TTC 计算或逐帧前方目标选择。
- 加入匀速缓行、离开后返回、短轨迹及采样缺口反例测试。阈值是开发启发式，不是行业标准，也不代表所有标注噪声都得到解决。
- 增加轨迹审计字段：目标速度、横向预测/暴露、自车速度、静止前车实例、静止分类、峰值速度与有限抖动证据。首帧自车速度的 0 是原有计算占位，不是观测到静止。
- 0073 不直接降分。停止牌提供法规停车语境，但不能排除同时存在的潜在横向冲突；实际未来没有近距，也不能证明此前不需要让行。

## 复跑命令

工作目录 `F:\Scene_cluster`；解释器 `D:\Python\Conda\envs\autodrive-cluster\python.exe`；数据 `nuScenes v1.0-trainval`。

```powershell
$env:SCENE_CLUSTER_SCENE_NAMES='scene-0053,scene-0055,scene-0056,scene-0109,scene-0073,scene-0011,scene-0030,scene-0007,scene-0097,scene-0068,scene-0074,scene-0122,scene-0026,scene-0103'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_review9_20260925.csv'
$env:SCENE_CLUSTER_AUDIT_OUTPUT='review9_trajectory_audit_20260925.json'
$env:MKL_THREADING_LAYER='SEQUENTIAL'
D:\Python\Conda\envs\autodrive-cluster\python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py
```

输入基线为 `scene_features_review8_20260922.csv` 和 `review8_trajectory_audit_20260922.json`。原有 GIF 来自 `exports/feature_check_batch4_20260711/scene-0030_CAM_FRONT_6fps.gif` 与 `exports/feature_check_batch8_20260816/scene-0073_CAM_FRONT_6fps.gif`；每 12 帧提取一张缩略图，诊断拼图保存在 `exports/diagnostic_20260925/`，时间标签按文件标称 6 fps 估算，不作为精确事件时间。

## 单元验证

新增 3 项测试首先因缺失接口失败，实现后通过。完整 HDBSCAN 110 项、KMeans 5 项测试通过，语法编译与 `git diff --check` 通过。KMeans 仍有 joblib 物理核探测警告，但测试成功。CIM 进程查询被权限拒绝，未据此改变环境；普通进程状态查询可用。

## 实景结果

提取退出码 0：NuScenes 加载 35.698 秒、反向索引 9 秒、14 场景提取约 118 秒。输出 14 行、129 列、52 个聚类字段，标识唯一且数值有限。两份比较表均经 `experiment_partition` 检查为开发数据。

与 9 月 22 日逐列比较：只有 0030 的 9 个字段变化，其余 13 条完全一致；所有 14 条风险分数均不变。

| 0030 特征 | 之前 | 本轮 |
| --- | --- | --- |
| 静止前车比例 | 0 | 0.15 |
| 堵路障碍比例 | 0 | 0.15 |
| 静止障碍事件数 | 0 | 1 |
| 静止前车最小间距 | 80（无目标占位） | 11.599 m |
| 避障横移 / 净航向变化 | 0 / 0 | 11.210 m / 0.170 rad |
| 避障标记 | 0 | 1 |
| 避障期间对向车暴露比例 / 事件数 | 0 / 0 | 0.075 / 1 |

静止障碍唯一实例为道路内摩托车 `4bcbde94a9884756aa02d3097d84e3d7`。0011 避障仍为 1；0053/0055/0056/0109 仍为 0；0026 摩托车 TTC 1.901 秒保留。0030 TTC 1.775 秒和风险 0.194312 均未改动。

**限制**：0030 对向暴露为恢复避障后激活的下游窗口特征，未证实真实冲突或因果关系，不应自动作为新增危险事件。位移/航向的旧全窗口启发式仍存在局限。新实际侵入和路线近距特征仍缺少本批实景正例验收。

## 0073 事件证据与未解决项

- 停止牌低速证据约在场景 13.00、13.55、14.00、14.50 秒。
- 停车前预测：卡车 `ef7f4554978d4642a1a0963057461f8d`，9.50–12.00 秒；自车速度从 5.64 降至 2.14 m/s。挂车 `c6ca20d3ea564971a3639556bdfcb34d` 同时在 11.50–12.00 秒触发。
- 起步后预测：小汽车 `c43ceb86fe894276adf3d53c5d31be91`，16.90–17.40 秒，自车速度约 2.70–2.90 m/s。
- 因此不能把全部预测合并归因为“为横向卡车停车”，也不能仅凭停止牌清空所有横向预测。当前交互分 0.733333、决策需求 0.4、总风险 0.30 保持；这不是宣称该风险已被人工确认。
- 0122 停车前横向小汽车预测约 5.45–6.95 秒，停止牌低速证据约 11.95–14.50 秒；也不能因停止牌存在而删除前一事件。0068/0074 已确认左转交互的特征与风险保留。

下一步应建立事件级路径/停车因果证据，并补足开发集实景正例，而不是继续调整场景级权重来凑合人工标签。单元测试通过不等于上述归因已解决。

## 评分审计与产物

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe HDBSCAN/scripts/audit_feature_revision.py --features HDBSCAN/tables/scene_features_review9_20260925.csv --baseline HDBSCAN/tables/scene_features_review8_20260922.csv --output-prefix HDBSCAN/tables/review9_20260925
D:\Python\Conda\envs\autodrive-cluster\python.exe -m unittest discover -s HDBSCAN/tests
D:\Python\Conda\envs\autodrive-cluster\python.exe -m unittest discover -s Kmeans/tests
git diff --check
```

审计前通过 `load_development_features` 验证新表，再用同一 partition 的 `assert_development_frame` 验证旧表。审计脚本本身尚未接入冻结划分守卫，不能直接对混合/评价数据使用，也不要复用既有输出前缀。

- 特征与来源：`HDBSCAN/tables/scene_features_review9_20260925.csv`、同名 `.csv.manifest.json`，记录开发划分、脚本和特征规则哈希。
- 风险与长表比较：`HDBSCAN/tables/review9_20260925_risk.csv`、`review9_20260925_comparison.csv`。
- 风险审计来源：`HDBSCAN/tables/review9_20260925_manifest.json`，包含输入/代码/输出 SHA-256 及环境。
- 轨迹诊断：`HDBSCAN/tables/review9_trajectory_audit_20260925.json`，SHA-256 `f181d619470040869b362f6fb36a18c004190d0a4908bb7160bd70f08d99b63c`。

未修改原始 nuScenes，未覆盖旧 850 场景输出，未运行完整开发集聚类，未提交或推送 Git。
