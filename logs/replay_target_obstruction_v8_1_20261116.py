"""Compare identity-local blocked aggregation against the saved v8 experiment."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from HDBSCAN.scripts import longitudinal_candidate_v7 as legacy
from HDBSCAN.scripts import target_obstruction_v8_1 as candidate


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    output = ROOT/'logs/target_obstruction_v8_1_development29_20261116.json'
    if output.exists():
        raise FileExistsError('Preserve original comparison')
    source = ROOT/'logs/target_obstruction_v8_development29_20261116.json'
    prior = json.loads(source.read_text(encoding='utf8'))
    for record in prior['sources']:
        if digest(record['path']) != record['sha256']:
            raise ValueError('v8 source changed')
    tables = ROOT/'HDBSCAN/tables'
    v7report = json.loads((tables/'longitudinal_v7_replay29_comparison_20261015.json').read_text(encoding='utf8'))
    for record in v7report['outputs']:
        if digest(record['path']) != record['sha256']:
            raise ValueError('v7 output changed')
    audits = json.loads((tables/'crossing_v5_2_regression29_trajectory_20261013.json').read_text(encoding='utf8'))
    ledgers = json.loads((tables/'longitudinal_v7_replay29_ledger_20261015.json').read_text(encoding='utf8'))['scenes']
    rows = pd.read_csv(tables/'scene_features_longitudinal_v7_replay29_20261015.csv', float_precision='round_trip')
    names = rows.scene_name.tolist()
    if len(names) != 29 or any([r['scene_name'] for r in collection] != names for collection in (audits, ledgers, prior['scenes'])):
        raise ValueError('Fixed29 identity/order mismatch')
    results = []
    for a, l, p, row in zip(audits, ledgers, prior['scenes'], rows.to_dict('records')):
        rejected = {tuple(v) for v in l['rejected'] + p['extra_rejected']}
        before, trace = legacy.summarize(a, l['ledger'], row, rejected)
        expected = {k: dict(before=row[k], after=v) for k, v in before.items() if v != row[k]}
        if expected != p['changes']:
            raise ValueError('Saved v8 change mismatch')
        after, evidence = candidate.update_blockage(a, row, before, trace)
        changes = {k: dict(before=before[k], after=v) for k, v in after.items() if v != before[k]}
        if row['scene_name'] in {'scene-0011', 'scene-0030', 'scene-0026', 'scene-0042'} and changes:
            raise ValueError('Positive control changed')
        results.append(dict(scene_name=row['scene_name'], changes=changes, evidence=evidence,
                            blocked_ratio=after['blocked_path_obstacle_ratio'], min_ttc=after['min_ttc']))
    result = dict(scope='fixed development29 candidate; same v8 target gates; no fit', scenes=results,
                  sources=[dict(path=str(p), sha256=digest(p)) for p in
                           [source, Path(__file__), Path(candidate.__file__)]])
    with output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps([dict(scene=r['scene_name'], changes=r['changes'], raw=r['evidence']['raw_deviation'])
                      for r in results if r['changes']], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
