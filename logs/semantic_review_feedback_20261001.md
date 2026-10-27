# 五场景人工反馈与排错记录

日期：2026-10-01。来源：用户观看本轮开发场景预览后的直接反馈。此记录为开发诊断，未作为独立评价标签，也不替代缺失的 0905/0544/0997/0703。

## 原始反馈

| 场景 | 用户原话 | 可确认事实 | 暂未确认 |
| --- | --- | --- | --- |
| 0158 | 是的，工人挪开锥桶，给自车放行 | 施工人员及锥桶控制自车通行 | 未给出价值等级、精确时间、是否存在近距碰撞风险 |
| 0107 | 侵入了，公交车起步后倾入自车车道 | 公交车起步后的真实入道交互 | 未给出严重程度、是否强制自车减速及精确时间 |
| 0151 | 不影响 | 对本轮所询问的行人/横向车辆交互，用户整体判断无实际影响 | 未指定误检目标与事件时刻 |
| 0032 | 是的，只是角度偏大接近uturn，人行横道也没有行人穿行，所以基本无风险 | 接近掉头的大角度转弯；无人横穿；整体低风险 | 不据此宣称所有 C9 成员低风险 |
| 0014 | 是的，红灯跳绿后，公交车起步，自车跟随起步 | 用户确认红灯转绿、前车起步与自车跟随的时序 | 当前地图特征不能自动识别具体灯色变化 |

## 与现有计算对照

- 0158 风险分为 0，VRU 暴露为正、观测冲突为零。风险低与施工放行交互并不矛盾，但当前特征未显式表达人员控制通行。先作为已确认的语义知识记录，不从人工反馈直接给整库添加自动特征或风险值。
- 0107 风险约 0.319，其中 0.300 来自交互分项。用户确认公交车侵入，保留为真实侧向交互回归对照，不因合流观测相关性为零而删除其侵入证据。
- 0151 风险约 0.160，其中约 0.150 来自预测横向车辆冲突，约 0.010 来自决策需求；VRU 风险分项已经为零。需要定位横向预测事件，不能把这次误报误归因到 VRU 风险分项。
- 0032 风险约 0.016，只有较弱决策需求，原始冲突特征均为零；与用户低风险判断相符。其大角度转弯是曲率反例，不应新增假避障或假冲突。
- 0014 风险约 0.005，停车起步标记符合反馈；红转绿由人工确认。保持实际灯色与地图控制证据的来源区分。

## 已启动的限定诊断

