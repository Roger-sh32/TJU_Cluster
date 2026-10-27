"""Ten fixed development review cards; reuse eight GIFs, export only two."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

import PIL
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'logs'))
import build_development_media_review_20261012 as renderer
from build_semantic_review_pack_20261001 import record
from evaluation_media_audit_20260926 import records

NAMES = ('scene-0453','scene-0552','scene-0068','scene-0073','scene-0151',
         'scene-0102','scene-0669','scene-0815','scene-0816','scene-0107')
NEW = ('scene-0068','scene-0073')
TABLES = ROOT/'HDBSCAN/tables'
DEST = ROOT/'exports/review10_20261014'
PROTOCOL = TABLES/'review10_package_protocol_20261014.json'
REPORT = TABLES/'review10_package_media_20261014.json'
DOCUMENT = ROOT/'outputs/人工复核/十场景集中复核包_20261014.md'
STATUS = ROOT/'logs/review10_package_20261014_status.json'
CURRENT = TABLES/'scene_features_crossing_v5_2_regression29_20261013.csv'
BASELINE = TABLES/'scene_features_development_candidate700_20261001.csv'
TRAJECTORY = TABLES/'crossing_v5_2_regression29_trajectory_20261013.json'
LABELS = {'crossing_vehicle_conflict_ratio':'横向冲突候选帧比',
          'left_turn_cross_traffic_interaction_ratio':'局部左转交互帧比',
          'vru_path_conflict_ratio':'VRU原始路径冲突帧比',
          'vru_observed_relevance_ratio':'VRU观测相关帧比',
          'obstacle_induced_route_deviation_flag':'严格受阻改道标记',
          'adjacent_lane_intrusion_ratio':'相邻车道侵入候选帧比',
          'stop_sign_stop_candidate':'Stop停车候选', 'min_ttc':'最低TTC/s'}
CARDS = {
 'scene-0453': ('起始小车与后续皮卡要分开', '0–2秒；随后8秒以后停车观察段作对照',
  '你已判断以Stop规则停车为主，随后皮卡又产生约束。初段0.499秒小汽车不是后续皮卡。',
  '只核对初段小汽车有没有进入自车实际通行路线，是否让自车减速、等待或调整位置？不能辨认该目标就保留无法判断。',
  ['crossing_vehicle_conflict_ratio','stop_sign_stop_candidate']),
 'scene-0552': ('公交让行、小汽车候选、卡车绕行分别看', '0–12秒公交/等待；13.4–13.9秒小汽车候选；左转后卡车占道',
  '你已确认先等待公交通过，再左转，后段向左调整尝试绕开部分占道卡车。当前严格改道仍为0，本轮没有修复绕行漏表达。',
  '13.4秒附近是否能辨认到另外的小汽车？它是否影响实际路线？另请指出卡车占道导致横向调整的大致秒数；不把它与公交等待合并。13.898秒后的六秒未来不完整，不要求猜视频外动作。',
  ['left_turn_cross_traffic_interaction_ratio','obstacle_induced_route_deviation_flag']),
 'scene-0068': ('缓慢减速等待左转是否正确保留', '7.5–12秒，候选锚点7.551/8.051秒',
  '你已确认左转需要等待卡车先通过。当前以持续温和减速保护候选，未直接认定停车因果。',
  '这段速度降低是否与横向卡车通过相对应？请确认等待结束/开始左转的大致时刻；不需重述整个场景。后段未知候选不默认属于同一次让行。',
  ['crossing_vehicle_conflict_ratio','left_turn_cross_traffic_interaction_ratio']),
 'scene-0073': ('Stop规则停车与横向车约束能否区分', '9.5–12秒横向曝光/低速段，随后右转',
  '你此前认为主要因停止牌停车，而不是为横向卡车让行。程序的响应保护仍可能保留候选，不等于已确认交通因果。',
  '停车结束后能否直接右转，还是还必须等某辆车？如主要是规则停车、横向车在不相交车道，请注明；没有影响也可以明确写无。',
  ['crossing_vehicle_conflict_ratio','stop_sign_stop_candidate']),
 'scene-0151': ('右转时自行车外推是否仍是误报边界', '2.5–3.1秒附近',
  '你此前确认对自车没有影响。当前横向候选一帧被过滤、一帧因目标轨迹缺口未知；VRU原始预测仍非0，观测相关为0。',
  '只核对可见自行车的位置/运动方向与自车右转后的路线是否相交。若前次无影响判断仍成立，一句话确认即可；不要用未知帧推定安全或冲突。',
  ['crossing_vehicle_conflict_ratio','vru_path_conflict_ratio','vru_observed_relevance_ratio']),
 'scene-0102': ('桥上人行道行人与路线隔离', '3.9–4.9秒行人段；转弯到桥上全过程为语境',
  '你已指出行人未横穿且有较宽护栏隔离。护栏仍是人工证据，不是自动地图识别；VRU/TTC本轮未修改。原话左转与元数据右转差异保留，不手改方向。',
  '只看该行人是否始终位于护栏/人行道外侧，是否存在实际穿越开口或路线占用；若仍无约束直接确认，不要求重复整体描述。',
  ['vru_path_conflict_ratio','vru_observed_relevance_ratio']),
 'scene-0669': ('转弯近距不能冒充对向静止车冲突', '约3.85秒自车转弯靠近对向车的时刻',
  '你已判断对向等待车及路边乘客没有实际影响，密集发生在对向。当前最低TTC约3.364秒尚未修；它不是3.364秒发生，事件时间约3.847秒。',
  '核对最近时刻是否仍隔着明确的对向车道边界，是否真正侵入/占用自车转弯出口；若只有转弯靠近但无制动/绕行，再确认即可。',
  ['min_ttc','crossing_vehicle_conflict_ratio','obstacle_induced_route_deviation_flag']),
 'scene-0815': ('起步邻车与末尾远车不是同一事件', '0–5秒信号起步；18.95秒末尾仅作可见性记录',
  '你已确认左侧车辆先起步但不影响自车右转。4.951秒候选过滤；18.950秒远车仅约0.5秒未来，继续未知。',
  '前段是否仍无路线约束？末尾若目标看不清或只剩很短片段，可以直接写证据不足；不要求判断视频外未来，不把未知作为需要你猜的题。',
  ['crossing_vehicle_conflict_ratio','left_turn_cross_traffic_interaction_ratio']),
 'scene-0816': ('环岛曲率误报的负例检查', '约6.05/8.00秒；整段是否连续顺畅',
  '你已确认顺畅通过环岛，无真实卡车/护栏/锥桶让行。两条横向投影按同步车身分离过滤，局部左转交互为0；雨天未新增自动特征。',
  '只核对这两个附近时段有没有实际让行、制动或受阻改道。如果仍是自然环岛行驶，简短确认即可，不因曲率大就认定交互。',
  ['crossing_vehicle_conflict_ratio','left_turn_cross_traffic_interaction_ratio']),
 'scene-0107': ('公交倾入的已知正例是否仍被保留', '公交车从起步到向自车侧偏移的一段，请标大致秒数',
  '你已确认公交车起步后倾入自车车道。当前侵入候选仍非0，这是未修改特征的保护控制，不是新增侵入算法。',
  '如仍是原先确认的真实倾入，一句话确认并标时段即可；可补充它是否使自车跟车距离/速度变化。不要把未发生事故当作无交互。',
  ['adjacent_lane_intrusion_ratio','crossing_vehicle_conflict_ratio']),
}


def runtime_record():
    return {'python':platform.python_version(),'pillow':PIL.__version__,
            'font':record('C:/Windows/Fonts/consola.ttf')}


def validate_runtime(expected):
    if runtime_record() != expected:
        raise ValueError('Frozen export runtime changed')


def fail_status(error):
    status = json.loads(STATUS.read_text(encoding='utf-8'))
    if status['phase'] == 'exporting_two_development_gifs':
        with STATUS.open('w',encoding='utf-8') as stream:
            json.dump({'phase':'failed_requires_inspection','protocol':status['protocol'],
                       'error':type(error).__name__+': '+str(error)},stream,indent=2)


def validate_scope(names, current, baseline, split):
    if tuple(names) != NAMES:
        raise ValueError('Only fixed ten review identities allowed')
    for name in names:
        if (name not in current or name not in baseline or name not in split
                or split[name]['split'] != 'development'
                or current[name]['scene_token'] != baseline[name]['scene_token']
                or current[name]['scene_token'] != split[name]['scene_token']):
            raise ValueError('Development/current/baseline identity mismatch: '+name)


def camera_pool(rows, sample_ids, data):
    rows = sorted(rows, key=lambda r:r['timestamp'])
    keys = [r for r in rows if r['is_key_frame']]
    if len(keys) != len(sample_ids) or {r['sample_token'] for r in keys} != set(sample_ids):
        raise ValueError('Incomplete front keyframe metadata')
    if len({r['token'] for r in rows}) != len(rows):
        raise ValueError('Duplicate camera token')
    for row in rows:
        path = (data/row['filename']).resolve()
        path.relative_to(data.resolve())
        row_ok = path.is_file() and path.stat().st_size > 0
        if row['is_key_frame'] and not row_ok:
            raise ValueError('Missing front keyframe; do not replace scene')
    bounded = [r for r in rows if keys[0]['timestamp'] <= r['timestamp'] <= keys[-1]['timestamp']]
    if any(not (data/r['filename']).is_file() or (data/r['filename']).stat().st_size == 0 for r in bounded):
        return keys, 'native_keyframes_2hz_no_interpolation'
    return bounded, 'nearest_6hz_native_timing'


def metadata():
    meta = ROOT/'nuScenes/v1.0-trainval'
    scenes = {r['name']:r for r in json.loads((meta/'scene.json').read_text(encoding='utf-8')) if r['name'] in NAMES}
    tokens = {r['token']:n for n,r in scenes.items()}
    samples = {r['token']:r for r in json.loads((meta/'sample.json').read_text(encoding='utf-8')) if r['scene_token'] in tokens}
    sensors = {r['token']:r for r in json.loads((meta/'sensor.json').read_text(encoding='utf-8'))}
    calibrated = {r['token'] for r in json.loads((meta/'calibrated_sensor.json').read_text(encoding='utf-8'))
                  if sensors[r['sensor_token']]['channel'] == 'CAM_FRONT'}
    camera = {n:[] for n in NAMES}
    for row in records(meta/'sample_data.json'):
        if row['sample_token'] in samples and row['calibrated_sensor_token'] in calibrated:
            camera[tokens[samples[row['sample_token']]['scene_token']]].append(row)
    starts, plans = {}, {}
    for name in NAMES:
        scene = scenes[name]
        ids = [t for t,s in samples.items() if s['scene_token'] == scene['token']]
        if len(ids) != scene['nbr_samples']:
            raise ValueError('Scene sample count mismatch')
        starts[name] = samples[scene['first_sample_token']]['timestamp']
        if name in NEW:
            pool, mode = camera_pool(camera[name], ids, ROOT/'nuScenes')
            plans[name] = {'pool':pool,'mode':mode}
    return scenes, starts, camera, plans


def verify_media(media, split, meta_rows, start):
    name = media['scene_name']
    if media['scene_token'] != split[name]['scene_token'] or media['log_token'] != split[name]['log_token']:
        raise ValueError('Media identity mismatch')
    expected = {r['token']:r for r in meta_rows}
    selected = media['selected_frames']
    for row in selected:
        reference = expected[row['token']]
        if row['timestamp'] != reference['timestamp'] or row['filename'] != reference['filename']:
            raise ValueError('Camera source metadata mismatch')
        source = (ROOT/'nuScenes'/row['filename']).resolve()
        source.relative_to((ROOT/'nuScenes').resolve())
        if source != Path(row['source']['path']).resolve():
            raise ValueError('Camera source path mismatch')
        renderer.verify_record(row['source'])
        if abs(row['scene_relative_seconds']-(row['timestamp']-start)/1e6) > 1e-8:
            raise ValueError('Camera relative time mismatch')
    if media['frame_durations_ms'] != renderer.timing(selected):
        raise ValueError('Non-native GIF timing')
    gif = None
    for output in media['outputs']:
        Path(output['path']).resolve().relative_to((ROOT/'exports').resolve())
        renderer.verify_record(output)
        if output['path'].endswith('.gif'):
            gif = output['path']
    if gif is None:
        raise ValueError('Missing GIF')
    with Image.open(gif) as image:
        if image.n_frames != media['frame_count'] or image.size != (960,576):
            raise ValueError('GIF dimensions/frame count mismatch')
        durations = []
        for i in range(image.n_frames):
            image.seek(i)
            image.load()
            durations.append(image.info['duration'])
        if durations != media['frame_durations_ms']:
            raise ValueError('Decoded GIF timing mismatch')


def media_only(item):
    fields = {'scene_name','scene_token','log_token','description','split','camera_record_count',
              'keyframe_count','selected_frames','frame_count','frame_durations_ms','data_span_seconds',
              'sampled_data_span_seconds','playback_seconds','final_frame_hold_seconds','sampling_mode',
              'outputs'}
    return {key:value for key,value in item.items() if key in fields}


def reuse_media():
    result = {}
    for filename in ['development_review_media_20261012.json','semantic_review_supplement_media_20261001.json']:
        for scene in json.loads((TABLES/filename).read_text(encoding='utf-8'))['scenes']:
            if scene['scene_name'] in NAMES and scene['scene_name'] not in NEW:
                if scene['scene_name'] in result:
                    raise ValueError('Duplicate reuse media')
                result[scene['scene_name']] = media_only(scene)
                result[scene['scene_name']]['reuse_source_report'] = record(TABLES/filename)
    if set(result) != set(NAMES)-set(NEW):
        raise ValueError('Eight existing timestamped GIFs required')
    return result


def document(media, current, baseline, audits):
    lines = ['# 十场景集中复核包', '', '2026-10-14。10条固定开发场景，针对待查目标/时段整理，不是10条全新抽样或独立盲评。'
        '不按排名选取，不给危险标签；不计算专家通过率。不重跑特征或聚类。', '',
        '## 怎么看', '',
        '先看前5条，后5条是误报边界/已知正例对照。每条只回答局部问题，已确认整体描述不必重写。'
        '前视不足或目标辨不清可写“无法判断”。没有目标框，实例ID不能自动对应画面中的某辆车。', '',
        '动图顶栏data t为相对首个sample的相机原始时间。约6Hz，按原始间隔播放，末帧额外保持一间隔；'
        '不是插帧。不按GIF帧序号猜秒数。8条复用已有带时间媒体，0068/0073只新增时间一致的导出，不改原图。', '',
        '数值表为冻结v4→v5.2同场景字段。未拟合v5.2，不展示旧簇号/排名；比值不是危险概率。'
        '响应保护不是因果确认，未知不是安全；VRU/TTC及0552后段严格绕行问题尚未修复。', '',
        '| 顺序 | 场景 | 本次核对 | 关键时段 |', '| --- | --- | --- | --- |']
    for i,name in enumerate(NAMES,1):
        title,window,known,question,fields = CARDS[name]
        lines.append(f'| {i:02d} | {name} | {title} | {window} |')
    for i,name in enumerate(NAMES,1):
        title,window,known,question,fields = CARDS[name]
        item = media[name]
        gif = next(o['path'] for o in item['outputs'] if o['path'].endswith('.gif'))
        lines += ['',f'## {i:02d}. {name}：{title}', '',f'![{name}]({Path(gif).as_posix()})','',
                  f'**重点时段：** {window}。', '', f'**已知反馈/边界：** {known}', '',
                  f'**本次只问：** {question}', '', '| 字段 | v4 | 当前v5.2 |','| --- | ---: | ---: |']
        for field in fields:
            def show(value):
                number = float(value)
                return f'{number*100:.2f}%' if field.endswith('_ratio') else f'{number:.3f}' if field == 'min_ttc' else str(int(number))
            lines.append(f'| {LABELS[field]} | {show(baseline[name][field])} | {show(current[name][field])} |')
        groups = defaultdict(list)
        for row in audits[name]['crossing_v5_audit']:
            groups[(row['instance_token'],row['state'])].append(row['time_s'])
        if groups:
            lines += ['', '横向逐目标记录（定位线索，不是画面目标身份确认）：', '',
                      '| 时间/s | 实例ID | 程序状态 |','| --- | --- | --- |']
            for (instance,state),times in groups.items():
                span = f'{min(times):.3f}' if len(times)==1 else f'{min(times):.3f}–{max(times):.3f}（{len(times)}帧）'
                lines.append(f'| {span} | `{instance}` | `{state}` |')
        lines += ['',f'媒体：{"本次新增" if name in NEW else "复用既有"}；模式 `{item.get("sampling_mode","nearest_6hz_native_timing")}`；'
                  f'{item["frame_count"]}帧。', '', f'反馈：`{name}：约__秒，目标__，是否影响实际路线__，是否减速/等待/调整__；或无法判断。`']
    lines += ['', '## 反馈与来源', '', '可以一次发10条，也可以只反馈有新增观察的场景。0815等视频末尾未来不足不要求猜测；'
        '后续反馈单独记到新日志，不回写已冻结媒体报告或旧协议。', '',
        '[执行记录](F:/Scene_cluster/logs/review10_package_20261014.md)，'
        '[当前特征对照](F:/Scene_cluster/outputs/人工复核/横向交互v5_2回归对照_20261013.md)。', '']
    return '\n'.join(lines)


def inputs():
    paths = [CURRENT, BASELINE, TRAJECTORY, TABLES/'evaluation_split_20260924.csv',
        TABLES/'crossing_v5_2_regression29_comparison_20261013.json',
        TABLES/'development_review_media_20261012.json', TABLES/'semantic_review_supplement_media_20261001.json',
        ROOT/'logs/development_review_feedback_20261012.md', ROOT/'logs/semantic_review_feedback_20261001.md',
        ROOT/'logs/review11_static_passages_20260925.md', ROOT/'logs/feature_batch_0051_0100_2026-07-12.md',
        Path(__file__), ROOT/'logs/test_review10_package_20261014.py',
        Path(renderer.__file__), ROOT/'logs/build_semantic_review_pack_20261001.py',
        ROOT/'logs/evaluation_media_audit_20260926.py', ROOT/'HDBSCAN/tests/test_evaluation_split.py']
    paths += [ROOT/'nuScenes/v1.0-trainval'/n for n in
              ['scene.json','sample.json','sample_data.json','sensor.json','calibrated_sensor.json']]
    return [record(p) for p in paths]


def run():
    if any(p.exists() for p in [DEST,PROTOCOL,REPORT,DOCUMENT,STATUS]):
        raise FileExistsError('Review package already exists; never overwrite or implicitly resume')
    current, baseline, split = (renderer.read_csv(p) for p in [CURRENT,BASELINE,TABLES/'evaluation_split_20260924.csv'])
    validate_scope(NAMES,current,baseline,split)
    comparison = json.loads((TABLES/'crossing_v5_2_regression29_comparison_20261013.json').read_text(encoding='utf-8'))
    if record(TABLES/'crossing_v5_2_regression29_comparison_20261013.json')['sha256'] != '160b527a62320f5c2715200a14380eebb016069dc8e3b782786ed9198a6a3a46':
        raise ValueError('Frozen v5.2 comparison changed')
    renderer.verify_record(comparison['features'])
    renderer.verify_record(comparison['trajectory'])
    renderer.verify_record(comparison['protocol'])
    parent = json.loads(Path(comparison['protocol']['path']).read_text(encoding='utf-8'))
    for path in [BASELINE,TABLES/'evaluation_split_20260924.csv']:
        matches = [r for r in parent['inputs'] if Path(r['path']).resolve() == path.resolve()]
        if len(matches) != 1:
            raise ValueError('Frozen input binding absent: '+str(path))
        renderer.verify_record(matches[0])
    bound = inputs()
    scenes, starts, camera, plans = metadata()
    reused = reuse_media()
    selected_meta = {}
    for name in NAMES:
        if scenes[name]['token'] != split[name]['scene_token'] or scenes[name]['log_token'] != split[name]['log_token']:
            raise ValueError('Scene metadata mismatch')
        chosen = renderer.select_frames(plans[name]['pool']) if name in NEW else reused[name]['selected_frames']
        tokens = {r['token'] for r in chosen}
        selected_meta[name] = [r for r in camera[name] if r['token'] in tokens]
        if len(tokens) != len(selected_meta[name]):
            raise ValueError('Selected media metadata missing')
        if name not in NEW:
            verify_media(reused[name],split,selected_meta[name],starts[name])
    for r in bound:
        renderer.verify_record(r)
    renderer.write_json(PROTOCOL, {'names':NAMES,'new_exports':NEW,'inputs':bound,
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],
        'executable':record(sys.executable),'runtime':runtime_record(),'starts':starts,'metadata':selected_meta,
        'selection':'Fixed pending issues plus known positive/negative controls within v5.2 development29; not random or blinded',
        'evaluation_used':False,'feature_extraction':False,'fit':False})
    seal = record(PROTOCOL)
    renderer.write_json(STATUS, {'phase':'exporting_two_development_gifs','protocol':seal})
    try:
        publish_package(reused,scenes,plans,starts,split,selected_meta,seal,bound,current,baseline)
    except Exception as exc:
        fail_status(exc)
        raise


def publish_package(reused,scenes,plans,starts,split,selected_meta,seal,bound,current,baseline):
    DEST.mkdir()
    media = dict(reused)
    old_dest = renderer.DEST
    try:
        renderer.DEST = DEST
        for name in NEW:
            media[name] = media_only(renderer.export_scene(scenes[name],plans[name]['pool'],starts[name]))
            media[name]['sampling_mode'] = plans[name]['mode']
            verify_media(media[name],split,selected_meta[name],starts[name])
            print(name+': timestamped GIF exported/decoded',flush=True)
    finally:
        renderer.DEST = old_dest
    for r in bound:
        renderer.verify_record(r)
    renderer.verify_record(seal)
    audits = {r['scene_name']:r for r in json.loads(TRAJECTORY.read_text(encoding='utf-8'))}
    with DOCUMENT.open('x',encoding='utf-8') as stream:
        stream.write(document(media,current,baseline,audits))
    renderer.write_json(REPORT, {'protocol':seal,'document':record(DOCUMENT),'names':NAMES,
        'scenes':[media[n] for n in NAMES],'new_export_count':len(NEW),'reused_count':8,
        'feature_version':'crossing_candidate_v5_2_20261013',
        'feature_scope':'Card numbers only; media records contain no historical features, clusters or rankings',
        'semantic_acceptance':False,'evaluation_used':False})
    # The status retains the original protocol seal throughout completion.
    with STATUS.open('w',encoding='utf-8') as stream:
        json.dump({'phase':'completed_requires_human','protocol':seal,'report':record(REPORT)},stream,indent=2)
    print(json.dumps({'protocol':seal,'report':record(REPORT)},ensure_ascii=False),flush=True)


def verify(expected_hash):
    status = json.loads(STATUS.read_text(encoding='utf-8'))
    if Path(status['protocol']['path']).resolve() != PROTOCOL.resolve():
        raise ValueError('Original protocol path mismatch')
    if not expected_hash or status['protocol']['sha256'] != expected_hash:
        raise ValueError('Original protocol hash required')
    if (status['phase'] != 'completed_requires_human'
            or Path(status['report']['path']).resolve() != REPORT.resolve()):
        raise ValueError('Incomplete package or report path mismatch')
    renderer.verify_record(status['protocol'])
    renderer.verify_record(status['report'])
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    if tuple(protocol['names']) != NAMES or tuple(protocol['new_exports']) != NEW:
        raise ValueError('Fixed selection changed')
    for r in protocol['inputs']:
        renderer.verify_record(r)
    renderer.verify_record(protocol['executable'])
    validate_runtime(protocol['runtime'])
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    if (report['protocol'] != status['protocol'] or tuple(report['names']) != NAMES
            or report['new_export_count'] != len(NEW) or report['reused_count'] != 8
            or Path(report['document']['path']).resolve() != DOCUMENT.resolve()):
        raise ValueError('Bound review package contract changed')
    renderer.verify_record(report['document'])
    current, baseline, split = (renderer.read_csv(p) for p in [CURRENT,BASELINE,TABLES/'evaluation_split_20260924.csv'])
    validate_scope(NAMES,current,baseline,split)
    if tuple(s['scene_name'] for s in report['scenes']) != NAMES:
        raise ValueError('Media list changed')
    for scene in report['scenes']:
        verify_media(scene,split,protocol['metadata'][scene['scene_name']],protocol['starts'][scene['scene_name']])
    audits = {r['scene_name']:r for r in json.loads(TRAJECTORY.read_text(encoding='utf-8'))}
    if DOCUMENT.read_text(encoding='utf-8') != document({s['scene_name']:s for s in report['scenes']},current,baseline,audits):
        raise ValueError('Review card replay mismatch')
    print('VERIFIED ten development scenes:8 reused/2 new, identity/hash/fullGIFdecode/timing/cards; no feature/evaluation changes.',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['run','verify'])
    parser.add_argument('--expected-protocol-sha')
    args = parser.parse_args()
    run() if args.action == 'run' else verify(args.expected_protocol_sha)
