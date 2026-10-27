# HDBSCAN 场景聚类目录说明

## 部分占道漏表达诊断（2026-10-16）

[0552诊断](../outputs/人工复核/0552部分占道绕行根因诊断_20261016.md)精确重现0552/0011/0669各31字段与完整选择轨迹，显示后段静态truck/trailer中心仅单帧入选候选、单帧blocked过滤为0及首个car锚点混入后续转向。仅说明旧规则为何输出0，不是改成避障成功或确认具体人工卡车；一维车身投影不代表真实车道占用。后续独立机制窄审未发现P1/P2，未独立重跑运行检查，见[补记](../logs/partial_bypass_review_followup_20261016.md)；未修改规则、阈值或候选表，0011短障碍与0669保护保持，设计继续暂挂。[只读配方](../logs/partial_bypass_diagnosis_20261016.md)。

## 重跑前警示（2026-10-16）

旧grid绑定[补查记录](../logs/grid_binding_audit_20261016.md)：180份可读JSON中定位到执行链路源索引和成对preflight两项当前源码摘要绑定，另两项只是路径引用。独立窄审无P1/P2，但两处拒读及排除范围未覆盖，不能宣称全局完整。旧源码/摘要未改，修复和新入口仍未批准；本清单不是新增全仓库冻结协议。

[最新执行链路审计](../outputs/实验准备/20261016/执行链路审计与恢复顺序.md)确认：v7仍是固定29重放，未接入全量提取；评价专用预测入口未完成。旧`grid_search.py`缺提取来源门控，同一v7候选表被主拟合preflight拒绝却通过旧网格preflight，**暂不要用于候选参数实验**。未运行任何网格拟合，修复短方案已暂挂，代码未改。

两个环境在单线程/MKL顺序配置下64×64 dot/SVD通过，主环境原生依赖导入也通过；这只更新有限环境证据，不代表完整UMAP/700规模运行已验证。旧模型仍有来源/版本失配，不能冒充当前模型。见[原始命令及边界](../logs/execution_chain_audit_20261016.md)。

本目录保存基于 `nuScenes v1.0-trainval` 的 `UMAP + HDBSCAN` 场景聚类流程、结果文件和后处理分析文件。

当前目录内已有一套独立结果，不应与仓库根目录下的同名 CSV 混用。根目录的历史文件来自更早的实验链路，字段结构与本目录结果不完全一致。

## 论文方法实现事实（2026-10-15）

2026-10-16另有[引文补注件](../outputs/论文初稿/方法与开发验证事实稿_引文补注_20261016.md)，将12条已核对引用放到相关小节；仅增补可剥离标记，原事实稿/公式/数值不变。不是对新候选或正式实验的批准，原始写作核验器不覆盖新补注。[集成检查](../logs/manuscript_citation_integration_20261016.md)。

已整理 [中文方法与开发验证稿](../outputs/论文初稿/方法与开发验证事实稿_20261015.md)，对齐现有52字段、TTC/事件规则、开发参考冻结评分和历史/候选版本边界。14行数值与25来源登记，7项写作核验/330项既有测试通过，正文公式和版本另经独立静态核对；不等于正式实验或全文验收。旧骨架稿/结果不覆盖，正式参数/评价/收益未代为决定。[核验命令与原始摘要](../logs/manuscript_facts_20261015.md)。

## 短暂静态正例补充（2026-10-15）

独立v2补查不满足blocked门槛的静态选中目标，并精确重现五条场景六个严格避障字段。0011单帧truck5.498秒的几何下界1.299m虽为分离，现有短暂避障分支仍成立；12.451秒最低TTC行驶car不是它。0030摩托车潜在相关保留；0042十九条同路径候选均非静态选中，不推断无障碍；0074新增短静态car9.751秒为未知，不能借v1其他查询分离验收。

10项诊断/330项HDBSCAN测试通过，窄审无P1/P2；新源码/测试/输入/协议/证据/报告已绑定，不编辑或重复run。旧规则/特征/评分/模型/评价/媒体不动，0669仍未修复。[对照报告](../outputs/人工复核/短暂静态障碍与持续受阻对照_20261015.md)、[命令/边界](../logs/short_static_diagnosis_v2_20261015.md)。

## 原始绕行保护诊断（2026-10-15）

独立诊断全部四条v7受保护场景及0026，重现原始保护来源并按同目标片段拆解，不改变规则或特征。0669把4个静态目标串为1.349秒受阻，单目标均不满足旧绕行判据；0074也有类似串接但另有真实让行，不能直接用分段结果取消整场保护。0011由严格避障分支保留，短暂静态障碍未进入blocked片段，本诊断最低TTC小车的几何不能替代早期障碍验证。0030摩托车单目标证据保留，0026末帧未来未知。

17项诊断/330项HDBSCAN及原始来源核验通过；源码/输入/协议/证据/报告已冻结，不重复run，不推广v7或修饰成语义验收。0669仍未修复，无新候选特征/模型/评价/媒体。[可读诊断](../outputs/人工复核/纵向绕行保护根因诊断_20261015.md)、[执行记录](../logs/longitudinal_protection_diagnosis_v1_20261015.md)、[人工/设计暂挂](../logs/deferred_decisions_20261015.md)。

## v7纵向目标重放（2026-10-15）

批准后新增独立 `scripts/longitudinal_candidate_v7.py` 及冻结配方，先精确复现固定29条的31纵向字段和静止/静态/原始偏离台账，再将完整未来路线分离门控放到最近前车选择前。393条有原始标注身份的候选；13个目标×帧过滤，重新选前车并统一重算直接依赖。

23条不变，0002/0056/0067/0093/0102/0552六条75格变化，其中13聚类格；0026摩托车及0011/0042完整选择轨迹保留，v6.1横向/VRU/权重/52字段清单不变。**0669没有修复**：旧原始绕行候选触发整场保护，TTC及静态/blocked不变。0552新最低目标car3df0ba待审，0067新货车不是先前横向公交目标。

330项HDBSCAN/7项配方及原始封印精确重放/拟合拒绝通过。所有新绑定源码/测试/配方/表格/报告不可原地编辑，不重复run。没有新提取、评分、模型、全700、评价或媒体。入口 [重点结果与待办](../outputs/人工复核/纵向v7重点结果与待办_20261015.md)，[执行命令/限制](../logs/longitudinal_v7_replay_20261015.md)。

## TTC与前车筛选历史诊断（2026-10-15）

[范围诊断与短设计](../logs/ttc_scope_diagnosis_20261015.md)是v7实施前的历史记录，后续已完成上方v7限定重放，但0669仍未修复。0669的3.364秒是对向静止车转弯投影，不是计算缺失；0026真实摩托车1.901秒发生于末帧、目标速度仅0.034m/s，不能用静止或未来不足一刀切。0669纵向分项已0，min_ttc不直接进入52聚类列，静止/堵路同源统计仍需处理。

