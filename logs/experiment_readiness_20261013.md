# 评价统计与实验证据准备

## 授权和边界

2026-10-13，用户批准先推进不依赖人工反馈的评价统计工具和论文实验证据表；最小对照/消融仅写准备方案。本轮是既有盲评流程的限定补充，不新建评审平台、不开展真实独立评价、不改变既有协议中的主指标/标签规则。

只用40条SYN虚构样本和SYN评审者演示，不使用真实场景身份、特征、视频或专家意见计算指标。证据核对只读既有JSON汇总和关联文件摘要，保留原始来源、旧700/150划分、所有v4/v5/v5.1/v5.2代码/结果/模型，不提取、拟合、选参、KMeans、下载或导出媒体。

## 本轮产物与执行检查

- [x] 按原盲评协议明确三人中位数/未知、固定TopK、同名单召回/预算、随机与日志重采样的计算边界。
- [x] 先失败后实现独立纯统计模块 `HDBSCAN/scripts/evaluation_metrics.py`；无输入文件读取/nuScenes加载/拟合入口。
- [x] 新增15项统计单元测试及6项生成配方契约测试，通过；全HDBSCAN276项通过。
- [x] 既有证据只读预检查63条文件绑定通过；报告约2660字，明确版本与不可宣称内容。
- [x] 独立代码复查、最终全测试、合成包生成及原始摘要封存/只读重验。
- [x] 更新项目入口和收尾状态，交付可读证据表；不把准备工作写成实测评价完成。

## 计算约定

三位独立评审全有效才取0/1/2中位数，2为高复核价值正例；None是NA/缺评，不能用0或两人平均替代。保留原始评分，完全一致率仅描述完整评分样本，不等于序数一致性系数。

固定TopK不删除未知补位，Precision给出命中上下界；存在全名单缺失或无正例时召回/同召回预算不可报告。预算比较绑定同一名单和标签摘要，保留负节省，预算不足显式失败；不换算时间或路测里程。

随机基线记录100个固定种子演示及均值/极值，说明它是随机排序波动，不是方法差异区间。配对整日志重采样使用同一日志样本、固定排序的重复场景按原位置计入，示范2000次/seed20261013的百分位区间。任何一次样本规模小于K则整个区间不可报告，不挑有效轮次、补抽或缩小K。参数只是合成演示约定，不代表正式评价冻结；12日志推断、专家不确定性及多重比较仍须明确限制。

工具未实现序数一致性系数、价值机制覆盖、等级排序指标或真实盲评导入入口；不能声称正式评价已全面接通。

## 已知排错与复查

首轮统计测试复现模块未实现；完成后13项通过。独立窄审定位两个P2：随机循环消耗迭代器导致空汇总/后续失败，日志编号尾部空格虚构独立分组。两项回归先失败，再改为一次实体化指标列表和拒绝带前后空格的日志编号；15项通过。

生成配方测试覆盖只生成SYN身份、关联文件摘要变更拒绝、输出目录限制、原始manifest摘要变更拒绝、禁止覆盖，以及解释器版本不符拒绝。运行环境检查亦记录失败后恢复通过的回归。没有调整环境或冻结来源。

## 环境和命令

工作目录 `F:/Scene_cluster`；解释器 `D:/Python/Conda/envs/autodrive-cluster/python.exe`，Python3.9.23；新统计/生成模块仅用标准库，不依赖原生UMAP/SVD。精确解释器文件摘要、源文件/测试/协议/既有证据/输出摘要由产物manifest记录。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest HDBSCAN.tests.test_evaluation_metrics logs.test_experiment_readiness_20261013 -v
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest discover -s HDBSCAN/tests
```

实际生成 `outputs/实验准备/20261013/` 三份文件：`实验收尾证据与下一步.md`、`synthetic_metrics.json`、`manifest.json`。后者原始SHA256 `444e398e9feee9f958b5cba941efa4a1aade85e81b28327c017ee472be4986e7`（15472 bytes），含69条输入/源码/测试绑定、解释器摘要和两个输出摘要。合成演示40条、100随机种子、2000次8日志配对重采样，均非真实场景成绩；不要把演示指标放入论文结果表。

独立配方窄审6项测试通过，无P1/P2；统计初审两项问题均由失败回归及修复后通过验证。随后实际生成和带原始摘要的只读重验均退出0，统计和证据报告精确重放，文件链接/摘要一致。没有活跃实验或正式评价任务。源码/测试/配方/协议和本包已哈希绑定，后续修改须另行版本化，不覆盖旧包或刷新原始摘要。

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/prepare_experiment_readiness_20261013.py --synthetic-demo
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/prepare_experiment_readiness_20261013.py --check-only --expected-manifest-sha 444e398e9feee9f958b5cba941efa4a1aade85e81b28327c017ee472be4986e7
```

第一条只记录首次生成命令，当前不能重跑到相同目录；第二条为可复现只读核验。控制台 `logs/experiment_readiness_generate_20261013.log`、`logs/experiment_readiness_verify_20261013.log`；测试 `logs/experiment_readiness_full_tests_20261013.log`、`logs/experiment_readiness_prelaunch_20261013.log`。本机PowerShell使用rg传入`logs/evaluation*`曾报路径模式无效，已改直接读已知文件；不影响生成。全测试只有既有sklearn参数更名FutureWarning，未改环境。

交付前21项针对性测试再次通过，原始manifest摘要的包重验再次通过，证据表所有本地链接存在；v5.2既有只读check递归验证v5/v5.1/v5.2成功，未改变其数值/来源。`git diff --check`无空白错误，仅既有CRLF提示。见 `experiment_readiness_delivery_tests_20261013.log`、`experiment_readiness_delivery_verify_20261013.log`、`experiment_readiness_preserve_candidate_20261013.log`。未进行Git提交/推送。工具/证据准备收尾，不代表论文整体或正式有效性评价完成。
