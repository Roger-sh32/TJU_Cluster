# 提取异常可观测性与五种子稳定性

日期：2026-09-27。用户批准先加审计、小样本回归，再检验固定参数下的 5 个随机种子。未改特征规则、权重和阈值，未运行 KMeans，未读取评价特征或下载媒体。

## 版本保护与改动

先将实际工作区脚本保存到 `logs/source_snapshot_20260927_pre_audit/HDBSCAN/scripts/`，逐项核对旧模型源码哈希；另保存 environment.yml 和冻结划分。旧模型与 700 条表保留原位，未覆盖。用快照模块和原 smoke 环境成功重载旧模型，核验 700 个训练身份。

稳定性实验在修改提取/冻结模型源码前运行。之后增加 `HDBSCAN/scripts/extraction_audit.py`：统计最终填值前各场景/字段的 NaN、正负 Inf，以及全部 8 处异常处理的阶段、类型和次数；每组最多记录 3 个报错样例，避免日志膨胀。原先的异常回退、判定与 Inf→30/NaN→0 处理保持不变。

新提取自动生成 `.csv.quality.json`，纳入输出防覆盖及提取 manifest。冻结模型新增审计代码哈希绑定，真实提取来源必须附带匹配的审计文件、场景和代码来源；合成工程测试仍显式标为 synthetic_features。审计存在不代表语义合格，报告异常不会自动变更风险或阻断所有诊断样例。

**版本边界：旧 700 条表和旧模型现在会被当前源码校验拒绝，这是预期保护。**不要重新写 manifest 让旧数据冒充新版本。读取旧模型、重跑旧表稳定性须使用上述快照；下一批提取使用当前源码。即使 8 场景回归相等，也不能据此伪造全量来源。

## 八场景回归

选择 0001、0011、0042、0062、0073、0315、0399、0536，全部属于开发集。覆盖四个地图地点，并包含 crossing_route_conflict_ratio 的唯一非零场景 0536、obstacle_avoidance_vru_conflict_ratio 的唯一非零场景 0011，以及已有待核验场景。此为定向检查，不是随机抽样或专家验收。

```powershell
$env:SCENE_CLUSTER_SCENE_NAMES='scene-0001,scene-0011,scene-0042,scene-0062,scene-0073,scene-0315,scene-0399,scene-0536'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_audit8_20260927.csv'
Remove-Item Env:SCENE_CLUSTER_AUDIT_OUTPUT -ErrorAction SilentlyContinue
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& D:/Python/Conda/envs/autodrive-cluster/python.exe HDBSCAN/scripts/scene_feature_hdbscan.py --preflight
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py 2>&1 | Tee-Object -FilePath logs/extraction_audit8_20260927_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/verify_extraction_audit8_20260927.py
```

以上为首次运行的命令。独立代码审查随后发现质量审计与轨迹审计路径可重名，已增加解析后路径（Windows 忽略大小写）去重，轨迹文件改为排他创建。首次报告保留为过程证据，不再作为当前源码入口的样例。

最终修订版另行执行（同样的场景与环境变量，不覆盖首次产物）：

```powershell
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_audit8_20260927_v2.csv'
& D:/Python/Conda/envs/autodrive-cluster/python.exe -u HDBSCAN/scripts/scene_feature_hdbscan.py 2>&1 | Tee-Object -FilePath logs/extraction_audit8_20260927_v2_console.log
& D:/Python/Conda/envs/autodrive-cluster/python.exe logs/verify_extraction_audit8_v2_20260927.py
```

首次元数据加载约 30 秒，反向索引约 6 秒，8 场景处理约 48 秒；修订版分别约 28、6、47 秒。两次退出码均为 0，特征 CSV 字节哈希相同，但各自来源 manifest 对应不同提取代码版本。

- 当前新表 `HDBSCAN/tables/scene_features_audit8_20260927_v2.csv` 为 8 行、129 列；所有列与首次审计表、旧 700 条对应行严格相等，风险分项严格相等，52 个聚类特征不变。
- 填值前 NaN=0、负 Inf=0、正 Inf=12；12 个均在 `merge_observed_min_distance` 和 `vru_observed_min_distance`（各 6 个），不在聚类白名单，也不被当前风险评分读取。
- 两个距离变量初始值是正无穷，只有候选轨迹得到有限同步距离才更新。这些值不是“已证实计算出错”，也不是有效距离；旧兜底会将它们写为 30。**不能把该列的 30 自动解释成实测 30 米**，其他有限值与空候选情况也不由本次审计自动判定。
- 捕获的查询异常总数为 0，包括地图加载、路口、停止线、人行横道及车道关系查询。仅对这 8 条有效，不能外推其余 692 条。
- 原始异常证据：同名 `.csv.quality.json`；来源：`.csv.manifest.json`；最终比对及输入哈希：`HDBSCAN/tables/extraction_audit8_comparison_20260927_v2.json`。无 v2 的审计/比对文件为首次运行证据。