当时提出的候选台账/29条精确复现/最近前车选择前门控已经由v7执行；不得只删最低值后填30或把未知当安全。后续保护改版仍单独暂挂，v6.1/旧结果均保持，未拟合、用评价或导媒体。

## v6.1 历史事件连续性（2026-10-15）

用户批准后新增独立 `scripts/crossing_candidate_v6_1.py`，只对同目标已保留且路线相关的已知响应种子，在原连续曝光片段及原六秒窗口内保留历史交互；不改变当前横向冲突或将未知升级确定。新规则不含场景号，指定实例仅用于冻结回归控制。

固定29重放完成，28条全字段不变；0068卡车第23帧（11.551秒）由同目标第15帧种子保留，局部左转0.230769→0.256410，小汽车第24帧不补回。所有v6当前横向/几何/未知、0453/0073过滤、0552程序公交语境及0107侵入保持。312项HDBSCAN/5项配方测试、原始封印和精确重放通过，正式拟合拒绝 `candidate_feature_replay`。

见 [对照与种子明细](../outputs/人工复核/横向交互v6_1事件连续性对照_20261015.md)、[精确命令/边界记录](../logs/crossing_v6_1_replay_20261015.md)。新模块/测试/配方/输入/输出已绑定，不原地编辑或重复run；不是新NuScenes提取或语义整体验收，不展开全700、拟合、评价、KMeans或新媒体。0067公交对应/0073近判据边界、TTC/VRU/部分绕行仍未解决。

## 路线相关性 v6 限定重放（2026-10-14）

**10月15日边界核对：**[同目标贡献与下一版短设计](../logs/crossing_v6_boundary_20261015.md)。0068卡车末帧与旁边小汽车不能混为一段恢复；后续路线分离不足以判定历史让行结束。0067目标为横向公交车，旧行人反馈不能直接验收。现有v6精确重验通过，v6.1尚未实现，拟仅修同目标局部事件连续性，不改几何/横向冲突列或扩大实验。

用户批准后新增独立 `scripts/crossing_candidate_v6.py`，先核对带方向车身与实际观测通行空间，再应用响应保护；局部左转原始响应锚点同样门控。沿用1m裕度，缺帧/未来不足/未驶离仍未知；不是精确车道识别、因果归因或在线安全证明。

固定v5.2开发29轨迹重放完成：25条全字段不变，4条/10格变化，1个聚类值变化。0453初车/0073横向候选归零，0068指定卡车两帧保留、0552两个公交程序语境保留、0107侵入不变；0067新过滤和0068尾段两个局部标记收紧待复核，0073下界1.009m接近1m判据不当作稳健安全结论。294项HDBSCAN/7项配方测试、原始封印与精确重放通过。见 [结果](../outputs/人工复核/横向交互v6重放对照_20261014.md)、[执行/边界记录](../logs/crossing_v6_replay_20261014.md)。

`tables/scene_features_crossing_v6_replay29_20261014.csv` 是 `candidate_feature_replay`，不是新提取质量审计，正式拟合拒绝；无全700、TTC/VRU/部分绕行修改或评价。源码/测试/配方/输入/输出已冻结，后续修订另起版本，勿覆盖或重复run。旧v5.2及媒体/统计包均保留。

## 集中开发复核（2026-10-14）

**后续十条反馈已收齐：**[原话与当前候选核对](../logs/development_review_feedback10_20261014.md)。0068约7.5秒卡车让行、0107约11.5秒公交侵入有人工支持；0073规则停车不等于让横向卡车，0453初车与0669对向近距无实际约束。0102/0151隔离VRU的原始预测仍影响聚类，0552约14秒后部分占道绕行仍漏表达。0815末尾可见但未来不足保持未知；0816局部过滤获支持，不是整体语义验收。本轮只更新反馈/入口，不改下述冻结复核包、状态、特征或模型。

用户愿意一次多看几条后，固定当前v5.2开发29内10条/7日志整理 [集中复核包](../outputs/人工复核/十场景集中复核包_20261014.md)。0453/0552/0068/0073/0151优先，0102/0669/0815/0816/0107补充；均是已见场景的具体目标/时段复核，不冒充10条全新随机场景。8条复用现有带时间GIF，只新增0068/0073两条约6Hz时间一致动图。

10条源图/场景身份/完整GIF解码/原始时序/文档重放通过，10项配方/276项HDBSCAN测试通过；旧媒体记录的历史特征/簇排名已剥离，卡片单独读v4/v5.2。没有目标框，无法辨认就保留未知，不重复要求整体判断或猜未来。原特征/模型/统计包只读核验不变，不抽评价或拟合。执行/原始协议封印见 [记录](../logs/review10_package_20261014.md)，当前无活跃导出，不重复运行。

## 评价统计准备（2026-10-13）

新增独立 `scripts/evaluation_metrics.py`，只在内存中计算三人中位数/缺失、Precision@K上下界、完整名单Recall@K、同召回复核预算、固定随机对照与配对整日志重采样区间。未知不当0、TopK不补位、预算节省可为负；无正例/缺标签不伪造召回，任何重采样不足K均不报告区间。调用者须在标签返回前固定总排名和并列排序规则。模块无真实数据文件导入或拟合入口。

40条SYN合成验证与来源/证据表已导出并只读精确重放；276项HDBSCAN/6项配方测试通过。入口 [证据表与对照方案](../outputs/实验准备/20261013/实验收尾证据与下一步.md)，命令/API边界见 [记录](../logs/experiment_readiness_20261013.md)。正式150条预测/盲评/指标仍关闭，序数一致性/机制覆盖/等级排序指标尚未实现；随机波动不是方法差异置信区间，12日志下推断有限。本包来源/测试/配方绑定不可原地编辑；不重跑已完成的场景提取或拟合。

## 横向交互 v5.2 限定候选（2026-10-13）

用户批准限定实现并要求人工问题统一收集。当前独立入口 `scripts/scene_feature_hdbscan_v5_2.py` 调用 `scripts/crossing_candidate_v5_2.py`，v4七模块和v5/v5.1全部已绑定来源/结果保留。同步方向车身与实际括界观测、独立未知标志、缓慢减速/同目标停止再启动保护均单独核验。候选表仍为129列/52聚类清单，原始预测/未知保存在轨迹；`candidate_feature_extraction`仍被正式拟合拒绝。

