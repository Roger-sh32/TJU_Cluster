# 执行链路收尾审计

## 目的与范围

本轮回到实验主线，核对解释器、受控原生运行、候选拟合保护、全量整合、旧模型与评价入口。依据用户“需要我审核或者决策的先放一放”，不修改冻结实现或启动正式场景实验，新增发现与修复短方案先记录。上一轮标准审计已落地，属于实际进展，不是等待后台任务。

产出：[执行链路审计与恢复顺序](F:/Scene_cluster/outputs/实验准备/20261016/执行链路审计与恢复顺序.md)。本报告不能替代语义批准、正式参数/模型/排名冻结或真实独立评价。

## 实际检查及原始记录

1. `logs/runtime_preflight_20261016.json`：两环境各一次包元数据查询、一次64×64低秩合成dot与SciPy SVD，15秒子进程上限；全部exit0且未超时。faulthandler计划10秒退出仅用于运算探针。不是训练、降维、预测或场景提取，未验证普遍数值精度/真实规模性能。
2. `logs/entry_preflight_20261016.json`：主环境实际import nuScenes/UMAP/HDBSCAN/sklearn/cv2，exit0，GUI NONE；主聚类候选preflight exit1、错误为提取来源失配，25秒上限且未超时。原先没有显式保存主入口输入环境变量，后来补做第5项更强绑定，保留此原记录不改。
3. `logs/grid_guard_preflight_20261016.json`：同v7候选表的旧网格preflight，20秒上限，exit0，输出development29/52字段。仅预检查，未执行其后的标准化/UMAP/HDBSCAN拟合。
4. `logs/historical_model_metadata_audit_20261016.json`：只读旧模型manifest JSON及当前运行/源码版本，未调用inspect_model/load_model/pickle。主环境numpy/sklearn与旧模型不同，4个来源项不同或缺失。smoke环境两项版本相同仍不能修复来源失配。
5. `logs/entry_guard_pair_verified_20261016.json`：针对独立审核指出的日志绑定不足，重新做**仅preflight**的一对受控检查。显式清除子进程继承的SCENE_CLUSTER变量并设置同表输入/输出，保存CSV/manifest绝对路径及原摘要、阶段、源码摘要、实际env、PID、命令和退出码。两个入口精确指向同一candidate_feature_replay表，主入口拒绝1、旧网格放行0；原始表、manifest及脚本前后摘要相同，6个预定输出前后均不存在。没有拟合或覆写旧日志。

运行条件均由父进程创建的子进程环境设置：`OMP_NUM_THREADS/OPENBLAS_NUM_THREADS/MKL_NUM_THREADS/NUMBA_NUM_THREADS=1`、`MKL_THREADING_LAYER=SEQUENTIAL`；入口检查另设`PYTHONDONTWRITEBYTECODE=1`。没有改全局Conda环境或安装包，父进程不使用WindowsApps的默认Python。原始JSON保存命令数组与探针程序，运行时JSON还保存每次过程环境覆盖；同表成对JSON保存了完整SCENE_CLUSTER覆盖。

本次原生探针和CLI检查均已观察到子进程终止，未发生超时。`Get-CimInstance Win32_Process`被拒绝访问，不能据此判断整台机器没有其他Python工作进程；没有要求提权、停止用户进程或重启任何历史任务。

## 新发现与短方案暂挂

**P2：旧网格来源门控缺失。** `grid_search.py`只有开发成员/字段有限性和输出防覆写检查，在preflight后直接fit；不像主拟合入口、种子稳定性或受控参数稳定性入口那样先调用`require_feature_provenance`。静态源码和绑定同表preflight共同证实。它没有放开评价成员，也不导出合格冻结模型；不能说发生了评价泄漏、成功拟合或正式模型生成。

拟修复范围是bounded：在任何成功preflight/原生拟合前复用既有来源/质量检查，继续拒绝candidate阶段和过期/缺失来源，保持参数、评分与开发隔离不变，并做拒绝路径回归。根据当前协作要求，**短方案先暂挂，不实施，不生成已修复的假状态**。全量JSON检索因两个旧临时目录权限失败，不能声称所有冻结绑定已查无；实施前仍需核对实际受影响的协议，后续有绑定则另版本。

为防误用，文档现明确警示旧网格不得作为候选重跑入口。这个警示不是正式关闭/修改代码，也不授权马上执行另一个参数脚本。

**全量整合缺口。** AST/源码检查显示普通提取器与v5.2入口未调用v6.1/v7模块；v5.2有固定29/显式名单和轨迹sidecar约束。v7配方读取v6.1表/既有冻结轨迹，强制固定29结构。不能仅改环境变量/扩大上限就宣称得到最新同源700。正式版本批准后还需要有受控整合、限定回归及质量/来源登记工作。

**评价入口缺口。** `predict_development.py`固定开发身份并排除模型训练成员；不是独立评价150的入口。当前审阅的HDBSCAN脚本目录没有专用评价预测脚本，已有工具职责也不允许把guard改宽代替设计。基础统计模块有纯计算函数，但没有真实标签导入/正式评估执行入口；序数一致性/覆盖/等级排序仍未实现。

## 版本与默认入口

