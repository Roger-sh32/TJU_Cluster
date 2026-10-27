# 纵向目标v7固定29条执行记录

## 授权与范围

用户于2026-10-15以“可以”批准上一轮短设计。新建独立v7，不改任何既有冻结版本、生产提取入口或历史表。环境为 `D:/Python/Conda/envs/autodrive-cluster/python.exe`。

固定开发29条，先还原逐帧同路径候选及原标注顺序、最近前车、31个纵向字段和静止目标/静态障碍/原始偏离台账。精确基线通过后，才允许在最近前车选择前过滤证据明确分离的永久静态对向转弯目标。重新选择剩余目标并重算直接依赖，不直接删最低TTC后填30。未重算分数。

新类别条件为 `cos(heading_delta)<0` 对向半平面，非调整旧角度阈值以命中某个场景。其余速度/局部转角判据、v6完整6秒扫掠几何/1m裕度、原TTC公式与截断保持。地图/未来未知不作为过滤依据。既有避障或原始偏离上下文整条保护；如改变避障依赖但不能重算VRU/对向车复合上下文，立即停止。0026摩托车和0011/0042保护目标完整选择轨迹，不仅核对汇总数值。

官方元数据只保留这29条开发样本的标注身份与几何核对；全表流式扫描不分析评价语义。无相机读取/导出、下载、全700提取、拟合、选参、评价150、KMeans或特征清单/权重更改。

## 实现与测试

- 新模块 `HDBSCAN/scripts/longitudinal_candidate_v7.py`，测试 `HDBSCAN/tests/test_longitudinal_candidate_v7.py`。
- 配方 `logs/longitudinal_v7_replay_20261015.py`，测试 `logs/test_longitudinal_v7_replay_20261015.py`。独占启动claim防重复进程覆盖成功状态；失败claim保留，不隐式重启。
- TDD初始14项缺模块失败保留于 `longitudinal_v7_ledger_red_20261015.log`；配方初始5项失败保留于 `longitudinal_v7_recipe_red_20261015.log`。后续增加集成门控、无未来保留、启动竞争、基线失败编排和依赖检查。
- 最新330项HDBSCAN测试通过，见 `longitudinal_v7_full_final_20261015.log`；7项配方测试通过，见 `longitudinal_v7_recipe_claim_final_20261015.log`。
- 首次窄审无模块P1/P2，提示集成门控测试缺口，已补。配方窄审指出启动竞争，已补独占claim和失败编排测试；最终复审无剩余P1/P2，并补正两个非阻塞测试设置问题。冻结前18项模块/7项配方测试通过，见 `longitudinal_v7_pre_freeze_tests_20261015.log`。
- 测试中 `TemporaryDirectory` 的mode0700在Windows沙箱产生不可重新打开的目录，`Get-Acl`也拒绝；父目录可访问。改用普通模式的专用随机测试目录并逐文件清理后通过。未修改环境/ACL；失败日志 `longitudinal_v7_recipe_claim_green_20261015.log` 虽名称含green，实际是失败尝试，保留而不冒充通过。先前创建的不可访问空临时目录不作为任何证据或输入。

## 命令

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest discover -s HDBSCAN/tests -v *> logs/longitudinal_v7_full_final_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest logs.test_longitudinal_v7_replay_20261015 -v *> logs/longitudinal_v7_recipe_claim_final_20261015.log
```

## 执行状态

20:24:06北京时间单次run完成，session39437退出0；无本批活跃进程。只读check的session16969也退出0，原始输入/父协议/运行环境/输出封印及精确基线/候选重放通过，正式拟合拒绝。

原始协议SHA256 `ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d`；比较报告SHA256 `b7df6d51107f04cf3b7fdf9142fcddf24cec1a997e99277555ce3eab4872bdf3`。所有新绑定源码/测试/配方/输入/输出自prepare后不可原地编辑，不刷新封印、不重复run。基线失败仍必须停止，不是允许绕过的可选条件。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/longitudinal_v7_replay_20261015.py prepare *> logs/longitudinal_v7_prepare_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/longitudinal_v7_replay_20261015.py run --expected-protocol-sha ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d *> logs/longitudinal_v7_run_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/longitudinal_v7_replay_20261015.py check --expected-protocol-sha ea4d2412a372e475989a96cc3d32e2b1804e4790e335ea55c0aecfb2d0daac3d *> logs/longitudinal_v7_check_20261015.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/prepare_experiment_readiness_20261013.py --check-only --expected-manifest-sha 444e398e9feee9f958b5cba941efa4a1aade85e81b28327c017ee472be4986e7 *> logs/longitudinal_v7_statistics_preservation_20261015.log
```

统计包原始封印检查也退出0，合成统计不是正式评价。上述prepare/run为历史执行记录，不可重做；后续仅用check。

文档更新后的最终复验仍全部退出0：`longitudinal_v7_final_verification_tests_20261015.log`（330项）、`longitudinal_v7_final_recipe_tests_20261015.log`（7项）、`longitudinal_v7_final_seal_check_20261015.log`（精确基线/候选与拟合拒绝）、`longitudinal_v7_final_statistics_check_20261015.log`（原统计包封印）。命令与上文对应，仅日志路径不同。未提交Git。

## 真实结果

29条×129列/52聚类字段。基线31个纵向字段、静止身份/静态障碍/原始偏离完整台账逐项精确相等；393条同路径候选，13个目标×帧被门控，23条全字段不变。0002/0056/0067/0093/0102/0552六条共75格变化，其中13格为聚类字段。0815另外两个非选中候选过滤但场景字段不变。

0026摩托车最低TTC1.901035秒及其末帧零未来证据、0011/0042完整选中目标轨迹保留。所有白名单外列完全不变，包括v6.1横向交互与VRU。没有风险重算/模型排名，不能用数值降低计算准确率或宣称六条已验收。

**0669尚未修复。** 其最终避障flag和上下文支持绕行flag均为0，但冻结轨迹的原始偏离候选为True（静态误投影后大转角/侧移），触发本轮整场保守保护。TTC3.363684秒和静态/blocked比例0.121951均保留。不能为了修该场景直接撤掉原始偏离保护，否则可能误删真正绕行目标；下一步需先区分真实局部阻挡响应与纯曲率产生的原始候选，另起版本/正例回归，不原地修改v7。

0552旧TTC目标是12.398秒rigid bus810978，新最低值转为14.399秒car3df0ba（7.500511秒），不是填30。该车是否关联后续卡车绕行未确认，不借用已有公交语境验收。0067本轮纵向过滤为1.399/1.900秒truck19d979，和v6的2.899秒bus30d55e不是同一目标，也不借先前行人反馈验收。

入口：[重点结果与待办](F:/Scene_cluster/outputs/人工复核/纵向v7重点结果与待办_20261015.md)；冻结完整对照：[生成报告](F:/Scene_cluster/outputs/人工复核/纵向目标v7固定29条对照_20261015.md)。输出仍是候选，不能因此推广v6.1或替换正式模型。

## 未解决

0102隔离VRU、0552部分占道绕行、0067具体语义及0073近1m边界稳健性仍待处理。既有TTC后置转弯过滤仍保留，v7不宣称已经重构所有纵向逻辑。元数据损坏/封印篡改/保存结果差异尚无本配方独立负例覆盖，父配方检查和原封印递归校验仍强制执行。
