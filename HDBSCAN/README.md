# HDBSCAN 场景聚类目录说明

本目录保存基于 `nuScenes v1.0-trainval` 的 `UMAP + HDBSCAN` 场景聚类流程、结果文件和后处理分析文件。

当前目录内已有一套独立结果，不应与仓库根目录下的同名 CSV 混用。根目录的历史文件来自更早的实验链路，字段结构与本目录结果不完全一致。

## 0. 当前开发状态（2026-07-11）

当前脚本已经进入“特征收紧与重构”阶段，正式 850 场景结果尚未用最新脚本全量重跑。

已更新但尚未全量重跑的内容：

- `scripts/scene_feature_hdbscan.py`
  - 路口特征拆分为 `intersection_density` 和 `lane_connector_density`
  - 前车/TTC 改为基于 ego 坐标系的前向与横向筛选
  - 重车特征新增 `truck_bus_dynamic_ratio`
  - VRU 特征新增 `pedestrian_front_ratio`、`pedestrian_crossing_risk_ratio`、`crosswalk_pedestrian_ratio`
  - 两轮车新增 `two_wheeler_dynamic_ratio`
  - ego 动态新增 `ego_decel_min`、`ego_hard_accel_ratio`
  - 支持 `SCENE_CLUSTER_MAX_SCENES` 和 `SCENE_CLUSTER_FEATURE_OUTPUT` 做小样本验证
- `scripts/cluster_umap_hdbscan.py`
  - 支持 `SCENE_CLUSTER_FEATURE_INPUT`、`SCENE_CLUSTER_CLUSTER_OUTPUT`、`SCENE_CLUSTER_CLUSTER_FIGURE`
- `scripts/corner_case_detection.py`
  - 风险分数改为加权风险组件
  - `corner_score` 权重改为 `rarity=0.25`、`atypical_norm=0.25`、`risk=0.50`
  - 支持 `SCENE_CLUSTER_CLUSTER_INPUT` 和 `SCENE_CLUSTER_SCORE_OUTPUT`

当前 debug 验证产物：

- `tables/scene_features_debug_50.csv`
- `tables/scene_features_debug_50_umap_hdbscan.csv`
- `tables/scene_features_debug_50_with_corner_score.csv`

这些 debug 文件只用于验证新特征定义，不应当替代正式论文结果。正式结果仍以完整 850 场景重跑后的 `scene_features.csv`、`scene_features_umap_hdbscan.csv`、`scene_features_with_corner_score.csv` 为准。

### 2026-07-11 事件窗口化 V2 验证

在用户人工复核 5 个场景后，当前开发版进一步将“目标暴露、路径交互、危险后果”拆开：

- 新增纯规则模块 `scripts/scene_feature_rules.py`，识别同车道跟随、合流暴露/冲突、横向交通暴露/冲突和 VRU 横穿暴露/冲突。
- ego 速度和加速度改用真实 sample 时间戳，航向变化处理 `+/-pi` 跳变。
- 周边车辆统计限制为自车 50 米内，前车距离改为车身净间距并过滤重叠标注。
- TTC 同车道横向中心带收紧为 `1.8m`，避免相邻车道和右转车辆进入纵向 TTC。
- 新增事件比例、事件次数和最长持续时间；路口停车作为“主动让行”上下文记录。
- 聚类改用 `scripts/feature_selection.py` 的显式场景语义白名单，不再输入 TTC、急刹、默认距离和 `frame_count`。
- HDBSCAN 输出新增 `cluster_probability` 和 `cluster_outlier_score`。
- corner score 改由 `scripts/corner_scoring.py` 计算纵向、合流/横穿、VRU、自车响应四组固定阈值风险，不再对风险特征逐列做批次 MinMax。
- 决策过程新增起始停车、行驶后停车、再起步、静止前车、避让换道、VRU 事件次数和真实后续轨迹相关性。
- VRU 补充同车道暴露、同向行走和“静止障碍避让窗口内 VRU 冲突”复合特征，分别描述车道占用与避障遮挡风险。
- 同车道 VRU 进一步使用 walkway 与自车 lane 中心线约束；严格 VRU 风险使用录像中的同步未来轨迹和真实车道进入复核，远距离或始终位于人行道的 VRU 只保留为暴露。
- 合流候选要求正向速度、同向 annotation 朝向和至少 1 秒持续时间；对向车辆不再仅因未来最近距离较小而算作合流。
- 侧向同向车辆进一步拆分为超车暴露、非超车的未来路径汇合、实际进入当前 ego lane 三层语义；超车本身不直接增加风险评分。
- VRU 观测相关性新增场景内最近接近时刻，用于区分冲突前接近、驶过后近距和路线分离。
- TTC 最小值新增目标 annotation/instance、类别、场景时刻、净距离、横向位置、目标速度、相对速度和航向差，支持从场景级数值回溯到具体参与者。
- TTC 新增局部转向投影过滤：转弯过程中短暂进入自车前向走廊的静止对向/路侧车辆不再形成危险 TTC。
- 新增 `blocked_path_obstacle_ratio`、`obstacle_induced_route_deviation_flag` 和 `route_deviation_decision_demand`，将施工占道后的被迫改道表达为决策复杂度而非碰撞风险。
- 避障要求持续静止障碍，或短时障碍后出现至少 `4m` 且航向恢复的强横移；仅凭近距离不再触发避障。
- 严格 VRU 风险新增持续性字段，约单帧 `0.5s` 的接近只保留为暴露，两帧以上的持续交互进入风险评分。
- 前方停止目标拆分为当前停止、永久静止障碍和场景内曾运动的暂时停车前车；左转横向车流交互与停车前/后横向冲突分别输出。
- 地图控制新增交通灯、停车标志、转向停车和非信号路口密度；交通灯相位在 nuScenes 中不可用。
- 评分拆分为 `observed_risk` 和 `decision_demand`：停车让行降低当前剩余冲突，但非信号环境下的观察与通行决策需求仍单独保留；检测到高密度交通灯控制时，非信号路口决策需求按最高 80% 衰减。

