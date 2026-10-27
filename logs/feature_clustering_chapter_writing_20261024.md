# 第四章特征与聚类事实稿写作记录

日期：2026-10-24，用户时区Asia/Shanghai。依据持续目标“按计划推进，需要人工审核或者决策的先放一放”。

## 范围与依据

上一目标轮属于实际进展：第五章正文及索引已落地。本轮再次以ORIGINAL索引
8c1ec7a2b33d3061b41301a5cc7f72bf037516e92e230646a308efe6cf3f90a2执行其check-only，退出0；
不是仅复述状态，也没有复跑登记或实验。

当前第三、五、六章已有独立事实稿，第四章仍主要分散在20261015方法稿和早期骨架。
本轮只补齐独立中文MEM章稿、17项直接来源的JSON索引和本记录。沿用骨架4.1—4.5，
不改原骨架、方法稿、第三/五/六章或任何绑定源码/结果，不新增提取器、检查器、模型或媒体。
作者/学校审定及正式特征、参数、保护机制、评价设计继续暂挂。

采用nature-writing的方法类/方法章节/generic路线；项目中文要求优先于技能英文输出默认值。
这是从已有作者实现和记录整理方法事实，不代写未经作者提出的新科学主张。
采用writing-plans的范围/验证步骤，由本代理内联完成文档，末尾安排一次独立窄审。
纯文档任务不增造生产代码的红绿测试、Git分支、提交或额外工作区；按项目目录约定将计划和过程合于本文件。

## 短设计与段落图

一句话论点：本项目将帧级几何、地图与交互证据聚合为固定顺序的场景表示，
再由开发数据拟合的标准化、UMAP与HDBSCAN形成分组；现有实现及候选重放可被说明，
但最新同源700、正式参数和独立有效性尚不能写成完成。

主要读者为MEM导师/作者，先解释方法可复现性，效果结论留给正式实验。
术语固定：场景scene；帧sample；实例instance_token；标注annotation_token；
语义白名单CLUSTERING_FEATURES；成员强度cluster_probability；离群分数cluster_outlier_score；
观测路线是离线后续观测，不称在线预测真值。

方案：不重写已封印方法稿，也不合并重排全部章节；只新增独立第四章。
完整论文合稿/排版需要作者与学校要求，生产链整合需要正式候选决策，均不是本轮替代路径。

| 小节 | 段落任务 | 关键边界 |
| --- | --- | --- |
| 4.1场景统计特征 | 输入/坐标/速度/地图/字段释义 | 统计范围并非所有类别统一50m；无目标帧零值；地图设施非实时相位 |
| 4.2事件窗口化交互特征 | TTC/时长/身份/暴露与相关性/候选层次 | 帧占比非时间积分；场景OR可串接目标；未知和成功响应不抹除 |
| 4.3聚类特征白名单 | 52列接口与精确有序表 | helper兼容选择不等于拟合严格检查；并非与评分绝对独立或消融分组 |
| 4.4数据预处理与UMAP降维 | 原始质量/填充值/严格入口/冻结变换 | 旧填充仍存在；来源一致不保证语义；默认值不是正式选择 |
| 4.5 HDBSCAN聚类 | 参数/软件量/输出/冻结开发预测/剩余缺口 | SYN不覆盖自动算法/真实拟合；不宣称正式评价或700最新模型 |

## 实施与验收计划

- [x] 读取当前入口、暂挂清单、骨架及方法稿，确定不触碰正式选择的章稿范围。
- [x] 静态读取17项直接来源；不导入有顶层执行的提取脚本，不加载模型或场景。
- [x] 新增第四章，F01—F12主张旁绑定来源，保留4.1—4.5标题。
- [x] 用一次性只读命令核对52字段顺序/唯一性、AST默认值、来源和既有原摘要、链接与公式块。
- [x] 为最终正文登记独立JSON索引，摘要只记录本轮来源，不刷新旧索引。
- [x] 独立窄审事实/公式/版本/字段表，记录实际返回状态，不将代码审查当作语义或作者验收。
- [x] 更新当前导航与CHANGLOG，最终再核对正文/来源摘要。

验收重点：helper缺列兼容与拟合入口拒绝的差异；VRU仅行人；intersection_flag是密度阈值而非任一帧命中；
非有限值在提取末端已被替换；v6.1/v7只是固定29重放，不能把描述模块写成全量完成；
成员强度不等于危险概率，GLOSH不等于1减成员强度。

## 探索中的非成功步骤

最初来源扫描误猜logs/execution_chain_audit_20261016.json，文件不存在，命令退出1。
随后按实际目录定位entry_guard_pair_verified_20261016.json作为S15，不创建假文件或冒充已读取。
rg枚举logs时两个既有tmp目录拒绝访问；未提权或处理目录，不作全仓穷尽声明。
其余来源均按明确路径静态读取。