固定8条问题+21条控制的v5.2于09:49:42完成并通过只读核验：23条全字段不变，6条/17格变化、3聚类格，零查询异常/39已知诊断正Inf。0068/0552让行表示保留；0816同步投影分离，0815末尾未知不当安全。12个未知为11场景末尾/1目标缺口，不再因遗漏现成括界帧而标未知。261项HDBSCAN/9项本版配方测试通过，代码窄审无P1/P2，不是语义验收。当前无本批活跃提取。见 [人工导航](../outputs/人工复核/本轮复核导航_20261013.md)、[执行记录](../logs/crossing_candidate_v5_20261013.md)。不改VRU/TTC、不提全700、不拟合/选参、不用评价/KMeans、不导出新媒体。

## 补数完成与开发复核（2026-10-12）

**后续逐目标诊断已完成：**[诊断结论](../outputs/人工复核/八场景诊断结论_20261012.md)及[时间/实例明细](../outputs/人工复核/八场景逐目标诊断_20261012.md)。八条重放与冻结 v4 对应行全部 129 列精确相等，52 聚类字段不变；查询异常 0，14 个正 Inf 仅诊断距离。0815 残留为末尾未来不足的远车，不是起步邻车；0816 方向车身仍接近整条路线，但同期较远，单改外接圆不够；0102 人行道 VRU 和 0669 转弯静止目标问题已定位。0453/0552 已过滤目标不能等同其真实让行目标。182 项既有/10 项诊断测试通过；只完成诊断，未改特征/模型或使用评价。首次地图后处理失败与单独续跑协议均保留，不重复提取。见 [执行记录](../logs/review8_target_diagnosis_20261012.md)。

**八条反馈已接收：**[原话与问题定位](../logs/development_review_feedback_20261012.md)。0002/0093 的过滤有支持；0102 的 VRU 原始预测、0669 的对向静止目标 TTC/障碍、0815 的残留横向冲突、0816 的环岛曲率/交互传播需继续诊断。0552 公交车让行与卡车绕行、0453 规则停车与后续皮卡约束不能一并过滤。未改 v4 特征或冻结协议，不算整批验收。媒体报告中的 pending 是导出时状态，后续反馈不回写原 JSON。

相机补数于北京时间 10 月 12 日 04:58 完成。03–10 包完成校验，176,569 张缺失图像补齐，限定 211,407 个文件的完整性及恢复来源核验通过。六路关键帧和前视关联非关键帧完整解码，其他相机非关键帧仅存在/非空检查。覆盖冻结评价 150 条及八条待审开发前视，不表示全数据集媒体完整。原图不覆盖、缓存不自动删除；没有运行中的补数 worker，不重复启动。见 [完成报告](tables/media_recovery_audit_20261011.json)和[执行记录](../logs/media_recovery_20261011.md)。媒体完整性不等于专家有效性通过。

用户批准继续开发复核后，[八场景复核包](../outputs/人工复核/候选特征八场景复核包_20261012.md)已生成约 6 Hz 带时间 GIF，含当前候选与历史审计特征对照，不套用旧聚类/排名。优先 0002/0552/0093/0102/0453，补充 0669/0815/0816；逐帧来源、身份、完整解码及时序通过核验，人工语义仍待反馈。见 [本批日志](../logs/development_media_review_20261012.md)。未修改特征/划分、拟合模型、选参或查看评价语义。

## 当前候选版本重建（2026-10-01）

用户已明确批准候选冻结及当前来源完整开发集重建。版本 `feature_candidate_v4_20261001`，固定七个源码模块、52 个聚类字段、700 条开发成员和顺序、运行环境及核验配方；副本见 `../logs/source_snapshot_candidate_20261001/`。候选冻结不是语义验收，也不是正式参数选择。

700 条重建于 2026-10-01 14:25（北京时间）完成，10 月 3 日 `check --check-only` 重验通过。表 `tables/scene_features_development_candidate700_20261001.csv` 含 129 列/52 聚类字段，查询异常 0，无常量聚类列，33 条/七条控制精确复现；1,078 个正 Inf 仅在两项诊断距离，未发现其他原始非有限值。相比历史表，691 条全字段不变，9 条共 26 个值变化；其中 scene-0002 的一个聚类值从 0.1 到 0，不能沿用旧拟合作当前版本结果。八条变化场景包括 0552 仍须复核，风险下降不等于已验证改善，不自动拟合或替换模型。

真实状态以 [运行状态 JSON](../logs/development_candidate700_20261001_status.json) 和 [控制台日志](../logs/development_candidate700_20261001_console.log) 为准；固定协议在 `tables/development_candidate700_protocol_20261001.json`，命令与限制见 [本批执行记录](../logs/development_candidate700_20261001.md)。不要重复启动。正式聚类参数、KMeans、评价提取/盲评及媒体恢复均不在本次授权内。

## 扩展开发回归（2026-10-01）

v4 后限定 33 条元数据回归已完成，来源/结构核验通过：21 条已有对照、四地点各三条新增，23 个日志；全部 52 聚类字段不变，31 条全部数值不变。0151 的已知修正精确复现；新变化 0552 风险 0.349963 → 0.200000 仍需专家复核，不能当作已证实改善。异常 0，44 个正 Inf 仅在两项诊断距离。182 项代码测试及四项分析测试通过。

新表 `tables/scene_features_crossing_regression33_20261001.csv`，提取前方案、审查补充方案、比较 JSON 和风险 CSV 均保留。未改特征源码、拟合模型、使用评价或批量导出媒体，仅针对新变化 0552 单独定位轨迹。检查器已纠正风险单调性/依赖字段假设，原方案不回写。状态与命令见 [本批日志](../logs/crossing_regression33_20261001.md)，不要自动重提全 700 条。

0552 单条精确复现，定位约 13.4–13.9 秒的小汽车预测；41 张前视关键帧全缺失，因此语义待验。后续用户已批准候选冻结及同版本 700 条重建，当前运行状态见上节；不将候选冻结等价为特征全部有效或正式参数已选定。

## 开发语义复核包（2026-10-01）

五条人工反馈已接收，原话与排错过程见 [反馈及修正记录](../logs/semantic_review_feedback_20261001.md)。0151 的自行车横穿误报来自右转前的直行外推；新增完整未来、实际路线、车身范围和让行保护，不改聚类特征清单或评分权重。最终 `tables/scene_features_semantic_feedback7_20261001_v4.csv` 已完成并核验：仅 0151 三个横向字段变化，风险 0.160460 → 0.010417；另外六条及七条全部 52 聚类字段不变，查询异常 0。182 项测试通过，独立代码复查无新增可执行问题。七条不等于全库验收。

**来源已变更：9 月 27 日审计 700 条和 9 月 30 日参数实验是修正前结果，不能直接作为当前来源拟合。**匹配源码保存在 `../logs/source_snapshot_20261001_pre_turning_crossing/`。本轮未重提全 700 条，也未更新模型或排名；v2/v3 是中间修正，v4 才是最终规则版本的七条提取。

