# TJU Cluster

这是一个面向同济 MEM 论文项目的 AI-native 研究与工程容器。

项目目标是基于 `nuScenes v1.0-trainval` 构建自动驾驶场景级特征，使用 UMAP/HDBSCAN 等聚类方法识别高价值、复杂或潜在安全关键场景，从而为自动驾驶路测提效和测试场景优先级排序提供依据。

## 当前重点

- 主线方法：场景特征工程、UMAP/HDBSCAN 聚类、corner case 评分、场景回看。
- 基线方法：KMeans 历史实验，用于后续对比。
- 论文产出：开题材料、中期报告材料、技术路线和后续论文正文素材。

## 目录结构

| 路径 | 内容 |
| --- | --- |
| `AGENTS.md` | AI 协作主入口，说明项目规则、目录约定和注意事项 |
| `HDBSCAN/` | 当前主线实验：特征提取、聚类、评分和场景回看 |
| `Kmeans/` | KMeans baseline / legacy track |
| `knowledge/sources/` | 原始资料：论文、标准、课程材料、用户提供文件 |
| `knowledge/wiki/` | 可复用知识：标准映射、特征体系、术语和结论 |
| `logs/` | 执行记录：错误、实验、环境、清理和反馈 |
| `outputs/` | 面向提交、汇报或分享的阶段性产出 |
| `nuScenes/` | 本地数据集目录，已被 Git 忽略 |
| `exports/` | 场景回看 GIF/图片等临时导出，已被 Git 忽略 |

## 环境

推荐使用项目提供的 Conda 环境配置：

```powershell
conda env create -f environment.yml
conda activate autodrive-cluster
```

如果环境已经存在，可用：

```powershell
conda env update -f environment.yml --prune
```

本地快速激活脚本：

```powershell
.\activate_project.ps1
```

注意：当前环境使用 `opencv-python-headless`，因此 OpenCV GUI 窗口可能不可用；场景回看脚本会优先使用 GIF fallback。

## HDBSCAN 主流程

从 `HDBSCAN/` 目录执行：

```powershell
Set-Location F:\Scene_cluster\HDBSCAN
python .\scripts\scene_feature_hdbscan.py
python .\scripts\cluster_umap_hdbscan.py
python .\scripts\corner_case_detection.py
```

主要输出：

- `HDBSCAN/tables/scene_features.csv`
- `HDBSCAN/tables/scene_features_umap_hdbscan.csv`
- `HDBSCAN/tables/scene_features_with_corner_score.csv`
- `HDBSCAN/pictures/Figure_1.png`

场景回看示例：

```powershell
python .\scripts\review_nuscenes_scenes.py --scene-name scene-0061 --play
```

## 当前注意事项

- 部分历史 CSV/XLSX 结果可能不是由最新脚本生成，使用前需核对 `HDBSCAN/README.md` 和 `HDBSCAN/logs.md`。
- 近期已修正 `intersection_flag` 的提取逻辑，但当前历史表格尚未重跑。
- `nuScenes/` 和 `Kmeans/聚类/` 是本地数据目录，不进入 Git。
- 原始论文资料保留在 `knowledge/sources/`；整理后的可复用结论应写入 `knowledge/wiki/`。

## Git 约定

不要直接提交大数据集或临时导出文件。当前 `.gitignore` 已排除：

- `nuScenes/`
- `exports/`
- `Kmeans/聚类/`
- Python 缓存和 Word 临时锁文件

常用提交流程：

```powershell
git status
git add <具体文件或目录>
git commit -m "说明这次修改"
git push
```