历史模型输入记录是`scene_features_development_20260926.csv`，不是审计版700或最新候选。其训练数700，因此同一模型没有未参与拟合的开发成员；这里不对评价语义作任何读取。旧模型应在匹配的历史源码/运行时回溯，不手改manifest或把重放表改成正式提取。

当前默认`scene_features_development.csv`及`scene_features_development_umap_hdbscan.csv`不存在。此为路径就绪问题，不能复制旧表到默认名字蒙混版本。本轮未创建这些默认文件，也未触发未配置的普通提取器执行。

`environment.yml`只是未锁全部版本的环境配置，不是此次运行指纹或历史模型可载入保证。运行记录按实际绝对解释器/包版本登记；OpenCV GUI NONE是当前包构建能力，不证明Python版本不支持绘图或依赖整体坏掉。

## 可重复的只读核验

原始JSON中的`command`和`env_overrides`记录实际执行，可用于理解步骤；不要把带`--preflight`的记录去掉该标志当成已批准实验。以下只检查落地证据及源摘要，不重新做原生运算、拟合或场景提取。

```powershell
@'
from pathlib import Path
import json,hashlib
root=Path('.')
runtime=json.loads(Path('logs/runtime_preflight_20261016.json').read_text(encoding='utf8'))
assert len(runtime['probes'])==4
assert all(r['returncode']==0 and not r['timed_out'] for r in runtime['probes'])
assert all('dot True' in r['stdout'] and 'svd True' in r['stdout'] for r in runtime['probes'] if r['probe']=='linear_algebra')
entry=json.loads(Path('logs/entry_preflight_20261016.json').read_text(encoding='utf8'))
assert entry['rows'][0]['returncode']==0 and 'imports_ok' in entry['rows'][0]['stdout']
assert 'NONE' in entry['rows'][0]['stdout']
pair=json.loads(Path('logs/entry_guard_pair_verified_20261016.json').read_text(encoding='utf8'))
a,b=pair['rows']; assert a['input_binding']==b['input_binding']
assert a['returncode']==1 and 'Feature extraction version/provenance mismatch' in a['stderr']
assert b['returncode']==0 and json.loads(b['stdout'])['preflight_only'] is True
assert all(not r['timed_out'] for r in pair['rows'])
assert a['env_overrides']['SCENE_CLUSTER_FEATURE_INPUT']==b['env_overrides']['SCENE_CLUSTER_FEATURE_INPUT']
assert a['input_binding']['stage']=='candidate_feature_replay'
for row in pair['rows']:
    for rec in [row['source'],row['input_binding']['features'],row['input_binding']['manifest']]:
        assert hashlib.sha256(Path(rec['path']).read_bytes()).hexdigest()==rec['sha256']
assert pair['outputs_absent'] and all(not Path(p).exists() for p in pair['output_paths'])
old=json.loads(Path('logs/historical_model_metadata_audit_20261016.json').read_text(encoding='utf8'))
assert hashlib.sha256(Path(old['model_manifest']).read_bytes()).hexdigest()==old['manifest_sha256']
assert old['historical_training_count']==700 and len(old['runtime_differences'])==2 and len(old['source_differences'])==4
print('VERIFIED recorded bounded runtime probes, exact paired guard gap and historical-model metadata; no new experiment')
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -c "import sys; exec(compile(sys.stdin.buffer.read().decode('utf8'),'audit_check','exec'))"
```

独立只读复核确认P2不是合法职责差异，并确认最新候选未接入全量链路；没有建议把runtime小矩阵通过扩大成完整UMAP通过。输入绑定缺口已由新的一对preflight补强，旧证据保留。

后续独立定向复核确认：新成对JSON已消除“同表依赖执行说明”的限界，记录摘要与当前输入/manifest/源码一致，六个探针输出当前均不存在；恢复报告未夸大完整UMAP恢复、同源700整合或保护已修复。保留较小证据限度：父进程执行时确有前后相等断言，但JSON只存一套摘要，没有分别存双份前/后快照，因此独立复核不能仅凭该JSON证明运行期间持续未变。未为消除这一表述限度重跑任何拟合或重复原生探针。

## 未完成与下一步

交付核对：19项输入/源码/原始日志摘要见[本次来源快照](F:/Scene_cluster/logs/execution_chain_audit_sources_20261016.json)，4115字节，SHA256 `0900518237ffa258c4e051a2fd47190e1582ccfb62098560039e1c4f210d3dea`。有限离线命令从本日志实际提取执行并exit0，19项长度/摘要与报告链接也通过。恢复报告9088字节，SHA256 `caa139000d77bc9fd44dbdfe9df3eddc430e28e4fb9def50ab1f3f8a43264716`；五份入口源码与原写作正文/索引原摘要不变。来源快照是本次审计记录，不是正式实验审批/全历史封印核验，不以改快照来消除失配。

报告把正式实验恢复拆为：语义收敛/版本批准 → 受控提取整合与来源保护 → 同源700和质量 → 参数/模型/排名冻结 → 专家校准与专用评价入口 → 正式比较和论文结果。不是全链路已可运行，也不是只剩点击“运行”。需要人工决定的先挂起，其余来源核对和只读工程审计可继续。

本轮没有新增科研拟合、真实评价、修改生产模块或运行完整测试套件；不沿用之前330测试通过来冒充本轮测试结果。未提交或推送Git。整体目标未完成。
