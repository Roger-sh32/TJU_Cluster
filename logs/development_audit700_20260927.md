# 700 条开发集全量异常审计

日期：2026-09-27。用户同意继续。本轮使用上一轮已通过 8 场景回归的审计版本，重新提取冻结的 700 条开发场景。不修改提取源码、特征判定、评分权重或参数，不使用评价场景，不跑 KMeans，不下载媒体，不导出轨迹/GIF。

## 状态

2026-09-29 核对：本批已于 2026-09-27 21:09:13 完成提取，21:09:26 完成自动核验。处理 700 场景耗时 1:27:50。原工具会话 `11994`（提取）和 `35190`（核验）的进度记录是历史状态，不要重复启动。

结果：700 条、129 列、52 个聚类特征，成员完整，地图可用 700 条，路口标记阳性 586 条，无聚类常量列。新旧 CSV 字节哈希相同，所有特征及风险分项完全一致。查询异常为 0；填值前 1,078 个正 Inf 全部来自两项诊断距离（合流 494、VRU 584），没有 NaN、负 Inf 或其他字段的非有限值。自动核验 `requires_review=false` 只针对其所检查的问题，不代表语义正确。

2026-09-29 已核验产物哈希、当前源码来源，700 条表也通过原生 UMAP 环境的拟合 preflight。尚未启动新的参数比较或拟合，本轮没有设置定时提醒。

启动前 F 盘剩余约 182 GiB。本轮只生成特征表和审计报告，没有消耗相机包下载空间。

## 输入、环境与保护

- 原始标注与地图：`nuScenes/v1.0-trainval/` 和本地地图；原始数据只读。
- 冻结成员：`HDBSCAN/tables/evaluation_split_20260924.csv`，SHA256 `0d288dba6f8fc404ab592939de2a24052cd42042e7bd64b9da40298019c535fa`。
- 提取版本：`HDBSCAN/scripts/scene_feature_hdbscan.py`、`scene_feature_rules.py`、`extraction_audit.py`，与 `scene_features_audit8_20260927_v2.csv` 对应的审计版本一致。运行期间不要改这些文件或来源校验代码。
- 环境：`D:/Python/Conda/envs/autodrive-cluster/python.exe`，单线程环境变量；未重装任何依赖。
- 历史比较基线：`HDBSCAN/tables/scene_features_development_20260926.csv`，只读，其源码版本通过旧快照核验，不冒充当前提取。
- 预检查通过：700 条开发身份，不含评价成员，输出名称未占用；启动前未发现运行中的 Python 提取任务。

## 实际命令

工作目录 `F:/Scene_cluster`。先预检查，再执行提取：

```powershell
$env:SCENE_CLUSTER_MAX_SCENES='700'
$env:SCENE_CLUSTER_START_INDEX='0'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_development_audit700_20260927.csv'
Remove-Item Env:SCENE_CLUSTER_SCENE_NAMES -ErrorAction SilentlyContinue
Remove-Item Env:SCENE_CLUSTER_AUDIT_OUTPUT -ErrorAction SilentlyContinue
& D:/Python/Conda/envs/autodrive-cluster/python.exe HDBSCAN/scripts/scene_feature_hdbscan.py --preflight
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py 2>&1 | Tee-Object -FilePath logs/development_audit700_20260927_console.log
exit $LASTEXITCODE
```

另一个已启动的依赖核验任务：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/check_development_audit700_20260927.py --wait-seconds 14400 2>&1 | Tee-Object -FilePath logs/development_audit700_check_20260927_console.log
exit $LASTEXITCODE
```

核验只在完成 manifest 出现后读取产物，不根据仅有 CSV/质量文件提前判定成功。源文件完整性、来源、成员或数值验证失败会异常退出，不生成成功报告；四小时超时同样不宣称通过。报告如发现数值变化、查询异常或非预期非有限值，会标记 `requires_review=true`，不会自动修改值或启动拟合。

## 已生成产物

以下文件均已生成并完成结构/来源核验：

- `HDBSCAN/tables/scene_features_development_audit700_20260927.csv`
- 同名 `.csv.quality.json`：填值前异常单元格和捕获的查询异常。
- 同名 `.csv.manifest.json`：提取完成及来源记录。
- `HDBSCAN/tables/development_audit700_comparison_20260927.json`：来源/结构核验、新旧值和风险变化、需复核原因。

核验器检查全部冻结成员一一对应、129 列与基线一致、52 聚类字段完整，并逐单元格比较。两项诊断最小距离的正 Inf 单独保留，作为已知占位值不自动判失败；NaN、负 Inf、其他字段正 Inf 或查询异常仍提示复核。即使没有提示，也不等同于语义正确或全部中间计算有效。

## 当前验证

新增核验单元测试先失败后通过：按身份对齐行顺序、记录真实数值差异、拒绝缺失/重复/错配身份或列，以及避免已知距离占位值掩盖其他异常。完整 HDBSCAN 测试 158 项通过。此处测试的是核验逻辑，不是尚在运行的 700 条结果已验收。

## 后续

2026-09-30 更新：已完成另行批准的四组参数、五种子实验，见 [参数对比记录](parameter_stability_20260930.md)。以下是本批提取刚完成时的计划，不代表参数实验仍未开始。

先读全量审计和差异，再限定少量参数组合做多种子对比；本轮尚未运行该参数实验，也未选择新参数。继续保留旧种子结果，不挑最优随机种子，不启动历史 2,304 组大搜索。评价集、媒体恢复与专家盲评仍保持原有边界。
