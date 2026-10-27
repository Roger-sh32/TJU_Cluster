# v6.1 同目标历史交互连续性

2026-10-15（北京时间）。用户明确批准实施上一轮短设计。限定目标是避免逐帧路线分离切短同一目标已建立的历史让行语境；不恢复当前横向冲突，不借卡车给无关小汽车补标，不修改几何阈值/TTC/VRU/权重，不提取/拟合/访问评价150。

## 实现与来源

- 新模块：`HDBSCAN/scripts/crossing_candidate_v6_1.py`，测试：`HDBSCAN/tests/test_crossing_candidate_v6_1.py`。
- 新配方：`logs/crossing_v6_1_replay_20261015.py`，测试：`logs/test_crossing_v6_1_replay_20261015.py`。
- 来源是冻结v6的29×129特征/横向与路线证据，以及冻结v5.2对应轨迹；不重新计算或改变v6几何、横向标记和未知状态。新输出明确为 `candidate_feature_replay`，正式拟合必须拒绝。
- 诊断依据：[0067/0068逐目标核对](F:/Scene_cluster/logs/crossing_v6_boundary_20261015.md)。原文件记录的是当时尚待审批的设计，本次批准和实施记在本日志，不改写该原始诊断。
- 环境：`D:/Python/Conda/envs/autodrive-cluster/python.exe`。固定29开发成员/顺序/52聚类字段不变，所有早期绑定文件原样保留。

实现先执行v6的局部门控，再仅对同目标已有保留、响应保护、路线潜在相关、未来完整且非未知的锚点，允许在其原连续曝光段、种子之后六秒内保留原局部左转逻辑本来成立的历史表示。曝光间隔仍用原0.75秒条件；不能跨目标、缺口、新曝光片段或回溯到种子之前。新诊断逐条记录恢复帧的实例、种子帧和 `historical_response_episode` 类型。尾帧即使未来未知，也只保留历史上下文，原未知状态不清除、不升级为当前冲突或因果确认。

指定0068卡车/小汽车仅用于冻结回归控制，不出现在规则算法中。要求卡车原连续曝光14–23帧历史语境保留、原横向15/16帧不变、小汽车24帧不能补回；同时检查0552公交程序语境、0107侵入和0453/0073既有过滤不回退。几何边界稳健性和具体公交画面身份不是本版已解决的问题。

## 测试与审查过程

新模块首轮12项测试中4项如预期失败，见 `crossing_v6_1_red_20261015.log`；实现后通过。无曝光时速度NaN被绕过的测试先失败后修复，见 `crossing_v6_1_validation_red_20261015.log`/`crossing_v6_1_validation_green_20261015.log`。配方5项先失败后实现，见 `crossing_v6_1_recipe_red_20261015.log`/`crossing_v6_1_recipe_green_20261015.log`。

首次独立窄审复现布尔帧号别名、字符串状态真值问题（属于畸形API输入，未证明冻结JSON已损坏）。补4个失败测试后，证据/路线索引限定为真实int、状态字段限定为真实bool，目标身份校验；18项模块+5项配方共23项通过，见 `crossing_v6_1_review_red_20261015.log`/`crossing_v6_1_review_green_20261015.log`。

全套测试、父版本封印检查和配方窄审进行中；尚未冻结或执行新重放，不把单元测试通过写成场景验收。后续原始摘要、精确命令与完成结果在本文件续记。

## 冻结与实际完成

后续全HDBSCAN312项、配方5项通过，最终独立窄审未发现剩余P1/P2。配方冻结前后都没有修改父版本源码或输出；窄审没有代替本地实际重放。命令见下，控制台为 `crossing_v6_1_full_tests_20261015.log`、`crossing_v6_1_recipe_green_20261015.log`、`crossing_v6_1_parent_before_20261015.log`。

原始协议 SHA256：`51b6be617bb455bfd44a2d8bcf9010b73ee1d16bc7aa9f60963dacc9186c3209`。原始报告 SHA256：`9cc0ff917895087587155ea65611099043ba288a8ec7f64513d1945c92bcc42a`。新规则/测试/配方/输入诊断/来源表/证据/运行环境与同目标边界控制在run前绑定，不得再原地编辑、重置状态或刷新封印。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -W ignore::FutureWarning -m unittest discover -s HDBSCAN/tests -q
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest logs.test_crossing_v6_1_replay_20261015 -q
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/crossing_v6_1_replay_20261015.py prepare
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/crossing_v6_1_replay_20261015.py run --expected-protocol-sha 51b6be617bb455bfd44a2d8bcf9010b73ee1d16bc7aa9f60963dacc9186c3209
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/crossing_v6_1_replay_20261015.py check --expected-protocol-sha 51b6be617bb455bfd44a2d8bcf9010b73ee1d16bc7aa9f60963dacc9186c3209
```

以上退出0，完成时间北京时间2026-10-15 19:38:01，run的session60030已退出，无活跃重放。状态 `completed_candidate_requires_review`，不自动成为正式模型或整批语义验收。只读重验使用上述原始摘要；不要重复prepare/run。精确核验重算29条历史事件并核对输入/源码/输出封印，正式拟合拒绝已确认。详见 `crossing_v6_1_prepare_20261015.log`、`crossing_v6_1_run_20261015.log`、`crossing_v6_1_verify_20261015.log`。

## 结果与限制

- 29×129/52聚类字段清单保持；相较v6，28条全字段不变，仅0068的 `left_turn_cross_traffic_interaction_ratio` 一格变化，也是一个聚类输入值：0.23076923076923078→0.2564102564102564。
- 仅一条目标帧恢复：卡车 `727349048e9044d98846cbeeb3a1b5fd` 的第23帧（11.551秒），种子为同一卡车第15帧（7.551秒），类型为历史响应事件。卡车原14–23连续曝光段均保留。
- 小汽车 `64a805096d9047a6bbc73734b0a90e67` 的局部左转标记仍全False，第24帧（12.001秒）不补回。因此没有为了匹配旧28.21%场景值而把小汽车一起恢复。
- v6所有当前横向冲突/路线几何/未知证据原样复用，0068原15/16横向锚点保留；0453/0073过滤没有回退，0067原待审过滤没有变化。0552公交程序语境和0107侵入不变。
- 不改变尾帧是否存在即时冲突或已知未来；恢复的是同一目标已建立的历史交互表示，不是新增碰撞、停车因果或独立风险标签。

结果入口：[v6.1事件连续性对照](F:/Scene_cluster/outputs/人工复核/横向交互v6_1事件连续性对照_20261015.md)。表、事件种子追踪和比较在 `HDBSCAN/tables/*v6_1_replay29*20261015*`。没有新的NuScenes查询质量审计，没有新媒体或全700/拟合/KMeans/评价使用。0073近1m边界稳健性、0067横向公交具体画面对应、0669 TTC、0102/0151 VRU和0552部分卡车绕行仍待后续，不宣称全部解决。

统计准备包原始manifest/算术只读核验通过，见 `crossing_v6_1_statistics_before_20261015.log`；早期候选完整来源/输出由递归父版本检查确认不变。所有原未知目标不清零。测试/结构通过不是专家有效性或论文提效成绩。
