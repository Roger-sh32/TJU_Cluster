# 补数后开发场景复核执行记录

## 范围与计划

用户在媒体补数完成后回复“开始吧”，本轮执行限定开发复核，不运行模型或评价。

- 核验补数完成报告与状态绑定，记录真实完成时间。
- 固定八条待审开发场景：0002、0552、0093、0102、0453、0669、0815、0816。前五条为优先反馈组，其余为补充组；按既有变化选择，不是随机代表性抽样。
- 只导出 CAM_FRONT，使用已恢复关键帧和关联相机帧，约 6 Hz、原始数据时间、保持图像比例。禁止覆盖既有输出。
- 对照当前候选 700 条与历史审计表，列明变化和问题；不引用旧聚类排名作为当前结果，不将风险下降视作改善。
- 验证逐帧来源、场景身份、GIF 解码和时序，更新 README、AGENTS 和变更记录。

## 媒体恢复完成核验

补数状态为 completed，报告完成时间 UTC 2026-10-11 20:58:02，即北京时间 **2026-10-12 04:58:02**。03–10 包全部完成，176,569 个缺失图像补齐，目标 211,407 个文件全部存在，恢复来源失败 0、损坏日志行 0。最终报告 SHA256：`ec708a4c29f1320a2b585b25ccef82efd95d63fb098af1e6c8f1fd6c3f7add3f`，与运行状态一致。

全部六路关键帧、CAM_FRONT 关联非关键帧已完整解码；其他相机非关键帧仅检查存在和非空。此结论限于冻结评价 150 条和指定开发八条，不意味着整个 nuScenes 数据集媒体完整。旧审计作为历史证据保留。

## 执行状态

限定八条导出已完成并核验，媒体报告 `HDBSCAN/tables/development_review_media_20261012.json`，固定协议 `HDBSCAN/tables/development_review_protocol_20261012.json`，人工入口 `outputs/人工复核/候选特征八场景复核包_20261012.md`。八张内部六帧缩略图已目视检查比例、时间顶栏、场景内容和编码可读性，不将抽帧观感标成专家标签。

八条人工语义反馈已接收，原话和问题定位见 `logs/development_review_feedback_20261012.md`，可读复核包已更新。0002/0093 的过滤得到支持；0102/0669 的车辆过滤得到支持，但其他字段仍需排查；0552/0453 有真实交互须保护，0815/0816 仍有误报。不是整批验收。未修改特征、划分、权重、阈值、模型或排名。评价集不展示、不调参。原四条旧簇语义缺媒体目标（0905/0544/0997/0703）不在本次开发补数/导出范围内，不宣称它们已可复核。原始媒体 JSON 保留导出时待反馈状态，不回写。

## 产物与核验

| 场景 | 关键帧 | 导出帧数 | GIF 播放秒数 |
| --- | ---: | ---: | ---: |
| 0002 | 40 | 118 | 19.65 |
| 0552 | 41 | 120 | 20.05 |
| 0093 | 39 | 116 | 19.20 |
| 0102 | 40 | 117 | 19.55 |
| 0453 | 41 | 121 | 19.95 |
| 0669 | 41 | 119 | 19.80 |
| 0815 | 40 | 118 | 19.55 |
| 0816 | 41 | 120 | 19.85 |

八个 GIF 和八张内部缩略图共 312.47 MiB，位于忽略的 `exports/development_review_20261012/`。前视约 6 Hz，保留最后一帧及额外一个间隔，按累计 10 ms 量化，全部原图哈希/时间及帧时长保留。缩略图保持比例。

来源复核 `check --check-only` 退出 0，候选表/风险与冻结源码匹配。四项配方契约测试先因缺少新配方失败，再通过：评价成员拒绝、token 不匹配拒绝、采样有序不重复且保留末帧、累计 GIF 时序。导出结束时核验通过，随后独立进程只读 `--verify` 再通过，逐帧重算来源及输出哈希、完整解码、帧数和时长，差异值与历史/当前 CSV 对应一致。

限定配方独立只读审查无新增 P1/P2；审查者没有检查最终媒体，因此不是独立媒体语义验收。本轮未改生产代码，不把旧 182 项测试当成本轮新运行。

## 环境与命令

工作目录 `F:/Scene_cluster`；`autodrive-cluster`，Python 3.9.23、Pillow 11.3.0。未安装/调整依赖。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest logs.test_development_media_review_20261012 -v *> logs/development_media_review_20261012_tests.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/development_candidate700_20261001.py check --check-only *> logs/development_media_review_20261012_candidate_check.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/build_development_media_review_20261012.py *> logs/development_media_review_20261012_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/build_development_media_review_20261012.py --verify *> logs/development_media_review_20261012_verification.log
```

执行会话 93963 已退出 0。日期限定输出禁止覆盖，复核只用 `--verify`，不要重复导出。配方协议绑定当前候选、历史表、差异/风险表、划分、媒体完成报告、元数据、七模块和本次配方/测试/复用的流式读取及哈希 helper。每个 GIF 所用原图逐帧绑定。输出不是当前候选的拟合/排序结果。
