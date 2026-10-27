# 静止/低速车辆旁通过诊断（2026-09-25 启动，09-26 完成）

## 已确认范围

用户已批准基于 0042 排错增加独立“道路内静止车旁通过”候选。只用于开发诊断，**不改变 TTC、风险权重、避障换道定义或 52 个聚类特征**。不修改人工原始反馈，不直接把通过候选当作两次避障。

新增入口 `HDBSCAN/scripts/audit_static_passages.py`。提取器仅在轨迹诊断中补充车宽，并将本次轨迹 JSON 的 SHA-256 写入特征提取 manifest；特征表仍应为 129 列。新入口同时检查冻结开发身份、同一场景集合、特征/轨迹配对哈希与输出覆盖保护。

## 候选证据

- 目标在经过片段内速度峰值 <1 m/s；只有局部位置满足有限抖动规则才为 `static_supported`，否则为 `low_speed_uncertain`。有限抖动要求至少 5 点、跨度 >=2 秒、位置直径 <=0.5 m、速度峰值 <1 m/s、90% 分位 <=0.5 m/s。低速本身不足以确认静止；全段峰值速度、完整位置直径和其他时段是否运动另存供复核。
- 近旁观测范围：纵向 ±30 m、横向 ±6 m；连续采样间隔不超过 1 秒，片段观测跨度至少 1 秒、自车累计移动至少 5 m。
- 要求目标从自车前方完整进入后方，包含目标方向投影长度及自车长 4.5 m 的包络。只靠近而未完成通过、目标移动较快或有关键时序缺口的不算候选。
- 经过时刻取目标纵向位置最接近 0 的关键帧；横向车身投影间距使用目标长宽和自车假设宽 1.85 m，上限 3 m。该值不是连续最小净空，负值不代表实际碰撞。
- 目标车身需与可行驶面相交，且经过时刻目标中心与自车中心有相同 lane 或 road_segment 证据。同一道路区域不等于同车道、占道或路径冲突。地图未知、道路外和道路关系不支持的事件单列排除原因，不混入确认候选。
- 片段自车横移范围 >=1.5 m 时记录“存在横移”；航向累计变化 >0.35 rad 时标“弯曲路径，尚不能归因”。其余记录“未观察到明确横向动作”。全部 `avoidance_cause=undetermined`，不自动声称避障。

这些距离、角度、速度与车身尺寸都是诊断启发式，未宣称来自行业标准。

## 复跑命令

目录 `F:\Scene_cluster`，数据 `nuScenes v1.0-trainval`，解释器 `D:\Python\Conda\envs\autodrive-cluster\python.exe`。沿用 review10 的 16 条开发场景，不使用评价集。

```powershell
$env:SCENE_CLUSTER_SCENE_NAMES='scene-0053,scene-0055,scene-0056,scene-0109,scene-0073,scene-0011,scene-0030,scene-0007,scene-0097,scene-0068,scene-0074,scene-0122,scene-0026,scene-0103,scene-0042,scene-0067'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_review11_20260925.csv'
$env:SCENE_CLUSTER_AUDIT_OUTPUT='review11_trajectory_audit_20260925.json'
$env:MKL_THREADING_LAYER='SEQUENTIAL'
D:\Python\Conda\envs\autodrive-cluster\python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py
```

8 项候选分类测试先失败后通过，覆盖完成通过、未经过、动态车、地图未知/道路外、多个实例、缓慢漂移、弯道、缺帧和非有限几何；随后增加配对来源测试。初轮全部 126 项 HDBSCAN、5 项 KMeans 测试通过，KMeans 有已知 joblib 物理核探测警告。

## 代码审查与回归

审查复现了两点：持续 0.4 m/s 爬行 8 m 被旧初版当作静止；目标在片段结束后才运动会被旧初版全场速度门槛删除。分别添加失败测试后修正为上述片段级判定。11 项本轮测试通过，完整 HDBSCAN 129 项、KMeans 5 项通过，语法编译与 diff 空白检查通过。

实景提取退出码 0：数据加载 30.684 秒，反向索引 8.6 秒，16 场景约 141 秒。新表与 review10 的 16 行、129 列逐值严格相等，52 个聚类字段和所有风险分项严格相等，不重复制造一份相同风险表。

## 产出与核验

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe HDBSCAN/scripts/audit_static_passages.py --features HDBSCAN/tables/scene_features_review11_20260925.csv --audit HDBSCAN/tables/review11_trajectory_audit_20260925.json --output-prefix HDBSCAN/tables/review11_static_passages_20260925 --preflight
D:\Python\Conda\envs\autodrive-cluster\python.exe HDBSCAN/scripts/audit_static_passages.py --features HDBSCAN/tables/scene_features_review11_20260925.csv --audit HDBSCAN/tables/review11_trajectory_audit_20260925.json --output-prefix HDBSCAN/tables/review11_static_passages_20260925
```

preflight 检查 16 场景、配对来源和几何结构，不加载地图或写文件。正式输出 13 条通过候选（9 条局部静止证据、4 条低速不确定），4 条单列排除记录；本批无地图查询未知错误。重复运行相同前缀被拒绝，输出哈希不变；报告中输入、脚本、地图、冻结划分和 Markdown 哈希均复核通过。

| 0042 目标 | 经过约/s | 近似车身横向间距/m | 状态 |
| --- | --- | --- | --- |
| 9a40b6773c3b459d8e68859e1205b851 | 5.90 | 1.42 | 同一 lane，多点局部静止证据 |
| adeac5d0524f40359579085ca5e475c9 | 6.40 | 1.47 | 同一 lane，低速但静止性未确认 |
| 531acdf6cae24c7e965ca4aad9e78603 | 13.30 | 1.35 | 同一 road_segment，车道关系和静止性未确认 |

三条均未观察到明确横向动作。该结论表示当前诊断证据不足，不抹掉原人工“避让两次”反馈。原 `ego_evasive_lane_change_flag=0` 保持，不能宣称严格避障漏检已经修复。

0030 的道路内摩托车为通过候选并有横移证据，道路外摩托车仍被排除。0053 有两条道路外排除记录和一条道路关系不支持记录，不把靠近的路外目标自动当作道路占用。0011 等场景仍有多个通过候选，但部分弯道或静止性未确认，因此候选总量不能作为准确率或已确认高价值场景数。

文件：

- `HDBSCAN/tables/scene_features_review11_20260925.csv` 与 `.csv.manifest.json`：开发特征及提取/轨迹绑定。
- `HDBSCAN/tables/review11_trajectory_audit_20260925.json`：含目标车宽的轨迹诊断。
- `HDBSCAN/tables/review11_static_passages_20260925.md`、`.json`：人工可读候选与完整证据、参数及输入/地图/代码哈希。

输出 JSON 创建时间为 `2026-09-25T16:00:17Z`，即北京时间 2026-09-26 00:00:17。文件名保留启动日期作为批次标识，未改名或覆盖以往结果。

## 剩余限制

近似车身净空不是连续扫掠距离；同路段不等于同车道；不进行行驶意图或因果识别。短片段、车道地图空洞、转弯、目标未完整经过均可能漏掉有价值交互。需要人工确认后再决定是否进入正式特征，不能直接把本诊断喂入聚类或风险排序。多输出文件仍非事务式写入，异常中断需保留错误并使用新批次前缀。

历史 review10 保留，未进行完整聚类、评价集调参、Git 提交或推送。
