# 第三至六章连续阅读版

日期：2026-10-27，Asia/Shanghai。继续推进论文交付，需要作者审定、学校格式、场景语义或正式实验选择的仍暂挂。
上一轮已完成Git推送并实测远端main与本地454d30e一致，属于实际进展；本轮不重复推送或宣称科研收尾。

## 设计与实施计划

目标是把四份已登记章节变成一份可连续阅读、可逐字回查的Markdown，不修改原章节或来源。
文档运行时预检查：捆绑Python3.12.14具备python-docx，但没有soffice.exe，且捆绑native目录没有LibreOffice。
因此尚不能按文档技能进行DOCX逐页渲染，不生成/交付未验收的Word，也不安装或调用未获批准的替代渲染器。
没有运行DOCX authoring marker或创建空DOCX项目。学校Word格式继续暂挂，不由本轮替作者决定。

方案采用最小封装而非重写：保留3/4/5/6章所有原文字节、公式、表格、日期与内部来源编号，
只新增阅读指引/章节边界/导航。各章内部S/C/D/E/F/P编号不跨章合并；各章原有待审文字保持历史状态，
不将连续版当作日期一致的新方法版本。新的输出索引只绑定4对原稿/原索引、新配方/测试和连续版，不刷新旧摘要。

采用writing-plans/TDD的内联流程；纯封装模块不改生产链。按项目约定计划与执行记录合并放logs，
不额外建立通用技能目录、空文件或新Git分支。此轮新增内容不自动提交或推送。

- [x] 新增6项隔离SYN测试：原始字节/顺序、输入摘要先于解析、原索引正文绑定、拒绝覆盖、原摘要必需、输出篡改拒绝。
- [x] 新增仅标准库的配方，先核对4对ORIGINAL摘要，再生成阅读版；失败不改源文件。
- [x] 独立窄审，检查字节保持、身份编号边界与不覆盖约束，不代替学术/作者审定。
- [x] 只构建一次真实连续版，记录原摘要、命令与结果；以后只能带原摘要check-only。
- [x] 运行交付检查、更新导航；不提取、拟合、评分、评价或导出场景媒体。

接口：load_chapters(root, specs)返回4个已核验章稿；render_reader(chapters)返回字节；
build(root,specs)只用独占创建；check(root,expected_manifest_sha,specs)先检查调用方给出的ORIGINAL索引摘要。
测试fixture全部标明SYN，放专用隔离目录，不使用真实场景或修改旧封印内容。

## 实现与实际检查

6项测试先因尚无配方而全部失败（预期RED）。增加配方后，最初使用Conda tempfile.TemporaryDirectory导致
系统临时目录子目录创建与清理WinError5；6项用例合计12个ERROR，不是正文或封装逻辑失败。
对照仓库现有workspace_tempdir后，新测试改为logs/SYN_chapter_reader_UUID，并在递归清理前核对resolved父目录与前缀。
没有改已有目录ACL、清理其他任务目录或提升权限；此前系统临时目录清理失败不冒充已清理。
接着一项输出篡改用例因异常文本Reader/reader大小写不匹配失败；修正用例模式后，6项实际全部通过。
工作区新SYN目录均由带边界检查的清理逻辑移除。以上修订均在真实输出首次构建前，旧文件未动。

四对真实输入预检查已通过，仅在内存拼接预览，不写输出：原章稿合计83818字节，
预览阅读版86376字节，SHA256 b7065d0187a2fec43657e8a3124ec2af4c729dc911e5a3c04ef501d909c5fe8f。
这个预览摘要不是已落地/登记的索引摘要，不据此宣称真实阅读版已构建。

独立只读审查已交给01a17d25-43ad-7751-b4fb-63cc69b888cc，范围为新配方/测试/计划，
不审整仓此前798文件提交，不运行真实构建或实验，未返回前保持待审。

## 交付测试命令

