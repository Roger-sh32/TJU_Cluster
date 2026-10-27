# 短暂静态目标诊断v2执行记录

## 延续目标与范围

上一轮完成原始绕行保护诊断，定位跨目标受阻聚合并补了可复现证据，属于实质进展。本轮继续不依赖人工决定的开发证据补全，保护改版和正式实验选择仍按 [暂挂清单](F:/Scene_cluster/logs/deferred_decisions_20261015.md) 保留，不因自动推进而视为已经批准。

v1仅查询blocked静态目标和最低TTC目标，漏了0011不满0.8秒的短暂静态选中目标。新独立v2查询所有selected static帧，包括短于blocked门槛的目标；最低TTC明确标注独立角色，不能与静态障碍身份混用。固定0011/0030/0042/0074/0669五条开发轨迹，重现六个既有严格避障字段，记录官方标注绑定身份/类别、时刻、目标速度与原始几何查询，分解既有候选经过的阶段。无新数据提取、媒体/评价读取、门控/阈值/权重/评分/模型/52字段清单改动或全700任务。

初步只读检查定位0011程序静态目标为5.498秒truck `8a557d57675e48eb801633e3e327d939`，净距离27.864m；十秒侧移4.833m/净转角0.076rad，现有短暂避障分支成立，而blocked为0。它不是12.451秒最低TTC的行驶car。此处是程序身份，并无逐目标人工确认。0042未选中静态目标，也不能据此否定人工观察的两次静止车绕行。

## 测试与审查

新配方 `logs/diagnose_short_static_v2_20261015.py`，测试 `logs/test_short_static_diagnosis_v2_20261015.py`。先8项缺模块失败（`short_static_diagnosis_v2_red_20261015.log`），后扩展10项通过（`short_static_diagnosis_v2_pre_freeze_tests_20261015.log`）。覆盖短暂static无blocked仍入查询、身份缺失/不一致/非布尔拒绝、无静态不推断无障碍、TTC/静态角色分离及重合、原始v1seal锁定、短暂严格避障集成反例和八类候选阶段区分。330项现有HDBSCAN测试通过，见 `short_static_diagnosis_v2_hdbscan_tests_20261015.log`。

窄审无P1/P2；指出真实身份/几何及六字段重现仍须实际执行，之后已按冻结配方核验。配方绑定新源码/测试/输入和环境，不改或续写v1原协议、代码、证据或报告。

## 环境与命令

2026-10-15，北京时间；环境 `D:/Python/Conda/envs/autodrive-cluster/python.exe`。父v1原始协议SHA256 `fd405aeee930f47ad9534bbb84b5f4a49c09ffc74eed1b4377aa954fa5a7637b`，原始seal SHA256 `9678da24c4ff50e2d37dff18354a22cd6926350d7bc9aa98c33d90cbcc50caf5`；祖先v7协议/原始报告摘要仍由v1强制校验。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest logs.test_short_static_diagnosis_v2_20261015 -v *> logs/short_static_diagnosis_v2_pre_freeze_tests_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest discover -s HDBSCAN/tests -v *> logs/short_static_diagnosis_v2_hdbscan_tests_20261015.log
```

## 执行与结果

单次run于21:35:24北京时间完成，session27384退出0，阶段 `completed_short_static_diagnosis`，没有活跃提取或诊断任务。新原始协议SHA256 `b7fb9861781d08ffd69a225ba986543556630e844eba5e6cd29f60771570afd6`，原始seal SHA256 `c951debde5f186a8269e52c3981c5cc604c777a313837f1521370a658d0ecf0b`。新配方/测试/协议/数值证据/报告/seal冻结，不原地编辑、刷新摘要或重复run。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/diagnose_short_static_v2_20261015.py prepare *> logs/short_static_diagnosis_v2_prepare_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/diagnose_short_static_v2_20261015.py run --expected-protocol-sha b7fb9861781d08ffd69a225ba986543556630e844eba5e6cd29f60771570afd6 *> logs/short_static_diagnosis_v2_run_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/diagnose_short_static_v2_20261015.py check --expected-protocol-sha b7fb9861781d08ffd69a225ba986543556630e844eba5e6cd29f60771570afd6 *> logs/short_static_diagnosis_v2_check_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/prepare_experiment_readiness_20261013.py --check-only --expected-manifest-sha 444e398e9feee9f958b5cba941efa4a1aade85e81b28327c017ee472be4986e7 *> logs/short_static_diagnosis_v2_statistics_check_20261015.log
```

prepare/run为历史执行命令，不再启动。精确重放check的session27455退出0，见 `short_static_diagnosis_v2_check_20261015.log`，再次核对原始seal摘要不变。祖先原始源/运行环境/输出封印与合成统计包检查通过，未产生新特征表。五条场景的六个严格避障相关字段精确重现，新增的是诊断锚点而不是重新提取。整体目标仍有语义/设计/正式实验/论文材料待办，本轮不标记完成或暂停。

0011静态truck `8a557d57675e48eb801633e3e327d939` 在5.498秒仅单帧被选中，旧算法补偿时长0.500秒，不满足blocked门槛；原短暂避障分支仍成立。它的完整未来几何为 `separated_observed_route`，下界1.299365m。12.451秒行驶car `1e33e49bbc8a4f368892118eb603166f` 的最低TTC几何为潜在相关，下界0.032752m，两者身份/角色不可混用。前者路线分离仍不能独立反驳人工确认的场景级避障，后者潜在相关也不是早期静态障碍的验证。该对照证明不能只凭已走过路线分离或持续blocked门槛来保护/删除短暂避障证据，但尚未建立目标级因果标签。

0030六帧同一摩托车的静态/blocked片段保留，六个查询均为潜在空间相关。0042的19条同路径候选全部落在 `selected_not_static` 阶段，没有静态选中锚点；只能定位当前分支的证据缺口，不能证明停车目标未标注或路面无障碍，更不能回填风险0。

0074新增查询先前不属于blocked的9.751秒静态car `698274afaabd4874a9d6ab422f88b155`，结果未知，其余已有分离查询保持。v1没有检查这个短片段，不能把此前四个分离查询扩展成该场景所有静态目标已知分离。0669五个静态锚点仍为分离，原保护和特征不变；新增控制防止后续改版误删0011短正例或将0074未知升级安全。

结果入口：[短暂静态与受阻对照](F:/Scene_cluster/outputs/人工复核/短暂静态障碍与持续受阻对照_20261015.md)，[完整数值证据](F:/Scene_cluster/logs/short_static_diagnosis_v2_evidence_20261015.json)。保护改版暂挂，没有增添新的人工整场复核任务或代替人工确认。

## 边界

诊断统计不作为危险性、因果或专家验收标签。单帧时长补偿不等于观测了连续半秒；已避让的未来路径分离不能单独否定目标曾有作用。程序目标与已有场景级人工反馈不自动对应。0042候选阶段仅解释已标注候选的计算去向，不证明标注完整或路面没有障碍。0669仍未修复，所有v7值保留。
