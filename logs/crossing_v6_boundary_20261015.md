# v6 新变化逐目标边界核对

日期：2026-10-15（北京时间）。状态：`diagnosed_design_pending_approval`。用户要求继续推进后，先收尾v6新增的0067/0068边界；本轮只读现有开发轨迹、调用冻结函数核对贡献，不实现新候选、不提取、不拟合、不调参数、不访问评价150或导出新媒体。

## 来源与封印

| 文件 | SHA256 |
| --- | --- |
| `HDBSCAN/tables/crossing_v5_2_regression29_trajectory_20261013.json` | `1b8723d72ed3de9f2d90fca91acf59d3716245f343bc5019326a99e972dbfc60` |
| `HDBSCAN/tables/crossing_v6_replay29_evidence_20261014.json` | `0337d03b460c9cdf7e3e5bc9b469f925b9e37fcc20fa2ccadf30a2ebc0fcd42d` |
| `HDBSCAN/scripts/crossing_candidate_v5_2.py` | `6392a09102de7bd735456be9243017c8bcb9355710cf19d3b28233729ab98242` |
| `HDBSCAN/scripts/crossing_candidate_v6.py` | `4403f470ddf11105320a155ce5c22c077a684c189aaae396f50aa73335e0b35d` |

环境为 `D:/Python/Conda/envs/autodrive-cluster/python.exe`。原v6协议摘要 `ae7db74041abe8758746d0819e5afe9fa8df48112d3864b13d1e76e412b9fd23` 的来源/运行环境/输出与精确29重放核验退出0，见 `logs/crossing_v6_boundary_parent_check_20261015.log`。这只是重验，不是重复run。

## 0068：两帧减少来自不同目标

程序同目标分解确认：

| 目标 | v5.2局部左转贡献帧 | v6局部左转贡献帧 | 本次定位 |
| --- | --- | --- | --- |
| 卡车 `727349048e9044d98846cbeeb3a1b5fd` | 14–23 | 14–22 | 卡车原连续曝光段末帧23（11.551秒）被逐帧路线门控删掉。 |
| 小汽车 `64a805096d9047a6bbc73734b0a90e67` | 17–24 | 无 | 早期响应锚点与路线分离；后段未来不足且没有新的响应锚点，未再形成局部左转关联。 |

所以场景比值28.21%→23.08%的两帧差异不是“同一卡车被删两帧”：第23帧原由卡车和小汽车共同贡献，第24帧（12.001秒）原来只有小汽车贡献。不能为恢复旧比值而把第24帧一并补回，也不能将小汽车未来未知改写为无威胁。

卡车7.551/8.051秒两个原始横向响应保护锚点仍保留。7.054–11.001秒的路线审计一直为潜在相关，到11.551秒才变为模型空间分离，下界1.330m。该时刻卡车仍在自车前方约19.37m/横向2.63m，自车速度从7.551秒的6.70m/s持续降至11.551秒的2.35m/s，12.001秒约2.00m/s。同期没有低于1m/s的停车标志，不能说算法确认了停车；人工此前明确确认持续减速让行。

根因：v6将“该目标从当前帧向后与观测路线分离”同时用于删除当前几何候选与历史交互事件中的曝光帧。前者不必然说明同一次让行事件已经结束。冻结v5.2的局部左转本来受同目标连续曝光和六秒窗口限制，v6逐帧遮掉第23帧后切短了该事件；这支持调整事件表示的必要性，不是已经证明11.551秒仍有即时冲突。

小汽车则不同：17–20帧（8.501–10.001秒）空间分离下界约1.484–2.308m，原温和减速锚点只发生在这些已分离帧；21–24帧未知，但 `_soft_response` 均为False。此目标没有被保留的路线相关响应锚点，不应借卡车的让行种子恢复。具体小汽车画面身份仍未人工确认。

## 0067：新过滤的是横向公交车

2.899秒、第6帧实例 `30d55e8a3a5b420ea40e230fc112be86`，标注类别 `vehicle.bus.rigid`，长8.466m/宽2.522m。该帧相对自车前向23.460m、横向14.833m，朝向差约-91.31度；它是横向车辆候选，不是VRU。

冻结记录中同期车身最小间距8.316m、观测路线包络分离下界6.607m，未来完整，无低速/温和减速保护；旧转弯过滤未生效主要因为局部航向变化0.275rad小于原0.35rad门槛。v6没有再以转角足够大作为必要条件，因路线分离过滤该候选。

这说明程序删的是哪个目标、走了哪条分支，但不能代替画面语义验收。旧人工反馈“让行行人、对向车轻微侵入”没有逐一确认这辆横向公交车，不将它套用为通过。本轮VRU/侵入字段未改。已有媒体 `exports/feature_check_batch7_20260815/scene-0067_CAM_FRONT_6fps.gif` 只是历史无本轮时间/目标绑定的参考，不冒称新的逐目标复核包。

