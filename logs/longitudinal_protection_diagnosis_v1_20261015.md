# 纵向绕行保护根因诊断v1执行记录

## 范围与假设

依据持续推进目标，本轮先完成不需要人工判定的既有开发轨迹诊断，人工/设计选择另存 [暂挂清单](F:/Scene_cluster/logs/deferred_decisions_20261015.md)。上一轮已产出v7候选与验证证据，属于实质进展；本轮不是轮询旧完成状态或重启实验。

假设：旧原始绕行判据把静态前车、全场最大受阻时长/最近距离与首段随后10秒的侧移或转角组合，没有证明同一目标对自车造成局部阻挡响应。正常曲率即可触发原始候选，再触发v7整场保护；不能通过撤销保护直接修0669。

只读v7及已冻结轨迹，检查全部四条受保护开发场景0669/0011/0030/0074，加0026末帧摩托车控制。重现保护分支及原始计算输入，按同目标/连续时段拆片段，记录1/3/6/10秒离散运动量和既有v6几何相关性。窗口是诊断展示，不是新增特征/阈值；不计算评分或门控，不改变候选、不调用`gate_candidates`，不读取媒体/评价语义或启动全700/拟合。

初帧速度占位0不当作已观测停车；末帧没有运动跨度记未知；真实未来括界和采样跨度分开记录，缺口不桥接。已观测路线可能是成功避让之后的路线，几何分离或没有制动都不能独立推断无交互。

## 测试与审查

新配方 `logs/diagnose_longitudinal_protection_v1_20261015.py`，测试 `logs/test_longitudinal_protection_diagnosis_v1_20261015.py`。初始8项缺模块失败保留于 `longitudinal_protection_diagnosis_v1_red_20261015.log`；扩展为17项测试，通过日志 `longitudinal_protection_diagnosis_v1_pre_freeze_tests_20261015.log`。包括目标切换/缺口分段、正常曲率旧判据反例、跨目标聚合反例、末帧未知/非网格括界、无静态障碍的最低事件锚点、原始无事件填值、保护源不变及原始报告摘要锁定。

330项现有HDBSCAN测试通过，见 `longitudinal_protection_diagnosis_v1_hdbscan_tests_20261015.log`。窄审指出不能仅信状态中的报告摘要，已新增原始v7报告摘要常量并先失败测试复现，见 `longitudinal_protection_diagnosis_v1_digest_red_20261015.log`（16项中仅这一项失败），随后修正；所有旧源码/表格/协议/报告不动。最终复审无剩余P1/P2，静态审查不代替实际执行。

## 运行环境与命令

`D:/Python/Conda/envs/autodrive-cluster/python.exe`，2026-10-15，北京时间。父v7协议原始SHA256 `ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d`，报告原始SHA256 `b7df6d51107f04cf3b7fdf9142fcddf24cec1a997e99277555ce3eab4872bdf3`。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest logs.test_longitudinal_protection_diagnosis_v1_20261015 -v *> logs/longitudinal_protection_diagnosis_v1_pre_freeze_tests_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest discover -s HDBSCAN/tests -v *> logs/longitudinal_protection_diagnosis_v1_hdbscan_tests_20261015.log
```

## 状态

21:21:41北京时间单次诊断完成，session87762退出0，状态 `completed_diagnosis_requires_design`，无活跃诊断进程。新协议原始SHA256 `fd405aeee930f47ad9534bbb84b5f4a49c09ffc74eed1b4377aa954fa5a7637b`；seal原始SHA256 `9678da24c4ff50e2d37dff18354a22cd6926350d7bc9aa98c33d90cbcc50caf5`。新绑定源码/测试/协议/证据JSON/报告/seal不可原地修改，不刷新封印或重复run。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/diagnose_longitudinal_protection_v1_20261015.py prepare *> logs/longitudinal_protection_diagnosis_v1_prepare_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/diagnose_longitudinal_protection_v1_20261015.py run --expected-protocol-sha fd405aeee930f47ad9534bbb84b5f4a49c09ffc74eed1b4377aa954fa5a7637b *> logs/longitudinal_protection_diagnosis_v1_run_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/diagnose_longitudinal_protection_v1_20261015.py check --expected-protocol-sha fd405aeee930f47ad9534bbb84b5f4a49c09ffc74eed1b4377aa954fa5a7637b *> logs/longitudinal_protection_diagnosis_v1_check_20261015.log
```

prepare/run是历史记录，不再执行；后续只读check。本诊断精确重放check的session16905退出0，见 `longitudinal_protection_diagnosis_v1_check_20261015.log`；随后再次核对原始seal摘要不变。原v7精确基线/候选29重放检查也退出0（`longitudinal_protection_diagnosis_v1_parent_check_20261015.log`），原合成统计包封印检查退出0（`longitudinal_protection_diagnosis_v1_statistics_check_20261015.log`）。没有重提场景或产生新特征表。人工/设计队列挂起不是整项目停工，整体目标仍未完成。

## 真实诊断结论

0669原始受阻最大时长1.349秒、最近距离18.211m、首段后10秒侧移46.805m/净转角1.382rad。受阻台账实际串接四个不同静态目标：a853cb…/8c9339…/fe685e…/03d6e4…。分为同目标片段后四段均不满足旧原始绕行判据；五个受阻/最低事件锚点的既有几何查询均为路线分离。最低TTC目标03d6e4…只在3.847秒贡献这类静态受阻标志，不能把其他车片段的持续时间借给它。说明除了正常曲率，还存在目标切换未切断事件导致的“持久受阻”聚合，后续整场保护放大了这项问题。

**不能直接按此诊断取消保护。** 0074同样存在三辆不同静态车的1.500秒聚合受阻，同目标三段均不满足旧绕行判据、四个查询均为路线分离，但该场景人工已确认真实横向车流让行。被查询的静态车不能借用横向让行的身份验收，也不能把过滤这些静态车误称为取消真实让行。下一版必须区分具体目标/具体机制，不能简单用全场“存在让行”或“分段后不成立”开关全部保护。

0030同一道路内摩托车4.399–6.899秒片段自身满足旧判据，六个查询为潜在空间相关；严格避障保护也成立。0011依靠严格避障分支保护，没有达到0.8秒门槛的静态blocked片段；本诊断0011唯一几何查询是最低TTC行驶小车，不是早期被绕行静态障碍，不能拿该查询冒充早期障碍的几何验证。v7原始选中轨迹仍完整保留，下一版保护回归需补短暂静态正例，不能只看blocked片段。

0026最低摩托车仍在末帧，几何和6秒运动窗口未知，不能以没有后续位移或缺未来删除。以上是保护来源诊断，非因果/危险性标签或五条语义验收；0669仍未修复，所有v7特征数值不变。

输出 [可读诊断](F:/Scene_cluster/outputs/人工复核/纵向绕行保护根因诊断_20261015.md) 与 [完整数值证据](F:/Scene_cluster/logs/longitudinal_protection_diagnosis_v1_evidence_20261015.json)。分段/窗口诊断没有改变TTC公式、几何裕度、评分、52字段清单、模型、700/150成员或任何正式评价。保护改版和新目标人工复核继续挂起，后续可独立补充同目标局部证据及合成/静态检查。
