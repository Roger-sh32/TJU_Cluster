# 2026-06-14 Python / Conda / Git 环境梳理

## 背景

本次梳理由 Codex 在 `F:\Scene_cluster` 执行，目标是确认当前电脑上的 Python、Conda、项目运行环境和 Git 状态。

未修改系统 PATH，未安装或卸载软件。

## 当前入口状态

### Python

`where.exe python` 输出顺序：

1. `D:\Python\Conda\python.exe`
2. `D:\Python\Python37\python.exe`
3. `C:\Users\MSI\AppData\Local\Microsoft\WindowsApps\python.exe`

当前 `python --version`：

- `Python 3.13.9`

`py -0p` 仅识别：

- `D:\Python\Python37\python.exe`
- 版本：`Python 3.7.9`

结论：

- `python` 默认进入 Conda base 的 Python 3.13。
- `py` 启动器默认只识别旧 Python 3.7。
- 两者入口不一致，容易造成误用。

### Pip

`where.exe pip` 输出顺序：

1. `D:\Python\Conda\Scripts\pip.exe`
2. `D:\Python\Python37\Scripts\pip.exe`
3. `C:\Users\MSI\AppData\Local\Microsoft\WindowsApps\pip.exe`

当前 `pip` 对应 Conda base：

- `pip 25.2 from D:\Python\Conda\Lib\site-packages\pip (python 3.13)`

结论：

- 直接运行 `pip install ...` 会改 Conda base，不会改项目环境。
- 项目应使用 `python -m pip ...`，且明确使用 `autodrive-cluster` 环境。

## Conda 状态

Conda 安装位置：

- `D:\Python\Conda`

Conda 版本：

- `conda 25.9.1`

已发现环境：

- `base`: `D:\Python\Conda`
- `autodrive-cluster`: `D:\Python\Conda\envs\autodrive-cluster`

项目环境验证：

```powershell
$env:PYTHONIOENCODING='utf-8'
conda activate autodrive-cluster
python -c "import sys; print(sys.executable); print(sys.version)"
```

输出确认：

- `D:\Python\Conda\envs\autodrive-cluster\python.exe`
- `Python 3.9.23`

核心依赖导入验证：

- `cv2=4.11.0`
- `numpy=1.26.4`
- `pandas=2.3.1`
- `sklearn=1.6.1`
- `umap=0.5.9.post2`
- `hdbscan=import-ok`
- `nuscenes=import-ok`

结论：

- `autodrive-cluster` 是当前项目可用环境。
- 项目不应使用 base 的 Python 3.13。

## Conda 已发现问题

### 1. `conda info --envs` 默认报错

默认执行：

```powershell
conda info --envs
```

会在 CUDA virtual package 探测处报错：

```text
PermissionError: [WinError 5] 拒绝访问。
```

可用绕过方式：

```powershell
$env:CONDA_OVERRIDE_CUDA='0'
conda info --envs
```

原因判断：

- Conda 的内置 CUDA virtual package 插件会创建子进程/管道探测 CUDA。
- 当前 Windows/Codex 运行上下文下该探测触发 `WinError 5`。
- 设置 `CONDA_OVERRIDE_CUDA=0` 后，Conda 不再自动探测 CUDA，环境列表可正常输出。

### 2. `conda activate` 可能遇到 GBK 编码错误

默认激活时曾出现：

```text
UnicodeEncodeError: 'gbk' codec can't encode character '\ufffd'
```

可用绕过方式：

```powershell
$env:PYTHONIOENCODING='utf-8'
conda activate autodrive-cluster
```

原因判断：

- 激活脚本输出内容中包含当前 GBK 控制台无法编码的字符。
- 设置 `PYTHONIOENCODING=utf-8` 后，`conda activate autodrive-cluster` 可正常切换。

## PATH 状态

用户 PATH 包含：

- `D:\Python\Python37\Scripts\`
- `D:\Python\Python37\`
- `C:\Users\MSI\AppData\Local\Microsoft\WindowsApps`
- `D:\Microsoft VS Code\bin`
- `E:\Code\cursor\resources\app\bin`
- `C:\Users\MSI\AppData\Roaming\npm`

系统 PATH 包含：

- `D:\虚拟机\bin\`
- Windows 系统目录
- OpenSSH
- NVIDIA 目录
- Node.js

当前进程 PATH 中 Conda 在前面，来源应为 Conda 初始化或当前 shell 注入，而不是系统 PATH 固定配置。

结论：

- 用户 PATH 中仍保留旧 Python 3.7。
- 系统 PATH 中没有 Git。
- Conda 入口主要依赖 shell 初始化，不是干净的系统 PATH 配置。

## Git 状态

`where.exe git` 无结果。

常见安装目录未发现 `git.exe`：

- `C:\Program Files`
- `C:\Program Files (x86)`
- `D:\Program Files`
- `D:\Program Files (x86)`
- `C:\Users\MSI\AppData\Local\Programs`

卸载注册表未发现 Git for Windows 记录。

当前项目目录：

- `F:\Scene_cluster` 下未发现 `.git` 目录。

结论：

- Git 大概率未安装。
- 当前项目目录目前也不是 Git 仓库。

## 建议整理顺序

1. 先固定项目运行方式：

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:CONDA_OVERRIDE_CUDA='0'
conda activate autodrive-cluster
Set-Location F:\Scene_cluster
```