不据此声称全部中间计算有效。显式数值默认值、被丢弃的中间量、无候选原因和语义误判仍不在本次审计保证范围。

## 五种子实验

输入为原 700 条开发特征，固定全部 UMAP/HDBSCAN 参数与评分规则，仅改变 UMAP random_state。预先指定 42、7、19、73、101，未按结果筛选种子。

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMBA_NUM_THREADS='1'
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe -u HDBSCAN/scripts/seed_stability.py --input HDBSCAN/tables/scene_features_development_20260926.csv --baseline HDBSCAN/tables/scene_features_development_20260927_umap_hdbscan.csv --output-dir HDBSCAN/tables/seed_stability_20260927 --preflight
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe -u HDBSCAN/scripts/seed_stability.py --input HDBSCAN/tables/scene_features_development_20260926.csv --baseline HDBSCAN/tables/scene_features_development_20260927_umap_hdbscan.csv --output-dir HDBSCAN/tables/seed_stability_20260927 2>&1 | Tee-Object -FilePath logs/seed_stability_20260927_console.log
```

这些是改动前的实际命令。现在复现应把脚本路径替换为快照中的同名脚本，输出换新目录；不能直接给当前入口喂旧特征。

| 种子 | 簇数 | 噪声数 | 相对 seed42 的 ARI（含噪声） | Top20 重合数 |
| --- | --- | --- | --- | --- |
| 42 | 12 | 54 | 1.000 | 20/20 |
| 7 | 8 | 0 | 0.349 | 10/20 |
| 19 | 8 | 0 | 0.357 | 9/20 |
| 73 | 15 | 64 | 0.684 | 13/20 |
| 101 | 16 | 36 | 0.712 | 13/20 |

seed42 重现原标签和评分（评分容差 1e-12），所有种子的规则风险分相同；排序变化来自聚类稀有度和离群分的变化。各次拟合约 1.4–4.8 秒，不含原生库导入。

10 个两两组合的 ARI 为 0.266–0.992，Top20 重合率为 35%–65%；相对原 seed42 为 45%–65%。五次均入 Top20 的只有 0068、0436、1080，这不是三个已验证危险标签。

输出 `HDBSCAN/tables/seed_stability_20260927/`：5 个 seed CSV 保留全部 700 条身份、标签、风险及评分和排名；`summary.json` 保留输入/脚本/运行时/输出哈希、全参数、各次 Top20、两两 ARI（含噪声及共同非噪声子集）、噪声成员一致率、Top20 重合率与 Jaccard。日志见 `logs/seed_stability_20260927_console.log`。

结论：当前默认配置存在明显随机种子敏感性，不适合将单次 Top20 直接作为稳定的论文结论。本轮不选最优种子，不更改原排序，不根据人工偏好挑结果。共同非噪声 ARI 的样本集合随两次拟合变化，应同时查看 joint_nonnoise_count；全量 ARI 把噪声作为一类，也有解释局限。

## 验证与后续边界

新增测试先失败后通过，覆盖填值前审计不改值、错误计数与限量样例、全部异常分支接入、审计来源防缺失/篡改，以及标签置换、行重排、并列排序和身份错配。修正旧 preflight 测试对历史真实 CSV 的版本耦合，改用明确标记的临时合成来源，未放宽生产保护。

本轮最终 HDBSCAN 154 项测试通过（`D:/Python/Conda/envs/autodrive-cluster/python.exe -W ignore::FutureWarning -m unittest discover -s HDBSCAN/tests -q`，三个线程环境变量同上）；真实 8 场景回归和 5 种子实验均完成。独立代码审查指出的输出路径冲突已修复，复审未发现残留 P1/P2；复审未独立重复整个测试套件。未将合成测试当作场景有效性证据。

下一步建议先用新审计版本重提 700 条，核查其余场景并明确距离无有效观测的标记；然后预先限定少量参数组合做多种子稳定性比较。不要启动 2,304 组历史大搜索，不为得到好看的 Top20 临时改权重。150 条评价集继续封存，评价媒体缺失和人工盲评待办保持。
