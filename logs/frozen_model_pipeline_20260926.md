# 冻结模型链路：开发集内工程验证

日期：2026-09-26。用户确认优先推进不依赖媒体的工作。本轮完成第一阶段的模型导出、载入和开发集内未参与拟合样本的预测诊断；不是正式 700/150 实验。没有下载相机包，没有更改特征规则或评分权重，没有生成专家标签。

## 已实现

- `HDBSCAN/scripts/cluster_umap_hdbscan.py` 保留标准化器与 UMAP 实例，并将其与 HDBSCAN、训练身份、52 列特征顺序、运行库版本、来源哈希、评分参考量保存到输出 CSV 同名前缀的 `.model/` 目录。
- `frozen_model.py` 保存/检查/载入模型；`predict_development.py` 提供 CLI 与不反序列化的 `--preflight`。只接受冻结开发集内、未参与该模型拟合的场景，继续拒绝 150 条评价集及训练身份混入。开发集内留出不声称具有日志隔离的正式评价效力。
- 模型、CSV 和 manifest 不覆盖旧输出。manifest 最后写入作为导出完成标志；失败留下的目录不得视作完整模型。
- 标准化器统计量与特征序、UMAP 拟合输入与标准化数据、HDBSCAN 输入与 UMAP 训练嵌入相互核验，避免误配批次。原始表与聚类表的原有特征/风险字段必须一致。
- 拟合和预测 CLI 要求可核验的特征提取 manifest，绑定输入 CSV、冻结划分、提取脚本、规则及字段定义的版本。旧表即使列名齐全也不能伪装成当前提取结果。合成测试数据明确标为 `synthetic_features`，不能与真实提取来源混用。
- 33 个固定风险输入字段显式要求存在且数值有限，不能由 dtype 推断后跳过异常字段。原有历史评分函数的兼容默认值不扩展到新模型入口。
- 稀有性使用训练样本数和训练簇大小；异常度用 `approximate_predict_scores`；风险权重仍为原值。归一化使用开发训练分数区间并裁剪到 [0,1]，不会根据预测批次重新估计。**排序使用原始 `corner_score`**，避免裁剪或常量参考区间产生的展示分数并列影响排序。
- UMAP 固定逐条 transform，再执行 HDBSCAN 近似分配，避免输入批次/排序影响转换策略；没有对查询集调用拟合。该方法不会发现新的聚类簇，全噪声训练模型明确拒绝预测，不伪造正常簇。

## 安全与版本边界

pickle 可以执行代码。载入必须明确给出 `--trusted-local-model`，只适用于本机自己生成的模型，不能信任网上下载模型。哈希检查不提供发布者认证。

反序列化前检查来源、版本、划分与 payload 哈希；反序列化后核对 pickle 内绑定的 manifest 摘要，防止只改评分参考 JSON。运行库版本不符会拒绝载入，而非猜测兼容。源码改变后旧模型也会被拒绝，需按新版本重建，不要手改 manifest 解除保护。

底层 `predict_development` 是已验证输入的计算函数；有文件来源核验需求时应使用 CLI，而不是绕过入口直接传入任意内存表。

## 验证记录

1. 首先添加 8 项测试，全部因功能未实现而失败，随后实现后通过。
2. 独立只读审查发现模型批次绑定、风险字段契约、原表/聚类表一致性、输入特征语义版本四项缺口。增加回归用例观察失败后修复；复审未发现新的 P1/P2。另为评分 manifest 被修改添加先失败后通过的测试。
3. 最终 HDBSCAN **143 项测试通过**，KMeans **5 项测试通过**，没有运行 KMeans 科研实验。第三方库仍有 sklearn 参数弃用和 joblib 物理核心识别警告，不影响本次测试退出码。
4. 原生真实 UMAP/HDBSCAN 冒烟测试：105 条合成训练向量、3 条合成查询向量，身份只借用开发名单；调用真实聚类/预测 CLI，模型重载后以及整批/逐条预测完全一致。**这些不是从 108 个真实场景提取的新实验结果。**

v3 完成后另载入实际模型，反转三条查询的行序并恢复索引比较，同时重复调用预测；与原整批结果逐列完全一致。该检查在 `autodrive-umap-smoke` 环境执行，没有使用评价场景。

最终有效冒烟目录：`exports/frozen_model_smoke_20260926_v3/`。其中 `smoke_result.json` 保存验证结果及模型 manifest 哈希，`SYNTHETIC_*` 文件不可用于论文结果。v1/v2 是修复过程的旧验证产物，不替代 v3。v3 共 11 个文件、367,051 字节，未产生大媒体文件；绘图因 smoke 环境没有 matplotlib 明确跳过。

模型 manifest SHA256：`4a3192bc0cf18cb1c112f0119e7042cf80a0304185c1ec08ab269dc5073bd911`。

主要命令（项目根目录）：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest discover -s HDBSCAN/tests -p 'test_*.py'
& D:/Python/Conda/envs/autodrive-cluster/python.exe -m unittest discover -s Kmeans/tests -p 'test_*.py'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMBA_NUM_THREADS='1'
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe -u HDBSCAN/tests/smoke_frozen_pipeline.py --output-dir exports/frozen_model_smoke_20260926_v3
```

冒烟命令拒绝覆盖已有目录；再次复验需新批次名。上述线程变量只设置在执行进程环境，未更改全局 Conda 环境。

## 环境问题

主 `autodrive-cluster` 环境的测试夹具使用 PCA 时卡在 `scipy.linalg` 的 SVD 工作区计算；换成随机投影后仍卡在矩阵乘法。两次各 90 秒的诊断均输出了停留栈并退出。这证明主环境仍有线性代数运行时问题，**不是环境已经全面修好**。

普通测试改为不依赖 BLAS/SVD 的测试专用二维投影，真实 UMAP/HDBSCAN 端到端验证在已有 `autodrive-umap-smoke` 环境运行。没有升级、卸载或重装依赖。正式提取可继续使用主环境，拟合/模型载入优先使用已验证的 smoke 环境，且模型导出/载入版本必须一致。

## 下一阶段

- 尚未生成新版 700 条开发特征表，尚未进行正式聚类参数选择、对照方法排序和全量拟合。
- 正式评价特征提取和独立预测入口仍关闭。当前开发诊断不能替代受冻结协议约束的评价入口。
- 仍需最终开发规则复核、700 条提取及数据质量检查，再进行正式模型与排名冻结；现有 16 条 review11 回归不等于全量特征有效性验证。
- 专家模板、标签与有效性计算尚未完成。媒体补齐仍暂缓，不能用缺图或 25 条可播放场景替代全部 150 条盲评。

实现参考：[UMAP 新数据转换](https://umap-learn.readthedocs.io/en/latest/transform.html)、[HDBSCAN 固定聚类近似预测](https://hdbscan.readthedocs.io/en/latest/prediction_tutorial.html)。这些接口只支持固定已学结构的预测，不代表真实场景实验有效性已经得到验证。