用未修改的当前提取代码仅重放七条开发场景并输出轨迹证据：本轮五条，另加已确认左转让行的 0068、0074 作为正例。不是重新提取 700 条或启动参数实验；运行期间不改提取/规则/来源代码。

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMBA_NUM_THREADS='1'
$env:SCENE_CLUSTER_SCENE_NAMES='scene-0158,scene-0107,scene-0151,scene-0032,scene-0014,scene-0068,scene-0074'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_semantic_feedback7_20261001.csv'
$env:SCENE_CLUSTER_AUDIT_OUTPUT='semantic_feedback7_trajectory_20261001.json'
& D:/Python/Conda/envs/autodrive-cluster/python.exe HDBSCAN/scripts/scene_feature_hdbscan.py --preflight
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py 2>&1 | Tee-Object -FilePath logs/semantic_feedback7_extraction_20261001_console.log
```

preflight 已确认七条均为冻结开发成员。未改规则的首次提取已完成：7 × 129 列，逐值等于旧审计 700 条对应行；52 聚类字段齐全，捕获查询异常 0。

## 定位与修正

0151 的预测目标为 `vehicle.bicycle`，instance `31a8227b9a194e099a25cf1b0deac81b`，发生在约 2.55、3.05 秒。直行外推与之后的实际右转不一致，六秒未来路线中心最小距离约 4.31、3.90 m，航向变化约 1.00、1.07 rad，未来无低速/强制动响应。单独的行人 VRU 风险本来就是 0，不能声称修好了原本不存在的 VRU 风险。

规则新增 `turning_crossing_projection_audit`：只在未来 ego/目标覆盖完整、无大于 0.75 秒间断、显著转弯、车身完全远离路线且无让行响应证据时拒绝直行预测；保留 `raw_crossing_conflict` 和每目标诊断。CSV 仍 129 列，52 个聚类字段及评分权重不变。

首个修正版 v2 已完成核验：只改 0151 的 `crossing_vehicle_conflict_ratio`、`crossing_conflict_pre_stop_ratio`（均 0.05 → 0）和 `crossing_conflict_max_duration`（1.000286 秒 → 0）。风险 0.160459582 → 0.010416667；残留为弱决策需求，不是近距冲突。0107 侵入和 0068/0074 真实让行对照、另外三条全部 129 列与风险不变；七条 52 聚类字段完全相同。

自查发现横向长车只按车宽保护会漏掉车头/车尾。新增长公交车测试先失败，再将路线保护扩展到整段目标矩形外接圆半径；对应重提 v3 的数值和 v2 完全相同，来源核验通过。独立代码审查进一步发现首次候选边界制动、单帧缺失、NaN 目标位置和未知尺寸的边界问题；四项失败测试复现后修正。最终 v4 纳入这些保护，16 条纯规则/时间线测试通过。v2/v3 均保留为中间版本，不当作最终来源；最终 v4 实际数据核验结果在下方追加。

## 来源与运行记录

修改前实际源码及划分存于 `logs/source_snapshot_20261001_pre_turning_crossing/`。两个历史提取 manifest 的脚本/规则/schema/audit/划分哈希与快照相符；快照模块正常接受旧审计 700 条来源，当前模块正常拒绝它。9 月 30 日结果仍是旧版本数值，不覆盖结果或重签 manifest。本轮没有全 700 提取、聚类拟合、评价使用、媒体下载或新增 GIF。

最终提取复用上面的环境及七条场景配置，替换以下文件名：

```powershell
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_semantic_feedback7_20261001_v4.csv'
$env:SCENE_CLUSTER_AUDIT_OUTPUT='semantic_feedback7_trajectory_20261001_v4.json'
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py 2>&1 | Tee-Object -FilePath logs/semantic_feedback7_extraction_20261001_v4_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/verify_semantic_feedback7_20261001.py --version v4
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest discover -s HDBSCAN/tests -p 'test_*.py'
```

输出均在 `HDBSCAN/tables/`：四版七条 CSV 及质量/来源 sidecar、四版轨迹 JSON、比较 JSON；控制台在 `logs/semantic_feedback7_*20261001*console.log`。核验脚本禁止覆盖旧报告；再次核验使用 `--check-only`，不能删改旧证据。脚本开发时最初用了不存在的质量计数键，并漏列一个派生变更字段；已按实际 schema 和全列比较纠正，未改变提取结果。最终核验只接受当前 v4，中间版本的当时验证报告保留。

参数稳定性测试的两处来源 fixture 改为临时、显式 `unit_test_fixture_only` 表，并新增当前入口拒绝真实旧表的测试。此 fixture 使用旧数值测试入口行为，不是新场景提取，不写回历史 CSV 或 manifest，不能当作实验。

## 局限与后续

- 七条开发回归只支持本次误报与对照不退化，不能等价于全库语义验收或独立评价精度。
- 0158 施工人员挪锥桶放行已人工确认，但尚无自动手势/移桶特征；低碰撞风险与高测试价值应分开表达。
- 0014 灯色变化为人工观察，不冒充地图自动识别；0032 低风险不外推整个簇。
- 过滤使用已观测未来路线，是离线回溯规则；低速/强制动保护未穷尽滚动温和让行与已有避险因果。暂无通过评价集证明的最优阈值。
- 0074 仍有左转横向交互语义（比例 0.125），预测冲突风险为 0；保留交互不代表强行提升其风险分。

## 最终 v4 核验完成

2026-10-01，提取进程正常结束（退出码 0），当前来源校验及全部回归断言通过。数据仍 7 × 129 列，52 聚类字段逐值相同，只有 0151 三个横向派生字段变化。没有捕获查询异常；填值前 9 个正 Inf 仅在诊断距离（merge 4、VRU 5），无 NaN/负 Inf 或聚类非有限字段。v2/v3/v4 数值完全相同，但各自来源 sidecar 不同，只有 v4 匹配最终源码。

| 场景 | 原规则风险 | v4 风险 | 核验结果 |
| --- | ---: | ---: | --- |
| 0158 | 0 | 0 | 施工放行人工语义已记录，未伪造自动识别 |
| 0107 | 0.318750 | 0.318750 | 公交车侵入及全部字段保留 |
| 0151 | 0.160460 | 0.010417 | 同一自行车两帧直行投影拒绝；仅弱决策需求残留 |
| 0032 | 0.016042 | 0.016042 | 大角度转弯未新增假冲突 |
| 0014 | 0.005250 | 0.005250 | 普通信号控制跟随起步保持低风险 |
| 0068 | 0.500000 | 0.500000 | 已确认真实让行正例全部字段/风险不变 |
| 0074 | 0.062500 | 0.062500 | 左转交互语义全部字段/风险不变 |

最终 CSV SHA256：`8bcc5c9d4a9d5b9e3524d058af203905bdd169f0b77d810179f2648e00f4cb95`。机器证据 `HDBSCAN/tables/semantic_feedback7_comparison_20261001_v4.json`，配方 `logs/verify_semantic_feedback7_20261001.py`，控制台 `logs/semantic_feedback7_verification_20261001_v4_console.log`。`--check-only` 会重算并核对已保存报告，不改文件。

最终测试：182 项通过，4.621 秒，控制台 `logs/semantic_feedback7_tests_20261001_v4_console.log`；独立复查确认四项边界问题修正后无新增可执行问题，16 项新规则测试独立通过。仍有滚动温和让行的语义局限，没有声明完整专家有效性评价或全库验收。
