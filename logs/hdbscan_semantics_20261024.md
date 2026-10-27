# HDBSCAN原理、软件量与项目用法核验

任务日期2026-10-24，沿用“持续按计划推进，人工/设计决定暂挂”。
上一目标轮产生了真实行人补证与原因对照，分类为progress，不重复运行其采集/分析。
本轮选择暂挂清单允许的原文细节与来源核验，不越过新特征、正式实验或评价批准。

## 设计和范围

只核对R04/R05/R06既有理论/软件引用与本地0.8.39实现的关系，不新增论文结果。
保存真正取得的原始来源；失败/受限页面单列，不能用搜索摘要宣称读到全文。
官方最新文档只用于概念，具体API算法以0.8.39发布源码与本地实际调用为准。
如做SYN树算例，仅调用合成数组/树的底层函数，不调用estimator.fit，不载入模型，不读场景/评价数据。
不改生产代码、参数、权重、旧写作/封印、环境或已有行人证据。
备选是立即写新版方法章，因全文/算法证据尚未核实且作者审定暂挂，本轮不采用。

> For agentic workers: use superpowers:executing-plans inline; new code uses TDD and one final independent review.

## 计划

- [x] 读取官方/作者来源，保存实际响应与0.8.39官方源包摘要，验证内容而不靠HTTP200猜全文。
- [x] 核对互达距离、稳定性、成员强度/GLOSH实现；必要时先测试再做SYN底层函数验证。
- [x] 形成knowledge/wiki中的版本限定公式/字段说明及来源/运行证据，不原地改旧正文。
- [x] 独立窄审、原始摘要/输出/旧来源校验，更新导航与CHANGLOG；设计决定仍暂挂。

## 已观察的访问情况

JCU官方记录明确Published Version仅限库工作人员，没有可用公开全文。
CORE全文链接在浏览工具返回403，不能当作论文已读。
USP记录浏览工具超时；另查作者机构目录，不绕过访问控制。
第一次Conda urllib在创建默认TLS上下文时读取Windows证书库报ASN1 NOT_ENOUGH_DATA，尚未收到HTTP响应。
改用certifi提供的CA文件创建启用证书/主机名校验的独立TLS上下文后，PyPI0.8.39元数据读取成功。
这只是当前请求的显式CA路径，不关闭验证、不改证书库/全局环境或重装包。
PyPI源包5771399字节，登记SHA256为2aa1351f42fa79efdc47d53695381aa9a2efef6d1855b96c42d030646fee74f7。

## 来源取得与失败记录

PowerShell7.6.5的Invoke-WebRequest在下载PyPI元数据时也报Authentication failed，未收到可用HTTP响应。
因此改用上面已验证的Python显式certifi上下文；没有关闭证书校验，也没有更改Conda/证书库。
创建的新目录随即填入真实文件，没有用空说明冒充PDF或源码。

实际请求逐项URL/时间/状态/Content-Type/字节摘要及五个精确归档member记录在：

    logs/hdbscan_source_retrieval_20261024.json
    ORIGINAL SHA256 a4dee09003a19499b4b119937ba8f10844e2b8ece701bef389a021404c6359c0

PyPI版本JSON和源包返回200且摘要/长度一致；源包5771399字节。
官方算法网页/离群网页/JCU记录在浏览工具可读，但主机抓取各返回403（原响应17字节），不能冒充HTML成功下载。
CORE返回403（5426字节），原响应以.response保存而不是.pdf；USP实际请求未收到成功响应。
作者旧目录重定向到机构首页、另一目录是JS空壳，本轮没有当作理论全文。
所有失败都不影响保存已经取得的官方源码，但R04/R05全文核验未完成。

原始抓取命令为PowerShell here-string送入以下解释器：

    & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -u -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'fetch_hdbscan_sources_20261024','exec'))"

抓取使用urllib.request.urlopen(url, context=ssl.create_default_context(cafile=certifi.where()), timeout=15或20)，
先下载 https://pypi.org/pypi/hdbscan/0.8.39/json，再按其sdist URL下载；对照PyPI原摘要/长度后，
仅用tarfile.extractfile读取LICENSE、hdbscan_.py、prediction.py、_hdbscan_tree.pyx、_hdbscan_reachability.pyx，
不使用extractall、不执行下载源码。每个真实响应均xb排他保存；摘要已完成后不重复抓取或覆盖。

本地hdbscan_.py SHA81511870830f5e6207f877ea7d535435675fe488f265355a4cd309c7335cc41a、
prediction.py SHAa3775742fcd42ac696e4b55f78997de88e5e3540892274105f97f2cda863376e，
与官方源包相同成员逐字节一致。未比较官方wheel编译二进制，不声称完整构建同一。

现有McInnes_2017_HDBSCAN_JOSS.pdf共2页；用bundled runtime的pypdf提取，pypdfium2以1.5倍渲染两页，
逐页实际查看（第一页面软件摘要/图；第二页面树图/参考文献）。
两张PNG在logs/hdbscan_semantics_pdf_20261024，原PDF未修改。没有把论文图中0.06s当本地性能结果。