## 复现入口

旧第五章只读核验：

    & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -u logs/verify_scoring_chapter_20261024.py --check-only --expected-index-sha 8c1ec7a2b33d3061b41301a5cc7f72bf037516e92e230646a308efe6cf3f90a2

本轮新正文/索引的只读核对命令、实际结果和独立意见在后续补记；登记前不宣称封印或验收通过。

## 草稿阶段的实际机械核对

一次性只读Python标准库命令退出0：AST读取CLUSTERING_FEATURES，与正文52行的序号、唯一性、字段顺序完全一致；
F01—F12及S01—S17引用集合完整；4.1—4.5标题顺序及8个展示公式块配对通过。
AST读到的UMAP七项及HDBSCAN三项显式参数与正文参数表一致，未导入生产模块。
6项旧正文/原索引/骨架摘要与此前记录一致，正文20个已有本地链接存在；当时只缺尚待创建的新索引链接。
这不是12项科学主张的完整机器证明，也不是单元测试或330项HDBSCAN套件结果。

审阅前草稿30223字节，SHA256：

    712b59672d4f72d20b0645a07b6654b8ec0e303c739bf2476c14f47fec428151

此处只是未登记草稿指纹，若审查发现事实问题可在首次登记前修订；不修改任何旧封印文件。
独立只读审查已交给01a16e02-fc6e-7551-86fe-9c28f72d7eca，要求聚焦事实/公式/字段含义与版本边界，
不把来源、程序候选、SYN或开发重放升级为真实冲突/正式实验验收。意见未返回前保持待审。

本轮解释器实测为D:/Python/Conda/envs/autodrive-cluster/python.exe，Python3.9.23；
只读文件/AST检查不需要导入nuScenes、UMAP、HDBSCAN或读取原始场景，不重装或更改环境。

## 独立意见与首次登记前纠正

审查者返回一项P2：后续观测确认的文字遗漏“无地图时放行进入布尔条件”。
其检查了正文、相关S01—S17及部分保护上下文；未确认其他P1/P2，未列P3。
审阅对象仅为712b5967…未登记草稿，不是后来修订版本的独立清洁结论。

本代理复查S03的合流与行人两段：均先置enters_ego_lane = not map_available，
地图可用才尝试补充程序进入证据。S02两个纯判定函数只检查进入布尔量和6米/15米距离。
因此“仅靠近不能替代进入依据”必须限定有图条件，原草稿确有遗漏；不推断29/700实际受影响。
这是写作缺陷，不在本轮重新设计无图语义、修生产代码或改原特征。

修前一次性unittest先AST确认两处无图回退，再只提取两个纯布尔函数到隔离命名空间：
同为SYN距离5米，无图布尔True两次返回True、有图但未识别进入的布尔False两次返回False。
随后要求正文明确区分有图与无图，并要求两行字段释义标明回退。测试实际退出1，
失败于文稿缺少“无地图时退化为距离判定”，不是源码运行失败。
修订仅触及新稿4.2.3、字段18/30及F06边界；同一命令复跑退出0，1项测试通过。
没有导入生产模块或执行原提取脚本；这4个纯谓词SYN调用不代表真实场景复算。

首次登记前已纠正该P2；修后只做本代理定向检查，没有安排第二轮独立重读。
不能写成“最终封印稿独立窄审无P1/P2”。隔离纯函数只证明此布尔回退反例，不证明完整图查询路径。
新增索引如实记录原审指纹、1项P2、本代理纠正、未独立复读与未获作者/学校验收。
完成后的审查者已关闭，未生成日程或继续重试。

## ORIGINAL登记

2026-10-24 13:07:44 UTC为登记前读取时钟，对应用户时区晚间。
正文30705字节，ORIGINAL SHA256：

    58d0fad6e121b88ebe1f946dc4f7172cbfc1611d58ed9657f4e14dc15851c6df

索引ORIGINAL SHA256：

    1a940aec8ac73d7d84b2de2b0b5fcb9f23666ce3426617b903d953bf9b7d8e59

索引记录12个F主张/17项直接来源/5项额外旧稿完整性记录，固定字段表52行。
正文/索引及绑定来源从此保留，后续修订另起版本，不能用重算摘要使旧记录适配新文件。
本日志和导航可补记实际后续状态，不属于上述封印正文。

## 可复现的限定只读检查

此命令先用本日志中的ORIGINAL摘要验证索引，再解析它；不注册、刷新或生成任何输出。
它只检查列出的字节/结构/链接/AST/特定回退披露，不验证全部正文、原理或场景语义。
不要把本命令或索引作为实验授权。

