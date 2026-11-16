# 第一天实验链路推进

作者已选择先修关键误判再跑全量，原版本选择等待解除。新增候选修复进展见critical_errors_v8_20261115.md；当前只完成目标连续片段组件及五条实际开发轨迹核对，尚未接通全链路。

日期：2026-11-15，提前开始11月16日排期。目标：真实数据提取至聚类、评分和评价预测的可运行链路；本记录为阶段进展，尚未完成第一天全部目标。

## 本轮实际结果

- 主环境绝对路径：D:/Python/Conda/envs/autodrive-cluster/python.exe。
- 单线程设置OMP_NUM_THREADS、OPENBLAS_NUM_THREADS、MKL_NUM_THREADS、NUMBA_NUM_THREADS均为1，MKL_THREADING_LAYER=SEQUENTIAL，PYTHONDONTWRITEBYTECODE=1。
- 100行12维make_blobs合成数据，random_state=42、3中心；UMAP使用15邻居、min_dist=0、10维、cosine、random_state=42、n_jobs=1、low_memory=True。原生导入11.83秒，UMAP完成累计16.22秒，HDBSCAN及两行transform/approximate_predict累计18.85秒。进程6623退出0。没有保存此探针模型。
- 进一步使用仓库实际smoke_frozen_pipeline.py：105行合成训练、3行合成查询，通过真实聚类入口、模型保存/加载、冻结评分、开发预测CLI；批次与逐行结果一致，重新加载后结果一致。进程75124退出0。
- 结果位于logs/SYN_day1_pipeline_20261115/smoke_result.json。使用开发身份做成员检查，但数值全部合成，未读取真实场景语义，不能作为论文效果。
- F盘当时可用375180460032字节。实际700条耗时及NuScenes全量加载内存尚未测量。

可复现命令（输出目录必须新建，已有结果不覆盖）：

    $env:OMP_NUM_THREADS='1'
    $env:OPENBLAS_NUM_THREADS='1'
    $env:MKL_NUM_THREADS='1'
    $env:MKL_THREADING_LAYER='SEQUENTIAL'
    $env:NUMBA_NUM_THREADS='1'
    $env:PYTHONDONTWRITEBYTECODE='1'
    & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -u HDBSCAN/tests/smoke_frozen_pipeline.py --output-dir logs/SYN_day1_pipeline_20261115

这次通过的范围是合成聚类/评分/开发预测，未覆盖真实特征提取和独立评价入口。出现sklearn参数弃用警告，没有运行错误。

## 当前具体阻塞

1. 普通scene_feature_hdbscan.py没有接入v6.1/v7。v5.2提取器要求显式场景名单、最多29条且绑定旧协议，不能简单扩大上限后冒充最新全量版本。
2. frozen_model.validate_prediction_input执行开发成员检查，predict_development只允许训练外开发成员。需要另版评价入口及严格身份/来源检查，不能把开发保护删掉来放行150条。
3. require_feature_provenance绑定提取器、特征规则、schema和质量审计源码。另版集成须同步设计其来源登记，保留历史摘要，不修改旧记录适配新代码。
4. 0669保护、隔离VRU、部分占道仍有语义问题。版本选择已向用户发出具体二选一：优先另版集成现有v6.1/v7并披露局限，或先修关键语义问题。回复前不代替决定。

## 下一步

续办核验：普通提取器以SCENE_CLUSTER_MAX_SCENES=3、SCENE_CLUSTER_FEATURE_OUTPUT=day1_preflight_only_20261115.csv运行--preflight，退出0，开发成员3条。未执行真实提取或生成CSV。已检查v5.2审计结构、v6/v6.1横向计算和v7完整31字段重算顺序，形成outputs/实验准备/第一天_实验接入方案_20261115.md。特别发现全量接入必须保留check_dependencies的避障锚点一致性约束，不能假设29条未发生依赖变化就代表700条也不会。版本问题仍待回复，未创建新生产模块。

命令：SCENE_CLUSTER_MAX_SCENES=3和SCENE_CLUSTER_FEATURE_OUTPUT=day1_preflight_only_20261115.csv为进程环境；D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 -u HDBSCAN/scripts/scene_feature_hdbscan.py --preflight。使用同一分割SHA 0d288dba6f8fc404ab592939de2a24052cd42042e7bd64b9da40298019c535fa。

准备新提取入口与现有纯函数之间的字段映射，确定逐目标台账与质量审计的最小接入范围。版本范围确定后实施新版本，先29条回归，再小批次真实提取；之后才测全量可行性。现有合成探针结果证明环境已能进行这些计算，仍不能担保700条完整链路。