2. 将以下用户环境变量持久化：

- `PYTHONIOENCODING=utf-8`
- `CONDA_OVERRIDE_CUDA=0`

3. 安装 Git for Windows，并确认：

```powershell
git --version
```

4. 再决定是否清理用户 PATH 中的旧 Python 3.7。

不建议立刻删除 `D:\Python\Python37`，因为 `py` 启动器当前只识别它；应先确认是否还有旧脚本依赖 Python 3.7。

5. 为本项目补充环境文件：

- 可将 `D:\Python\environment.yml` 迁移或整理为 `F:\Scene_cluster\environment.yml`
- 后续所有实验记录应写明使用 `autodrive-cluster`

## 推荐项目命令

在当前环境未完全清理前，最稳妥的项目运行方式是直接调用项目环境 Python：

```powershell
& 'D:\Python\Conda\envs\autodrive-cluster\python.exe' HDBSCAN\scripts\scene_feature_hdbscan.py
```

或先设置环境变量后激活：

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:CONDA_OVERRIDE_CUDA='0'
conda activate autodrive-cluster
```

## 2026-06-14 后续整理操作

### 已备份

整理前已备份用户级环境和编辑器配置到：

- `C:\Users\MSI\.codex\env-backups-20260614-100628`

### 用户环境变量

已持久化用户环境变量：

- `PYTHONIOENCODING=utf-8`
- `CONDA_OVERRIDE_CUDA=0`

目的：

- 避免 PowerShell / VS Code 终端中 `conda activate` 出现 GBK 编码错误。
- 避免 Conda 在 `conda info --envs` 时自动探测 CUDA 并触发 `WinError 5`。

### 用户 PATH

已将用户 PATH 整理为：

1. `C:\Program Files\Git\cmd`
2. `D:\Python\Conda\condabin`
3. `C:\Users\MSI\AppData\Local\Microsoft\WindowsApps`
4. `D:\Microsoft VS Code\bin`
5. `E:\Code\cursor\resources\app\bin`
6. `C:\Users\MSI\AppData\Roaming\npm`

已从用户 PATH 移除：

- `D:\Python\Python37\Scripts\`
- `D:\Python\Python37\`

说明：

- 未删除 Python 3.7 安装，只是不再让它抢默认命令入口。
- `py` 启动器仍可识别 Python 3.7。
- 未激活 Conda 环境时，裸 `python` 可能仍指向 WindowsApps 占位符；项目开发应先激活环境或使用 VS Code 指定解释器。

### Conda 配置

已执行：

```powershell
conda config --set auto_activate false
conda config --set report_errors false
conda config --set plugins.anaconda_telemetry false
```

当前效果：

- 新终端不再自动进入 `(base)`。
- Conda 错误报告不再交互询问是否上传。
- 关闭 Anaconda telemetry。

### PowerShell profile

已在用户 PowerShell profile 前部加入：

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:CONDA_OVERRIDE_CUDA = '0'
```

保留原有 `conda init` 管理块。

### VS Code / Cursor

已将 VS Code 和 Cursor 的全局 Python 默认解释器改为：

- `D:\Python\Conda\envs\autodrive-cluster\python.exe`

并加入终端环境变量：

- `PYTHONIOENCODING=utf-8`
- `CONDA_OVERRIDE_CUDA=0`

### 项目新增文件

已新增：

- `.vscode/settings.json`
- `activate_project.ps1`
- `environment.yml`

用途：

- 固定本项目 VS Code 解释器。
- 一条命令激活项目环境。
- 将项目环境依赖从 `D:\Python\environment.yml` 迁移到项目根目录，便于复现。

### Git

已通过 winget 安装 Git for Windows：

- 安装位置：`C:\Program Files\Git`
- 版本：`git version 2.54.0.windows.1`

已设置全局 Git 基础配置：

```powershell
git config --global init.defaultBranch main
git config --global core.autocrlf true
git config --global core.editor "code --wait"
git config --global credential.helper manager
```

未设置：

- `user.name`
- `user.email`

原因：

- 这两个值需要用户确认，不应猜测。

### 验证结果

在 `F:\Scene_cluster` 执行：

```powershell
. .\activate_project.ps1
python --version
python -c 'import sys, pandas, hdbscan, umap, nuscenes; print(sys.executable); print(123)'
git --version
```

确认：

- `Python 3.9.23`
- `D:\Python\Conda\envs\autodrive-cluster\python.exe`
- 核心依赖可导入
- `git version 2.54.0.windows.1`
