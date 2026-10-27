# 第八批人工反馈与特征修订（2026-09-21 至 2026-09-22）

## 用户人工标签

- scene-0053：跟行，自行车在旁边草坪内、无威胁；左侧汇入面包车才是实际威胁。
- scene-0055：没有借道避让。
- scene-0056：正常连续弯，未受障碍影响。
- scene-0109：环岛曲率导致假避障。
- scene-0073：停车后右转，停车是停止牌要求，并非为横向卡车让行。

标签是用户对 CAM_FRONT GIF 的人工解释；自动轨迹推断应与其比对，不能直接将场景名写入规则。

## 修订原则

1. TTC 与静止障碍候选增加车身与 drivable_area 相交证据；车道距离仅保留诊断。地图缺失计数保留，不能解释为已确认安全。
2. 避障位移限制为 1.5–15 m；短暂障碍的例外限 4–8 m、净航向变化不超过 0.1 rad、障碍不远于 30 m。阈值为开发启发式，需要独立数据检验。
3. 相邻车道侵入要求目标自身向自车路径横移，持续 0.8–4 s、相对横向距离收缩、进入自车走廊且前向净距不超过 25 m；明显转弯窗口拒绝该推断。
4. 横向预测冲突保留为诊断；新增实际路线相关性，检查目标轨迹与自车未来六秒路线距离以及同步距离。
5. 停止牌停车候选要求低速持续、停止线与当前朝向相交且距离近。它是控制上下文证据，不声称恢复真实驾驶意图。无实际路线冲突、左转横向交通或持续 VRU 相关性时保留 40% 路口决策需求；原始预测横向风险不因未来无近距而清零。
6. 新增侧前方低速朝向内侧的车辆候选，表达潜在汇入观察任务，不等同于已经发生的合流。

## 首轮回归命令

环境：`D:\Python\Conda\envs\autodrive-cluster\python.exe`。

```powershell
$env:SCENE_CLUSTER_SCENE_NAMES='scene-0053,scene-0055,scene-0056,scene-0109,scene-0073,scene-0011,scene-0030,scene-0007,scene-0097,scene-0068,scene-0074,scene-0122,scene-0026,scene-0103'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_review8_20260921.csv'
D:\Python\Conda\envs\autodrive-cluster\python.exe -u HDBSCAN\scripts\scene_feature_hdbscan.py
```

首轮结果仅用于排错，不作为当前结果。初版车道距离硬过滤误删了 `0011` 的堵路车辆；停止牌结合未来近距为零的硬过滤则降低了 `0074` 的真实决策价值。第二版修正车身边界与中心线端点仍未完全解决前者，最终取消单一车道距离的硬门槛，并撤销横向风险清零。

## 最终提取与评分命令

在仓库根目录 `F:\Scene_cluster` 运行。数据为本地 `nuScenes v1.0-trainval`；未修改源数据。

```powershell
$env:SCENE_CLUSTER_SCENE_NAMES='scene-0053,scene-0055,scene-0056,scene-0109,scene-0073,scene-0011,scene-0030,scene-0007,scene-0097,scene-0068,scene-0074,scene-0122,scene-0026,scene-0103'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_review8_20260922.csv'
$env:SCENE_CLUSTER_AUDIT_OUTPUT='review8_trajectory_audit_20260922.json'
$env:MKL_THREADING_LAYER='SEQUENTIAL'
D:\Python\Conda\envs\autodrive-cluster\python.exe -u HDBSCAN\scripts\scene_feature_hdbscan.py
D:\Python\Conda\envs\autodrive-cluster\python.exe HDBSCAN\scripts\audit_feature_revision.py --features HDBSCAN/tables/scene_features_review8_20260922.csv --baseline HDBSCAN/tables/scene_features_route_tightening_regression_0011_0042.csv --baseline HDBSCAN/tables/scene_features_route_tightening_0051_0100_final.csv --baseline HDBSCAN/tables/scene_features_route_tightening_smoke_0011.csv --output-prefix HDBSCAN/tables/review8_20260922
```

提取耗时：加载 34.15 秒、反向索引 6.9 秒、14 场景处理约 118 秒。退出码为 0。输出共 14 行、129 列，其中聚类语义白名单可用 52 列。14 个名称和 token 均唯一，数值列均为有限值，地图可用率 14/14，目标地图查询未知计数为 0。