绝对解释器为D:/Python/Conda/envs/autodrive-cluster/python.exe，Python3.9.23。
只对子进程设置OMP_NUM_THREADS/OPENBLAS_NUM_THREADS/MKL_NUM_THREADS/NUMBA_NUM_THREADS=1，
MKL_THREADING_LAYER=SEQUENTIAL、PYTHONDONTWRITEBYTECODE=1，不修改全局环境。

    python -X utf8 -m unittest logs.test_chapter_reader_20261027 -v

上述限定6项测试退出0。随后按以下Python入口收集主线330项、KMeans5项、近期23项与新增6项，合计364项，
已实际全部通过（5.862s，exit0），输出保存logs/chapter_reader_tests_20261027.log。
日志仍包含sklearn force_all_finite改名FutureWarning，不改旧源码/环境消除它，也不将测试等同真实实验验收。
模型相关既有单测只使用小型SYN矩阵/临时文件；没有nuScenes提取、正式模型/排名/评价或场景媒体导出。

    from pathlib import Path
    import unittest
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for folder in ['HDBSCAN/tests', 'Kmeans/tests']:
        for path in sorted(Path(folder).glob('test_*.py')):
            suite.addTests(loader.loadTestsFromName('.'.join(path.with_suffix('').parts)))
    for name in ['logs.test_collect_human_evidence_20261024', 'logs.test_analyze_human_candidates_20261024', 'logs.test_hdbscan_semantics_20261024', 'logs.test_verify_scoring_chapter_20261024', 'logs.test_chapter_reader_20261027']:
        suite.addTests(loader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(not result.wasSuccessful())

## 独立窄审返回

审查者已完成，只对新配方、测试与计划返回“未发现可复现P1/P2”，不扩大为原四章学术验收。
其重新运行6项SYN测试，核对4对原稿/原索引及同目录链接，并静态检查字节拼接、独占创建、原摘要门槛与实现绑定。
未做真实build/check-only、并发/中断写入全分支或递归父sources重审，也未审此前798项Git检查点。
一项P3指向旧计划的“系统临时目录”表述；主代理在审查并行期间已将第28行改为“专用隔离目录”，
并补记Windows ACL失败与工作区清理边界。返回后实际rg确认该句已同步，没有改配方/测试来掩盖问题。
审查者自报文件摘要不变仅限其观察窗口，不代表本轮可追加的过程日志从未更新。
工具代理现已关闭，没有第二轮审查、后台构建或自动推送。

## 实际单次构建与ORIGINAL索引

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -u logs/build_chapter_reader_20261027.py --build
```

实际退出0，四章83818字节原文保留在86376字节阅读版中；额外文字只为阅读指引、章节边界和导航。
正文ORIGINAL SHA256：

    b7065d0187a2fec43657e8a3124ec2af4c729dc911e5a3c04ef501d909c5fe8f

来源索引ORIGINAL SHA256：

    cfe3914849976d081c53af7e7d4d61dd1f4977a62d0d8a026bc74afc9b7c33c0

来源索引绑定4对原稿/原索引及2项新配方/测试，保留所有旧摘要，不替换原稿。
此后保留阅读版/索引/新配方/测试，不能复跑真实build或刷新摘要来适配修改；如需修订另起版本。
单元测试的独立SYN fixture与以下check-only允许使用，不扩大到真实重提取/科研实验。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -u logs/build_chapter_reader_20261027.py --check-only --expected-manifest-sha cfe3914849976d081c53af7e7d4d61dd1f4977a62d0d8a026bc74afc9b7c33c0
```

实际退出0。四章原字节、输入/实现绑定和完整重拼接一致；同目录53处本地文件链接与4个章节锚点目标均存在。
这些是完整性/导航检查，不是所有公式视觉渲染、语义、学校排版或正式成绩证明。
当前无受验收DOCX，仅交付Markdown阅读版，不将缺少渲染器说成已解决。
本轮新增未提交/推送，先前454d30e远端同步状态不被本地新文件自动升级。
整体目标仍未完成，需要作者/专家/正式方法决定的事项继续暂挂。
