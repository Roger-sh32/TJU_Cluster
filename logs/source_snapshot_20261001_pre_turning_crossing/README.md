# 转弯横向投影修正前的真实源码快照

创建日期：2026-10-01，修改转弯过滤前。这里只存实际源码副本和冻结划分，不是新的结果批次，也不是当前开发入口。

与本快照匹配的历史提取：`HDBSCAN/tables/scene_features_development_audit700_20260927.csv`、本轮未修改规则的七条 `scene_features_semantic_feedback7_20261001.csv`。七条的所有 129 列与历史 700 条对应行精确相同。核验配方为根目录 `logs/verify_semantic_feedback7_20261001.py`，检查两个提取 manifest 内的 script、schema、rules、audit 及冻结划分哈希；没有修改历史 manifest。

真实内容：`HDBSCAN/scripts/` 中七个提取、规则、评分、特征选择、划分、审计和冻结模型模块；`HDBSCAN/tables/` 中冻结划分 CSV 及其 manifest。未生成 `_manifest.json`，不应引用不存在的文件。

9 月 30 日参数实验使用上述历史 700 条，其数值是修正前的结果。当前代码不得直接接受这些历史提取为新来源，也不得刷新其 manifest 绕过保护。本快照不包含旧参数运行入口或新模型。

历史提取来源可以在根目录使用匹配模块核验，不加载 pickle、不重拟合：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -c "import sys,pandas as pd; sys.path.insert(0,'logs/source_snapshot_20261001_pre_turning_crossing/HDBSCAN/scripts'); from frozen_model import require_feature_provenance; p='HDBSCAN/tables/scene_features_development_audit700_20260927.csv'; require_feature_provenance(p,pd.read_csv(p,float_precision='round_trip')); print('historical extraction provenance ok')"
```

更早的 9 月 27 日旧模型使用 `logs/source_snapshot_20260927_pre_audit/`，不是本快照。不要覆盖回当前源码，不在快照目录提取数据，不编辑冻结成员。
