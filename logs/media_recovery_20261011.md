# 相机媒体补数执行记录

## 授权和方案

2026-10-11 用户在确认只补必要相机文件、逐包下载校验后回复“好啊 那就补一下吧”，恢复此前因磁盘空间而暂停的下载。该授权不开放评价调参、正式标签或模型拟合。

这是既有补数流程的限定执行：保留 01/02 批和所有已有图像；补齐冻结 150 条评价场景六路相机的关键帧/关联非关键帧，同时补齐待审开发 0002/0093/0102/0453/0552/0669/0815/0816 的前视图像。仅读取身份、时间、路径、尺寸，不查看评价语义。

第 03 包 HEAD/1MiB Range 连通性已验证，ETag 与旧清单一致；初始 F 盘可用约 508 GiB。03–10 批是候选包，不假装已有最小包映射；顺序下载，达到清单齐备即停止后续包。只从归档恢复清单内且目标路径不存在的 JPEG；已有文件包括空文件都不覆盖。缓存位于 Git 忽略的 `exports/media_recovery_20261011/`，本次不自动删除压缩包。

## 执行步骤

1. 新批次准备：复查冻结划分、当前元数据、缺失文件，重新 HEAD 校验官方对象，固定配方和输入哈希。
2. 安全性测试：Range/ETag/长度、路径穿越/链接、解码尺寸、空间余量、禁止覆盖；在开始写原始数据前通过测试及独立复查。
3. 顺序下载和恢复：专用缓存、断点续传、TLS 验证、对象绑定；gzip CRC/归档完整性检查后再逐个暂存、解码、无覆盖发布，记录哈希。
4. 元数据完整性重审：冻结 150 条六路关键帧全部解码，CAM_FRONT 关联非关键帧全部解码；其他非关键帧检查存在/非空。开发八条单列，不混入评价标签。

## 当前状态

**已完成，2026-10-12 04:58:02（北京时间）。** 状态 completed，03–10 包下载、校验及限定恢复结束，176,569 张全部补齐，剩余缺失 0。目标 211,407 个文件完整性和恢复来源核验通过；来源失败 0、损坏日志行 0。最终报告 SHA256 `ec708a4c29f1320a2b585b25ccef82efd95d63fb098af1e6c8f1fd6c3f7add3f` 与运行状态一致，10 月 12 日复查一致；原 worker 已退出。不要重新运行补数，不自动删除缓存。

六路关键帧与 CAM_FRONT 关联非关键帧已完整解码；其他相机关联非关键帧仅检查存在/非空。结论限于预先选择的评价 150 条和开发八条，不等于完整 nuScenes 数据集齐备。没有查看评价语义或修改划分/特征/模型。经用户同意，下一步开发八条复核见 `logs/development_media_review_20261012.md`。

以下启动阶段和传输补充是历史过程，旧状态不能解释为当前仍在运行。首个会话 45661 停止后，分段续传会话 27054 完成。原审计/恢复清单及协议保持不变。

## 本批输入与数量

新的 `exports/media_recovery_20261011/camera_files.jsonl` 包含 211,407 个预期图像文件：评价六路及开发八条前视。需要补齐 176,569 个（评价关键帧 30,312、关联非关键帧 145,074；开发前视关键帧 204、关联非关键帧 979）。目前已有的 34,838 个图像文件不覆盖，包括仍须解码复审的已有文件。

八个官方对象本日 HEAD 均为可访问、支持 Range，长度/ETag 与原清单一致，总上限 143,184,610,383 字节（143.18 GB / 133.35 GiB），不是预估解压量或承诺最小下载量。缓存保留压缩包，不自动清理用户数据。

准备协议 `exports/media_recovery_20261011/protocol.json` SHA256 `7400a5e08fbe20ef98ccad2e04757790e0f8bdaf7a96dd91f82d85452885f9a5`；最终启动协议 `launch_protocol.json` SHA256 `17c80daf80159bdc3b464a282fdea589e41c36a837a8f3444b597d1fc6767d2e`。准备协议不改写；独立复查追加原子 receipt 写入修正后，保留准备阶段配方/测试副本于 `prepared_sources/`，启动协议校验旧版本哈希并另绑最终配方/测试及原协议。身份清单、划分和元数据不变。

## 实际命令

