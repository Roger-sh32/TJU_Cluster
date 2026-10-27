# Git交付记录

日期：2026-10-27，按用户时区Asia/Shanghai记录。用户明确请求“推送下git”。
本轮只整理提交和推送，不继续此前尚未开始的Word合稿工作，不启动nuScenes实验。

## 初始状态

- 当前分支main，HEAD与origin/main均为0a92540a4545fbe878ec818618856aa42d88af24。
- 原暂存区为空；21个已修改文件，780个未跟踪文件约98.3MB，属于此前项目开发和证据积累。
- 远端为https://github.com/Roger-sh32/TJU_Cluster.git。
- 默认Windows schannel探测失败，错误SEC_E_NO_CREDENTIALS；单命令使用http.sslBackend=openssl后ls-remote成功。
- 不关闭TLS证书检查，不改全局Git连接配置，不强制推送、不变基或改写历史。

## 提交范围

提交已有代码/测试、入口与知识文档、论文事实稿、派生CSV/JSON、过程与验证日志。
不提交nuScenes原始数据集、exports临时媒体、Conda环境和模型pickle。
本次新出现的两个第三方PDF、hdbscan源码压缩包和五张原文渲染QA图片仅保留本地，不扩大原始资料二进制发布范围；
它们的来源/摘要记录可以提交，但这不代表这些本地原件已经上传或克隆后所有证据文件齐备。
不删除它们，不修改任何旧来源摘要来掩盖未上传文件。

预检查对790个变更/未跟踪文本文件做固定模式扫描，未命中私钥、GitHub/AWS令牌、Bearer、签名URL或URL密码模式。
这只是限定静态筛查，不是任意秘密检测保证；结果不记录潜在凭据原文。

## 换行保护

现有.gitattributes要求文本LF，core.autocrlf也为true；当前部分绑定文件实际为CRLF。
直接添加会改变Git blob字节并破坏原证据摘要。为满足既有不可刷新摘要约束，
在.gitattributes末尾以* -text !eol覆盖归一化，不改既有文件内容或全局配置。
既有二进制diff/merge属性保留；随后将逐一对比暂存blob与本地字节，不能仅凭设置猜测成功。
.gitignore新增*.pkl，模型manifest仍可保留，实际估计器载荷不上传。

## 计划与验证边界

- [x] 核对分支/远端、暂存区和敏感信息/大小，恢复经TLS验证的连接。
- [x] 增加字节保留和模型忽略保护，不动冻结代码/结果。
- [x] 运行HDBSCAN、KMeans单元测试及近期限定证据测试；模型单测只使用40行合成矩阵和临时文件，不是真实场景拟合。
- [x] 核对第三至六章原索引/正文和直接来源；不刷新原摘要。
- [x] 选择性暂存，排除上述本地二进制；逐项核对暂存blob字节和文件范围。
- [ ] 提交并正常推送main；以远端实际SHA确认成功。

整体研究目标仍未完成，Git同步不批准正式特征/参数、模型/排名、专家评价或学校格式。

## 实际测试与来源核对

以下在D:/Python/Conda/envs/autodrive-cluster/python.exe下执行，Python3.9.23。
仅子进程设置OMP/OPENBLAS/MKL/NUMBA线程1、MKL_THREADING_LAYER=SEQUENTIAL和PYTHONDONTWRITEBYTECODE=1，未改永久环境。

    python -X utf8 -m unittest discover -s HDBSCAN/tests -p 'test_*.py' -v
    python -X utf8 -m unittest discover -s Kmeans/tests -p 'test_*.py' -v
    python -X utf8 -m unittest logs.test_collect_human_evidence_20261024 logs.test_analyze_human_candidates_20261024 logs.test_hdbscan_semantics_20261024 logs.test_verify_scoring_chapter_20261024 -v

实际完整命令均使用上述绝对解释器，输出由Tee-Object分别保存至同目录git_delivery_hdbscan_tests_20261027.log、
git_delivery_kmeans_tests_20261027.log、git_delivery_evidence_tests_20261027.log。
330/5/23项全部通过，三个命令退出0。HDBSCAN日志有sklearn force_all_finite改名的FutureWarning，
不是测试失败，也没有为消除此兼容提示修改被冻结源码/环境。

四份论文原索引先核对固定ORIGINAL SHA，再只读递归检查其path/sha256记录，全部匹配：
第三章c3409b17…、第四章1a940aec…、第五章8c1ec7a2…、第六章4e14e158…。
这是摘要保持核对，不是重新做章节语义验收，也不重新登记索引。

普通git diff --check将原有CRLF的CR报告为行尾空白，退出1；没有修剪已绑定内容。
保留CR并以git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check核对，退出0。
这是对换行约定的显式检查，不关闭真正的行尾空格/空行等检查。

## 暂存区实际核对

普通权限git add因.git/index.lock写入权限被拒绝，退出128；未自行删除锁文件。
经受控提权仅写Git元数据后，选择性git add退出0。实际暂存798项，约87.3MB，最大单项14,839,364字节；
逐项按Git blob头加文件字节计算对象ID，与暂存OID全部一致，没有换行转换或内容差异。
未纳入nuScenes/、exports/、任何pickle、源码压缩包或logs里的渲染PNG。
其余8个未跟踪原件保留本地；不声称工作区完全无未跟踪内容。

暂存全量白空检查仍非零：30个文件共3347项，分布在保存的原始网页/源码/SDK文档、
两份进度控制台日志及四份已封印引文/写作材料，属于原始空白和末尾空行，未修剪。
本轮.gitattributes/.gitignore的定向检查退出0；不能把它或此前已跟踪差异检查写成全暂存区lint通过。
已知旧grid/KMeans来源保护及正式实验缺口仍按原文保留，本提交是可追溯开发检查点，不是生产发布或正式实验验收。

远端main在提交前再次核对仍是0a92540a4545fbe878ec818618856aa42d88af24，无需合并或强制推送。
计划提交消息：Checkpoint development evidence and thesis fact drafts。
本文件属于提交前证据，不预先填写未来提交SHA或推送成功；最后一项勾选保留为提交时状态。
实际提交/推送结果以本次会话返回的Git退出码及远端SHA为准，不为追写自指SHA再改写本提交。
