# 专家盲评操作材料准备

日期：2026-10-16，Asia/Shanghai。范围：按已存准备协议制作填写说明及内部汇总示例，不启动真实盲评、不确定专家名单或正式指标/规则。前一目标轮产出0552诊断和逐帧证据，属于实际进展；独立窄审未完成的限制保留。

## 现有材料与本轮产出

只读检查了 `outputs/人工复核/`、`outputs/实验准备/` 的文件清单以及相关代码。已有开发回看包、700/150划分与准备协议，尚未发现现成的专家填写说明；不复用带算法语义/分数的开发回看包作为正式盲评包。

新增 [专家盲评填写说明_待校准](F:/Scene_cluster/outputs/实验准备/20261016/专家盲评填写说明_待校准.md)。仅面向专家的中立填写工作稿，沿用0/1/2/NA及已有多选价值机制，未填写任何真实场景或专家记录。没有新建空CSV/XLSX、真实150条映射、标签表或评审平台。

本文是协调者内部记录，不与专家填写说明一起直接发布。下面的三人汇总演示、源码和来源路径只供内部核对，正式专家材料不携带这些示例答案或算法统计。

## 来源与版本边界

- 原准备协议：[独立评价与专家盲评协议](F:/Scene_cluster/knowledge/wiki/独立评价与专家盲评协议.md)。该文件已被20261013统计包绑定，保持不改；其中20260926媒体缺失状态是历史记录。
- 媒体恢复状态：`logs/media_recovery_20261011_status.json`为completed，指向原报告SHA256 `ec708a4c29f1320a2b585b25ccef82efd95d63fb098af1e6c8f1fd6c3f7add3f`。恢复范围限于已授权150评价/8开发；六路关键帧和CAM_FRONT关联非关键帧已解码，其他相机非关键帧仅检查存在/非空。准备媒体不等于已完成正式盲评包或目标可判断性验收。本轮仅核对该历史报告摘要，不重新查看/解码评价图像。
- 既有纯统计模块：[evaluation_metrics.py](F:/Scene_cluster/HDBSCAN/scripts/evaluation_metrics.py)，原SHA256 `1c4f1cf858953a4244cb19d5ed3313a752105c1c109784c4f9a9915f1ebbe7dc`。仅接收调用者提供的内存评分/排序；正式文件导入、真实标签审核、序数一致性等仍未实现。
- 专家人数、校准案例/结果、正式版本/排序与指标仍须后续确认和锁定。本稿不代替这些决定，也不以人工开发反馈生成正式评价标签。

## 正式发布前的协调者检查

以下是原准备协议已有的依赖顺序，不是本轮批准的执行命令，也不是已完成打勾清单。

1. 核对媒体可用性和盲评包的中立性；历史恢复审计不能替代实际评审材料的可判断性检查，不能只挑容易解释的片段。
2. 确认专家及资历记录，使用开发集5–10个案例校准；具体案例尚未选择，不能借评价集调整判据。
3. 确认并锁定评分、主要/次要指标、未知处理及补评规则，保留版本和日期。本文只是既有草案的操作说明，不完成正式批准。
4. 在收正式标签前冻结模型、所有待比较完整排序及其摘要。现有候选仍未收敛，不能把旧模型或开发排名冒充当前冻结排序。
5. 全部150条以匿名编号混排，协调者单独保存身份映射；专家材料隐藏模型名称、分数、原排名和自动语义，不只发某个方法的TopK。
6. 分别收集独立原始意见，检查重复、未提交、NA及理由/时段完整性。补评和讨论结论另列，不覆盖独立评分；正式文件导入接口尚未接通。
7. 只有满足已锁定规则和相应数据完整性条件，才汇总和评价；缺失不可用有利样本补位，不以协议/模板准备完成替代150条真实评价完成。

## 内部合成汇总示例

下表全部是SYN虚构编号和数值，只演示原协议/现有函数。不是场景评分建议，不进入论文结果表，也不展示给专家作为示例答案。

