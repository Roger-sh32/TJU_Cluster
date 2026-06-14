# HDBSCAN 场景聚类目录说明

本目录保存基于 `nuScenes v1.0-trainval` 的 `UMAP + HDBSCAN` 场景聚类流程、结果文件和后处理分析文件。

当前目录内已有一套独立结果，不应与仓库根目录下的同名 CSV 混用。根目录的历史文件来自更早的实验链路，字段结构与本目录结果不完全一致。

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
| `scripts/scene_feature_hdbscan.py` | 主流程脚本 | 从 `nuScenes` 提取场景级特征，输出 `tables/scene_features.csv` | 当前版本可运行 | 输出 850 个场景、24 个特征；不包含 `scene_token` / `scene_name` |
| `scripts/cluster_umap_hdbscan.py` | 主流程脚本 | 对特征做标准化、UMAP 降维、HDBSCAN 聚类 | 当前版本可运行 | 输出 `tables/scene_features_umap_hdbscan.csv` 和 `pictures/Figure_1.png` |
| `scripts/corner_case_detection.py` | 主流程脚本 | 基于聚类结果计算 `rarity / atypical / risk / corner_score` | 当前版本可运行 | 输出 `tables/scene_features_with_corner_score.csv` |
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

