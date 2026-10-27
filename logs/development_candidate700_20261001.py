"""User-approved candidate freeze, development-only rebuild and dependent QA."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from HDBSCAN.scripts.corner_scoring import calculate_grouped_risk
from HDBSCAN.scripts.experiment_partition import (
    assert_development_frame, assert_new_outputs, current_features, file_record,
    load_partition, select_development_scenes,
)
from HDBSCAN.scripts.feature_selection import CLUSTERING_FEATURES
from HDBSCAN.scripts.frozen_model import require_feature_provenance, source_hashes
from logs.crossing_regression33_20261001 import baseline, revision_review_flags
from logs.check_development_audit700_20260927 import compare_frames, review_reasons

TABLES = ROOT / 'HDBSCAN/tables'
OUTPUT = TABLES / 'scene_features_development_candidate700_20261001.csv'
PROTOCOL = TABLES / 'development_candidate700_protocol_20261001.json'
REPORT = TABLES / 'development_candidate700_comparison_20261001.json'
RISK = TABLES / 'development_candidate700_risk_20261001.csv'
STATUS = ROOT / 'logs/development_candidate700_20261001_status.json'
CONSOLE = ROOT / 'logs/development_candidate700_20261001_console.log'
SNAPSHOT = ROOT / 'logs/source_snapshot_candidate_20261001'
REGRESSION = TABLES / 'scene_features_crossing_regression33_20261001.csv'
SEVEN = TABLES / 'scene_features_semantic_feedback7_20261001_v4.csv'
EXTRACTOR = ROOT / 'HDBSCAN/scripts/scene_feature_hdbscan.py'
ENVIRONMENT = {
    'SCENE_CLUSTER_MAX_SCENES': '700', 'SCENE_CLUSTER_START_INDEX': '0',
    'SCENE_CLUSTER_SCENE_NAMES': '', 'SCENE_CLUSTER_AUDIT_OUTPUT': '',
    'SCENE_CLUSTER_FEATURE_OUTPUT': OUTPUT.name,
    'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
    'NUMBA_NUM_THREADS': '1', 'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8',
}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value, exclusive=True):
    with path.open('x' if exclusive else 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def runtime():
    packages = ['numpy', 'pandas', 'nuscenes-devkit', 'shapely', 'pyquaternion']
    return {'executable': file_record(sys.executable), 'python': platform.python_version(),
            'packages': {name: importlib.metadata.version(name) for name in packages}}


def verify_records(records):
    for record in records:
        if file_record(record['path'])['sha256'] != record['sha256']:
            raise ValueError('Frozen input/source changed: ' + record['path'])


def validate_frame(frame, names, columns, features):
    if (frame.scene_name.tolist() != names or list(frame.columns) != columns
            or not frame.scene_name.is_unique or not frame.scene_token.is_unique
            or frame[['scene_name', 'scene_token']].isna().any().any()):
        raise ValueError('Candidate identity/order/schema mismatch')
    values = frame[features].apply(pd.to_numeric, errors='coerce').to_numpy(dtype=float)
    if (not np.isfinite(values).all()
            or not np.isfinite(frame.select_dtypes(include='number').to_numpy()).all()):
        raise ValueError('Candidate nonfinite or nonnumeric features')


def assert_controls(frame, controls):
    ordered = frame.set_index('scene_name').loc[controls.scene_name].reset_index()
    pd.testing.assert_frame_equal(ordered, controls.reset_index(drop=True),
                                  check_dtype=False, rtol=0, atol=0)


def review_flags(changes, before, after):
    flags = revision_review_flags({r['column'] for r in changes}, before, after)
    flags['pending_semantic_scenes'] = sorted({'scene-0552'} |
        ({r['scene_name'] for r in changes} - {'scene-0151'}))
    flags['requires_review'] = True  # Candidate freeze never clears the pending 0552 case.
    return flags


def output_paths():
    return [OUTPUT, Path(str(OUTPUT) + '.quality.json'), Path(str(OUTPUT) + '.manifest.json'),
            REPORT, RISK, CONSOLE, STATUS]


def prepare():
    assert_new_outputs([PROTOCOL, SNAPSHOT, *output_paths()])
    partition = load_partition()
    old = baseline(partition)
    if old.shape != (700, 129) or len(CLUSTERING_FEATURES) != 52:
        raise ValueError('Unexpected baseline/schema dimensions')
    metadata = ROOT / 'nuScenes/v1.0-trainval/scene.json'
    selection = select_development_scenes(read_json(metadata), partition, '', 0, 700)
    names = [r['name'] for r in selection]
    if len(names) != 700 or set(names) != set(old.scene_name):
        raise ValueError('Incomplete development selection')
    for path in (REGRESSION, SEVEN):
        controls = pd.read_csv(path, float_precision='round_trip')
        require_feature_provenance(path, controls)
    hashes = source_hashes()
    inputs = [metadata, Path(partition['file']['path']),
              TABLES / 'evaluation_split_20260924_manifest.json',
              TABLES / 'scene_features_development_audit700_20260927.csv',
              REGRESSION, SEVEN]
    for path in (inputs[3], REGRESSION, SEVEN):
        inputs.extend([Path(str(path) + '.manifest.json'), Path(str(path) + '.quality.json')])
    helpers = [Path(__file__), ROOT / 'logs/test_development_candidate700_20261001.py',
               ROOT / 'logs/crossing_regression33_20261001.py',
               ROOT / 'logs/check_development_audit700_20260927.py']
    historical_sources = ROOT / 'logs/source_snapshot_20261001_pre_turning_crossing/HDBSCAN/scripts'
    inputs.extend(historical_sources / name for name in hashes)
    records = [file_record(path) for path in inputs + helpers]
    SNAPSHOT.mkdir()
    for name, digest in hashes.items():
        path = ROOT / 'HDBSCAN/scripts' / name
        if file_record(path)['sha256'] != digest:
            raise ValueError('Source changed while freezing')
        shutil.copy2(path, SNAPSHOT / name)
    for path in inputs[1:3]:
        shutil.copy2(path, SNAPSHOT / path.name)
    if source_hashes() != hashes:
        raise ValueError('Source changed while freezing')
    snapshot_records = [file_record(path) for path in sorted(SNAPSHOT.iterdir())]
    protocol = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'candidate_version': 'feature_candidate_v4_20261001',
        'authorization': 'Human approved candidate freeze and current-source development700 rebuild: 好的 那开始吧',
        'scope': 'Development-only metadata extraction and structural QA; not semantic acceptance',
        'source_hashes': hashes, 'bound_records': records + snapshot_records,
        'runtime': runtime(), 'environment': ENVIRONMENT,
        'commands': {'preflight': [sys.executable, str(EXTRACTOR), '--preflight'],
                     'extract': [sys.executable, str(EXTRACTOR)]},
        'scene_names': names, 'scene_tokens': [r['token'] for r in selection],
        'columns': old.columns.tolist(), 'clustering_features': CLUSTERING_FEATURES,
        'output': str(OUTPUT), 'report': str(REPORT), 'pending_semantic_scenes': ['scene-0552'],
        'final_parameters': None, 'fit_requested': False, 'evaluation_requested': False,
        'kmeans_requested': False, 'media_requested': False, 'trajectory_export': False,
        'limitations': ['Only scene selection metadata is hash-bound among raw nuScenes tables; other raw tables/maps are not fully hashed.',
                       'Projection and rolling-yield causality remain limited; no new accuracy claims.',
                       'Risk deltas can have either sign; all newly changed scenes require review.'],
    }
    write_json(PROTOCOL, protocol)
    print(json.dumps({'protocol': file_record(PROTOCOL), 'scene_count': len(names),
                      'candidate_version': protocol['candidate_version']}, ensure_ascii=False), flush=True)


def verify_freeze():
    protocol = read_json(PROTOCOL)
    verify_records(protocol['bound_records'])
    if protocol['source_hashes'] != source_hashes() or protocol['runtime'] != runtime():
        raise ValueError('Frozen candidate source/runtime mismatch')
    return protocol


def check(check_only=False):
    protocol = verify_freeze()
    current = pd.read_csv(OUTPUT, float_precision='round_trip')
    require_feature_provenance(OUTPUT, current)
    partition = load_partition()
    assert_development_frame(current, partition)
    validate_frame(current, protocol['scene_names'], protocol['columns'], protocol['clustering_features'])
    if current.scene_token.tolist() != protocol['scene_tokens']:
        raise ValueError('Frozen tokens mismatch')
    for path in (REGRESSION, SEVEN):
        assert_controls(current, pd.read_csv(path, float_precision='round_trip'))
    old = baseline(partition).set_index('scene_name').loc[current.scene_name].reset_index()
    comparison = compare_frames(old, current)
    before, after = calculate_grouped_risk(old), calculate_grouped_risk(current)
    risk = current[['scene_name', 'scene_token', 'log_location']].copy()
    for column in before:
        risk[column + '_before'] = before[column]
        risk[column + '_after'] = after[column]
    risk['risk_delta'] = after.risk - before.risk
    flags = review_flags(comparison['changes'], before.assign(scene_name=current.scene_name),
                         after.assign(scene_name=current.scene_name))
    quality_path = Path(str(OUTPUT) + '.quality.json')
    quality = read_json(quality_path)
    quality_flags = review_reasons(quality, 0)
    features = current_features(current)
    cluster_changes = old[CLUSTERING_FEATURES] != current[CLUSTERING_FEATURES]
    report = {
        'scope': protocol['scope'], 'candidate_version': protocol['candidate_version'],
        'protocol': file_record(PROTOCOL), 'input': file_record(OUTPUT),
        'manifest': file_record(Path(str(OUTPUT) + '.manifest.json')),
        'quality': file_record(quality_path), 'source_hashes': protocol['source_hashes'],
        'scene_count': len(current), 'column_count': len(current.columns),
        'clustering_feature_count': len(features.columns),
        'all_development_members_present_once': True, 'structural_source_checks_passed': True,
        'regression33_and_seven_controls_exactly_reproduced': True,
        'map_available_scene_count': int(current.map_available.eq(1).sum()),
        'intersection_flag_positive_count': int(current.intersection_flag.gt(0).sum()),
        'constant_clustering_features': [c for c in features if features[c].nunique() == 1],
        'query_exception_count': quality['query_exception_count'],
        'query_exception_counts_by_stage': quality['query_exception_counts_by_stage'],
        'nonfinite_by_column': quality['nonfinite_by_column'],
        'nonfinite_cell_count': quality['nonfinite_cell_count'],
        'raw_quality_checks_clear': not quality_flags, 'quality_review_reasons': quality_flags,
        'feature_comparison': comparison, 'changed_clustering_cell_count': int(cluster_changes.to_numpy().sum()),
        'changed_clustering_fields': cluster_changes.columns[cluster_changes.any()].tolist(),
        'risk_changed_scenes': risk.loc[risk.risk_delta.abs() > 1e-15].to_dict('records'),
        'review_flags': flags, 'semantic_validity_verified': False,
        'fit_started': False, 'model_or_ranking_replaced': False,
    }
    verify_freeze()
    if check_only:
        if read_json(REPORT) != report:
            raise ValueError('Saved QA report differs from fresh verification')
        pd.testing.assert_frame_equal(pd.read_csv(RISK, float_precision='round_trip'), risk,
                                      check_dtype=False, rtol=0, atol=0)
    else:
        assert_new_outputs([REPORT, RISK])
        write_json(REPORT, report)
        risk.to_csv(RISK, index=False, mode='x')
    print(json.dumps({k: report[k] for k in ['scene_count', 'query_exception_count',
                      'changed_clustering_cell_count', 'raw_quality_checks_clear', 'review_flags']},
                     ensure_ascii=False), flush=True)
    return report


def run():
    protocol = verify_freeze()
    assert_new_outputs(output_paths())
    state = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'wrapper_pid': os.getpid(),
             'protocol': file_record(PROTOCOL), 'phase': 'preflight', 'console': str(CONSOLE)}
    write_json(STATUS, state)
    environment = os.environ.copy()
    environment.update(protocol['environment'])
    try:
        with CONSOLE.open('x', encoding='utf-8') as console:
            for phase, command in protocol['commands'].items():
                verify_freeze()
                state['phase'] = phase
                console.write('COMMAND ' + json.dumps(command) + '\n')
                console.flush()
                child = subprocess.Popen(command, cwd=ROOT, env=environment,
                                         stdout=console, stderr=subprocess.STDOUT)
                state['child_pid'] = child.pid
                write_json(STATUS, state, exclusive=False)
                print(phase + ' pid=' + str(child.pid), flush=True)
                code = child.wait()
                state['child_exit_code'] = code
                if code:
                    raise RuntimeError(phase + ' exited ' + str(code))
            state['phase'] = 'checking'
            write_json(STATUS, state, exclusive=False)
            report = check()
            state['phase'] = 'completed_requires_review'
            state['report'] = file_record(REPORT)
            state['raw_quality_checks_clear'] = report['raw_quality_checks_clear']
    except BaseException as error:
        state['phase'] = 'failed'
        state['error'] = repr(error)
        raise
    finally:
        state['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(STATUS, state, exclusive=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'run', 'check'])
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only and args.stage != 'check':
        parser.error('--check-only applies to check stage')
    {'prepare': prepare, 'run': run, 'check': lambda: check(args.check_only)}[args.stage]()
