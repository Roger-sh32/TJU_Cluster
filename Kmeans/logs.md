# KMeans logs

## 2026-08-15

### Changed

- 新增 `scripts/kmeans_semantic_baseline.py`，直接复用 HDBSCAN 的 48 个语义聚类特征。
- 新增直接特征与 PCA 80%/90%/95% 方差表示，搜索 `K=2..10`，并以 5 个随机种子评估稳定性。
- 新增 silhouette、Davies-Bouldin、Calinski-Harabasz、稳定性 ARI、惯性和簇规模门槛。
- 新增最小特征支持过滤，排除当前样本中仅有 0–2 个非零支持或全常数的距离轴。
- 新增 5 个单元测试，覆盖可靠候选筛选、弱结果标记、稳定聚类、PCA 和支持度过滤。

### Environment

- 复现 NumPy SVD 和 sklearn 测试卡死，根因是 Windows Conda 环境中的 MKL 与多套 OpenMP 线程运行时冲突。
- 设置 `MKL_THREADING_LAYER=SEQUENTIAL` 后，小型 SVD 从超时恢复为约 0.016 秒完成。
- 已将 `MKL_THREADING_LAYER` 写入 `environment.yml`，脚本入口也提供安全默认值。

### Result

- 输入：`HDBSCAN/tables/scene_features_route_tightening_0051_0100_final.csv`，50 条场景、48 个语义特征。
- 原始特征候选全部不可靠；最高 silhouette 为 0.2039，但稳定性 ARI 仅 0.4156。
- 最小支持过滤保留 41 个特征，最终选择 `supported_pca_80, K=2`。
- 最终 silhouette 为 0.2009，稳定性 ARI 为 1.0000，簇规模为 37/13。
- 结果仅支持粗粒度 KMeans 基线；不支持细粒度价值场景分类结论。
- 另行验证特征块均衡方案，没有候选同时通过全部门槛，因此未加入正式链路。

### Command

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe -u Kmeans\scripts\kmeans_semantic_baseline.py --input HDBSCAN\tables\scene_features_route_tightening_0051_0100_final.csv --output-prefix kmeans_semantic_0051_0100
```

### Not Done

- 未重提取或覆盖正式 850 条 HDBSCAN 特征表。
- 未把当前 50 条开发结果作为论文最终 KMeans 对照结论。

## 2026-06-13

### Changed

- Created `scripts/`, `tables/`, and `pictures/`.
- Moved `scene_feature_kmeans_baseline.py` to `scripts/`.
- Moved `scene_features.csv` to `tables/`.
- Moved `Figure_1.png` and `Figure_2.png` to `pictures/`.
- Updated the KMeans script to resolve paths relative to its own directory.
- Updated the script output paths to write generated tables to `tables/` and generated figures to `pictures/`.

### Not changed

- No KMeans experiment was rerun.
- The local `聚类/` data directory was not moved.
- Historical result files were not deleted.