[五场景复核包](../outputs/人工复核/聚类语义五场景复核包_20261001.md) 已准备好：0158、0107、0151、0032、0014，共五条不同开发日志，带原始数据时间的约 6 Hz GIF 已完整解码及时序核验。原计划的 0905/0544/0997/0703 前视媒体全缺失，四条补充只检查同簇解释，原问题继续待查。

现存语义 JSON 的 94 × 52 数值画像本轮独立重算相符，旧分析配方和报告在当前目录缺失，来源缺口保留。用户已确认施工放行、公交车侵入、0151 无影响、大角度低风险转弯及红转绿起步；这些只用于开发诊断，不是盲评有效性结果。30/1 仍未定为正式模型。媒体来源、命令及限制见 [本轮执行记录](../logs/semantic_review_pack_20261001.md)。

## 最新参数对比（2026-09-30）

已完成批准的 4 组参数 × 5 个种子，20 次全部成功，使用修正前审计版 700 条特征。入口 `scripts/parameter_stability.py` 支持 `--preflight`、完整开发成员与来源/质量校验、禁止覆盖，固定小范围，不会启动历史大网格。10 月 1 日之后旧表被当前来源保护拒绝是预期行为。

- [四组汇总表](tables/parameter_stability_20260930/configurations.csv)：30/1 的簇数为 13–14，十对种子 ARI 中位数 0.740、Top20 重合率中位数 70%；原 15/1 分别为 0.353、47.5%。最大簇占比中位数 13.71%。
- min_samples=5 的两组 ARI 中位数更高，但最大簇占比中位数约 52%，且部分种子差异较大，不能据单指标直接判优。
- 全部身份、评分重算、文件哈希与 40 对比较核验通过，原配置五个种子均复现旧结果；165 项测试通过。没有自动选参、导出替代模型或覆盖原排序。
- 全部单次排名、运行指标、两两比较和固定方案见 `tables/parameter_stability_20260930/`；命令及局限见 [实验记录](../logs/parameter_stability_20260930.md)。下一步优先检查开发簇语义，不使用评价集，不重提 700 条。

## 审计与初始稳定性（2026-09-27）

- **700 条全量审计已完成，2026-09-29 核验通过。**历史全量表 `tables/scene_features_development_audit700_20260927.csv` 与更早表数值完全一致，风险分项不变；查询异常 0，1,078 个正 Inf 均属于两项诊断距离，没有 NaN、负 Inf 或其他字段非有限值。不是语义验收；10 月 1 日之后已非当前来源，不刷新旧 manifest。见 [本批记录](../logs/development_audit700_20260927.md)。
- 当时源码对应的小样本表：`tables/scene_features_audit8_20260927_v2.csv`，8 条开发场景覆盖四个地点，129 列及风险分项与旧表完全相等；10 月 1 日后也属于历史来源。无 v2 文件是输出路径保护修订前的过程快照。
- 新增 `.csv.quality.json`：记录最终填值前的 NaN/Inf 及全部 8 处查询异常。8 条中异常 0、NaN 0、正 Inf 12，均是两项诊断最小距离，不进入聚类/风险评分。旧填充值 30 不能自动解释成实测距离；此审计不能证明其余 692 条或全部中间计算有效。
- 原 700 条开发表的 5 种子实验已完成：8–16 个簇、0–64 个噪声点；其他种子与 seed42 的 Top20 重合率仅 45%–65%。结果见 `tables/seed_stability_20260927/summary.json`，不挑选最优种子、不改原排序，不能把单次排序当稳定结论。
- **源码版本已变化**：当前拟合/模型载入会拒绝旧 700 条来源。旧表和模型没有覆盖；如需复现，用 [旧源码快照说明](../logs/source_snapshot_20260927_pre_audit/README.md)，不要改 manifest 或绕过版本保护。新表需附带质量审计来源。
- 154 项 HDBSCAN 测试通过，输出路径冲突问题已修复并复审。仍不跑 KMeans、不开放正式评价、不下载媒体。命令、分析和局限见 [执行记录](../logs/extraction_audit_and_stability_20260927.md)。

## 700 条开发实验（2026-09-27，审计改造前）

700 条开发场景已完成特征提取、结构检查、单组默认参数 UMAP/HDBSCAN 拟合和评分。**这是开发探索结果，不是专家确认的危险场景或最终有效性结论。**

- 特征：`tables/scene_features_development_20260926.csv`，700 行、129 列、52 个聚类特征；地图可用 700 条，路口标记阳性 586 条，无聚类常量/全零列。历史非有限值填充仍限制计算有效性的判断。
- 聚类：`tables/scene_features_development_20260927_umap_hdbscan.csv`，12 个簇、54 条噪声（7.71%）。UMAP 为 15 邻居、10 维、cosine、seed 42；HDBSCAN 为 min_cluster_size=20、min_samples=1。没有网格搜索。
- 评分：`tables/scene_features_development_20260927_with_corner_score.csv`；[完整优先级排序](tables/development_priority_ranking_20260927.csv)按原始 corner_score 降序排列，保留各风险分项。高分与噪声均不等于危险标签。
- 冻结模型：聚类表同名前缀 `.model/`，可信本地重载及训练输出、固定参考评分重算一致性均通过。700 条均参与拟合，不能再作为该模型的未见开发样本。
- 环境：`autodrive-umap-smoke`；本轮未修复主环境、未运行 KMeans、未使用评价场景、未下载媒体。缺少 matplotlib，未生成新聚类图。

命令、Top5 分项及下一步见 [实验记录](../logs/development_clustering_20260927.md)；机器可读摘要见 `tables/development_fit_summary_20260927.json`。下列 review 批次是历史诊断，不替代本批来源。

## 评价准备（2026-09-24）

已冻结自定义开发/评价划分：`tables/evaluation_split_20260924.csv`，700/150 条、56/12 个采集日志，日志不交叉，覆盖四个地点。此划分不是官方 train/val；850 条都曾用于旧无监督探索，独立性指从现在起不再使用留出场景调规则或参数。

来源和文件哈希见同名前缀的 manifest JSON，命令与审计见 [划分记录](../logs/evaluation_setup_20260924.md)，专家评分与对照规则见 [盲评协议](../knowledge/wiki/独立评价与专家盲评协议.md)。生成器 `scripts/prepare_evaluation_split.py` 禁止覆盖已有划分。

**开发入口已接入保护，评价预测尚未实现：**特征提取默认只选 700 条开发场景；聚类、搜索和评分拒绝混入评价场景。拟合输入必须含当前全部 52 列语义字段和合法 scene_name/token，旧 24/48 列表不再自动降级接受。媒体尚未齐备、样本外预测和专家标签尚未完成，不要把入口验证写成实验有效性通过。

