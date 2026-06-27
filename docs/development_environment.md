# 开发环境与跨设备协同说明

本文档用于在 Windows 主机和后续 macOS 设备之间同步开发状态。目标是让新设备拉取仓库后，能用一致的 Conda 环境、目录约定和命令复现实验流程。

最后更新：2026-06-27

## 1. 仓库定位

项目仓库：

- GitHub: `https://github.com/Roger-sh32/TJU_Cluster.git`
- Windows 本地路径：`F:\Scene_cluster`
- 推荐 macOS 本地路径：`~/Projects/Scene_cluster` 或任意不含空格的工作目录

主线任务：

- 数据集：`nuScenes v1.0-trainval`
- 主方法：场景特征工程 + UMAP/HDBSCAN 聚类 + corner case 评分
- 基线方法：KMeans 历史实验
- 论文上下文：同济 MEM 自动驾驶场景聚类与路测提效方向

## 2. Git 同步边界

进入 Git 的内容：

- 代码脚本
- README / AGENTS / logs / docs
- 小规模结果表、论文材料、可复用知识文档
- 当前已整理过的 HDBSCAN/KMeans 结果产物

不进入 Git 的内容：

- `nuScenes/`
- `exports/`
- `Kmeans/聚类/`
- Python 缓存、虚拟环境、本地临时文件

这些规则由 `.gitignore` 管理。

## 3. Windows 当前状态

### 3.1 Python / Conda

当前主要开发环境：

- Conda 安装路径：`D:\Python\Conda`
- 项目环境名：`autodrive-cluster`
- 项目 Python：`D:\Python\Conda\envs\autodrive-cluster\python.exe`
- Python 版本：`3.9.23`

已确认核心包可导入：

- `numpy`
- `pandas`
- `scikit-learn`
- `umap-learn`
- `hdbscan`
- `nuscenes-devkit`
- `opencv-python-headless`

Windows 快速进入项目环境：

```powershell
Set-Location F:\Scene_cluster
. .\activate_project.ps1
```

`activate_project.ps1` 会设置：

- `PYTHONIOENCODING=utf-8`
- `CONDA_OVERRIDE_CUDA=0`
- `conda activate autodrive-cluster`
- `Set-Location F:\Scene_cluster`

这两个环境变量用于规避 Windows 下已遇到的问题：

- `PYTHONIOENCODING=utf-8`：避免 Conda 激活输出触发 GBK 编码错误。
- `CONDA_OVERRIDE_CUDA=0`：避免 Conda 自动探测 CUDA 时触发 `WinError 5`。

### 3.2 Python 3.7 清理状态

独立安装的 Python 3.7 已卸载。旧目录没有直接删除，已改名备份：

- `D:\Python\Python37.uninstalled-backup-20260614`

当前 Windows 卸载清单中应只保留：

- `Miniconda3 py313_25.9.1-3`
- `Python Launcher 3.13.x`

### 3.3 Git

Windows 当前 Git：

- 安装路径：`C:\Program Files\Git`
- 版本：`2.54.0.windows.1`
- 全局用户：`Roger-sh32 <sunhan11111@me.com>`

建议日常检查：

```powershell
git status
git pull --ff-only
git push
```

### 3.4 VS Code / Cursor

Windows 上 VS Code 和 Cursor 已配置默认解释器：

```text
D:\Python\Conda\envs\autodrive-cluster\python.exe
```

仓库内也有项目级配置：

- `.vscode/settings.json`

如果 Python 扩展异常弹窗或仍探测旧解释器，优先检查：

- VS Code 是否已经完全重启
- 是否仍缓存 `D:\Python\Python37`
- 记录见 `logs/environment_audit_2026-06-14.md`

### 3.5 仍需注意的 Windows 系统项

曾发现机器级 PATH 中存在损坏项：

```text
C:;Windows\system32
```

正确值应为：

```text
C:\Windows\system32
```

该项需要管理员 PowerShell 修复。若 Windows 继续出现奇怪的命令解析或 `python.exe` 弹窗，应优先复查 Machine PATH。

## 4. macOS 初始化步骤

### 4.1 安装基础工具

推荐使用 Homebrew：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git
```

推荐安装 Miniforge，而不是系统 Python 或 Anaconda 大包：

```bash
brew install --cask miniforge
```

安装后重新打开终端，确认：

```bash
git --version
conda --version
```

### 4.2 克隆仓库

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/Roger-sh32/TJU_Cluster.git Scene_cluster
cd Scene_cluster
```

首次拉取后建议检查：

```bash
git status
git remote -v
```

### 4.3 创建 Conda 环境

从仓库根目录执行：

```bash
conda env create -f environment.yml
conda activate autodrive-cluster
```

如果环境已经存在：

```bash
conda env update -f environment.yml --prune
conda activate autodrive-cluster
```

验证环境：

```bash
python --version
python -c "import numpy, pandas, sklearn, umap, hdbscan, nuscenes; print('env ok')"
```

预期：

- Python 3.9.x
- 输出 `env ok`

### 4.4 macOS 激活方式

macOS 不使用 `activate_project.ps1`。建议在仓库根目录手动执行：

```bash
conda activate autodrive-cluster
```

如果希望有本地快捷脚本，可自行创建不提交的 shell alias，例如：

```bash
alias sc='cd ~/Projects/Scene_cluster && conda activate autodrive-cluster'
```

