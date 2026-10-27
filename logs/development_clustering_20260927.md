# 700 条开发集聚类、评分与冻结模型核验

日期：2026-09-27。用户要求继续推进。范围为冻结开发集的探索实验，不使用 150 条评价场景，不跑 KMeans，不下载媒体，不新增专家标签。本轮没有修改生产特征、风险规则或评分权重。

后续状态：同日已完成五种子稳定性和审计代码升级，见 [后续记录](extraction_audit_and_stability_20260927.md)。本页描述升级前的单次拟合，仍保留为原始实验记录；旧模型/表须使用匹配代码快照，当前源码不能直接接受。五种子结果不支持把单次 Top20 当作稳定结论。

## 输入与环境

- 输入：`HDBSCAN/tables/scene_features_development_20260926.csv`，700 行、129 列，其中 52 个聚类特征。
- 输入 SHA256：`b1d11f454f13ecac463c5fcc279f9d08d4c4c9d0ce76364f64e4d85a88e30ec3`；提取 manifest、身份与当前脚本来源核验通过。
- 冻结划分：`HDBSCAN/tables/evaluation_split_20260924.csv`；SHA256 `0d288dba6f8fc404ab592939de2a24052cd42042e7bd64b9da40298019c535fa`。
- 提取已于前一日 23:49 完成，结构质检见 `HDBSCAN/tables/development_quality_20260926.json`。不是重新提取一遍。
- 拟合/评分环境：`D:/Python/Conda/envs/autodrive-umap-smoke/python.exe`。Python 3.9.23、numpy 1.24.4、pandas 2.3.1、scikit-learn 1.3.2、umap-learn 0.5.5、hdbscan 0.8.39、numba 0.58.1、joblib 1.5.1；完整运行时记录见模型 manifest。
- 使用既有环境规避主环境 SVD/矩阵运算卡顿，没有全局重装依赖。matplotlib 缺失，程序明确跳过画图；不存在本批新聚类图。

## 实际命令

工作目录 `F:/Scene_cluster`，各阶段退出码均为 0。输出已存在，以下是复现记录，不能直接覆盖原批次；重跑应换新的输出批次名。

```powershell
$env:SCENE_CLUSTER_FEATURE_INPUT='scene_features_development_20260926.csv'
$env:SCENE_CLUSTER_CLUSTER_OUTPUT='scene_features_development_20260927_umap_hdbscan.csv'
$env:SCENE_CLUSTER_CLUSTER_FIGURE='development_20260927_umap_hdbscan.png'
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe HDBSCAN/scripts/cluster_umap_hdbscan.py --preflight
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMBA_NUM_THREADS='1'
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe -u HDBSCAN/scripts/cluster_umap_hdbscan.py 2>&1 | Tee-Object -FilePath logs/development_clustering_20260927_console.log

$env:SCENE_CLUSTER_CLUSTER_INPUT='scene_features_development_20260927_umap_hdbscan.csv'
$env:SCENE_CLUSTER_SCORE_OUTPUT='scene_features_development_20260927_with_corner_score.csv'
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe HDBSCAN/scripts/corner_case_detection.py --preflight
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe -u HDBSCAN/scripts/corner_case_detection.py 2>&1 | Tee-Object -FilePath logs/development_scoring_20260927_console.log
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe -u logs/audit_development_fit_20260927.py
```

## 参数与结果

仅运行一组历史默认参数，没有搜索或按本轮结果调参。UMAP：`n_neighbors=15, min_dist=0, n_components=10, metric=cosine, random_state=42, n_jobs=1, low_memory=True`。HDBSCAN：`min_cluster_size=20, min_samples=1, prediction_data=True`。评分权重保持 `rarity=0.20, atypical_norm=0.25, risk=0.55`。

- 12 个非噪声簇，54 条噪声，占 7.71%。簇 0 至 11 大小依次为 40、28、82、65、24、33、30、98、29、67、53、97。
- 原始 corner_score 范围 0.172 至 0.576125；排序按原始分数降序，平分按 scene_name 升序。
- Top20 来自 6 个簇，没有噪声点。噪声是密度意义上的未归类，不是危险性标签。

| 排名 | 场景 | 簇 | corner_score | risk | 纵向风险 | 交互风险 | VRU风险 | 决策需求 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | scene-1081 | 3 | 0.576125 | 0.476179 | 0.731941 | 0.066667 | 0 | 1 |
| 2 | scene-0071 | 0 | 0.548710 | 0.404333 | 0.060000 | 0 | 1 | 0.666667 |
| 3 | scene-0277 | 10 | 0.538144 | 0.412366 | 0 | 0.749553 | 0 | 0.937500 |
| 4 | scene-0916 | 0 | 0.500774 | 0.317176 | 0.334790 | 0 | 0 | 1 |
| 5 | scene-0253 | 3 | 0.495420 | 0.483503 | 0.517152 | 1 | 0 | 0.012500 |

以上为算法分项，不是人工验证的语义。0071 的纵向分项已很低，当前高分主要涉及 VRU 与决策需求，不能仅据旧反馈断定仍是旧 TTC 误报，也不能据此认为问题解决。

## 产物与验收

全部表格位于 `HDBSCAN/tables/`：

- `scene_features_development_20260927_umap_hdbscan.csv` 及 `.manifest.json`。
- `scene_features_development_20260927_umap_hdbscan.model/`：`estimators.pkl` 和 `manifest.json`，保存 scaler、UMAP、HDBSCAN、身份/来源及训练评分参考量。只允许可信本地加载。
- `scene_features_development_20260927_with_corner_score.csv` 及 `.manifest.json`。
- `development_priority_ranking_20260927.csv`：700 条完整排序与分项，新增 priority_rank。
- `development_fit_summary_20260927.json`：输入/模型/排序哈希、参数、簇大小、Top20 与核验结果。

独立批次审计脚本 `logs/audit_development_fit_20260927.py` 已核验：冻结开发成员无遗漏/重复、特征从输入到聚类与评分均未改变、可信模型重载通过、保存标签/概率/离群分与表格一致、开发评分与冻结训练参考评分重算均与原表一致（容差 1e-12）。审计只读输入并生成新摘要/排序，拒绝覆盖，不重新拟合。

本轮没有修改生产代码，未重跑完整单元测试套件；不将之前的 143/5 项测试表述成本轮新增验证。

## 局限与下一步

1. 提取器仍将 Inf 填为 30、NaN 填为 0，结构质检通过不证明所有中间计算有效。应先增加填充前审计，再决定是否需要新版本提取；保留本批证据，不原地改写。
2. `crossing_route_conflict_ratio`、`obstacle_avoidance_vru_conflict_ratio` 各仅 1 条非零，需要开发集正例复核；已有 0042、0073 等问题也未因这次拟合自动消失。
3. 仅单一参数与随机种子，没有稳定性、消融或同批基线结果，不宣称参数最优。后续搜索只在开发集内进行，KMeans 仍暂缓。
4. 全部 700 条开发场景均参与当前模型拟合，没有剩余未见开发身份可用于该模型的样本外验证。不能用训练场景预测充当独立评价；150 条正式评价入口保持关闭。
5. 未生成专家标签，不能报告 Precision@K、召回率或路测效率提升。150 条评价媒体缺失问题仍待磁盘条件允许后处理，不以可用 25 条替代正式成员。

下一步优先处理非有限值可观测性和开发结果稳定性，再完成冻结协议及独立评价工程；人工复核可使用已有开发媒体，但不能伪装成正式评价。