2026-09-26 [媒体完整性审计](../logs/evaluation_media_audit_20260926.md)：150 条评价场景中 25 条前视关键帧齐全且解码通过，125 条全部缺失；六路各缺 5,052 张。没有检查非关键帧，不能视作完整视频已就绪。保持冻结成员，不用现有 25 条替代正式评价，也不将缺失记为低价值。逐项证据见 `tables/evaluation_media_audit_20260926.json`（仅协调者使用）。700 条开发提取预检查通过，本轮未运行全量提取或拟合。

后续[补数定位](../logs/evaluation_media_recovery_20260926.md)未找到可恢复缺失示例的本地副本；已生成关键帧及关联非关键帧共 175,386 个缺失文件的清单，并验证第 03–10 批官方相机包可访问，总计约 143.2 GB。**用户因磁盘空间不足暂缓下载**，尚未补齐；不要自动启动补数或将下载准备记为媒体修复完成。优先推进模型保存/冻结预测与开发集实验准备。当前提取逻辑不读取相机图像，媒体缺失不直接阻塞此步骤；完整视频盲评仍须等待补数。

### 开始前先检查

在根目录、autodrive-cluster 环境执行：

```powershell
python HDBSCAN/scripts/scene_feature_hdbscan.py --preflight
$env:SCENE_CLUSTER_FEATURE_INPUT='scene_features_audit8_20260927_v2.csv'
python HDBSCAN/scripts/cluster_umap_hdbscan.py --preflight
python HDBSCAN/scripts/grid_search.py --preflight
```

此处 8 条回归输入仅验证入口，不用于正式拟合。模型导出要求当前提取及质量审计来源，旧 review 和旧 700 条表不再作为当前源码拟合的预检查示例。后续应生成新版本的完整开发表；不要直接去掉 preflight 拟合这份 8 条回归表。

默认新输出为 `scene_features_development.csv`、`scene_features_development_umap_hdbscan.csv`、`scene_features_development_with_corner_score.csv`，本轮没有生成。拟合/评分附 `.csv.manifest.json`，不允许覆盖已有输出。开发评分只接受来源可核验的新聚类表。`SCENE_CLUSTER_START_INDEX` 现相对开发清单，显式名称不能包含评价场景。详见 [入口保护记录](../logs/development_guard_20260924.md)。

## 工程与 review11 状态（历史记录，2026-09-26）

新增[冻结模型工程链路](../logs/frozen_model_pipeline_20260926.md)：主拟合入口保存 scaler、UMAP、HDBSCAN 与固定评分参考量到 `.model/`；`scripts/predict_development.py` 只诊断未参与拟合的开发场景，支持 `--preflight`，真实载入需 `--trusted-local-model`。尚不开放 150 条正式评价入口。143 项 HDBSCAN、5 项 KMeans 测试通过，另以真实原生模型验证 105/3 合成样例，不是新场景实验。主环境 SVD/矩阵乘法仍会卡住，原生 UMAP 验证使用 `autodrive-umap-smoke`；本轮未修复全局环境。

**700 条开发提取及结构检查已完成：**结果为 `tables/scene_features_development_20260926.csv`，不导出轨迹/GIF；9 月 27 日另行完成开发拟合，见本页顶部。继续工作前先看[提取日志](../logs/development_extraction_20260926.md)，避免重复运行。提取器仍有历史非有限值填充，有限性检查不等于计算有效性或人工识别通过。

已整理 [五场景人工复核包](../outputs/人工复核/review11_五场景复核包_20260926.md)：0042、0030、0011、0026、0053。使用原有动图与 review11 证据，状态为待反馈，不是新增标签或独立盲评。旧 GIF 播放时间与数据时间不完全一致，文档已明确标注。

- review11 提取为 `tables/scene_features_review11_20260925.csv`，16 条开发场景、129 列、52 个聚类特征；逐列与 review10 完全一致，风险分项也完全一致。文件名日期为批次启动日，该诊断批次跨日完成，未重跑聚类。
- 新增独立 [静止/低速车辆旁通过诊断](tables/review11_static_passages_20260925.md)，共 13 条候选（9 条有局部静止证据、4 条静止性未确认），另有 4 条地图关系不支持或道路外记录。**不是新增风险标签，不进入评分和聚类。**
- 0042 识别出约 5.90、6.40、13.30 秒的 3 个目标经过记录，近似横向车身间距约 1.35–1.47 m；一条有静止证据，两条静止性未确认，均未观察到明确横向动作。保留原人工反馈，但没有强行把避障换道标记从 0 改成 1。
- 入口 `scripts/audit_static_passages.py` 支持 `--preflight`、开发集保护、同批特征/轨迹哈希核验和禁止覆盖；需要带车宽的新轨迹。`tables/review11_trajectory_audit_20260925.json` 的哈希已写入提取 `.csv.manifest.json`。
- 129 项 HDBSCAN、5 项 KMeans 测试通过；同批来源、未覆盖文件及原特征/评分不变均已核验。命令、规则和局限见 [本轮日志](../logs/review11_static_passages_20260925.md)。0073 因果归因及风险有效性仍未解决。

## review10 状态（历史基线，2026-09-25）

- 当前表：`tables/scene_features_review10_20260925.csv`，16 条开发场景、129 列、52 个聚类特征，未进行聚类拟合。原 14 条之外补测 0042、0067。
- 对向候选同时要求车头朝向与速度方向接近反向，0030 的假避障期间对向比例 0.075→0，避障标记仍为 1；0042、0067 的真实对向目标通过方向检查。
- 原 14 条仅 0030 的对向比例/事件数两列改变，其余特征与风险分数不变；未修改风险权重。0042 避障标记仍为 0，是新暴露的待修漏检，不能声称全部人工反馈已通过。
- 新增独立 [事件审查记录](tables/review10_events_20260925.md)，0073 拆成停车前卡车、挂车、停止牌低速停车、停车后小汽车四条记录，停车原因均为未确定。其风险仍为 0.30，并非评分问题已经解决。
- 来源与比较：`tables/scene_features_review10_20260925.csv.manifest.json`、`tables/review10_20260925_manifest.json`、`tables/review10_20260925_comparison.csv`、`tables/review10_20260925_risk.csv`；事件 JSON 保存输入和脚本哈希。
- 新入口 `scripts/audit_interaction_events.py` 支持 `--preflight`，拒绝评价身份、重复场景、无效时序和覆盖已有结果。完整命令和剩余问题见 [本轮记录](../logs/review10_revision_20260925.md)。118 项 HDBSCAN、5 项 KMeans 测试通过。

## review9 状态（历史基线）