比较基线最后匹配优先，`0011` 必须用最新的 smoke 表覆盖较早回归表。`0007` 未在这三份基线中，其 before 留空，不伪造比较数据。两侧风险均由当前评分器计算；旧表缺少新增字段时使用兼容分支。

## 五条反馈结果

| 场景 | 核验结果 | 局限 |
| --- | --- | --- |
| 0053 | 假避障 1→0；最低 TTC 2.329→4.062 秒，目标由 bicycle 改为 car；潜在侧向汇入比例 0.1795 | 包含左侧面包车 instance `8259bd12edcc4b89970c493b79bffff7`；其标注轨迹近乎静止，所以是候选，不宣称实际侵入已发生 |
| 0055 | 假避障 1→0 | 风险分数此前已为 0，不能把标签改善写成分数下降 |
| 0056 | 假避障 1→0 | TTC 仍为 3.072 秒；没有仅为了降低分数而删除道路上的卡车 |
| 0109 | 环岛假避障 1→0 | 新侧向候选比例 0.10 尚待人工核验，风险 0.0125→0.03；不能声称所有误报都降低 |
| 0073 | 停止牌停车候选 1；决策需求 1→0.4；风险 0.42→0.30 | 原始横向预测仍有残留，不能自动确证“只为停止牌停车”，本条仅部分改善 |

## 回归对照与未解决项

- `0011`：真实避障标记仍为 1，风险仍为 0.25。
- `0026`：摩托车 TTC 1.901 秒保留。
- `0068`：左转车流交互风险保留，风险仍为 0.50；排除了初版侧向侵入的假阳性。
- `0074`：左转间隙选择需求仍为 0.3125，风险仍为 0.0625，未因停止牌候选误降。
- `0007/0097`：相邻车道侵入均为 0，未把旁车超越直接当成切入。
- `0030`：避障标记 1→0，与用户“存在避障”不符。旧障碍对应摩托车 `1462e9f27d254a5bb0b570fc87db040c`，其车身不与本地可行驶面相交；过滤后未找到替代的正确障碍目标。需要进一步逐帧核验地图边界及目标关联，不能把本轮标成全部回归通过。
- 两项新语义特征 `adjacent_lane_intrusion_ratio`、`crossing_route_conflict_ratio` 在这 14 条中均为零。纯规则正例已通过测试，但缺少实景正例验收，不能据此证明全量提取有效，也不能用缺乏实际近距证明没有潜在风险。
- 固定位移尺度和停止牌决策衰减均为开发启发式，不是标准规定阈值。该批用于开发回归，不是独立泛化评估集。

## 文件与版本边界

- 当前原始特征：`HDBSCAN/tables/scene_features_review8_20260922.csv`。
- 当前轨迹诊断：`HDBSCAN/tables/review8_trajectory_audit_20260922.json`。
- 风险分项：`HDBSCAN/tables/review8_20260922_risk.csv`；没有伪造聚类标签或 corner score。
- 长表对比：`HDBSCAN/tables/review8_20260922_comparison.csv`。
- 环境、代码/输入/输出 SHA-256：`HDBSCAN/tables/review8_20260922_manifest.json`。代码哈希记录的是审计时版本，本轮审计前提取脚本未再变动。
- `scene_features_review8_20260921.csv`、`scene_features_review8_diagnostic.csv`、`scene_features_review8_final_20260921.csv` 以及对应旧 JSON 均为被替代的排错快照。尤其带 `final_20260921` 的文件名不代表最终有效版本。
- 未重跑 UMAP/HDBSCAN 聚类、KMeans 实验或 850 场景。三个正式历史表时间仍为 2026-06-16 21:57:13 / 21:58:49 / 21:58:58。

## 验证

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe -m unittest discover -s HDBSCAN/tests
$env:MKL_THREADING_LAYER='SEQUENTIAL'
D:\Python\Conda\envs\autodrive-cluster\python.exe -m unittest discover -s Kmeans/tests
git diff --check
```

HDBSCAN 82 项、KMeans 5 项测试通过。KMeans 测试有 joblib 物理核数量探测警告，随后回退逻辑核并通过。测试通过不等于上述人工语义问题已全部解决。
