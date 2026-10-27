# 八条开发场景逐目标诊断

## 目的与范围

用户在八条反馈后回复“好 继续”，执行已说明的限定诊断：重放 0002/0093/0102/0453/0552/0669/0815/0816，不重提 700 条、不拟合、不使用评价、不改冻结来源或特征规则。保留真实让行与部分占道绕行；没有直接清零场景字段的授权或做法。

## 计划与核验门槛

1. 验证当前七模块与 v4 绑定、八条开发身份、已有候选表来源；禁止覆盖日期限定输出。
2. 用未经修改的提取器重放八条，附原有逐车轨迹。独立诊断配方通过 runpy 执行原文件，保留运行环境及输入哈希，随后在同一已加载数据上重建人类 VRU 原始候选，避免再次加载全数据表。没有猴子补丁、代码注入或替换规则。
3. 重放 CSV 与冻结 700 表对应八条逐列精确相等，质量异常 0；原始正 Inf 只能是已知诊断距离。任何不一致不报告为成功。
4. 列出横向候选目标/时间/过滤阻碍，最低 TTC 目标和当时局部转角，VRU 人行道及车道几何证据，停止/让行时序和静止障碍目标。不用“观测未近距”自动证明无让行，不从未来缺失推导安全。
5. 整理可读定位结果与下一版建议；生产修改另按新候选版本、小批失败后通过测试及保护正例执行。

## 当前状态

限定诊断已完成，2026-10-12 北京时间 21:23 生成八条逐目标报告，随后完成独立数值复核及车身几何诊断。状态为 `completed_diagnostics_requires_review`，不是修复后通过或语义验收。没有运行中的本批提取任务，不要重复启动。

八行、129 列与冻结 v4 开发 700 表对应行逐列精确一致，52 个聚类字段均不变。查询异常 0；14 个正 Inf 仅为 `merge_observed_min_distance` / `vru_observed_min_distance` 的已知诊断哨兵，无其他异常非有限值。提取阶段约 56 秒，未做聚类、评分替换或全量重提。

## 配方、失败与续跑

运行环境：`D:/Python/Conda/envs/autodrive-cluster/python.exe`，Python 3.9.23。原协议绑定七模块、固定划分、八条身份、v4 表、元数据/地图、配方和依赖哈希；运行包版本见原协议 `runtime`。

以下是已经执行的命令，仅用于追溯，不要重跑写入型配方；均禁止覆盖已有输出：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/diagnose_review8_20261012.py --preflight
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/diagnose_review8_20261012.py
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/complete_target_diagnosis8_20261012.py
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/summarize_target_diagnosis8_20261012.py
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/check_target_geometry_20261012.py
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest discover -s HDBSCAN/tests
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest logs.test_review8_target_diagnosis_20261012 logs.test_complete_target_diagnosis8_20261012 logs.test_target_geometry_20261012 -v
```

首次提取已成功，但逐目标 VRU 后处理遇到地图 API 限制：`lane_connector is not a polygon layer`。保留原失败状态和控制台，不回写失败历史。续跑单独冻结补充协议，复用已完成 CSV/轨迹，不重复提取；只在诊断地图适配器中跳过无多边形的 connector 点查询并记 `None/unknown_not_queried`，不当作不存在。通过 AST 只加载冻结来源的五个几何函数定义，不执行提取器主程序，也没有修改生产模块。

- [原协议](F:/Scene_cluster/HDBSCAN/tables/target_diagnosis8_protocol_20261012.json)：SHA256 `f8c69b34de416bd3fe4d76033fa9e41521e645a430417b49afc0f31df51ae30b`。
- [续跑协议](F:/Scene_cluster/HDBSCAN/tables/target_diagnosis8_continuation_protocol_20261012.json)：SHA256 `d2ce73cd9424d272648d70f5b7b880860add1a8b9b8b278ce283f23a2199f908`。
- [诊断 JSON](F:/Scene_cluster/HDBSCAN/tables/target_diagnosis8_20261012.json)：SHA256 `ca28a0801b7269cd61c91f11e7c9e6a8a2b1a57e4c5077d4f5063c1aa0a57df1`。
- [逐列核验与可读报告绑定](F:/Scene_cluster/HDBSCAN/tables/target_diagnosis8_verification_20261012.json)：重算原始横向候选与过滤阻碍、核对 VRU 帧比，未把人工反馈写成真值。
- [方向车身几何](F:/Scene_cluster/HDBSCAN/tables/target_diagnosis8_geometry_20261012.json)：独立绑定配方、三项测试、报告和轨迹来源；无重新提取、过滤或改分。

控制台在 `review8_target_diagnosis_20261012_console.log`、`review8_target_diagnosis_20261012_continuation_console.log`；失败状态在 `review8_target_diagnosis_20261012_failed_status.json`。182 项既有 HDBSCAN 测试通过，新增 5+2+3 项诊断契约测试均先失败后通过，最后合跑 10 项通过；日志在本目录同前缀的 `hdbscan_tests.log` / `recipe_tests.log`。这些测试不是场景识别准确率。

最终只读复验同时核对原协议、续跑协议、报告、轨迹、几何配方/测试和七模块哈希，并再次精确比较八条全部字段，结果通过；日志 `review8_target_diagnosis_20261012_final_check_utf8.log`。首次临时核验命令使用 Windows 默认 GBK 读取 UTF-8 JSON 失败，保留 `final_check.log`；仅加 Python `-X utf8` 后重验，没有环境重装或结果重写。`git diff --check` 通过，仅提示已有提取脚本的 CRLF/LF 行尾规范化。

## 诊断结论与下一步边界

可读总览见 [八场景诊断结论](F:/Scene_cluster/outputs/人工复核/八场景诊断结论_20261012.md)，具体实例与时间见 [逐目标明细](F:/Scene_cluster/outputs/人工复核/八场景逐目标诊断_20261012.md)。

0815 的残留是 t=18.950 秒的远处车辆，不是起步邻车；未来仅 0.500 秒，直线投影到走廊约需 5.278 秒。当前规则因未来不足和转角不足未删，不能把未删等同确认交互。0816 的 t=8.001 秒卡车中心到未来折线 5.921 m，车身到整条路线最小 0.714 m，而同帧自车中心到车身最小 8.486 m；因此仅缩窄外接圆不够，必须处理空间相交与同时到达的区别。仅检查关键帧车身、未减自车车身/安全裕度，不能据此认证无碰撞风险。

0102 的三帧 VRU 候选均为同一地图人行道行人，当前车道中心距 10.52–11.05 m，观测同步最近距约 9.84 m。护栏仍是人工证据，不能声称地图识别出护栏。0669 的最低 TTC 来源于静止对向车，129.50°朝向差未达现有 134.65°门槛，局部转角已足够；应检查实际通行路线和目标占道，不直接调一个角度迎合该场景。

0453 已过滤的 t=0.499 秒车先于 t=8.349 秒开始的持续停车，不是已确认的后续穿行皮卡；0552 已过滤的 t=13.398/13.898 秒小汽车也不是已确认的前段公交车让行目标。不能因场景有真实交互就反向恢复所有原始候选，也不能把这些真实交互一起清掉。

下一版应另建候选来源，先设计末尾未知/预测/确认分层、局部时序及同向车身占用核验，再做小批保护回归。完整未来、实际制动/低速让行及静止占道正例必须保留；环岛曲率不能触发全场左转交互传播。v4 七模块、旧 CSV/manifest、700 成员、评分和模型均保持原样。没有正式评价、KMeans、媒体下载或新 GIF；雨天因素仍未自动实现。
