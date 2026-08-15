# 阻塞改道与转弯误判收紧实施计划

> 按测试先行执行；正式 850 场景结果不覆盖。

**目标：** 新增阻塞导致的路线偏移特征，删除转弯时路侧或对向静止车辆造成的虚假 TTC/避障，并保留真实合流、VRU 让行和横向车流让行。

**架构：** 几何与时序判定放在 `scene_feature_rules.py`，nuScenes 数据聚合放在 `scene_feature_hdbscan.py`，聚类输入与评分分别由 `feature_selection.py` 和 `corner_scoring.py` 显式接入。原始诊断字段继续保留，严格风险字段使用收紧后的事件。

## 全局约束

- 不读取场景 description 参与特征计算。
- 不覆盖正式 850 场景表。
- 所有新增规则先写失败测试，再做最小实现。
- 使用第七轮 5 个场景和历史人工确认场景做回归。

## 任务一：纯规则函数

**文件：**

- 修改：`HDBSCAN/scripts/scene_feature_rules.py`
- 测试：`HDBSCAN/tests/test_scene_feature_rules.py`

步骤：

1. 为转弯投影伪影写失败测试：目标速度低于 `0.5m/s`、目标与自车朝向差大于 `2.35rad`、局部转向大于 `0.35rad` 时返回真；真实同向跟车返回假。
2. 实现 `is_turning_projection_artifact(target_speed, heading_delta, local_heading_change)`。
3. 为阻塞改道写失败测试：静止障碍持续至少 `1.0s`、最近距离不超过 `15m`，且后续净转向至少 `0.35rad` 或横移至少 `4m` 时返回真。
4. 实现 `is_obstacle_induced_route_deviation(...)` 和归一化决策需求计算。
5. 收紧 `is_evasive_lane_change`：删除“短时目标只因距离小于 20m 即可成立”的分支，要求静止障碍持续至少 `1.0s`。
6. 为 VRU 持续性写测试：单帧约 `0.5s` 事件被严格风险过滤，两帧约 `0.9s` 事件保留。

## 任务二：特征提取集成

**文件：**

- 修改：`HDBSCAN/scripts/scene_feature_hdbscan.py`
- 测试：`HDBSCAN/tests/test_scene_feature_hdbscan.py`

步骤：

1. 暂存每帧 TTC 候选及静止目标的速度、朝向差和帧索引，场景轨迹完整后计算局部转向。
2. 过滤转弯投影伪影后再汇总 `min_ttc`、危险 TTC 持续时间和静止障碍事件。
3. 输出 `blocked_path_obstacle_ratio`、`obstacle_induced_route_deviation_flag`、`route_deviation_decision_demand`。
4. 保留原始 `vru_observed_relevance_ratio` 作为暴露诊断，新增 `vru_sustained_relevance_ratio` 和 `vru_sustained_max_duration` 作为严格风险输入。

## 任务三：聚类与评分接入

**文件：**

- 修改：`HDBSCAN/scripts/feature_selection.py`
- 修改：`HDBSCAN/scripts/corner_scoring.py`
- 测试：`HDBSCAN/tests/test_feature_selection.py`
- 测试：`HDBSCAN/tests/test_corner_scoring.py`

步骤：

1. 将三个阻塞改道语义字段加入显式聚类特征清单。
2. 评分优先使用持续 VRU 字段；旧表缺列时保持历史兼容。
3. 决策需求取原交叉口决策需求与 `route_deviation_decision_demand` 的较大值。
4. 验证真实合流字段和评分路径不受 TTC 收紧影响。

## 任务四：场景回归与文档

**文件：**

- 更新：`HDBSCAN/README.md`
- 更新：`knowledge/wiki/阻塞改道与转弯误判收紧设计.md`
- 更新：`logs/feature_batch_0051_0100_2026-07-12.md`

步骤：

1. 运行全部单元测试和语法检查。
2. 先对 `0071/0067/0103/0102/0126` 做小批量重提取。
3. 验证 `0071` 阻塞改道保留且 TTC 消失，`0102` TTC/避障消失，`0067` 持续 VRU 保留，`0103` 合流保留，`0126` VRU 严格风险消失。
4. 对历史人工样本运行回归，记录任何未达到预期的边界。
5. 仅生成新的调试表，不覆盖正式结果，并记录命令、环境、输入和输出路径。
