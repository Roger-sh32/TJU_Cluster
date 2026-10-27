"""Synthetic-only metric exercise and read-only experiment evidence ledger."""

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from HDBSCAN.scripts.evaluation_metrics import (
    aggregate_reviews, ranking_metrics, random_baseline, budget_savings, paired_log_bootstrap,
)

TABLES = ROOT/'HDBSCAN/tables'
DEFAULT_OUTPUT = ROOT/'outputs/实验准备/20261013'


def record(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}


def verify(expected):
    actual = record(expected['path'])
    if any(actual[key] != value for key, value in expected.items()):
        raise ValueError('Bound evidence hash/size changed: '+expected['path'])


def bound_summary(path, keys):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    for key in keys:
        values = data[key] if isinstance(data[key], list) else [data[key]]
        for value in values:
            verify(value)
    return data


def validate_destination(path):
    path = Path(path).resolve()
    try:
        relative = path.relative_to(ROOT/'outputs/实验准备')
    except ValueError as exc:
        raise ValueError('Outputs must stay under outputs/实验准备') from exc
    if not relative.parts:
        raise ValueError('Use a new dated packet subdirectory')
    return path


def synthetic_demo():
    ids = [f'SYN{i:04d}' for i in range(1,41)]
    labels = {item: 2 if i % 4 == 0 else 1 if i % 4 == 1 else 0 for i,item in enumerate(ids)}
    reviewers = ['SYN_R1','SYN_R2','SYN_R3']
    raw = [{'item_id': item,'reviewer': reviewer,'priority': value}
           for item,value in labels.items() for reviewer in reviewers]
    aggregation = aggregate_reviews(ids, raw, reviewers)
    first = sorted(ids, key=lambda item: (-labels[item], item))
    second = list(reversed(first))
    ks, targets = [10,20,30], [.5,.8,1.]
    result_first = ranking_metrics(first, labels, ks, targets)
    result_second = ranking_metrics(second, labels, ks, targets)
    missing = {**labels, first[1]: None}
    return {'synthetic_only': True, 'real_evaluation_accessed': False,
        'scope': 'Arithmetic/software verification only; not thesis effectiveness data',
        'cohort_size': len(ids), 'labels': labels, 'aggregation': aggregation,
        'fixture_a': result_first, 'fixture_b': result_second,
        'missing_label_example': ranking_metrics(first, missing, ks, targets),
        'random_fixture': random_baseline(labels, ks, targets, list(range(100))),
        'budget_fixture_comparison': {str(t): budget_savings(result_second['budgets'][t], result_first['budgets'][t]) for t in targets},
        'paired_log_fixture': paired_log_bootstrap(first, second, labels,
            {item: f'SYN_LOG{i//5:02d}' for i,item in enumerate(ids)}, 20, 2000, 20261013),
        'configuration_note': 'Demonstration settings only; not final evaluation freeze or parameter selection.'}


def collect_evidence():
    specs = {
        'split': ('evaluation_split_20260924_manifest.json', ['output']),
        'audit700': ('development_audit700_comparison_20260927.json', ['input','baseline','quality','extraction_manifest']),
        'v4_700': ('development_candidate700_comparison_20261001.json', ['protocol','input','manifest','quality']),
        'v52': ('crossing_v5_2_regression29_comparison_20261013.json',
                ['protocol','features','quality','trajectory','manifest','risk_comparison','document','pending']),
        'parameters': ('parameter_stability_20260930/summary.json', ['input','extraction_manifest','quality','outputs']),
        'old_fit': ('development_fit_summary_20260927.json', ['inputs','model_manifest','ranking']),
        'media': ('media_recovery_audit_20261011.json', []),
    }
    values, bindings = {}, []
    for key,(name, fields) in specs.items():
        path = TABLES/name
        values[key] = bound_summary(path, fields)
        bindings.append(record(path))
        for field in fields:
            records = values[key][field] if isinstance(values[key][field], list) else [values[key][field]]
            bindings.extend(records)
    status_path = ROOT/'logs/crossing_v5_2_regression29_20261013_status.json'
    status = bound_summary(status_path, ['comparison','protocol'])
    if status['phase'] != 'completed_candidate_requires_review':
        raise ValueError('Candidate checkpoint changed; revise ledger deliberately')
    bindings.append(record(status_path))
    if record(TABLES/specs['media'][0])['sha256'] != 'ec708a4c29f1320a2b585b25ccef82efd95d63fb098af1e6c8f1fd6c3f7add3f':
        raise ValueError('Frozen media audit hash changed')
    for module, digest in values['v4_700']['source_hashes'].items():
        current = record(ROOT/'HDBSCAN/scripts'/module)
        if current['sha256'] != digest:
            raise ValueError('Frozen v4 module changed')
        bindings.append(current)
    return values, bindings


