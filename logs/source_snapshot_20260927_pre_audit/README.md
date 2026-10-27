# 2026-09-27 审计改造前的代码快照

这是实际脚本的逐字节副本，不是第二套开发入口。创建于增加异常审计之前；所有旧模型 `manifest.json` 中列出的源码哈希均已核对。额外保留本次稳定性脚本和冻结划分副本，支持旧特征的来源核验。没有复制原始数据或模型大文件。

关联结果：根项目 `HDBSCAN/tables/scene_features_development_20260926.csv`、`scene_features_development_20260927_umap_hdbscan.model/` 和 `seed_stability_20260927/`。模型仍在原位置，本目录不包含另一份训练结果。

不要把快照覆盖回当前代码，也不要删除版本校验。旧特征/模型与新版审计源码不同，应在原环境用快照模块读取；新版提取产物则走当前入口。以下命令已在根目录验证通过，未绕过任何哈希、运行时或划分检查：

```powershell
& D:/Python/Conda/envs/autodrive-umap-smoke/python.exe -c "import sys; sys.path.insert(0,'logs/source_snapshot_20260927_pre_audit/HDBSCAN/scripts'); from frozen_model import load_model; b=load_model('HDBSCAN/tables/scene_features_development_20260927_umap_hdbscan.model',trusted=True); print(len(b['manifest']['scene_tokens']))"
```

原稳定性实验可通过本目录的 `HDBSCAN/scripts/seed_stability.py` 重跑：输入仍指向根项目中的原特征与聚类表，输出必须换新目录。冻结清单副本只用于验证成员；不能改它来选择评价场景。

快照不是独立完整数据项目，不能直接在此重提场景。需要复现原提取时，须在独立工作区恢复相同目录布局及原始只读数据路径，不在当前工作区回滚。