V2 debug 产物：

- `tables/scene_features_v2_debug_50.csv`
- `tables/scene_features_v2_debug_50_umap_hdbscan.csv`
- `tables/scene_features_v2_debug_50_with_corner_score.csv`
- `tables/scene_features_decision_debug_50.csv`
- `tables/scene_features_decision_debug_50_umap_hdbscan.csv`
- `tables/scene_features_decision_debug_50_with_corner_score.csv`

注意：最新 50 条调试表包含 95 列原始场景字段，并形成两个开发簇（28/22）。该批次经过多轮人工案例定向调参，不能用其 `corner_score` 排名或簇分布作为论文正式结论；正式结论仍需完整 850 场景复跑和独立抽样验证。

第二个独立开发批次使用 nuScenes scene 表索引 `50:100`，输出为 `tables/scene_features_batch_0051_0100*.csv`。实际 scene 名范围为 `scene-0053` 至 `scene-0126`。2026-08-15 收紧后的独立验证表为 `scene_features_route_tightening_0051_0100_final.csv`，共 50 条、118 列，其中 112 个数值字段、6 个追溯文本字段，48 个核心语义特征进入聚类。当前固定参数仍将 50 条均标为噪声，因此该批次仅用于规则验证。详细命令、抽样方法和人工审核问题见 `logs/feature_batch_0051_0100_2026-07-12.md`。

## 1. 当前目录文件清单

### 1.0 目录结构

| 目录 | 内容 |
| --- | --- |
| `scripts/` | HDBSCAN 链路脚本和场景回看工具 |
| `tables/` | CSV/XLSX 表格结果与人工分析表 |
| `pictures/` | 聚类图、报告插图等图片产物 |
| `README.md` | 本目录说明 |
| `logs.md` | 本目录历史批次与变更记录 |

### 1.1 核心脚本

| 文件 | 类型 | 作用 | 当前状态 | 备注 |
| --- | --- | --- | --- | --- |
| `scripts/scene_feature_hdbscan.py` | 主流程脚本 | 从 `nuScenes` 提取场景与事件特征，输出 `tables/scene_features.csv` | V2 debug 已验证 | 当前输出包含 `scene_token` / `scene_name`，正式 850 表尚未重跑 |
| `scripts/scene_feature_rules.py` | 规则模块 | 车辆/VRU 交互分类、事件持续时间和航向变化 | 单元测试覆盖 | 不直接读取 nuScenes |
| `scripts/feature_selection.py` | 聚类输入模块 | 明确场景语义白名单 | 单元测试覆盖 | 排除结果型风险和哨兵值 |
| `scripts/cluster_umap_hdbscan.py` | 主流程脚本 | 对白名单特征做标准化、UMAP 降维、HDBSCAN 聚类 | V2 debug 已验证 | 额外输出成员概率和离群分数 |
| `scripts/corner_scoring.py` | 评分模块 | 计算分组物理风险和综合 corner score | 单元测试覆盖 | 不使用批次 MinMax 定义危险阈值 |
| `scripts/corner_case_detection.py` | 主流程脚本 | 加载聚类表并调用分组评分 | V2 debug 已验证 | 输出 `tables/scene_features_with_corner_score.csv` |
| `scripts/grid_search.py` | 试验脚本 | 搜索 UMAP/HDBSCAN 超参数组合 | 当前目录下无对应输出文件 | 属于参数试验脚本，不是主结果链路的一部分 |
| `scripts/review_nuscenes_scenes.py` | 工具脚本 | 回看具体场景；支持按 `scene_name` 播放或导出 GIF | 当前版本可用 | OpenCV GUI 不可用时会自动回退为 GIF 导出 |

