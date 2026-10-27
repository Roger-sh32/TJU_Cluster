# 开发簇语义媒体复核包

日期：2026-10-01。用户要求继续推进，遇到需要其确认的事项告知。本轮完成可供用户直接观看的五场景材料；最终语义判断与后续规则修改等待实际反馈。

## 当前目录差异

保留的 `HDBSCAN/tables/cluster_semantics_20260930.json` SHA256 为 `420bd453d4c23c0934a7e432fa126da43c25fd38bd792ba5b396a16d8fa9aff2`，与前序记录一致。但是 `logs/analyze_cluster_semantics_20260930.py`、旧核验脚本、旧报告和日志在当前目录未找到。无法确认缺失原因，没有覆盖或篡改旧 JSON 的来源记录。

本轮新配方和验证脚本独立核对现有来源，重算旧 JSON 的 94 组 × 52 字段画像、正值计数及典型样本选择，全部相符。旧配方本身的历史可复现性缺口仍存在。新报告明确区分数值复核和视频语义验收。

## 原计划媒体检查

原计划开发场景 0158、0905、0544、0997、0703；身份逐条与冻结 split、当前审计特征表和 30/1 seed42 结果一致。用流式 JSON 解析读取 sample_data，避免完整加载 263 万条表；只检查指定开发场景的 CAM_FRONT 关键帧及其间 sweeps。

| 场景 | 关键帧缺失 | 关键帧时间跨度内相机文件缺失 | 结果 |
| --- | --- | --- | --- |
| 0158 | 0/40 | 0/228 | 导出成功 |
| 0905 | 40/40 | 232/232 | 保留待查，未导出 |
| 0544 | 41/41 | 238/238 | 保留待查，未导出 |
| 0997 | 41/41 | 230/230 | 保留待查，未导出 |
| 0703 | 40/40 | 235/235 | 保留待查，未导出 |

无需用户确认即可完成以上检查；本轮没有下载任何媒体。

## 补充选择与导出

在冻结开发集扫描 CAM_FRONT 关键帧存在/非空情况，145/700 条通过存在性检查，尚不等于全媒体完整或所有关键帧可解码。根据相同 anchor 簇，排除已有 GIF 场景和原计划五条，优先不同采集日志，以原始 52 维全开发集标准差缩放后的特征均方根距离选择补充场景：

| 原缺失场景 | 补充场景 | anchor 簇 | 特征 RMS 距离 | 规则风险 |
| --- | --- | --- | ---: | ---: |
| 0905 | 0107 | C5 | 0.796 | 0.319 |
| 0544 | 0151 | C3 | 0.937 | 0.160 |
| 0997 | 0032 | C9 | 0.659 | 0.016 |
| 0703 | 0014 | C8 | 1.013 | 0.005 |

补充目的为检查同簇解释，不能替代对缺失原目标的判断。0032 尤其是低风险背景对照，不能据其正常行驶宣称 0997 的高风险已证实/排除。可用性抽样有偏，未据此估计有效性。

0158 加四条补充均来自不同日志；五条全部 CAM_FRONT sweeps 在关键帧跨度内存在、非空。按原始时间约 6 Hz 取最近实际相机帧，保留最后一帧；GIF 时长按时间累计舍入至 10 ms，解决旧 GIF 固定 160 ms 导致的加速。原始逐帧时间、文件哈希、采样索引、实际编码时长均保存。

| 场景 | 导出帧数 | 实际播放时长/s |
| --- | ---: | ---: |
| 0158 | 118 | 19.50 |
| 0107 | 118 | 19.45 |
| 0151 | 116 | 19.10 |
| 0032 | 118 | 19.65 |
| 0014 | 117 | 19.40 |

末帧额外停留一个采样间隔，播放总时长因此比数据时间跨度稍长。所有选中原图完整解码并核对元数据尺寸；五个 GIF 再逐帧解码、核对帧数和时长。五个 GIF 加内部六帧缩略图共约 209.8 MiB。没有生成其他摄像头或批量场景预览。

内部缩略图已目视检查内容、场景身份和时间标签，未将缩略检查当专家标签。缩略图只用于快速检查，人工以保持原比例的 GIF 为主。

## 复现命令与环境

工作目录 `F:/Scene_cluster`，解释器 `D:/Python/Conda/envs/autodrive-cluster/python.exe`，使用现有 Pillow、pandas、numpy。未调整依赖或改动受来源约束的特征/评分/聚类脚本。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/build_semantic_review_pack_20261001.py 2>&1 | Tee-Object -FilePath logs/semantic_review_pack_20261001_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/select_available_review_cases_20261001.py 2>&1 | Tee-Object -FilePath logs/semantic_review_supplements_20261001_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/export_review_supplements_20261001.py 2>&1 | Tee-Object -FilePath logs/semantic_review_supplement_export_20261001_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/verify_semantic_review_pack_20261001.py 2>&1 | Tee-Object -FilePath logs/semantic_review_pack_verification_20261001_console.log
```

配方拒绝覆盖日期限定的既有输出。新配方运行前后核对关键输入；全部代码/输入/所选原图/GIF 哈希保存在媒体报告、补充选择报告和拟定的补充导出 protocol 中。导出 helper 最后控制台的分母固定显示 `/5`，补充实际为四条，以报告 scenes 数组和 exported_count=4 为准，未把计数显示当作第五条失败。

产物：

- `outputs/人工复核/聚类语义五场景复核包_20261001.md`：五条可观看预览、逐条特征与待回答的问题；没有伪填用户反馈。
- `HDBSCAN/tables/semantic_review_media_20261001.json`：原计划五条检查，一条导出、四条缺失。
- `HDBSCAN/tables/semantic_review_supplements_20261001.json`：补充选择规则与同簇身份。
- `HDBSCAN/tables/semantic_review_supplement_export_protocol_20261001.json`：补充导出前固定的四条与配方来源。
- `HDBSCAN/tables/semantic_review_supplement_media_20261001.json`：四条补充预览及帧来源/播放时间。
- `exports/semantic_review_20261001/`、`exports/semantic_review_supplements_20261001/`：生成媒体，继续由 Git 忽略。

## 核验与待确认

独立核验退出码 0：旧 94 × 52 画像相符、全部现存输入/输出哈希一致、五个 GIF 完整解码和时序一致、四对补充同簇、五条来自不同开发日志。前序 20 次参数结果另由 `logs/verify_parameter_stability_20260930.py` 重新核验，通过身份、来源、分项评分与 40 对比较。本轮没有改动主线行为，不把旧 165 项测试结果当本轮新运行。

当前需要用户确认五条的实际交互含义，具体问题见复核包；尤其是施工人员控制通行的测试价值、0107 是否真实侵入、0151 转弯前后行人与车辆是否相关。反馈前不据这些预览修改风险权重或冻结参数。正式 150 条评价集继续隔离，原四条缺失问题保持待查。
