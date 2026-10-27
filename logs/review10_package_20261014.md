# 十场景集中复核包

## 授权与范围

2026-10-14，用户表示可一次多看几条。按当前待查与已知正反例固定10条开发场景：0453、0552、0068、0073、0151、0102、0669、0815、0816、0107。不是10条全新抽样，不是随机样本或150条独立盲评，也不据其计算有效性成绩。

复用8条已有带时间动图，只有0068/0073从原图新增带时间导出，避免旧6fps文件的时间对齐不明。优先约6Hz原始间隔，缺非关键帧时只允许显式2Hz关键帧降级，不插帧；关键帧缺失则停止，不换场景、不下载。F盘初始空余约350GiB，不删除媒体包或旧输出。

数值只读冻结v4完整开发表与v5.2限定29表；10条均在当前29条内且匹配冻结开发身份。当前v5.2没有拟合，不能套用旧簇号/排名。0102 VRU、0669 TTC、0552严格绕行仍未修，回复模板明确局部问题、已有反馈和证据不足边界。视频末尾未来缺失不要求人工猜测。

## 执行状态

- [x] 既有目录/媒体报告/当前特征及逐目标证据检查；固定10条，不读取评价语义。
- [x] 新配方 `logs/build_review10_package_20261014.py` 与10项契约测试；先失败后实现身份、媒体缺失、路径/原始摘要、运行环境、失败状态保护。
- [x] 窄审发现旧媒体记录夹带历史特征值与簇排名，用失败回归复现后改成明确媒体字段白名单；当前卡片独立读v4/v5.2数值，旧记录不冒充当前结果。
- [x] 最终窄审及全测试通过后，冻结来源/帧计划并导出2条新GIF。
- [x] 10条全GIF解码、源图/输出摘要、帧元数据/原始时序/文档重放核验；更新入口。

本轮未修改冻结代码/测试/协议/结果，没有特征提取、拟合、选参、KMeans、下载、评价预测或盲评。原始媒体报告及既有GIF不改。后续用户反馈单独新增日志，不回写本包或历史协议。

## 产物

已生成 `outputs/人工复核/十场景集中复核包_20261014.md`；8条嵌入旧GIF，2条新GIF及联系图在 `exports/review10_20261014/`。来源/名单/帧计划在 `HDBSCAN/tables/review10_package_protocol_20261014.json`，媒体记录在同目录 `review10_package_media_20261014.json`，状态在 `logs/review10_package_20261014_status.json`。

每条给出关键秒数、已知观察、局部问题、v4→v5.2有限字段和按实例合并的横向候选时段。没有目标框，不将实例ID自动指认成镜头中的某辆车。普通反馈、无法判断、与前次一致均可，不预填新的人工答案。

## 环境与命令

使用 `D:/Python/Conda/envs/autodrive-cluster/python.exe`。新代码仅做既有媒体导出封装和文档准备，复用已冻结渲染/JSON流式读取工具；协议记录解释器文件、Python/Pillow版本、字体、配方/测试、输入和相关输出摘要。运行后禁止编辑已绑定配方/测试，不重复启动。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest logs.test_review10_package_20261014 -v
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest discover -s HDBSCAN/tests
```

最终窄审无剩余P1/P2，10项配方契约和276项HDBSCAN测试通过；已有sklearn参数更名警告，不改环境。实际生成已启动，会话61021，控制台 `logs/review10_package_run_20261014.log`；先做元数据/源图/GIF预检查，再冻结协议和导出，仅此一项媒体任务，不重复启动。尚未完成前不写成媒体完成。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/build_review10_package_20261014.py run
```

## 最终状态

实际生成已完成，会话61021退出0，无本批活跃任务；状态 `completed_requires_human`，不是人工验收通过。10条来自7个开发日志，8条复用/2条新导出，均为约6Hz原始间隔，没有降级或插帧。0068新GIF116帧，0073为118帧，另两张联系图合计新占用约75MiB；旧媒体及缓存无覆盖/删除。

原始协议SHA256 `de85c4a9c1c90c3521e726a983186c64ec2221e0c6d929e2f1c095d14b405c49`（748714 bytes）；媒体报告SHA256 `bde790fda535d03224779a4f2f041e6f59596392a39dd55d3da3c59a182920d2`（728212 bytes）。本包配方/测试/输入/帧计划/媒体/文档现已绑定，不原地编辑或重导；新反馈放另一个日志。旧媒体记录中的历史特征、风险、簇/排名及pending注释已通过白名单剥离，JSON不冒充当前特征。

带原始协议摘要的只读verify成功：10条身份、源图摘要、相机元数据、相对时间、全GIF逐帧解码/时长和卡片文本重放均通过。10个嵌入动图和全部本地链接检查通过；已目视检查两张新联系图的场景/时间顶栏及版面，未据此给语义标签。10项配方契约/276项HDBSCAN通过，最终窄审无剩余P1/P2。

既有v5/v5.1/v5.2只读check递归通过，原始摘要的统计准备包重放亦通过。没有改特征数值/阈值/权重/模型/划分，没有读取评价语义。校验控制台分别见 `review10_package_verify_20261014.log`、`review10_package_document_check_20261014.log`、`review10_package_candidate_preservation_20261014.log`、`review10_package_statistics_preservation_20261014.log`。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/build_review10_package_20261014.py verify --expected-protocol-sha de85c4a9c1c90c3521e726a983186c64ec2221e0c6d929e2f1c095d14b405c49
```

首次run命令仅记录来源，当前不能再运行；verify可只读复核。人工入口 [十场景集中复核包](F:/Scene_cluster/outputs/人工复核/十场景集中复核包_20261014.md)，先前导航/协议仍保留，不回写旧文档。无需重复已经确认的整段描述，也不要求判断视频外未来。

交付前10项配方测试及原始协议摘要的全包verify再次通过；`git diff --check`无空白错误，仅既有CRLF提示。最终日志 `review10_package_delivery_tests_20261014.log`、`review10_package_delivery_verify_20261014.log`。未提交/推送Git，未形成新人工结论。
