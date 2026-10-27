# KMeans 同特征基线实验记录

日期：2026-08-15

## 目的

使用与 HDBSCAN 完全相同的当前语义特征，重建可复现、可诊断的 KMeans 对照链路，并判断当前 50 条开发样本是否支持可靠聚类。

## 输入与环境

- 输入表：`HDBSCAN/tables/scene_features_route_tightening_0051_0100_final.csv`
- 样本数：50
- 原始聚类特征：48
- Python：`D:\Python\Conda\envs\autodrive-cluster\python.exe`
- 安全环境变量：`MKL_THREADING_LAYER=SEQUENTIAL`

环境排查中，未设置安全变量时，`40×6` NumPy SVD 超过 15 秒仍不返回；设置后约 0.016 秒完成。`threadpoolctl` 同时曾报告 Windows `0xc06d007f`，证据指向 MKL/OpenMP 动态运行时冲突，而非 Python 版本不支持 PCA 或 KMeans。

## 首轮原始特征结果

原始 48 维及其 PCA 变体均未通过可靠性门槛。最高 silhouette 候选为 `raw_pca_95, K=3`：

- silhouette：0.2039
- stability ARI：0.4156
- 簇规模：38/9/3
- 结论：分离度勉强，但随机初始化不稳定，不可作为有效结果。

数据审计发现：

- `obstacle_avoidance_vru_conflict_ratio` 在 50 条中全为 0。
- 6 个特征只有 1–2 条非零支持。
- 多组特征相关系数高于 0.95。
- 稀疏列经 StandardScaler 放大后容易形成单例轴和小簇。

## 改进实验

加入最小支持过滤：只有至少 3 条样本非零且不是常数的特征进入改进表示。原始 CSV 和 48 维簇画像均保留，过滤明细写入摘要 JSON。

当前保留 41 个特征，排除 7 个低支持特征。最终通过门槛的候选为 `supported_pca_80, K=2`：

- PCA 分量：12
- 方差解释率：0.8204
- silhouette：0.2009
- stability ARI：1.0000
- Davies-Bouldin：1.8964
- Calinski-Harabasz：9.5207
- 簇规模：37/13

与原始最高 silhouette 候选相比，最终结果的 silhouette 略低约 0.003，但稳定性 ARI 提高约 0.584，并消除了极小簇。改进重点是结果可复现和规模有效，而非追求单一分离度指标。

另测了按语义块除以特征数平方根的块均衡表示。其最高分候选仍存在 46/4 的严重失衡，且没有候选同时通过全部门槛，因此未纳入当前脚本。

## 语义审核

13 条小簇更突出跟车持续时间、跟车比例、超车暴露、速度与信号控制；37 条大簇相对突出转向、无信号路口和较低跟车暴露。近期人工审核的 `scene-0067`、`scene-0071`、`scene-0102`、`scene-0103`、`scene-0126` 均进入大簇。

这说明当前 KMeans 只能形成宏观交通形态二分，不能细分施工阻塞改道、行人让行、合流和转弯误 TTC 等机制。它适合作为对照基线，也反向说明 HDBSCAN 对稀有和非球形场景更合适。

## 输出

- `Kmeans/tables/kmeans_semantic_0051_0100_metrics.csv`
- `Kmeans/tables/kmeans_semantic_0051_0100_clusters.csv`
- `Kmeans/tables/kmeans_semantic_0051_0100_cluster_sizes.csv`
- `Kmeans/tables/kmeans_semantic_0051_0100_profiles.csv`
- `Kmeans/tables/kmeans_semantic_0051_0100_summary.json`
- `Kmeans/pictures/kmeans_semantic_0051_0100_pca.png`

## 限制与后续

当前 50 条是开发验证批次，不是随机完整样本。正式论文比较必须先用最新特征提取代码重跑完整 850 条，再用同一脚本重跑 KMeans，并重新审核低支持特征是否仍需过滤。