def report_text(values, day):
    split, audit, v4, current, parameters, old, media = [values[k] for k in
        ('split','audit700','v4_700','v52','parameters','old_fit','media')]
    def link(name, file):
        return f'[{name}]({(TABLES/file).as_posix()})'
    lines = ['# 论文实验证据与下一步', '', f'核对日期：{day}。准备性产出，不是新增场景实验或独立评价成绩。', '',
        '本轮只读JSON汇总并核验关联产物的文件摘要，不重新提取/拟合，不加载模型pickle，'
        '不读取150条评价场景的特征、视频或专家标签。历史源码/环境的完整重放仍应使用匹配快照，'
        '本轮文件校验不能替代历史重放。', '',
        '## 版本与证据', '', '| 工作包 | 已有证据及来源 | 可用于论文的表述 | 不可声称/仍缺什么 |', '| --- | --- | --- | --- |',
        f'| E1 划分 | {split["counts"]["development"]}/{split["counts"]["evaluation"]}条，'
        f'{split["log_counts"]["development"]}/{split["log_counts"]["evaluation"]}日志；'
        +link('划分来源','evaluation_split_20260924_manifest.json')+' | 自2026-09-24起冻结的自定义日志隔离留出集 | 不是官方train/val，也非历史完全未接触 |',
        f'| E2/E4 历史审计 | {audit["scene_count"]}×{audit["column_count"]}，{audit["clustering_feature_count"]}聚类字段；'
        +link('审计','development_audit700_comparison_20260927.json')+' | 当时版本的结构/数值审计 | 不能作为当前候选全量特征 |',
        f'| E4 v4完整开发表 | {v4["scene_count"]}条、{v4["clustering_feature_count"]}字段；'
        +link('v4核验','development_candidate700_comparison_20261001.json')+' | 冻结v4的700条开发提取 | v5.2只有29条，不是当前全700 |',
        f'| E2 当前候选 | v5.2，29条，{len(current["changed_scenes"])}条/{len(current["changes"])}格变化，'
        f'{len(current["clustering_changes"])}聚类格，查询异常{current["query_exception_count"]}；'
        +link('限定回归','crossing_v5_2_regression29_comparison_20261013.json')+' | 同步几何/局部交互的开发回归证据 | 人工待审，不是准确率或正式推广 |',
        f'| E3 历史主模型 | {old["scene_count"]}条、{old["cluster_count_excluding_noise"]}簇、{old["noise_count"]}噪声；'
        +link('历史拟合','development_fit_summary_20260927.json')+' | 当时冻结输入上的可运行原型 | 不是v4/v5.2正式模型，不能套旧簇号/排名 |',
        f'| E6/E8 历史稳定性 | {parameters["successful_runs"]}/{parameters["planned_runs"]}次，'
        f'{len(parameters["configurations"])}配置×{len(parameters["seeds"])}种子；'
        +link('稳定性','parameter_stability_20260930/summary.json')+' | 修正前输入上的稳定性比较 | 未选正式配置，不是语义有效性 |',
        f'| E5 媒体 | {media["selected_file_count"]}个限定文件；'
        +link('恢复审计','media_recovery_audit_20261011.json')+' | 150评价/8开发授权范围的媒体准备 | 非全库完整；非前视关联非关键帧未解码；盲评/标签未完成 |',
        '| E7 评价统计 | 本包合成演示JSON和独立纯计算模块 | 指标程序具备可测试口径 | 无真实Precision/Recall/预算节省成绩 |',
        '| E9/E10 案例与写作 | 已有人工反馈、逐目标诊断、版本来源 | 开发误差分析/方法边界 | 不把开发反馈当独立专家验证，不把条数节省写成时间/路测里程节省 |', '',
        '## 评价工具口径', '',
        '- 三名独立专家均有效才取0/1/2中位数；缺评或NA保留未知，不用两人平均或算法分补齐。原始独立评分保留。',
        '- TopK固定，不跳过未知补位。未知存在时给Precision命中上下界；全名单不完整则不报告完整召回/同召回复核预算。',
        '- 同召回预算比较绑定同一名单和标签摘要，保留负节省；预算内未达到目标则显式失败。',
        '- 随机重复的均值/最小/最大值描述抽样波动，不是方法差异置信区间。',
        '- 方法差异使用相同的整日志重采样；固定排序不重拟合，重复场景按原排名位置计入。任一重采样名单不足K，整个区间列为不可报告，不静默丢弃或补抽。',
        '- 日志分组百分位区间仅是待正式锁定的计算约定；12日志的推断有限。多方法/多K比较及专家标签不确定性不由该区间自动解决。',
        '- 完全一致率仅是完整评分样本的描述；序数一致性系数、价值机制覆盖和等级排序指标尚未实现。', '',
        '## 最小对照/消融待执行方案', '',
        '| 比较 | 保持相同 | 改变什么 | 何时可执行 |', '| --- | --- | --- | --- |',
        '| 四类优先级排序 | 同版本样本/专家标签/预算K/预注册顺序 | 完整、仅风险、仅稀有异常、随机 | 模型/公式/未知处理/排序哈希冻结并批准后，先于盲评标签返回 |',
        '| 评分消融 | 同一冻结聚类输出与开发归一化参考 | 单独移除稀有或异常项；公式和归一化必须先登记 | 不用评价成绩挑消融或调权；本轮不计算 |',
        '| 特征组消融 | 开发成员、版本、评价方式一致 | 地图/路径复核组、决策特征组分别移除；需重新拟合 | 正式特征组/公共预处理/参数选择策略先确认；不拿不同来源旧模型拼接 |',
        '| 聚类/降维对照 | 同源语义特征与共同样本 | UMAP+HDBSCAN、PCA+HDBSCAN及KMeans | 单独批准公平预处理和预算；KMeans继续暂缓 |', '',
        '此表不是参数或最终消融列清单冻结。需要人工决定的只有候选语义收敛、专家/校准、正式版本和对照方案；'
        '不为了填论文表格反复增加特征或挑最优种子。', '',
        '## 后续顺序', '',
        '1. 完成已集中暂存的开发语义复核，尤其0453/0552；0102 VRU/0669 TTC继续单列，不冒充已解决。',
        '2. 明确正式特征/模型和公平对照的冻结范围，再决定是否重建同版本开发700；不自动启动。',
        '3. 开发案例校准专家判据，确认专家和盲评流程；先冻结所有排序/指标/缺失规则，再收正式标签。',
        '4. 授权接通冻结评价预测后，真实标签进入正式统计；本包演示数绝不能抄成实验成绩。', '',
        '[当前人工导航](F:/Scene_cluster/outputs/人工复核/本轮复核导航_20261013.md)。'
        '原盲评协议中的历史媒体缺失段落已由2026-10-12恢复审计在授权范围内取代，评价规则本轮不改。', '']
    return '\n'.join(lines)