- 当前开发回归表：`tables/scene_features_review9_20260925.csv`，14 行、129 列、52 个聚类语义特征；仍不是完整开发集拟合结果。
- 针对标注抖动增加整段轨迹静止证据，0030 避障标记由 0 恢复为 1，目标为道路内摩托车；没有恢复道路外目标，也没有更改 TTC 或风险权重。
- 对比 9 月 22 日结果，仅 0030 的 9 列变化，其余 13 条完全一致；14 条风险分数均未变化。0011 真避障与 0053/0055/0056/0109 假避障回归保持。
- 风险分项和对比：`tables/review9_20260925_risk.csv`、`tables/review9_20260925_comparison.csv`；提取来源见 `.csv.manifest.json`，风险审计来源见 `tables/review9_20260925_manifest.json`。
- **未解决**：0073 包含停车前卡车和起步后小汽车两组横向预测，不可直接解释成“为卡车停车”，当前分数暂保留；0030 派生的对向车暴露需另行核验。0109 侧向候选及实际侵入/路线近距的实景正例验收仍待完成。
- 新轨迹诊断：`tables/review9_trajectory_audit_20260925.json`；完整命令、证据与局限见 [本轮记录](../logs/review9_revision_20260925.md)。110 项 HDBSCAN、5 项 KMeans 测试通过；未拟合聚类、未使用 150 条评价场景。

## 上一轮特征状态（2026-09-22，历史基线）

第八批人工反馈已完成一轮特征修订和 **14 场景回归**，没有全量重跑，也没有重跑聚类。以下旧章节保留为历史说明，不应替代本节的版本边界。

- 当前特征表：`tables/scene_features_review8_20260922.csv`，14 行、129 列；其中 52 列进入聚类语义白名单，其他列包含标识、诊断和风险证据。
- 对比与分项评分：`tables/review8_20260922_comparison.csv`、`tables/review8_20260922_risk.csv`；输入、脚本哈希和环境见 `tables/review8_20260922_manifest.json`。
- 新增道路外目标过滤、避障位移尺度限制、侧方汇入候选、实际侵入轨迹、横向路线复核和停止牌停车上下文。车道中心线距离只作诊断，不据此硬删前方障碍。
- `0055/0056/0109` 假避障消除，`0053` 草坪自行车不再贡献原最低 TTC；`0011` 真避障和 `0068/0074` 左转交互保留。
- **未解决**：`0073` 横向风险仍有残留；`0030` 真避障未被新规则保留；`0109` 新侧向候选尚未人工确认。实际侵入与路线近距两项新特征在这批中全零，仍需实景正例验收。
- `tables/*review8*20260921*` 和 `scene_features_review8_diagnostic.csv` 是被替代的排错快照；即使名字含 `final` 也不应用作当前结论。
- 复跑命令、人工标签及逐项结果见 [实验记录](../logs/review8_revision_20260921.md)，规则边界见 [车辆路径与停车归因](../knowledge/wiki/车辆路径与停车归因.md)。

## 0. 历史开发状态（2026-07-11）

当前脚本已经进入“特征收紧与重构”阶段，正式 850 场景结果尚未用最新脚本全量重跑。

已更新但尚未全量重跑的内容：

- `scripts/scene_feature_hdbscan.py`
  - 路口特征拆分为 `intersection_density` 和 `lane_connector_density`
  - 前车/TTC 改为基于 ego 坐标系的前向与横向筛选
  - 重车特征新增 `truck_bus_dynamic_ratio`
  - VRU 特征新增 `pedestrian_front_ratio`、`pedestrian_crossing_risk_ratio`、`crosswalk_pedestrian_ratio`
  - 两轮车新增 `two_wheeler_dynamic_ratio`
  - ego 动态新增 `ego_decel_min`、`ego_hard_accel_ratio`
  - 支持 `SCENE_CLUSTER_MAX_SCENES` 和 `SCENE_CLUSTER_FEATURE_OUTPUT` 做小样本验证
- `scripts/cluster_umap_hdbscan.py`
  - 支持 `SCENE_CLUSTER_FEATURE_INPUT`、`SCENE_CLUSTER_CLUSTER_OUTPUT`、`SCENE_CLUSTER_CLUSTER_FIGURE`
- `scripts/corner_case_detection.py`
  - 风险分数改为加权风险组件
  - `corner_score` 权重改为 `rarity=0.25`、`atypical_norm=0.25`、`risk=0.50`
  - 支持 `SCENE_CLUSTER_CLUSTER_INPUT` 和 `SCENE_CLUSTER_SCORE_OUTPUT`

当前 debug 验证产物：

- `tables/scene_features_debug_50.csv`
- `tables/scene_features_debug_50_umap_hdbscan.csv`
- `tables/scene_features_debug_50_with_corner_score.csv`

这些 debug 文件只用于验证新特征定义，不应当替代正式论文结果。正式结果仍以完整 850 场景重跑后的 `scene_features.csv`、`scene_features_umap_hdbscan.csv`、`scene_features_with_corner_score.csv` 为准。

### 2026-07-11 事件窗口化 V2 验证

在用户人工复核 5 个场景后，当前开发版进一步将“目标暴露、路径交互、危险后果”拆开：

- 新增纯规则模块 `scripts/scene_feature_rules.py`，识别同车道跟随、合流暴露/冲突、横向交通暴露/冲突和 VRU 横穿暴露/冲突。
- ego 速度和加速度改用真实 sample 时间戳，航向变化处理 `+/-pi` 跳变。
- 周边车辆统计限制为自车 50 米内，前车距离改为车身净间距并过滤重叠标注。
- TTC 同车道横向中心带收紧为 `1.8m`，避免相邻车道和右转车辆进入纵向 TTC。
- 新增事件比例、事件次数和最长持续时间；路口停车作为“主动让行”上下文记录。
- 聚类改用 `scripts/feature_selection.py` 的显式场景语义白名单，不再输入 TTC、急刹、默认距离和 `frame_count`。
- HDBSCAN 输出新增 `cluster_probability` 和 `cluster_outlier_score`。
- corner score 改由 `scripts/corner_scoring.py` 计算纵向、合流/横穿、VRU、自车响应四组固定阈值风险，不再对风险特征逐列做批次 MinMax。
- 决策过程新增起始停车、行驶后停车、再起步、静止前车、避让换道、VRU 事件次数和真实后续轨迹相关性。
- VRU 补充同车道暴露、同向行走和“静止障碍避让窗口内 VRU 冲突”复合特征，分别描述车道占用与避障遮挡风险。
- 同车道 VRU 进一步使用 walkway 与自车 lane 中心线约束；严格 VRU 风险使用录像中的同步未来轨迹和真实车道进入复核，远距离或始终位于人行道的 VRU 只保留为暴露。
- 合流候选要求正向速度、同向 annotation 朝向和至少 1 秒持续时间；对向车辆不再仅因未来最近距离较小而算作合流。
- 侧向同向车辆进一步拆分为超车暴露、非超车的未来路径汇合、实际进入当前 ego lane 三层语义；超车本身不直接增加风险评分。
- VRU 观测相关性新增场景内最近接近时刻，用于区分冲突前接近、驶过后近距和路线分离。
- TTC 最小值新增目标 annotation/instance、类别、场景时刻、净距离、横向位置、目标速度、相对速度和航向差，支持从场景级数值回溯到具体参与者。
- TTC 新增局部转向投影过滤：转弯过程中短暂进入自车前向走廊的静止对向/路侧车辆不再形成危险 TTC。
- 新增 `blocked_path_obstacle_ratio`、`obstacle_induced_route_deviation_flag` 和 `route_deviation_decision_demand`，将施工占道后的被迫改道表达为决策复杂度而非碰撞风险。
- 避障要求持续静止障碍，或短时障碍后出现至少 `4m` 且航向恢复的强横移；仅凭近距离不再触发避障。
- 严格 VRU 风险新增持续性字段，约单帧 `0.5s` 的接近只保留为暴露，两帧以上的持续交互进入风险评分。
- 前方停止目标拆分为当前停止、永久静止障碍和场景内曾运动的暂时停车前车；左转横向车流交互与停车前/后横向冲突分别输出。
- 地图控制新增交通灯、停车标志、转向停车和非信号路口密度；交通灯相位在 nuScenes 中不可用。
- 评分拆分为 `observed_risk` 和 `decision_demand`：停车让行降低当前剩余冲突，但非信号环境下的观察与通行决策需求仍单独保留；检测到高密度交通灯控制时，非信号路口决策需求按最高 80% 衰减。

