# TTC与前车目标筛选：限定范围诊断

日期：2026-10-15（北京时间）。状态：`diagnosed_next_design_pending_approval`。v6.1完成后，用户要求继续推进；本轮先只读核对0669及开发对照0011/0026/0042/0552，不实现新筛选或改变任何数值。不拟合、不访问评价语义、不下载或导出媒体。

## 结论

1. 0669不是缺值/计算失败：t=3.847秒，静止对向小车在转弯坐标系下落入自车前向走廊，算术精确复现TTC=3.363684秒。现有same_path不要求同向车道；目标静止时纵/横速度接近0，容易满足该判据。可行驶面只说明车在路面，不说明在自车将要通过的车道。
2. 原转弯伪影过滤还要求朝向差>=2.35rad（134.645度），本目标为129.503度，未被过滤。不能把角度阈值改到刚好命中0669，也不能把所有静止目标删掉。
3. 0026是关键保护对照：最低TTC=1.901035秒确实对应前方摩托车；目标瞬时速度0.034417m/s、整段最大速度1.302962m/s。其最低TTC发生在末帧，未来可用时长0秒。静止不等于无风险，未来不足也不能直接删TTC或改成安全。
4. 0669当前纵向风险分项已经是0，`min_ttc`本身不在52个聚类字段中。其静止前车/blocked_path比例约0.121951仍进入聚类。只修最低TTC数字既不能声称降低了本场景纵向风险，也不能解决同源静止/堵路误报。
5. 现有轨迹没有完整 `ttc_candidate_events` 台账。CSV仅保留全场最低有效事件；若删除该目标，不能直接把min_ttc填成30，必须重新选择剩余合法候选并更新持续时间/比例。当前代码先选最近前车、后做转弯过滤，可能已丢掉同帧其他合法候选；新门控应在最近目标选择之前应用，不能仅在最小值上补丁。

## 当前数值核对

以下是现有冻结v6.1数值及只读轨迹诊断，不是新提取结果或新的风险标签。TTC和事件相对时间不是同一个量。

| 场景 | 最低TTC/s | 发生时间/s | 目标/瞬时速度 | 重要边界 |
| --- | ---: | ---: | --- | --- |
| 0669 | 3.363684 | 3.847081 | 静止car，0m/s，实例03d6e4… | 前向22.805m/横向0.463m；朝向129.503度、局部转角0.692rad；未来实际括界完整，同期车身最近9.273m。路线/车道相关性待门控，纵向分项已0。 |
| 0026 | 1.901035 | 19.049457（末帧） | motorcycle，0.034417m/s，实例6834e1… | 朝向差4.113度，同向前方；未来0秒仍应保留TTC证据。当前纵向分项0.646716是程序评分，不等于危险概率或专家等级。 |
| 0011 | 4.880104 | 12.451010 | car，0.948007m/s，实例1e33e4… | 此最低目标是较慢行驶小车，不是初段被绕行的静止车；不能用它冒充静止障碍正例。原人工避障/VRU语境独立保护。 |
| 0042 | 30（填充值） | -1 | 无有效TTC目标 | 不是测得30秒，也不能据此否定人工观察到的两次静止车绕行。 |
| 0552 | 6.679788 | 12.397926 | rigid bus，0.041045m/s，实例810978… | 朝向-133.191度、局部转角0.496rad，未达旧角度过滤门槛；不是此前已保护的两条bendy bus程序语境实例。不能借已确认的公交让行替该TTC目标验收。 |

0669地图支持记录为on_surface=True、lane_distance=None、supported=True。None是未知，不是无车道/不占道。0552此TTC目标的诊断车道中心距离24.544m，但当前选中车道会受转弯与拓扑影响，该数不能单独证明目标无关。已观测未来路径还可能是成功避让之后的结果，不能把“绕开了”误作“原来不影响”。

## 下一轮短设计（待批准）

这是对现有前车筛选分支的限定修正，不增加新的模型或重新定义整套风险分：

- 新建独立候选，先补逐帧、逐目标TTC候选/选择/过滤原因台账，精确复现当前固定29条基线后才允许改变门控。仅核对当前最低值不算完整复现；实例、时间、最小值、有效比例及持续时间均需对齐。
- 将有证据的目标路线相关性门控放到最近前车选择之前，同一入口用于TTC与同源跟随/静止前车统计，避免TTC过滤了却仍把同辆对向车当堵路。过滤后重新选合法前车，不能直接将最低TTC填30或保留旧目标身份。
- 仅有明确路线/车道分离证据才过滤转弯时的对向静止目标；缺地图、缺未来或证据冲突记未知/保留，不按场景号硬编码，不单纯放宽角度或删静止车。真实前向静止障碍、成功避障和0026近乎静止的摩托车必须保护。
- 保持横向v6.1、VRU、几何裕度、TTC公式/截断范围、评分权重和52字段清单不动；限定重算受目标筛选直接影响的TTC/跟随/静止统计，明确字段白名单和依赖。必要时只补这29条的元数据诊断，不下载媒体，不重提全700、不拟合或用评价。
- 先失败测试，再冻结新源码/测试/输入/配方，跑同29条；任何基线无法精确复现或保护案例丢失应停下记录，不绕过旧封印。0067公交对应、0073边界稳健性仍保留为单独待审项。

需用户确认此短设计后才进入实现。原v6.1仍为候选，不因本次诊断自动推广。

## 来源、命令与核验

环境：`D:/Python/Conda/envs/autodrive-cluster/python.exe`。来源：

