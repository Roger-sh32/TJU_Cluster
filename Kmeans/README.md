# KMeans 同特征基线

本目录保存论文的 KMeans 对照链路。当前基线不再重复提取旧特征，而是直接读取 HDBSCAN 最新特征表，并调用同一份语义特征白名单，确保算法比较使用相同场景和相同输入。

KMeans 仅作为对照方法。当前 50 条开发样本只能得到稳定的粗粒度二分，不能替代 HDBSCAN 识别稀有场景与非球形簇。

## 目录

| 目录 | 内容 |
| --- | --- |
| `scripts/` | 当前同特征基线和历史 KMeans 脚本 |
| `tests/` | KMeans 评估、筛选与支持度过滤测试 |
| `tables/` | 指标、聚类、簇规模、簇画像和运行摘要 |
| `pictures/` | 聚类调试图和历史图片 |

## 当前入口

自 2026-09-24 起，`scripts/kmeans_semantic_baseline.py` 默认读取：

`../HDBSCAN/tables/scene_features_development.csv`（尚未本轮生成）。在支持度筛选、标准化和 PCA 前校验冻结划分，只允许开发场景，要求当前 52 列 schema；旧 48 列开发批次只能作历史分析。新增 `--preflight` 可只检查输入，默认输出前缀为 `kmeans_development`，禁止覆盖已有产物。

下列流程和后文数值描述的是 2026-08-15 的历史 48 列实验，不代表最新正式比较已经完成：

1. 调用 `HDBSCAN/scripts/feature_selection.py` 选择同一组 48 个语义特征。
2. 同时评估原始 48 维和最小支持过滤后的表示。
3. 对每种表示评估直接 KMeans、PCA 80%、PCA 90% 和 PCA 95%。
4. 搜索 `K=2..10`，使用 5 个固定随机种子检查稳定性。
5. 只有同时满足 silhouette、ARI、最小簇和最大簇占比门槛的候选才标记为可靠。

最小支持过滤只影响 KMeans 距离计算，不改写原始特征表。当前阈值为至少 3 个非零样本，用于防止单例特征经标准化后制造单样本簇；被过滤列和支持样本数会完整写入摘要 JSON。

## 运行

在项目根目录执行：

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe -u Kmeans\scripts\kmeans_semantic_baseline.py `
  --input HDBSCAN\tables\scene_features_review8_20260922.csv --preflight
```

此命令仅验证现有 14 条回归输入，不启动 KMeans。正式运行应在特征冻结后换成新生成的开发表，使用新的输出前缀。当前无样本外评价接口，不能将评价集混入候选搜索。

测试命令：

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe -u -m unittest discover -s Kmeans\tests -v
```

## 当前结果

2026-08-15 的 50 条开发实验选择 `supported_pca_80, K=2`：

- 使用 41 个有足够样本支持的特征，PCA 保留 12 个分量和 82.04% 方差。
- silhouette 为 0.2009，跨种子稳定性 ARI 为 1.0000。
- 两个簇分别包含 37 和 13 条场景，满足预定义规模门槛。
- 原始 48 维没有可靠候选；其最高 silhouette 候选的 ARI 仅为 0.4156。

该结果主要区分宏观交通形态，例如跟车/超车暴露、速度、转向和路口控制差异。它尚不能稳定拆分施工改道、行人让行、合流等细粒度价值机制，因此只能作为开发基线。正式论文比较仍需在最新特征代码上重提取完整 850 条场景后重跑。

## 输出

| 文件 | 内容 |
| --- | --- |
| `tables/kmeans_semantic_0051_0100_metrics.csv` | 全部表示和 K 候选指标 |
| `tables/kmeans_semantic_0051_0100_clusters.csv` | 场景、原始特征和最终簇标签 |
| `tables/kmeans_semantic_0051_0100_cluster_sizes.csv` | 簇规模和占比 |
| `tables/kmeans_semantic_0051_0100_profiles.csv` | 原始 48 个特征的标准化簇画像 |
| `tables/kmeans_semantic_0051_0100_summary.json` | 输入、特征支持度、筛选过程和限制 |
| `pictures/kmeans_semantic_0051_0100_pca.png` | 最终候选的二维调试图 |

## 历史链路

`scripts/scene_feature_kmeans_baseline.py` 和 `tables/scene_features.csv` 为旧版结果，仅用于追溯。旧脚本自行提取约 24 个过期特征，包含旧 TTC/坐标判断和固定 `K=4`，不得作为当前论文对照结果。