V2 debug 产物：

- `tables/scene_features_v2_debug_50.csv`
- `tables/scene_features_v2_debug_50_umap_hdbscan.csv`
- `tables/scene_features_v2_debug_50_with_corner_score.csv`
- `tables/scene_features_decision_debug_50.csv`
- `tables/scene_features_decision_debug_50_umap_hdbscan.csv`
- `tables/scene_features_decision_debug_50_with_corner_score.csv`

注意：最新 50 条调试表包含 95 列原始场景字段，并形成两个开发簇（28/22）。该批次经过多轮人工案例定向调参，不能用其 `corner_score` 排名或簇分布作为论文正式结论；正式结论仍需完整 850 场景复跑和独立抽样验证。

第二个独立开发批次使用 nuScenes scene 表索引 `50:100`，输出为 `tables/scene_features_batch_0051_0100*.csv`。实际 scene 名范围为 `scene-0053` 至 `scene-0126`。2026-08-15 收紧后的独立验证表为 `scene_features_route_tightening_0051_0100_final.csv`，共 50 条、118 列，其中 112 个数值字段、6 个追溯文本字段，48 个核心语义特征进入聚类。当前固定参数仍将 50 条均标为噪声，因此该批次仅用于规则验证。详细命令、抽样方法和人工审核问题见 `logs/feature_batch_0051_0100_2026-07-12.md`。

## 1. 当前目录文件清单

### 1.0 目录结构

| 目录 | 内容 |
| --- | --- |
| `scripts/` | HDBSCAN 链路脚本和场景回看工具 |
| `tables/` | CSV/XLSX 表格结果与人工分析表 |
| `pictures/` | 聚类图、报告插图等图片产物 |
| `README.md` | 本目录说明 |
| `logs.md` | 本目录历史批次与变更记录 |

### 1.1 核心脚本

| 文件 | 类型 | 作用 | 当前状态 | 备注 |
| --- | --- | --- | --- | --- |
| `scripts/scene_feature_hdbscan.py` | 主流程脚本 | 从 `nuScenes` 提取场景与事件特征，输出 `tables/scene_features.csv` | V2 debug 已验证 | 当前输出包含 `scene_token` / `scene_name`，正式 850 表尚未重跑 |
| `scripts/scene_feature_rules.py` | 规则模块 | 车辆/VRU 交互分类、事件持续时间和航向变化 | 单元测试覆盖 | 不直接读取 nuScenes |
| `scripts/feature_selection.py` | 聚类输入模块 | 明确场景语义白名单 | 单元测试覆盖 | 排除结果型风险和哨兵值 |
| `scripts/cluster_umap_hdbscan.py` | 主流程脚本 | 对白名单特征做标准化、UMAP 降维、HDBSCAN 聚类 | V2 debug 已验证 | 额外输出成员概率和离群分数 |
| `scripts/corner_scoring.py` | 评分模块 | 计算分组物理风险和综合 corner score | 单元测试覆盖 | 不使用批次 MinMax 定义危险阈值 |
| `scripts/corner_case_detection.py` | 主流程脚本 | 加载聚类表并调用分组评分 | V2 debug 已验证 | 输出 `tables/scene_features_with_corner_score.csv` |
| `scripts/grid_search.py` | 试验脚本 | 搜索 UMAP/HDBSCAN 超参数组合 | 当前目录下无对应输出文件 | 属于参数试验脚本，不是主结果链路的一部分 |
| `scripts/review_nuscenes_scenes.py` | 工具脚本 | 回看具体场景；支持按 `scene_name` 播放或导出 GIF | 当前版本可用 | OpenCV GUI 不可用时会自动回退为 GIF 导出 |

### 1.2 结果文件

| 文件 | 生成阶段 | 作用 | 当前状态 | 关键说明 |
| --- | --- | --- | --- | --- |
| `tables/scene_features.csv` | 特征提取 | 场景级特征表 | 有效 | `850 x 24`，仅保留数值特征，没有场景标识列 |
| `tables/scene_features_umap_hdbscan.csv` | 聚类 | 聚类结果表 | 有效 | `850 x 25`，新增 `cluster` 列 |
| `tables/scene_features_with_corner_score.csv` | corner case 评分 | 综合优先级结果表 | 有效 | `850 x 30`，新增 `rarity / atypical / risk / corner_score / corner_score_norm` |
| `pictures/Figure_1.png` | 聚类 | UMAP 2D 可视化散点图 | 有效 | 来自聚类脚本的可视化输出 |
| `tables/cluster_semantic_labels_enhanced.xlsx` | 人工分析 | 聚类簇语义标签、簇画像、术语表 | 有效 | 包含 3 个 sheet：`Cluster_Labels`、`Cluster_Profile`、`Feature_Glossary` |
| `top20_corner_cases_analysis.xlsx` | 人工分析 | Top 20 场景的人工总结 | 有效 | `scene_id` 是本地结果表的行号，不是 nuScenes 的 `scene-xxxx` |

### 1.3 临时或可忽略文件