## 5. nuScenes 数据放置

数据集不进入 Git。两台设备需要各自本地准备 `nuScenes v1.0-trainval`。

Windows 当前约定：

```text
F:\Scene_cluster\nuScenes
```

macOS 推荐约定：

```text
~/Projects/Scene_cluster/nuScenes
```

仓库脚本应尽量使用相对仓库路径解析数据。如果脚本中存在硬编码 Windows 路径，应优先改为基于脚本位置或仓库根目录解析。

检查数据目录时，至少应能看到类似结构：

```text
nuScenes/
  samples/
  sweeps/
  maps/
  v1.0-trainval/
```

注意：

- 本地部分相机图片可能缺失，场景回看 GIF 导出可能失败。
- 这类失败属于数据完整性问题，不应直接判断为算法错误。

## 6. 主流程命令

### 6.1 HDBSCAN 主线

Windows PowerShell：

```powershell
Set-Location F:\Scene_cluster
. .\activate_project.ps1
Set-Location .\HDBSCAN
python .\scripts\scene_feature_hdbscan.py
python .\scripts\cluster_umap_hdbscan.py
python .\scripts\corner_case_detection.py
```

macOS / bash：

```bash
cd ~/Projects/Scene_cluster
conda activate autodrive-cluster
cd HDBSCAN
python scripts/scene_feature_hdbscan.py
python scripts/cluster_umap_hdbscan.py
python scripts/corner_case_detection.py
```

主要输出：

- `HDBSCAN/tables/scene_features.csv`
- `HDBSCAN/tables/scene_features_umap_hdbscan.csv`
- `HDBSCAN/tables/scene_features_with_corner_score.csv`
- `HDBSCAN/pictures/Figure_1.png`

每次重跑后，应在 `logs/` 新增或更新运行记录，写明：

- 日期
- 设备
- 分支 / commit
- 命令
- 输入数据
- 输出文件
- 异常或环境差异

### 6.2 场景回看

示例：

```bash
cd ~/Projects/Scene_cluster/HDBSCAN
conda activate autodrive-cluster
python scripts/review_nuscenes_scenes.py --scene-name scene-0061 --play
```

当前环境使用 `opencv-python-headless`，OpenCV GUI 窗口可能不可用。脚本会尝试 GIF fallback，默认导出到仓库根目录的 `exports/`。

## 7. 跨平台注意事项

### 7.1 路径

优先使用：

- `pathlib.Path`
- 相对仓库根目录的路径
- 脚本文件所在目录推导路径

避免在代码中写死：

- `F:\Scene_cluster`
- `D:\Python`
- `C:\Users\MSI`
- `/Users/<name>/...`

### 7.2 换行符

仓库使用 `.gitattributes` 固定常见文本文件为 LF。这样 Windows 和 macOS 协作时，不会因为 CRLF/LF 导致大面积无意义 diff。

如果已有历史文件显示 mixed line endings，先不要单独为换行符制造大提交；尽量在真实修改该文件时顺带规范。

### 7.3 依赖

环境以 `environment.yml` 为主。不要只在本机 `pip install` 后不记录。

如果新增依赖：

1. 更新 `environment.yml`
2. 在 `logs/` 记录原因
3. 在另一台设备上执行 `conda env update -f environment.yml --prune`
4. 验证脚本能运行

### 7.4 大文件

不要提交：

- 原始 nuScenes 数据
- 临时导出的 GIF / 图片序列
- 大型中间缓存
- 本地虚拟环境

如果后续确实需要同步大结果，先评估：

- 是否应该压缩后放 `outputs/`
- 是否应该放 GitHub Release / 网盘
- 是否只保留可复现脚本和日志

## 8. Git 工作流建议

每台设备开始工作前：

```bash
git status
git pull --ff-only
```

完成一次明确任务后：

```bash
git status
git add <files>
git commit -m "说明本次修改"
git push
```

如果 Windows 和 macOS 都会改同一批实验输出，建议先在一台设备上完成并 push，再到另一台设备 pull，避免 CSV/XLSX 结果冲突。

## 9. 当前已知风险

- `HDBSCAN/` 中部分 CSV/XLSX 结果可能与最新脚本版本不完全对应，使用前需看 `HDBSCAN/README.md` 和 `logs/experiment_rerun_2026-06-14.md`。
- `intersection_flag` 逻辑已在 2026-06-14 修订，历史结果和最新重跑结果需区分。
- 现有 HDBSCAN 特征表过去曾缺少 `scene_token` / `scene_name`，直接回溯到 nuScenes 场景时需核对当前表结构。
- Windows 机器曾出现 Python/Conda/Launcher 清理问题，详细记录见 `logs/environment_audit_2026-06-14.md`。
- macOS 上若使用 Apple Silicon，少数包可能由 conda-forge 解析为不同构建；以 `environment.yml` 和导入验证为准。

## 10. 新设备检查清单

macOS 首次配置完成后，至少确认：

- `git status` 干净或只包含自己明确修改的文件
- `conda activate autodrive-cluster` 成功
- `python --version` 为 3.9.x
- 核心依赖导入成功
- `nuScenes/` 本地数据目录存在
- 能从 `HDBSCAN/` 启动至少一个脚本
- 不把 `nuScenes/`、`exports/`、本地环境目录加入 Git
