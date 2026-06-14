# HDBSCAN 变更日志

本文件用于记录 `F:\Scene_cluster\HDBSCAN` 目录内的重要改动、实验批次和结果文件变化。

## 1. 记录规则

后续每次改动，建议按以下格式追加：

```md
## YYYY-MM-DD

### 变更
- 改了什么文件
- 为什么改

### 影响
- 哪些输出需要重跑
- 哪些历史结果失效

### 产物
- 新增/更新了哪些文件
```

## 2. 当前明确记录

## 2026-06-14

### 变更
- 修改 `scripts/scene_feature_hdbscan.py` 的路口识别逻辑。
- 原逻辑依赖 `lane.turn_direction`，但本地 nuScenes map 的 `lane` 记录没有该字段，导致 `intersection_flag` 容易全为 0。
- 新逻辑优先使用 `road_segment.is_intersection`，并用 `lane_connector` 作为补充拓扑线索。
- 新增 `intersection_density`，表示单个 scene 中靠近路口的帧占比。

### 影响
- 下一次重跑 `scene_feature_hdbscan.py` 会改变 `tables/scene_features.csv` 的列结构。
- 下游 `cluster_umap_hdbscan.py` 会自动把 `intersection_density` 作为数值特征纳入聚类。
- 当前已有 CSV 尚未重跑，仍然是旧结果。

### 产物
- 更新后的 `scripts/scene_feature_hdbscan.py`

## 2026-06-13

### 变更
- 新建 `scripts/`、`tables/`、`pictures/`
- 将 HDBSCAN 相关 Python 脚本移动到 `scripts/`
- 将 CSV/XLSX 表格结果移动到 `tables/`
- 将聚类图片移动到 `pictures/`
- 更新脚本内默认输入/输出路径，避免移动目录后读写到错误位置
- 更新 README、日志和中期大纲中的引用路径

### 影响
- 运行脚本时建议仍在 `HDBSCAN/` 目录执行，例如 `python .\scripts\cluster_umap_hdbscan.py`
- 表格结果统一从 `tables/` 读取
- 图片结果统一从 `pictures/` 读取

### 产物
- `scripts/`
- `tables/`
- `pictures/`
- 更新后的 `README.md`
- 更新后的 `logs.md`

## 2026-04-09

### 变更
- 更新 `scripts/review_nuscenes_scenes.py`
- 支持按 `scene_name` 直接查询和回看场景
- 修正 nuScenes 回放接口中 `scene_name` / `scene_token` 的使用错误
- 在 OpenCV 无 GUI 时自动回退为 GIF 导出
- 新增 `README.md`
- 新增 `logs.md`
- 对 `HDBSCAN` 目录进行归档说明，明确区分主脚本、试验脚本、结果文件、人工分析文件和临时文件
- 按文件时间戳重建当前目录的实验批次

### 影响
- 回看工具现在可直接用于 `scene-0061` 这类场景名输入
- 若本地相机图片缺失，GIF 导出仍会失败，这属于数据完整性问题
- 不修改现有实验数据
- 不改变当前脚本逻辑
- 仅补充文档，便于后续接入 GitHub

### 产物
- 更新后的 `scripts/review_nuscenes_scenes.py`
- `README.md`
- `logs.md`

## 3. 历史批次回填

以下内容不是人工实时记录，而是根据当前目录文件时间戳和内容反推得到，用于后续 GitHub 整理。

## 2025-12-22

### 变更
- 形成 HDBSCAN 主流程脚本基线版本
- 保存以下脚本：
  - `scripts/cluster_umap_hdbscan.py`
  - `scripts/grid_search.py`
  - `scripts/scene_feature_hdbscan.py`
  - `scripts/corner_case_detection.py`

### 影响
- 形成最早可追溯的 HDBSCAN 处理链路

### 产物
- 4 个主流程脚本

## 2026-04-03 / Batch-1

### 变更
- 运行特征提取链路

### 影响
- 生成当前目录内主特征表

### 产物
- `tables/scene_features.csv`

## 2026-04-03 / Batch-2

### 变更
- 运行聚类链路

### 影响
- 生成当前目录内主聚类结果和可视化图

### 产物
- `tables/scene_features_umap_hdbscan.csv`
- `pictures/Figure_1.png`

## 2026-04-03 / Batch-3

### 变更
- 运行 corner case 评分链路

### 影响
- 生成当前目录内综合评分结果表

### 产物
- `tables/scene_features_with_corner_score.csv`

## 2026-04-03 / Batch-4

### 变更
- 进行簇语义解释和 Top 20 场景人工分析

### 影响
- 形成面向论文写作的解释层材料

### 产物
- `tables/cluster_semantic_labels_enhanced.xlsx`
- `top20_corner_cases_analysis.xlsx`

## 2026-04-03 / Batch-5

### 变更
- `scripts/scene_feature_hdbscan.py` 再次修改

### 影响
- 当前脚本时间晚于 `tables/scene_features.csv`
- 当前脚本与当前结果文件可能不是严格同一批次

### 产物
- 更新后的 `scripts/scene_feature_hdbscan.py`

## 4. 当前待解决事项

- 本目录主结果文件不包含 `scene_token` / `scene_name`，不能稳定回连 nuScenes 原始场景
- 当前目录缺少 `scripts/grid_search.py` 对应的结果文件
- OpenCV 为 `GUI: NONE`，场景回放只能回退到 GIF 导出
- 个别场景本地相机图片缺失，GIF 导出可能失败