| 文件或目录 | 说明 |
| --- | --- |
| `scripts/tempCodeRunnerFile.py` | VS Code 临时文件，不属于正式流程；当前已清理 |
| `scripts/__pycache__/` | Python 缓存目录，不属于正式结果；当前已清理 |

## 2. 当前结果摘要

基于当前目录内 `tables/scene_features_umap_hdbscan.csv`：

- 样本数：`850`
- 标签数（含噪声）：`18`
- 有效簇数（不含 `-1`）：`17`
- 噪声占比：`0.0647`

基于当前目录内 `tables/scene_features_with_corner_score.csv`：

- `risk` 均值：`0.4935`
- `corner_score_norm` 范围：`0.0 ~ 1.0`
- Top 20 分析结果已单独整理到 `top20_corner_cases_analysis.xlsx`

## 3. 推荐执行顺序

建议始终在本目录内执行脚本。脚本已经按当前位置解析路径，输出会落在 `tables/` 或 `pictures/` 下，不会污染仓库根目录。

```powershell
conda activate autodrive-cluster
Set-Location F:\Scene_cluster\HDBSCAN
```

### 3.1 提取场景特征

```powershell
python .\scripts/scene_feature_hdbscan.py
```

输出：

- `tables/scene_features.csv`

### 3.2 可选：做参数搜索

```powershell
python .\scripts/grid_search.py
```

预期输出：

- `tables/umap_hdbscan_grid_search.csv`

说明：

- 当前目录内没有保存这一步的结果文件。
- 仓库根目录曾有一份历史 `tables/umap_hdbscan_grid_search.csv`，但不应默认视为当前目录结果的直接来源。

### 3.3 运行聚类

```powershell
python .\scripts/cluster_umap_hdbscan.py
```

输出：

- `tables/scene_features_umap_hdbscan.csv`
- `pictures/Figure_1.png`

### 3.4 计算 corner case 分数

```powershell
python .\scripts/corner_case_detection.py
```

输出：

- `tables/scene_features_with_corner_score.csv`

### 3.5 回看具体场景

直接按 nuScenes 场景名回看：

```powershell
python .\scripts/review_nuscenes_scenes.py --scene-name scene-0061 --play
```

说明：

- 当前 OpenCV 构建为 `GUI: NONE`，不能弹本地窗口。
- 脚本会自动回退为导出 GIF，默认输出到 `F:\Scene_cluster\exports`。
- 若本地缺失对应相机图片，GIF 导出会失败；这是数据缺失问题，不是算法问题。

## 4. 可追溯批次梳理

以下批次是根据文件时间戳和文件内容反推得到，用于整理仓库，不代表严格的实验日志。

| 批次 | 时间 | 主要动作 | 产物 | 备注 |
| --- | --- | --- | --- | --- |
| Batch-0 | `2025-12-22 17:04 ~ 17:07` | HDBSCAN 主流程脚本首次成型 | `scripts/cluster_umap_hdbscan.py`、`scripts/grid_search.py`、`scripts/scene_feature_hdbscan.py`、`scripts/corner_case_detection.py` | 脚本基线版本 |
| Batch-1 | `2026-04-03 20:42` | 特征提取 | `tables/scene_features.csv` | 当前目录内主特征表 |
| Batch-2 | `2026-04-03 21:00` | 聚类与可视化 | `tables/scene_features_umap_hdbscan.csv`、`pictures/Figure_1.png` | 当前目录内主聚类结果 |
| Batch-3 | `2026-04-03 21:18` | corner case 评分 | `tables/scene_features_with_corner_score.csv` | 当前目录内主评分结果 |
| Batch-4 | `2026-04-03 21:55 ~ 22:05` | 聚类解释和 Top20 人工分析 | `tables/cluster_semantic_labels_enhanced.xlsx`、`top20_corner_cases_analysis.xlsx` | 结果解读层文件 |
| Batch-5 | `2026-04-03 22:20` | 特征脚本修改 | `scripts/scene_feature_hdbscan.py` | 脚本更新时间晚于 Batch-1 输出，说明脚本和结果未必完全对应 |
| Batch-6 | `2026-04-09` | 文档整理 | `README.md`、`logs.md` | 当前整理批次 |

## 5. 关键口径和识别规则

### 5.1 `scene_id` 的含义

`top20_corner_cases_analysis.xlsx` 里的 `scene_id` 不是 nuScenes 的 `scene-0687` 这种场景名，而是当前结果表的零基行号。

例子：

- `scene_id = 687`
- 对应的是 `tables/scene_features_with_corner_score.csv` 排序前的第 `688` 行
- 不是直接等于 `scene-0687`

后续如果要把本目录结果严格回连到 nuScenes 原始场景，建议在 `scripts/scene_feature_hdbscan.py` 中补充：

- `scene_token`
- `scene_name`

否则结果表只能按行号回溯，不能稳定映射回具体原始场景。

### 5.2 当前结果与脚本的一致性

当前目录存在一个明确的可重复性风险：

- `scripts/scene_feature_hdbscan.py` 的修改时间晚于 `tables/scene_features.csv`
- 说明当前脚本内容和当前结果文件未必完全对应

这不影响你继续分析现有结果，但如果后续要严格挂到 GitHub 并追求可复现，建议重新跑一次完整链路，并把输出和脚本版本锁定在同一批次。

## 6. 当前已知问题

### 6.1 场景标识缺失

本目录内的 3 个主 CSV 都没有：

- `scene_token`
- `scene_name`

这导致：

- 结果表无法直接关联 nuScenes 原始场景
- 回看脚本不能直接用本目录结果按 `cluster` 回连原始场景

### 6.2 `scripts/grid_search.py` 缺少当前批次结果

当前目录内没有：

- `tables/umap_hdbscan_grid_search.csv`

所以当前 README 只能把 `scripts/grid_search.py` 标为试验脚本，不能把它视为这批主结果的可追溯证据。

### 6.3 OpenCV 无 GUI

当前环境的 OpenCV 为：

- `GUI: NONE`

所以：

- 不能使用 `cv2.namedWindow()` 弹窗播放
- `scripts/review_nuscenes_scenes.py` 只能优先尝试播放，失败后导出 GIF

### 6.4 局部相机文件缺失

个别场景的相机图片在本地缺失，例如某些 `CAM_FRONT` 文件不存在，会导致 GIF 导出失败。

这是本地数据完整性问题，不是脚本逻辑问题。

## 7. GitHub 整理建议

当前不做移动文件，只先建立文档和日志。后续如果要正式挂 GitHub，建议至少做以下 4 件事：

1. 重新跑完整链路，并让脚本和输出时间一致。
2. 在特征表中加入 `scene_token` 和 `scene_name`。
3. 把 `scripts/grid_search.py` 的输出留在本目录内。
4. 把 `tempCodeRunnerFile.py` 和 `__pycache__/` 加入 `.gitignore`。