| SYN条目 | 三份原始独立意见 | 当前汇总 | 说明 |
| --- | --- | --- | --- |
| SYN_ITEM_A | 2、2、0 | 2 | 三份有效才取中位数；有分歧但不要求一致，原始0仍保留 |
| SYN_ITEM_B | 0、1、2 | 1 | 不能挑最高分，也不以讨论结果覆盖原始意见 |
| SYN_ITEM_C | 2、2、NA | 未知 | NA不能填0，不能只取两份有效评分 |
| SYN_ITEM_D | 2、2、未提交 | 未知 | 未提交不伪装成一次已完成的NA；两者在数值模块中都表现为缺失，但过程记录必须区分 |

原始记录层须保留NA原因/未提交状态、可判断性、时段、理由和补评/讨论版本。现有 `aggregate_reviews` 的数值结果不能独自承担这些过程信息；正式导入未接通，本轮不新增导入规则或CLI。

标签缺失时，固定TopK中的未知不删除、不补位。主指标Precision@20等口径仍沿用准备协议，尚未正式批准或计算；完整评价集召回/同召回复核预算需满足既有完整标签等条件。三人完全一致率不能冒充序数一致性系数。

## 复核命令

以下只使用4条SYN身份、3个SYN评审者和现有纯函数，不读取真实成员/视频/标签。NA用`None`表示；未提交示例故意不提供该评审者行。

```powershell
@'
from HDBSCAN.scripts.evaluation_metrics import aggregate_reviews

items = ["SYN_ITEM_A", "SYN_ITEM_B", "SYN_ITEM_C", "SYN_ITEM_D"]
reviewers = ["SYN_R1", "SYN_R2", "SYN_R3"]
ratings = {"SYN_ITEM_A": [2, 2, 0], "SYN_ITEM_B": [0, 1, 2],
           "SYN_ITEM_C": [2, 2, None], "SYN_ITEM_D": [2, 2]}
rows = [{"item_id": item, "reviewer": reviewers[i], "priority": value}
        for item, values in ratings.items() for i, value in enumerate(values)]
result = aggregate_reviews(items, rows, reviewers)
assert result["labels"] == {"SYN_ITEM_A": 2, "SYN_ITEM_B": 1, "SYN_ITEM_C": None, "SYN_ITEM_D": None}
assert result["raw_independent_ratings"]["SYN_ITEM_A"] == [2, 2, 0]
assert result["complete_review_count"] == 2 and result["missing_review_count"] == 2
assert result["complete_agreement_rate"] == 0.0
assert len(rows) == 11
print("PASS: 4 SYN items / 11 independent synthetic rows; complete-case median and missing handling match existing implementation")
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'expert_guide_examples','exec'))"

& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest HDBSCAN.tests.test_evaluation_metrics -v
```

说明：11行是故意缺1份的合成演示，不是11条真实评价，也不是专家已参加。本轮不生成或重封20261013合成包。

## 检查结果

上述四条SYN/11行演示命令已执行exit0，三人完整中位数、原始分歧保留及NA/未提交缺失结果与旧函数一致。现有统计模块15项测试本轮重新执行全部通过（0.019s），但不覆盖正式导入、专家独立性、材料盲性或真实有效性。

原20261013统计包manifest ORIGINAL SHA256 `444e398e9feee9f958b5cba941efa4a1aade85e81b28327c017ee472be4986e7` 未变；由该原索引核对准备协议/统计模块/对应测试三份绑定均相符：协议 `bdd31422b2ff04ceacad6591333fc7b42f16842d1118e7b862ea5d93aeed7bbd`，模块 `1c4f1cf858953a4244cb19d5ed3313a752105c1c109784c4f9a9915f1ebbe7dc`，测试 `b298dbfb61f858704b218c9fb5e9576dc088e90727db495c9e8d3afa252fcbca`。原媒体恢复报告摘要也相符，没有重封或修改旧协议。

本轮只做主线程文档核对，未取得独立审定，不将测试通过等同于作者接受、表单验收或正式规则冻结。没有新增实验、真实专家意见、模型/特征改动或Git提交。

交付前复核了新说明/日志的本地链接与空白、入口文档的`git diff --check`，均通过；对专家说明做了有限敏感标记检查，未含实际场景号、内部路径、SYN汇总答案或模型标识。该字符串检查不证明未来评审包整体盲性。原来源摘要与合成示例再次核对通过。填写说明初始版本4839字节，SHA256 `0da78f003b276394b4f3680f128c211ea261b7e98e242df13dee427c0b34232a`；本稿仍待校准，不据此创建正式标签或扩大评价访问。