## 下一版短设计（尚未批准或实现）

这是现有流程内的限定修改，不做新子系统：另建v6.1，只修局部左转事件连续性，不修改v6横向候选、几何裕度、TTC、VRU或权重。

- 仅当同一目标已有保留的响应保护锚点且锚点路线相关时，允许其原连续曝光片段在原六秒窗口内保留历史交互表示；不将其重新标记为当前横向冲突。
- 不能跨目标、跨曝光缺口或跨后续新事件传播；未知不能作为建立确定交互的新种子。没有有效种子的路线分离目标仍受v6门控，例如0073无关横向车以及0068旁边小汽车。
- 用失败测试覆盖同目标尾帧、干扰小汽车、片段间断、窗口边界、未知不升格；再冻结独立配方，重放同29条。保留原v6及所有前版源码/测试/协议/输出。
- 必须保护0068已确认卡车锚点及事件表示、0552已有公交程序语境、0107侵入；0453/0073过滤不得回退。0067仍待人工对应，不自动推广为正式结果。

该设计需用户确认后才能实现。0073近1m的几何边界稳健性仍是限制，没有趁本轮调阈值；之后再分步处理0669 TTC、0102/0151 VRU和0552部分卡车绕行，不同时扩展所有规则。

## 可重放命令

原始核验：

```powershell
& D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 logs/crossing_v6_replay_20261014.py check --expected-protocol-sha ae7db74041abe8758746d0819e5afe9fa8df48112d3864b13d1e76e412b9fd23
```

同目标分解只读命令如下；控制台及来源摘要保存于 `logs/crossing_v6_boundary_diagnosis_20261015.log`，退出0。此命令没有新特征输出。

```powershell
@'
import hashlib,json
from pathlib import Path
import numpy as np
from HDBSCAN.scripts import crossing_candidate_v5_2 as p, crossing_candidate_v6 as v
source=Path('HDBSCAN/tables/crossing_v5_2_regression29_trajectory_20261013.json')
target=Path('HDBSCAN/tables/crossing_v6_replay29_evidence_20261014.json')
for f in (source,target,Path(p.__file__),Path(v.__file__)):
 print('SOURCE',str(f),'SHA256',hashlib.sha256(f.read_bytes()).hexdigest())
a=json.loads(source.read_text());b=json.loads(target.read_text())['scenes']
for name in ('scene-0067','scene-0068'):
 s=next(x for x in a if x['scene_name']==name); n=next(x for x in b if x['scene_name']==name)
 t=np.asarray(s['times']); speed=np.asarray(s['ego_speeds'])
 print('SCENE',name)
 for identity,track in s['vehicle_tracks'].items():
  old=[x for x in s['crossing_v5_audit'] if x['instance_token']==identity]
  new=[x for x in n['crossing'] if x['instance_token']==identity]
  routes=[x for x in n['routes'] if x['instance_token']==identity]
  left=p.local_left_interaction_flags(t,s['ego_yaws'],{identity:track},old,s['crossing_yield_flags'],speed)
  now=v.local_left_interaction_flags(t,s['ego_yaws'],{identity:track},new,s['crossing_yield_flags'],speed,route_evidence=routes)
  if any(left) or any(now):
   print('CONTRIBUTION',identity,track[0]['category'],'PARENT',[i for i,x in enumerate(left) if x],'V6',[i for i,x in enumerate(now) if x])
   for r in track:
    i=r['index']
    if r['crossing_exposure']:
     q=next(x for x in routes if x['index']==i)
     print('EXPOSURE',json.dumps(dict(index=i,time_s=float(t[i]-t[0]),forward=r['forward'],lateral=r['lateral'],ego_speed=float(speed[i]),raw_conflict=r.get('raw_crossing_conflict'),soft_response=p._soft_response(t,speed,i),relation=q['relation'],route_lower=q['spatial_clearance_lower_m'])))
 if name=='scene-0067':
  for item in n['crossing']:
   track=s['vehicle_tracks'][item['instance_token']]; r=next(x for x in track if x['index']==item['index'])
   print('FILTERED_TARGET',json.dumps(dict(item,category=r['category'],forward=r['forward'],lateral=r['lateral'],heading_delta=r['heading_delta'])))
print('READ_ONLY_DIAGNOSIS_COMPLETE; no extraction, feature change, fit or evaluation.')
'@ | & D:/Python/Conda/envs/autodrive-cluster/python.exe -X utf8 - 2>&1 | Tee-Object -FilePath logs/crossing_v6_boundary_diagnosis_20261015.log
```

早期探索调用内部 `_soft_response` 时直接传入Python列表，触发NumPy比较类型错误；已按该内部函数原调用约定转为数组，不改冻结源码，也不将其报告为生产缺陷。搜索exports时一个无关临时目录拒绝访问，未改权限/删目录，仅使用已定位路径。纯文档/诊断工作未重跑单元测试，不沿用昨天的294项当作本轮新测试结果。
