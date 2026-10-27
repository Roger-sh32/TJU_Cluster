# KMeans公平对照链路审计

日期：2026-10-16。仅核查当前代码和固定开发29条的两个预检查，不是KMeans实验、算法优劣结论或正式方案批准。

## 来源保护缺口

同一输入为 `HDBSCAN/tables/scene_features_longitudinal_v7_replay29_20261015.csv`，manifest阶段为 `candidate_feature_replay`；不是700条正式特征，更不是评价数据。

| 入口 | 本轮结果 | 含义 |
| --- | --- | --- |
| 主UMAP/HDBSCAN预检查 | exit1，Feature extraction version/provenance mismatch | 来源门控拒绝候选，预期行为 |
| KMeans预检查 | exit0，29条/52列、preflight_only为true | 成员/列通过，但未拒绝候选阶段 |

两子进程正常结束，无超时、无拟合；11个计划实验输出执行前后不存在，六个源/测试及候选CSV、manifest摘要不变。[实际JSON](../../../logs/kmeans_comparison_chain_20261016.json)与[命令/环境](../../../logs/kmeans_comparison_chain_audit_20261016.md)保留。

**P2：KMeans预检查通过不等于正式来源验收。** `run_experiment`调用公共`load_development_features`后直接进入preflight或表示构建，缺少主入口的`require_feature_provenance`。公共加载器检查冻结成员、唯一身份、52列和有限数值，不检查提取阶段/源码/质量sidecar。本轮仅实测该候选，不声称已遍历缺失/过期manifest全部情况。

这不是评价成员绕过证据：开发成员检查仍在，本轮未构造真实评价样本或读取评价语义。源码未修，当前不要用该入口运行候选正式基线；修复/版本迁移继续暂挂，不能刷新旧摘要适配修复。

## 公平对照仍缺什么

下表来自源码阅读，不是运行结果。

| 环节 | 当前差异 | 解释边界 |
| --- | --- | --- |
| 初始字段 | 双方共用有序52列 | 同列名不代替同版本/同成员/同来源 |
| 表示 | 主入口全列StandardScaler后UMAP；KMeans有raw/supported两支，各含direct与PCA80/90/95 | 最佳结果属于表示+聚类流水线比较，不是只换聚类器 |
| 支持度 | KMeans保留非零支持数至少3且有变化的列，主入口无同类删除 | 稀少/常量列会被排除，须披露；不替双方决定过滤 |
| 搜索 | KMeans默认K2–10/五种子，可靠门槛后按silhouette/ARI选；全弱仍输出unreliable诊断候选 | 内部门槛不等于专家有效性，不直接与单次固定结果称同预算 |
| 画像 | KMeans按原52列标准化值算画像，即使最终选supported/PCA | 画像不是最终距离空间，不说明52列全参与最终距离 |
| 样本外 | KMeans不持久化Scaler/所选PCA/final_model估计器包；主入口有保存逻辑但最新候选无正式模型 | 现有表格不能替代固定样本外预测；preflight没执行表示构建 |
| 排序 | KMeans只产kmeans_cluster，不产HDBSCAN的cluster_outlier_score；当前corner_scoring依赖该离群分项 | 不能重命名簇或缺失填0后宣称同评分公平；比较范围/可比排序量须另决定 |

样本足够、表示可构建且各项成功时，默认名义搜索为8种表示×9个K×5种子=360次拟合，再fit最终模型一次。这是代码计数，不是本轮运行数、计算耗时或已批准预算；本轮一次拟合也没有运行。

KMeans README仍保留早期48列/50条结果及完整850重提取的历史文字，不能据此恢复全850无隔离拟合。当前仍保留开发700/评价150边界；此次未改该README或历史表格。

## 恢复依赖

1. 先确认正式特征语义/版本和同源开发输入，不把v7的29条升格为全量。
2. 另版处理KMeans及旧grid来源门控、历史证据迁移与候选/缺失/过期来源拒绝控制；不刷新旧封印。
3. 明确比较流水线还是聚类器、表示/搜索预算及内部诊断口径，本报告不替代决定。
4. 若保留独立排序评价，再补固定估计器、样本外预测和可比排序量；不在评价批次筛支持度、缩放、PCA或选K。
5. 就绪后才做同版本实验/专家盲评，不重用开发反馈充当独立标签。

以上是依赖关系，不是批准的实施方案。没有新成绩、特征/参数冻结、KMeans拟合、正式评价或Git提交。

## 证据边界

直接核对[KMeans入口](../../../Kmeans/scripts/kmeans_semantic_baseline.py)、[五项旧测试定义](../../../Kmeans/tests/test_kmeans_semantic_baseline.py)、[主入口](../../../HDBSCAN/scripts/cluster_umap_hdbscan.py)、[公共加载](../../../HDBSCAN/scripts/experiment_partition.py)、[52字段](../../../HDBSCAN/scripts/feature_selection.py)、[来源检查](../../../HDBSCAN/scripts/frozen_model.py)、[评分](../../../HDBSCAN/scripts/corner_scoring.py)。测试文件仅阅读，未运行其实际拟合测试，不声称测试全通过。未做全仓库绑定/完整性审查。

诊断JSON ORIGINAL SHA256：`28febdcba1c96b1063fdd5b12074a7a7592f37ef23591970baa699051a12bf82`。只读核对先验原摘要再信任绑定；不刷新JSON使其匹配后续源码。
