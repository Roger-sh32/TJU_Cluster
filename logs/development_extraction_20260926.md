# 700 条开发集特征提取

日期：2026-09-26。用户要求继续推进，媒体下载仍暂缓。目标是用当前开发规则提取冻结清单中的 700 条开发场景，供质量检查与后续拟合，不是已冻结的论文最终结果。

## 输入与范围

- 数据：`nuScenes/v1.0-trainval/` 标注、位姿及现有地图，不读取或下载相机图片。
- 成员：`HDBSCAN/tables/evaluation_split_20260924.csv`，SHA256 `0d288dba6f8fc404ab592939de2a24052cd42042e7bd64b9da40298019c535fa`。
- 程序：`HDBSCAN/scripts/scene_feature_hdbscan.py`，本轮不改特征规则。
- 环境：`D:/Python/Conda/envs/autodrive-cluster/python.exe`。
- 目标：`HDBSCAN/tables/scene_features_development_20260926.csv` 及其 `.manifest.json`，不覆盖旧结果。
- 不生成 GIF、全量逐目标轨迹或新专家标签；不使用 150 条评价场景调参。

## 执行命令

```powershell
$env:SCENE_CLUSTER_MAX_SCENES='700'
$env:SCENE_CLUSTER_START_INDEX='0'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_development_20260926.csv'
Remove-Item Env:SCENE_CLUSTER_SCENE_NAMES -ErrorAction SilentlyContinue
Remove-Item Env:SCENE_CLUSTER_AUDIT_OUTPUT -ErrorAction SilentlyContinue
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py
```

第一次工具包装因未把脚本目录加入 `sys.path`，在导入 `experiment_partition` 时退出，未进行数据提取；错误保留在 `logs/development_extraction_20260926_console.log`。第二次补上路径后已进入 NuScenes 元数据加载，控制台保留在 `logs/development_extraction_20260926_run2_console.log`。未为此修改提取脚本。

第二次包装实际调用：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u -c "import sys, runpy, faulthandler; from pathlib import Path; sys.path.insert(0, str(Path('HDBSCAN/scripts').resolve())); faulthandler.dump_traceback_later(600, repeat=True); runpy.run_path('HDBSCAN/scripts/scene_feature_hdbscan.py', run_name='__main__')" 2>&1 | Tee-Object -FilePath logs/development_extraction_20260926_run2_console.log
```

环境变量同上。每 600 秒输出诊断调用栈，不设置提取超时；该诊断不是失败标志，应结合进度与退出码判断。

## 状态

2026-09-27 核验：第二次执行已于 2026-09-26 23:49 完成，处理阶段耗时约 1 小时 29 分 44 秒；CSV、提取 manifest 与结构质检报告均已生成。早期 23/700 是历史进度，不是当前状态，不要重复启动同名任务。

结果为 700 行、129 列，52 个聚类特征及 33 个必需风险字段完整；冻结开发成员一一对应，700 条地图可用，586 条 intersection_flag 阳性。52 个聚类特征中无常量或全零列。`crossing_route_conflict_ratio` 和 `obstacle_avoidance_vru_conflict_ratio` 各仅 1 条非零，正例识别仍需复核，不能仅凭稀疏性删列或调参。详细结果见 `HDBSCAN/tables/development_quality_20260926.json`。

依赖完成 manifest 的自动结构质检已于 23:49:52 完成；只读检查，不改特征、评分或源数据。实际命令：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/validate_development_batch_20260926.py --wait-seconds 14400 2>&1 | Tee-Object -FilePath logs/development_quality_20260926_console.log
```

已生成 `HDBSCAN/tables/development_quality_20260926.json`，没有自动开始模型拟合。9 月 27 日用户要求继续后另行完成开发拟合，见 [后续实验记录](development_clustering_20260927.md)。

已通过的结构验收：700 条成员与身份一一对应；不含评价场景、重复或遗漏；52 个聚类字段和 33 个风险字段完整且数值有限；来源 manifest 可核验；报告常量/全零字段但不据此直接调规则。

检查中发现的现存局限：提取器末尾仍有全表 Inf→30、NaN→0 的历史填值逻辑。因此最终 CSV 的有限性检查只能证明成表格式有效，不能单独证明中间计算没有失败。本轮保持代码版本不变；若需以本表作为正式实验依据，还须补充原始非有限值审计，不能将“无缺失”直接写成“全部特征识别正确”。
