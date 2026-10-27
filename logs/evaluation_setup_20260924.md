# 独立评价集与专家审查准备

日期：2026-09-24。承接用户同意的“在现有 850 条中划分开发/拟合集与独立评价集，使用专家盲评评价排序”方案。本轮只准备数据划分与评审规则，不提取新特征、不拟合模型、不填专家标签。

## 实施计划

- [x] 编写划分测试：日志不交叉、开发证据隔离、地点覆盖、固定种子可复现、无可行解显式失败。
- [x] 实现 `HDBSCAN/scripts/prepare_evaluation_split.py`，只读取 scene/log 元数据及现有开发证据，不导入 nuScenes 大表。
- [x] 生成一份划分 CSV 和带来源哈希的 manifest，不覆盖已有输出。
- [x] 编写专家盲评协议，明确标签是专家参照而不是客观事故真值。
- [x] 验证实际划分并更新 README/AGENTS/CHANGLOG。

## 设计与约束

输入为 `nuScenes/v1.0-trainval/scene.json`、`log.json`。开发证据来自 HDBSCAN 小批特征 CSV、logs/wiki 中明确的场景引用以及 exports 文件名。保守地将被引用场景及其同日志全部分入开发集。所有 850 条都曾参与旧无监督探索，因此本次是从现在起冻结的留出评价，不能声称历史上完全未接触。

分组单位为 log_token；固定种子；优先保留所有地点，再在可行日志组合内使地点数量接近全库比例。目标为 150 条，若整组条件下无解则显式停止，不悄悄拆分日志。本规则不根据风险分数或专家标签挑样本。

输出应记录场景标识、日志标识、地点、开发/评价角色和匿名评审编号；不带风险分数、描述或预填结论。原始数据只读。脚本与测试独立于既有特征/聚类流程；下游仍需显式接入划分，本轮不宣称自动防泄漏已完成。

## 验证边界

测试输入覆盖重复标识、缺失日志、未知排除场景、输入顺序变化和不可能的样本规模。剩余风险包括未记录的人工查看历史、同一地区不同日志的空间相似性、缺失视频和后续误用整库拟合；需要在后续接入和盲评导出时继续检查。

## 实际执行

环境：`D:\Python\Conda\envs\autodrive-cluster\python.exe`，本脚本仅使用 Python 标准库。工作目录：`F:\Scene_cluster`。

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe -m unittest HDBSCAN.tests.test_evaluation_split
D:\Python\Conda\envs\autodrive-cluster\python.exe HDBSCAN/scripts/prepare_evaluation_split.py --evaluation-count 150 --seed 20260924 --ignore-note logs/evaluation_setup_20260924.md --output-prefix HDBSCAN/tables/evaluation_split_20260924
D:\Python\Conda\envs\autodrive-cluster\python.exe -m unittest discover -s HDBSCAN/tests
```

首次运行已完成。原前缀已被冻结，再次运行会报 FileExistsError，不能覆盖。需要重建比对时使用新输出前缀，并先核对 manifest 内所有来源的哈希；新增开发记录可能改变候选池。运行日志自身通过 `--ignore-note` 排除，避免执行记录被用作新的开发证据。

| 地点 | 开发集 | 评价集 | 合计 |
| --- | ---: | ---: | ---: |
| boston-seaport | 384 | 83 | 467 |
| singapore-onenorth | 151 | 32 | 183 |
| singapore-queenstown | 95 | 20 | 115 |
| singapore-hollandvillage | 70 | 15 | 85 |
| 合计 | 700 | 150 | 850 |

27 份小批特征 CSV 覆盖 100 个不同场景；联合日志/知识记录/预览文件名后保守引用集为 110 条，不等同于确认人工看过 110 条。其 21 个采集日志共 274 条全部锁定开发用途。剩余 576 条中按整日志、地点比例和固定种子选择 150 条；最终开发/评价日志数分别为 56/12，无交集。

## 产物与验证

- `HDBSCAN/tables/evaluation_split_20260924.csv`：850 条成员表，包含 split、采集日志及评价场景的 E0001–E0150 匿名编号。
- `HDBSCAN/tables/evaluation_split_20260924_manifest.json`：命令、解释器、种子、来源/脚本/输出哈希、证据清单及历史接触边界。
- `knowledge/wiki/独立评价与专家盲评协议.md`：0/1/2/NA 标签、先独立后裁决、相同预算对照和 Precision@20 主指标等实施约定，正式评审前仍需校准锁定。
- 新增 8 项划分测试通过，全部 HDBSCAN 测试共 90 项通过。另独立读取实际 CSV 验证 700/150、850 个唯一场景、日志无交叉、已知开发引用不进入评价集、匿名编号唯一、反转输入顺序重建一致以及来源/代码/输出哈希一致。

测试中曾遇到 Conda 的 TemporaryDirectory 创建后 Windows ACL 拒绝访问；测试夹具已改为继承工作区权限的唯一临时目录，清理前验证绝对路径仍在 tests 内。未更改 Conda 环境或生产数据权限。

本轮不生成专家评分，不对评价集做语义回看，不重跑特征或聚类。文件级媒体检查、开发集特征收敛、模型拟合/样本外评分接口和盲评包是后续工作；现有默认整批聚类入口尚未自动限制 split，必须先接入再开展正式拟合。