### 1.2 结果文件

| 文件 | 生成阶段 | 作用 | 当前状态 | 关键说明 |
| --- | --- | --- | --- | --- |
| `tables/scene_features.csv` | 特征提取 | 场景级特征表 | 有效 | `850 x 24`，仅保留数值特征，没有场景标识列 |
| `tables/scene_features_umap_hdbscan.csv` | 聚类 | 聚类结果表 | 有效 | `850 x 25`，新增 `cluster` 列 |
| `tables/scene_features_with_corner_score.csv` | corner case 评分 | 综合优先级结果表 | 有效 | `850 x 30`，新增 `rarity / atypical / risk / corner_score / corner_score_norm` |
| `pictures/Figure_1.png` | 聚类 | UMAP 2D 可视化散点图 | 有效 | 来自聚类脚本的可视化输出 |
| `tables/cluster_semantic_labels_enhanced.xlsx` | 人工分析 | 聚类簇语义标签、簇画像、术语表 | 有效 | 包含 3 个 sheet：`Cluster_Labels`、`Cluster_Profile`、`Feature_Glossary` |
| `top20_corner_cases_analysis.xlsx` | 人工分析 | Top 20 场景的人工总结 | 有效 | `scene_id` 是本地结果表的行号，不是 nuScenes 的 `scene-xxxx` |

### 1.3 临时或可忽略文件

| 文件或目录 | 说明 |
| --- | --- |
| `scripts/tempCodeRunnerFile.py` | VS Code 临时文件，不属于正式流程；当前已清理 |
| `scripts/__pycache__/` | Python 缓存目录，不属于正式结果；当前已清理 |

## 2. 当前结果摘要

基于当前目录内 `tables/scene_features_umap_hdbscan.csv`：

- 样本数：`850`
- 标签数（含噪声）：`18`
- 有效簇数（不含 `-1`）：`17`
- 噪声占比：`0.0647`

基于当前目录内 `tables/scene_features_with_corner_score.csv`：

- `risk` 均值：`0.4935`
- `corner_score_norm` 范围：`0.0 ~ 1.0`
- Top 20 分析结果已单独整理到 `top20_corner_cases_analysis.xlsx`

## 3. 推荐执行顺序

建议始终在本目录内执行脚本。脚本已经按当前位置解析路径，输出会落在 `tables/` 或 `pictures/` 下，不会污染仓库根目录。

```powershell
conda activate autodrive-cluster
Set-Location F:\Scene_cluster\HDBSCAN
```

### 3.1 提取场景特征

```powershell
python .\scripts/scene_feature_hdbscan.py
```

输出：

- `tables/scene_features.csv`

### 3.2 可选：做参数搜索

```powershell
python .\scripts/grid_search.py
```

预期输出：

- `tables/umap_hdbscan_grid_search.csv`

说明：

- 当前目录内没有保存这一步的结果文件。
- 仓库根目录曾有一份历史 `tables/umap_hdbscan_grid_search.csv`，但不应默认视为当前目录结果的直接来源。

### 3.3 运行聚类

```powershell
python .\scripts/cluster_umap_hdbscan.py
```

输出：

- `tables/scene_features_umap_hdbscan.csv`
- `pictures/Figure_1.png`

### 3.4 计算 corner case 分数

```powershell
python .\scripts/corner_case_detection.py
```

输出：

- `tables/scene_features_with_corner_score.csv`

### 3.5 回看具体场景

直接按 nuScenes 场景名回看：

```powershell
python .\scripts/review_nuscenes_scenes.py --scene-name scene-0061 --play
```

说明：

- 当前 OpenCV 构建为 `GUI: NONE`，不能弹本地窗口。
- 脚本会自动回退为导出 GIF，默认输出到 `F:\Scene_cluster\exports`。
- 若本地缺失对应相机图片，GIF 导出会失败；这是数据缺失问题，不是算法问题。