工作目录 `F:\Scene_cluster`，解释器 `D:\Python\Conda\envs\autodrive-cluster\python.exe`，不重装环境、不关闭 TLS 校验。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest logs.test_recover_camera_media_20261011 -v *> logs/media_recovery_20261011_safety_tests.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest discover -s HDBSCAN/tests *> logs/media_recovery_20261011_hdbscan_tests.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/recover_camera_media_20261011.py prepare *> logs/media_recovery_20261011_prepare_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/recover_camera_media_20261011.py freeze-launch *> logs/media_recovery_20261011_launch_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/recover_camera_media_20261011.py run *> logs/media_recovery_20261011_console.log
```

以上为实际阶段命令，不要照抄重新 prepare/freeze-launch；它们禁止覆盖。`run` 支持失败后验证对象身份并续传，持有进程锁防重复；恢复前先看状态/进程和错误。工作进程关闭或机器重启不会自行恢复，不存在隐藏定时任务。

## 安全核验

13 项操作测试及现有 182 项 HDBSCAN 测试通过；有现有 sklearn 弃用提示，不是失败。独立复查发现并修复：空 partial 重试、gzip 之外的完整 tar 结构/链接/路径检查、归档与 receipt 中断恢复、图像发布前持久化来源日志，以及 receipt 自身的原子发布。各修正均先观察失败测试，再验证通过；最终窄范围独立复审没有剩余 P1/P2。

Range 续传必须匹配 HTTP206/Content-Range/对象 ETag/长度。归档通过完整 gzip CRC、每个 tar 物理头校验及双零结束块、全成员安全检查后才恢复。逐个图像暂存、完整解码/尺寸检查，先 fsync 来源意图，再无覆盖发布。最终审计要求所有原先缺失但已存在的图像能对应来源哈希，不以“文件存在”掩盖来源丢失。

完成后报告位置为 `HDBSCAN/tables/media_recovery_audit_20261011.json`；应检查完整性和来源失败计数再开展人工复核。无评价语义展示或标签生成，700/150 划分、特征候选、旧模型和排序保持不变。

## 传输分段补充

首个 worker 已开始第 03 包，遇到 HTTP 声明全包长度但响应提前 EOF；原有 If-Match/Range 检查允许从已下载前缀安全续传，没有覆盖或错误拼接全包。为避免单个长连接多次被截断，停止了仅下载中的 PID 23008，保留 1,084,671,428 字节缓存；尚无图像发布、恢复日志或完成归档。

补充为每次最多 64 MiB 的精确 Range 请求，第一段也要求 HTTP206，逐段校验 Content-Range 起止/总长、ETag 和本段长度；每段最多五次重试，完成一段后重置重试预算。全包仍须通过完整 gzip/tar 校验才恢复图像。新增三项失败后通过测试，其中包含空缓存到多段完整归档的离线端到端验证；现共 16 项安全测试。

旧启动协议和源码/测试副本保留于 `launch_sources_v1/`，旧运行状态另存 `download_v1_status.json`。新增启动补充 `transfer_protocol_v2.json` SHA256 `73ee4228aa3c1c8466ea6005ffb24cefb995f56a019a1553186b20b2ef78c5eb`，绑定原启动协议、旧源码副本和最终分段代码/测试，身份清单和元数据保持不变。没有改写前两个协议。

实际新增命令：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest logs.test_recover_camera_media_20261011 -v *> logs/media_recovery_20261011_transfer_tests.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/recover_camera_media_20261011.py freeze-transfer *> logs/media_recovery_20261011_transfer_launch_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u logs/recover_camera_media_20261011.py run *> logs/media_recovery_20261011_transfer_console.log
```

分段版 worker 已启动，后续状态仍写同一个状态 JSON；读旧状态不能当作旧 PID 仍运行。16 项安全测试和最终重跑的 182 项 HDBSCAN 测试通过；分段增量独立复查未发现 P1/P2，额外离线短 EOF/读取错误探针均精确断点续传、产出相同字节。实际输入哈希也已再次核验，未改特征源码。

回复前实际检查点：分段 worker PID 23968、会话 27054，2026-10-11 11:02:22（北京时间）处于 `downloading`，第 03 包已保存 1,218,889,156 / 16,599,534,206 字节，约 7.34%。连续两个 64 MiB 分段已完成并进入下一段，attempt=1、last_network_error=null；确认不是只有空缓存或排队。还没有完整归档通过核验，数据集图像尚未发布，不能据下载进度宣称媒体已补齐。运行需要电脑持续开机联网，退出/休眠后要先查看状态再恢复，不自动重启任务。