## SYN实现与测试

新增logs/hdbscan_semantics_20261024.py及test_hdbscan_semantics_20261024.py。
4项测试先因缺少实现失败，随后通过：手算稳定性、原摘要错误拒绝、原生SYN反例/EOM-leaf、AST无fit/场景加载调用。
SYN只含3×3矩阵、5点树、7点树，数值手工指定；没有从nuScenes提取样本或拟合HDBSCAN estimator。
源码中get_probabilities为私有cdef，不能直接导入；通过公开get_clusters间接覆盖其返回成员量。
不会从这三个算例推广为全库正确性、MST/Boruvka路径、原文理论或近似预测验收。

    $env:OMP_NUM_THREADS='1'
    $env:OPENBLAS_NUM_THREADS='1'
    $env:MKL_NUM_THREADS='1'
    $env:MKL_THREADING_LAYER='SEQUENTIAL'
    & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest logs.test_hdbscan_semantics_20261024 -v

以上环境变量只属于本轮工具子进程，不写永久环境配置。
另运行source_bindings只读预检查，核对源包/来源、本地源文件和生产/旧稿/行人索引，不做原生计算。
独立代码/数学说明窄审未发现可复现P1/P2；4项合成测试、源包成员/本地wrapper逐字节对照及摘要先验拒绝通过。
该审查时尚无最终运行索引，不写成审查者已经验收真实产出/原摘要闭环，更不作正式方法验收。

## 最终SYN运行与交付

    & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -u logs/hdbscan_semantics_20261024.py --run

只创建一次SYN证据，退出0。完成主机UTC为2026-10-24T03:35:26.410340+00:00。
25秒上限的自建worker正常退出0，stderr为空；只跑矩阵/树底层函数，无estimator.fit/模型载入或场景数据。
运行版本：Python3.9.23，hdbscan0.8.39，numpy1.26.4，scipy1.13.1，scikit-learn1.6.1。
进程内OMP/OPENBLAS/MKL/NUMEXPR/NUMBA线程均1、MKL_THREADING_LAYER=SEQUENTIAL，未写全局配置。

SYN-NOISE的labels=[0,0,1,1,-1]，
membership=[0.5,1,1,1,0]，outlier=[0.5,0,0,0,0.5]。
最后一个合成点是噪声，成员强度0而1-O=0.5，反驳总互补关系；不是现实场景危险概率。
原稳定性为{5:4.5,6:4,7:2}，与手算一致。
SYN-EOM-LEAF的原稳定性{7:7,8:20,9:2,10:6,11:6}，
EOM标签[0,0,0,0,0,1,1]，leaf标签[-1,1,1,2,2,0,0]；不由此选择正式切树配置。
两个案例的所有outlier不一定都非零：嵌套树本次实际全0，原样保存，没有“修到想要的反例”。

logs/hdbscan_synthetic_semantics_20261024.json绑定31项输入/1项wiki输出。
ORIGINAL SHA256：

    4b1e6f12cc3505fd368813670d90e02f4fa7ed68daedb3c52a16f080bb8505d3

绑定的新配方/测试/wiki、来源和输出不原地改写，不重复--run或刷新原摘要。
允许重做单元测试或下列只读检查；新的算例/解释/版本须另起文件，不覆盖本次证据。

    & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -u logs/hdbscan_semantics_20261024.py --check-only --expected-sha 4b1e6f12cc3505fd368813670d90e02f4fa7ed68daedb3c52a16f080bb8505d3

该check-only成功退出0，仅核对源/输出字节与状态，不重算。
另对原行人补证报告9035ce0e…和原因对照5a457c29…做原摘要check-only，两者均通过；
生产聚类/评分/frozen_model源码和旧方法稿也在本次绑定校验中保持原摘要。

### 仍未完成

R04/R05全文逐式核验、任意树/零或无穷分母、完整自动MST/Boruvka路径、近似预测API和编译构建等同性均未被本轮证明。
原稿没有原地更新，未来可基于新wiki另版写作，但不能据SYN/源码核验批准正式特征、参数、实验或评价。
原目标未完成，人工/设计事项继续暂挂；本轮仅减少方法证据缺口，不改写全目标的完成条件。

## 最后验证

将既有11项行人补证、4项原因对照与本轮4项SYN测试合并执行，19项全部通过。
没有将此结果扩写为旧HDBSCAN全套330测试或完整数据流程通过。

    & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -m unittest logs.test_collect_human_evidence_20261024 logs.test_analyze_human_candidates_20261024 logs.test_hdbscan_semantics_20261024 -v

同进程线程配置如上，SYN原摘要check-only随后再次通过。
新来源/说明/过程相关本地链接已检查存在；不代表整个仓库/外部网页链接全覆盖。
更新的只是当前入口与CHANGLOG；已绑定wiki/配方/测试/输出均未在封印后重写。
