# 开发集入口保护

本轮目标：接入冻结的 700/150 划分，确保默认开发入口不提取评价场景、不将评价场景用于标准化/UMAP/HDBSCAN/KMeans/参数搜索或开发评分。不做全量实验，不实现样本外预测。

## 实施步骤

- [x] 添加共享划分校验：校验冻结 CSV 哈希、场景名称/token/日志一致性、重复和未知场景。
- [x] 编写拒绝混合集、伪造标识、缺字段、覆盖历史输出的测试。
- [x] 接入提取、聚类、网格搜索、KMeans 和开发评分，增加只读 preflight。
- [x] 实际执行入口 preflight 和全部单元测试，不运行真实拟合。
- [x] 更新入口文档，记录限制和下一步。

设计决策：拟合入口拒绝而不是静默过滤混合表，防止用户误以为 850 条都参与训练；特征提取默认从开发清单选取，显式请求评价场景也拒绝。当前完整 52 列为开发输入 schema 下限，旧 24/48 列表不能被当作最新正式输入；以后若收敛白名单必须同步版本和文档。

输出使用独立 development 名称并禁止覆盖已有产物；开发评分要求当前受保护拟合入口产生的可校验来源记录，不能把整库聚类结果事后切出 700 条伪装成开发集拟合。共享纯评分函数仍可供测试，但不等同于正式实验入口。

## 行为变更

- 新模块 `HDBSCAN/scripts/experiment_partition.py` 校验成员文件哈希、双标识、角色、可用时的日志/地点、重复场景和非有限特征值。输入不合格即停止，不静默丢弃评价行，不把错误值填成 0。
- 特征提取先只读取 scene 元数据筛出开发场景，再加载完整 NuScenes；`--preflight` 在加载大表前退出。`SCENE_CLUSTER_START_INDEX` 现在相对于开发清单而不是原始 850 条；显式名称只允许开发场景，沿用显式名称优先于起止范围的规则。
- 聚类和搜索在通过校验后才导入 UMAP/HDBSCAN 并拟合。KMeans 在支持度过滤、标准化和 PCA 前进行同样校验。
- 开发评分不仅校验成员，还要求聚类 CSV 对应 `.csv.manifest.json` 的 stage、成员顺序、划分哈希、输出哈希一致。缺失 provenance 的旧结果只能作历史材料，不能直接从此正式入口评分。
- 聚类标签、成员概率和离群分数必须合法且有限，避免将 NaN 离群证据降为 0 后继续输出排序。
- 产物使用独立 development 名称；检测到已有 CSV、manifest 或相关图表时要求换新版本名称，不覆盖。运行记录保存输入、输出、划分、脚本、共享检查及特征白名单哈希。

## 网格搜索的关联修正

旧网格仍包含 96 个 UMAP 配置、12 个 HDBSCAN 配置，即 1152 个候选，未在本轮执行。现在同一 UMAP 配置只拟合一次并供 12 个 HDBSCAN 候选复用，默认 n_jobs=1。

原来的 `persistence` 实际是 DBCV，现已改名 `dbcv`，失败/不适用返回空指标并记录 status/error，而不是伪造数值 0。主流程和搜索都使用同一 52 列白名单及 StandardScaler，不再把风险/诊断数值列自动带入搜索。这些是代码层修正，不是新参数实验或性能结论；下一阶段仍应缩小搜索空间并确定选择准则。

## 本轮实际命令与结果

工作目录 `F:\Scene_cluster`，解释器 `D:\Python\Conda\envs\autodrive-cluster\python.exe`。

```powershell
python HDBSCAN/scripts/scene_feature_hdbscan.py --preflight
$env:SCENE_CLUSTER_FEATURE_INPUT='scene_features_review8_20260922.csv'
python HDBSCAN/scripts/cluster_umap_hdbscan.py --preflight
python HDBSCAN/scripts/grid_search.py --preflight
python Kmeans/scripts/kmeans_semantic_baseline.py --input HDBSCAN/tables/scene_features_review8_20260922.csv --preflight
```

以上 python 均通过前述解释器绝对路径执行。提取 preflight 返回 700 条开发场景，后三者返回 14 条、52 列。全部使用划分哈希 `0d288dba6f8fc404ab592939de2a24052cd42042e7bd64b9da40298019c535fa`。

负向检查：`SCENE_CLUSTER_CLUSTER_INPUT=scene_features_route_tightening_0051_0100_umap_hdbscan.csv` 后执行评分 `--preflight`，按预期退出码 1，提示缺少受保护拟合来源。单元测试同时覆盖 850 条混合表在两个聚类入口和 KMeans 被拒绝、显式评价场景在加载 NuScenes 前被拒绝、合成有效 provenance 的评分 preflight 可通过。合成夹具只在临时测试目录中，已自动清理，不是实验结果。

```powershell
$env:MKL_THREADING_LAYER='SEQUENTIAL'
python -m unittest discover -s HDBSCAN/tests
python -m unittest discover -s Kmeans/tests
```

新增 17 项检查与入口测试，HDBSCAN 共 107 项通过；KMeans 5 项通过（仅保留 joblib 物理核探测回退警告）。六个修改/新增的入口与共享模块通过 py_compile。没有运行真实提取、UMAP/HDBSCAN/KMeans 参数实验，没有生成新科学结果或覆盖历史产物。

## 仍未完成

目前只有开发拟合保护，不存在评价提取/预测的解锁开关。标准化器、降维器和聚类器的冻结导出、样本外分配、评价侧稀有性/异常性定义仍待实现。调用共享规则或旧 legacy 脚本不属于受保护正式流程，README 中仅推荐本轮列出的当前入口。

下一步先在开发集内收敛 0030/0073 等特征问题，再确定正式特征版本；不要仅因本轮入口测试通过，就把旧 14 条或全量旧 CSV 当作正式模型结果。