```powershell
@'
from pathlib import Path
import ast, hashlib, json, re
index=Path('outputs/论文初稿/第四章_场景级特征构建与无监督聚类方法事实稿_20261024_证据索引.json')
expected='1a940aec8ac73d7d84b2de2b0b5fcb9f23666ce3426617b903d953bf9b7d8e59'
assert hashlib.sha256(index.read_bytes()).hexdigest()==expected,'Original index mismatch'
data=json.loads(index.read_text(encoding='utf8'))
assert data['stage']=='writing_only_feature_clustering_chapter'
assert len(data['sources'])==17 and len(data['facts'])==12
for record in [data['document'],*data['sources'].values(),*data['preservation_records']]:
    raw=Path(record['path']).read_bytes()
    assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256'],record['path']
body=Path(data['document']['path'])
text=body.read_text(encoding='utf8')
tree=ast.parse(Path(data['sources']['S01']['path']).read_text(encoding='utf8'))
fields=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CLUSTERING_FEATURES' for t in n.targets))
rows=re.findall(r'^\| (\d{2}) \| `([^`]+)` \|',text,re.M)
assert len(fields)==len(set(fields))==52
assert [int(i) for i,_ in rows]==list(range(1,53)) and [v for _,v in rows]==fields
assert {'F'+x for x in re.findall(r'【F(\d{2})】',text)}==set(data['facts'])
assert {'S'+x for x in re.findall(r'【S(\d{2})】',text)}==set(data['sources'])
assert all(ref in data['sources'] for refs in data['facts'].values() for ref in refs)
assert re.findall(r'^## (4\.[1-5]) ',text,re.M)==['4.1','4.2','4.3','4.4','4.5']
assert sum(line.strip()=='$$' for line in text.splitlines())==16
params={}
for node in ast.walk(ast.parse(Path(data['sources']['S07']['path']).read_text(encoding='utf8'))):
    if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='dict':
        for target in node.targets:
            if isinstance(target,ast.Name) and target.id in ('umap_params','hdb_params'):
                params[target.id]={k.arg:ast.literal_eval(k.value) for k in node.value.keywords}
assert params['umap_params']==dict(n_neighbors=15,min_dist=0.,n_components=10,metric='cosine',random_state=42,n_jobs=1,low_memory=True)
assert params['hdb_params']==dict(min_cluster_size=20,min_samples=1,prediction_data=True)
links=re.findall(r'\[[^\]]*\]\(([^)]+)\)',text)
assert all((body.parent/link.split('#')[0]).is_file() for link in links if '://' not in link)
assert '无地图时退化为距离判定' in text and text.count('无图回退为距离条件')==2
assert data['independent_review']['final_reviewer_reread'] is False
assert data['scope']['real_scoring_fit_ranking_or_evaluation'] is False
print('PASS: original body/index,17 sources,5 preservation records,52 ordered fields,12 facts,8 math blocks,2 AST parameter sets,21 local links; LIMITED DOCUMENT CHECK')
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'chapter4-final-check','exec'))"
```

本轮不运行全HDBSCAN测试套件或真实管线，不沿用旧330/23项结果冒充本轮全套通过。
正文范围检查与回退反例是限定文档检查，不能替代真实运行/效果核验。

## 交付核对

已从上方日志实际提取并执行完整只读Python块，退出0，结果为：

    PASS: original body/index,17 sources,5 preservation records,52 ordered fields,12 facts,8 math blocks,2 AST parameter sets,21 local links; LIMITED DOCUMENT CHECK

将该命令的expected索引摘要仅在内存中换为64个0，实际在解析索引前以Original index mismatch拒绝；
外层负向探针捕获此预期断言并退出0，没有改索引/正文或刷新摘要。
旧第五章固定ORIGINAL摘要check-only在本轮开始和交付时均退出0。
回退说明的1项定向unittest由RED转GREEN；其余为文档检查，不包装成23/330或全仓测试通过。

只改当前入口README、HDBSCAN/README、CHANGLOG和AGENTS导航/警示，新增正文、索引与本日志；
没有新增检查器脚本、修改生产模块或旧来源，也未提交/推送Git。
检索测试配置时明确指定的pyproject.toml/pytest.ini/setup.cfg不存在，rg因此退出1；
这不是测试执行失败，不据此推断仓库没有其他测试配置或测试框架。

本轮完成的是第四章方法事实整理，而非整体目标。正式特征设计、整合、700同源重建、模型/排名冻结、
专家/评价选择与作者/学校审定继续依原暂挂清单处理；不新增整场景人工审核请求。