def check_packet(destination, expected_hash):
    destination = validate_destination(destination)
    path = destination/'manifest.json'
    if not expected_hash or record(path)['sha256'] != expected_hash:
        raise ValueError('Original packet manifest hash required; do not refresh the seal')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    verify(manifest['executable'])
    if platform.python_version() != manifest['python']:
        raise ValueError('Recorded Python runtime changed')
    for item in manifest['inputs']+manifest['outputs']:
        verify(item)
    expected = json.loads(json.dumps(synthetic_demo(), allow_nan=False))
    if json.loads((destination/'synthetic_metrics.json').read_text(encoding='utf-8')) != expected:
        raise ValueError('Synthetic arithmetic replay mismatch')
    values, _ = collect_evidence()
    if (destination/'实验收尾证据与下一步.md').read_text(encoding='utf-8') != report_text(values, manifest['china_day']):
        raise ValueError('Evidence report replay mismatch')
    print('VERIFIED: synthetic arithmetic, source/output seals and evidence ledger; no real evaluation.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--synthetic-demo', action='store_true')
    mode.add_argument('--check-only', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--expected-manifest-sha')
    args = parser.parse_args()
    destination = validate_destination(args.output_dir)
    if args.check_only:
        check_packet(destination, args.expected_manifest_sha)
        return
    if destination.exists():
        raise FileExistsError('Use a new packet directory; never overwrite evidence')
    values, bindings = collect_evidence()
    bindings += [record(p) for p in [Path(__file__), ROOT/'logs/test_experiment_readiness_20261013.py',
        ROOT/'HDBSCAN/scripts/evaluation_metrics.py', ROOT/'HDBSCAN/tests/test_evaluation_metrics.py',
        ROOT/'HDBSCAN/tests/test_evaluation_split.py', ROOT/'knowledge/wiki/独立评价与专家盲评协议.md']]
    now = datetime.now(timezone.utc)
    day = now.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    demo = synthetic_demo()
    report = report_text(values, day)
    for item in bindings:
        verify(item)
    destination.mkdir(parents=True, exist_ok=False)
    demo_path, report_path = destination/'synthetic_metrics.json', destination/'实验收尾证据与下一步.md'
    with demo_path.open('x', encoding='utf-8') as stream:
        json.dump(demo, stream, ensure_ascii=False, indent=2, allow_nan=False)
    with report_path.open('x', encoding='utf-8') as stream:
        stream.write(report)
    manifest = {'created_at_utc': now.isoformat(), 'china_day': day, 'stage': 'synthetic_statistics_and_evidence_preparation',
        'command': [sys.executable, *sys.argv], 'python': platform.python_version(), 'executable': record(sys.executable),
        'inputs': bindings, 'outputs': [record(demo_path),record(report_path)],
        'real_evaluation_accessed': False, 'feature_or_model_changed': False,
        'formal_evaluation_ready': False, 'semantic_acceptance': False}
    with (destination/'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(record(destination/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