## 4. 可追溯批次梳理

以下批次是根据文件时间戳和文件内容反推得到，用于整理仓库，不代表严格的实验日志。

| 批次 | 时间 | 主要动作 | 产物 | 备注 |
| --- | --- | --- | --- | --- |
| Batch-0 | `2025-12-22 17:04 ~ 17:07` | HDBSCAN 主流程脚本首次成型 | `scripts/cluster_umap_hdbscan.py`、`scripts/grid_search.py`、`scripts/scene_feature_hdbscan.py`、`scripts/corner_case_detection.py` | 脚本基线版本 |
| Batch-1 | `2026-04-03 20:42` | 特征提取 | `tables/scene_features.csv` | 当前目录内主特征表 |
| Batch-2 | `2026-04-03 21:00` | 聚类与可视化 | `tables/scene_features_umap_hdbscan.csv`、`pictures/Figure_1.png` | 当前目录内主聚类结果 |
| Batch-3 | `2026-04-03 21:18` | corner case 评分 | `tables/scene_features_with_corner_score.csv` | 当前目录内主评分结果 |
| Batch-4 | `2026-04-03 21:55 ~ 22:05` | 聚类解释和 Top20 人工分析 | `tables/cluster_semantic_labels_enhanced.xlsx`、`top20_corner_cases_analysis.xlsx` | 结果解读层文件 |
| Batch-5 | `2026-04-03 22:20` | 特征脚本修改 | `scripts/scene_feature_hdbscan.py` | 脚本更新时间晚于 Batch-1 输出，说明脚本和结果未必完全对应 |
| Batch-6 | `2026-04-09` | 文档整理 | `README.md`、`logs.md` | 当前整理批次 |

## 5. 关键口径和识别规则

### 5.1 `scene_id` 的含义

`top20_corner_cases_analysis.xlsx` 里的 `scene_id` 不是 nuScenes 的 `scene-0687` 这种场景名，而是当前结果表的零基行号。

例子：

- `scene_id = 687`
- 对应的是 `tables/scene_features_with_corner_score.csv` 排序前的第 `688` 行
- 不是直接等于 `scene-0687`

后续如果要把本目录结果严格回连到 nuScenes 原始场景，建议在 `scripts/scene_feature_hdbscan.py` 中补充：

- `scene_token`
- `scene_name`

否则结果表只能按行号回溯，不能稳定映射回具体原始场景。

### 5.2 当前结果与脚本的一致性

当前目录存在一个明确的可重复性风险：

- `scripts/scene_feature_hdbscan.py` 的修改时间晚于 `tables/scene_features.csv`
- 说明当前脚本内容和当前结果文件未必完全对应

这不影响你继续分析现有结果，但如果后续要严格挂到 GitHub 并追求可复现，建议重新跑一次完整链路，并把输出和脚本版本锁定在同一批次。

## 6. 当前已知问题

### 6.1 场景标识缺失

本目录内的 3 个主 CSV 都没有：

- `scene_token`
- `scene_name`

这导致：

- 结果表无法直接关联 nuScenes 原始场景
- 回看脚本不能直接用本目录结果按 `cluster` 回连原始场景

### 6.2 `scripts/grid_search.py` 缺少当前批次结果

当前目录内没有：

- `tables/umap_hdbscan_grid_search.csv`

所以当前 README 只能把 `scripts/grid_search.py` 标为试验脚本，不能把它视为这批主结果的可追溯证据。

### 6.3 OpenCV 无 GUI

当前环境的 OpenCV 为：

- `GUI: NONE`

所以：

- 不能使用 `cv2.namedWindow()` 弹窗播放
- `scripts/review_nuscenes_scenes.py` 只能优先尝试播放，失败后导出 GIF

### 6.4 局部相机文件缺失

个别场景的相机图片在本地缺失，例如某些 `CAM_FRONT` 文件不存在，会导致 GIF 导出失败。

这是本地数据完整性问题，不是脚本逻辑问题。

## 7. GitHub 整理建议

当前不做移动文件，只先建立文档和日志。后续如果要正式挂 GitHub，建议至少做以下 4 件事：

1. 重新跑完整链路，并让脚本和输出时间一致。
2. 在特征表中加入 `scene_token` 和 `scene_name`。
3. 把 `scripts/grid_search.py` 的输出留在本目录内。
4. 把 `tempCodeRunnerFile.py` 和 `__pycache__/` 加入 `.gitignore`。

