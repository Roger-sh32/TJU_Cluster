# 小范围参数与随机种子对比

日期：2026-09-30。用户明确批准 4 组参数 × 5 个种子。20 次聚类全部成功；仅开发集，不跑 KMeans、不使用评价特征/反馈、不提取新场景、不下载媒体。

## 固定方案

- 输入：`HDBSCAN/tables/scene_features_development_audit700_20260927.csv`，700 条、129 列、52 个聚类字段；SHA256 `b1d11f454f13ecac463c5fcc279f9d08d4c4c9d0ce76364f64e4d85a88e30ec3`。当前源码/审计 manifest 和完整冻结成员验证通过。
- UMAP 邻居数：15、30；HDBSCAN min_samples：1、5；min_cluster_size 固定 20。
- 种子：42、7、19、73、101；UMAP 仍为 10 维、cosine、min_dist=0、n_jobs=1、low_memory=True；HDBSCAN prediction_data=True，其余库默认参数由运行时版本约束。
- 标准化、特征和评分不变，权重仍为 rarity 0.20、atypical_norm 0.25、risk 0.55。不自动选最优参数或种子，不替换原模型和排序。
- 同邻居数/种子的嵌入供两个 HDBSCAN 配置复用，总计 10 次 UMAP、20 次 HDBSCAN。每个配置的五个种子生成全部 10 对比较，共 40 对。
- 环境：`D:/Python/Conda/envs/autodrive-umap-smoke/python.exe`，Python 3.9.23；依赖版本、线程配置、输入/源码哈希和预先固定的参数写入 `protocol.json`，该文件在原生拟合前生成。

新入口 `HDBSCAN/scripts/parameter_stability.py` 复用已有种子比较函数。不修改原 `seed_stability.py`、提取/评分或冻结模型源文件，旧结果来源不受本次新入口影响。

## 实际命令

工作目录 `F:/Scene_cluster`：

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMBA_NUM_THREADS='1'
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe HDBSCAN/scripts/parameter_stability.py --input HDBSCAN/tables/scene_features_development_audit700_20260927.csv --output-dir HDBSCAN/tables/parameter_stability_20260930 --preflight
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe -u HDBSCAN/scripts/parameter_stability.py --input HDBSCAN/tables/scene_features_development_audit700_20260927.csv --output-dir HDBSCAN/tables/parameter_stability_20260930 2>&1 | Tee-Object -FilePath logs/parameter_stability_20260930_console.log
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe logs/verify_parameter_stability_20260930.py
```

全部退出码 0。协议时间为北京时间 08:28:43，完成记录为 08:29:10，约 27 秒（包含原生库导入）；已有输出禁止覆盖，复跑须换新的输出目录。不需要重新提取 700 条。

## 结果

下表 ARI 和 Top20 是每组 **五种子的全部十对比较的中位数**，不是仅相对 seed42；最大簇占比以非噪声最大簇为分子、全部 700 条为分母。噪声比例给出五次范围。

| 邻居数 / min_samples | 簇数范围 | 噪声比例范围 | 最大簇占比中位数 | ARI 中位数 | Top20 重合率中位数 |
| --- | --- | --- | --- | --- | --- |
| 15 / 1（原配置） | 8–16 | 0–9.14% | 16.00% | 0.353 | 47.5% |
| 15 / 5 | 6–11 | 0–8.43% | 52.14% | 0.924 | 45.0% |
| 30 / 1 | 13–14 | 6.00–13.00% | 13.71% | 0.740 | 70.0% |
| 30 / 5 | 8–13 | 1.43–17.71% | 51.86% | 0.973 | 75.0% |

重要边界：

- 30/1 的 ARI 范围为 0.621–0.818，Top20 为 45%–80%，最大簇占比为 11.57%–15.29%。相对原配置，结果在簇数和划分稳定性上更均衡，可作为后续簇语义审查的候选，但本轮没有将它设为正式参数。
- 15/5 和 30/5 虽有较高 ARI 中位数，却存在覆盖约 52% 场景的大簇；ARI 最低分别为 0.310 和 0.304，不能隐去不稳定的种子组合。大簇并不自动判为错误，但需要检查是否合并了过多不同场景。
- 原 15/1 的最大簇占比中位数是 16%，但最大达到 52.29%，中位数会掩盖部分种子变化；完整范围保留在 CSV/JSON。
- 五次都进入 Top20 的场景数依次为 3、3、7、13。30/1 的交集是 0071、0262、0417、0436、0660、0916、1081，仅表示排名稳定，不是专家确认高价值。
- 20 次均至少两个非噪声簇，没有全噪声或单簇退化；这不排除大簇占优，也不证明场景语义与危险识别准确。
- 本轮不计算最优综合分，不按人工反馈调参，不报告 Precision@K 或路测提效。ARI 不等于语义质量；Top20 重合率仍不足以证明排序有效性。

## 产物与验证

输出目录：`HDBSCAN/tables/parameter_stability_20260930/`。

- `protocol.json`：拟合前固定的方案和来源。
- 20 个 `n*_s*_seed*.csv`：各 700 条完整身份、标签、成员概率、离群分、规则风险、评分和排名。
- `runs.csv`：20 次运行的簇数、噪声、最大簇占比、状态与时间；失败不会被填成正常指标。
- `configurations.csv`：四组参数的最小/中位/最大统计，适合快速比较。
- `pairwise.csv`：40 对比较，包括全量 ARI、共同非噪声 ARI及样本数、噪声成员一致率、Top20 重合率和 Jaccard。
- `summary.json`：全量机器可读结果、文件哈希与各次 Top20。selected_configuration 为 null，无模型替换。

`logs/verify_parameter_stability_20260930.py` 已核验：20 × 700 身份、排名排序及分项评分重算、全部文件/源码哈希、40 对比较与汇总一致；原 15/1 的五个种子均复现 9 月 27 日结果（标签相等，评分容差 1e-12）。没有把旧模型加载失败当作绕过保护的理由。

新增七项测试覆盖：固定配置、最大簇/噪声分母、退化标记、只预检查不导入原生库、不覆盖输出、拒绝评价混入、五种子完整性、失败留痕；构造器调用数量/参数也已断言。完整 HDBSCAN 套件 165 项通过。独立只读代码审查未发现 P1/P2；UMAP 故障注入和运行中来源变化的专门单元测试仍未覆盖，实际原生完整成功路径已由本轮结果验证。

## 下一步

优先比较 30/1 各簇的语义分布、代表场景与原配置的合并/拆分关系，确认稳定性改善不是丢失重要交互类别。可保留 30/5 作为大簇对照，但不因 ARI 更高就直接采用。先在开发集完成解释与参数选择依据，再另行冻结正式模型；150 条评价集继续保持隔离。