| 文件 | SHA256 |
| --- | --- |
| `HDBSCAN/tables/scene_features_crossing_v6_1_replay29_20261015.csv` | `081a0a13b5ee7e18a38d0e1fdf5e315a15913e65e883ebab36c92f1578f88147` |
| `HDBSCAN/tables/crossing_v5_2_regression29_trajectory_20261013.json` | `1b8723d72ed3de9f2d90fca91acf59d3716245f343bc5019326a99e972dbfc60` |
| `HDBSCAN/scripts/scene_feature_rules.py` | `6a21d3d56a08fe7ee60e9143dbb0aa1d3db02f573cfb4206eed17062c92e181d` |
| `HDBSCAN/scripts/crossing_candidate_v5_2.py` | `6392a09102de7bd735456be9243017c8bcb9355710cf19d3b28233729ab98242` |
| `HDBSCAN/scripts/corner_scoring.py` | `18c9f88e48087017e5615f0639f13503b54d64335264d94df209fcbc7bbec620` |

代码已读：`scene_feature_hdbscan_v5_2.py`的same_path/地图支持/最近前车/TTC聚合/轨迹导出分支，`scene_feature_rules.py`相关纯函数，`feature_selection.py`的52字段清单。0026人工语境来自 `logs/feature_optimization_2026-07-11.md` 的第五批反馈；0669及0552语境来自冻结十条反馈，不改原文。

原始v6.1来源/运行环境/输出与精确29重放检查退出0，未运行prepare/run：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/crossing_v6_1_replay_20261015.py check --expected-protocol-sha 51b6be617bb455bfd44a2d8bcf9010b73ee1d16bc7aa9f60963dacc9186c3209
```

控制台 `logs/ttc_scope_parent_check_20261015.log`。最低值算术和身份核对退出0，见 `logs/ttc_scope_diagnosis_v2_20261015.log`，以下为实际只读命令。第一版尝试把整行字段都转float，因地点字符串失败；原失败日志 `logs/ttc_scope_diagnosis_20261015.log`保留，修正为按冻结模块读取真实类型后完成核对。未改数据或生产代码，未重跑单元测试。

```powershell
@'
import csv,json,math,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from HDBSCAN.scripts import scene_feature_rules as r, crossing_candidate_v5_2 as g, corner_scoring as scoring
f=Path('HDBSCAN/tables/scene_features_crossing_v6_1_replay29_20261015.csv')
t=Path('HDBSCAN/tables/crossing_v5_2_regression29_trajectory_20261013.json')
for p in (f,t,Path(r.__file__),Path(g.__file__),Path(scoring.__file__)):
 print('SOURCE',str(p),'SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
audits={s['scene_name']:s for s in json.loads(t.read_text())}
frame=pd.read_csv(f,float_precision='round_trip'); scores=scoring.calculate_grouped_risk(frame)
scores['scene_name']=frame.scene_name; scores=scores.set_index('scene_name')
with f.open(encoding='utf-8-sig',newline='') as stream: rows=list(csv.DictReader(stream))
for row in rows:
 if row['scene_name'] not in ('scene-0669','scene-0026','scene-0011','scene-0552','scene-0042'):continue
 s=audits[row['scene_name']]; identity=row['min_ttc_target_instance_token']
 if identity=='none':
  print('MINIMUM',row['scene_name'],'no valid TTC,30 is fill, not measured30');continue
 times=np.array(s['times']); yaws=np.array(s['ego_yaws']); pos=np.array(s['ego_positions']); speed=np.array(s['ego_speeds'])
 k=int(np.argmin(abs(times-float(row['min_ttc_scene_time'])))); actor=next(x for x in s['vehicle_tracks'][identity] if x['index']==k)
 velocity=actor['velocity']; a=yaws[k]; vf=velocity[0]*math.cos(a)+velocity[1]*math.sin(a); vl=-velocity[0]*math.sin(a)+velocity[1]*math.cos(a)
 clearance=r.longitudinal_clearance(actor['forward'],actor['length']); relative=speed[k]-vf; ttc=float(np.clip(clearance/relative,0,30))
 future=g._geometry_future(times,k); track=[x for x in s['vehicle_tracks'][identity] if x['index'] in future]
 complete=times[future[-1]]-times[k]>=6 and [x['index'] for x in track]==future and not np.any(np.diff(times[future])>.75)
 minimum,lower=g._clearances(pos,yaws,track); turn=r.local_heading_change_around_index(yaws,times,k)
 support=[x for x in s['lane_targets'] if x['index']==k and x['instance']==identity]
 detail=dict(scene=row['scene_name'],frame=k,time_s=float(times[k]),instance=identity,category=actor['category'],ttc_s=ttc,stored_ttc_s=float(row['min_ttc']),target_speed=float(np.linalg.norm(velocity)),instance_max_speed=s['instance_max_speeds'][identity],heading_deg=math.degrees(actor['heading_delta']),turn_rad=turn,forward=actor['forward'],lateral=actor['lateral'],same_path=r.classify_vehicle_interaction(actor['forward'],actor['lateral'],vf,vl,speed[k]).same_path,old_turn_filter=r.is_turning_projection_artifact(float(np.linalg.norm(velocity)),actor['heading_delta'],turn),future_complete=bool(complete),available_future_s=float(times[future[-1]]-times[k]),synchronized_box_clearance=minimum,modeled_clearance_lower=lower,map_support=support,longitudinal_risk=float(scores.loc[row['scene_name'],'longitudinal_risk']))
 assert abs(ttc-float(row['min_ttc']))<1e-12
 print('MINIMUM',json.dumps(detail,ensure_ascii=False))
print('READ_ONLY minimum arithmetic/identity checked; no candidate ledger or new features generated.')
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 - 2>&1 | Tee-Object -FilePath logs/ttc_scope_diagnosis_v2_20261015.log
```
