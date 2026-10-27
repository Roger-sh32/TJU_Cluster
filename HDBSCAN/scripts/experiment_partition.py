"""Fail-closed development partition checks shared by experiment entry points."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

try:
    from .feature_selection import CLUSTERING_FEATURES
except ImportError:
    from feature_selection import CLUSTERING_FEATURES


DEFAULT_SPLIT = Path(__file__).resolve().parents[1] / 'tables/evaluation_split_20260924.csv'


def file_record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def load_partition():
    manifest = json.loads(DEFAULT_SPLIT.with_name(DEFAULT_SPLIT.stem + '_manifest.json').read_text(encoding='utf-8'))
    record = file_record(DEFAULT_SPLIT)
    if record['sha256'] != manifest['output']['sha256']:
        raise ValueError('Frozen partition hash mismatch')
    frame = pd.read_csv(DEFAULT_SPLIT, keep_default_na=False)
    required = {'scene_name', 'scene_token', 'log_token', 'log_location', 'split'}
    if not required.issubset(frame.columns) or frame.empty:
        raise ValueError('Invalid partition schema')
    if any((frame[c] == '').any() for c in required):
        raise ValueError('Missing partition identity')
    if not frame.scene_name.is_unique or not frame.scene_token.is_unique:
        raise ValueError('Duplicate partition identity')
    if dict(Counter(frame['split'])) != manifest['counts']:
        raise ValueError('Partition counts do not match manifest')
    if set(frame['split']) != {'development', 'evaluation'}:
        raise ValueError('Unknown partition role')
    if (frame.groupby('log_token')['split'].nunique() > 1).any():
        raise ValueError('Log overlaps development and evaluation')
    rows = frame.to_dict('records')
    return {'rows': rows, 'by_name': {r['scene_name']: r for r in rows}, 'file': record}


def assert_development_frame(frame, partition):
    if frame.empty or not {'scene_name', 'scene_token'}.issubset(frame.columns):
        raise ValueError('Input must contain nonempty scene_name and scene_token identities')
    if frame[['scene_name', 'scene_token']].isna().any().any():
        raise ValueError('Missing scene identity')
    if not frame.scene_name.is_unique or not frame.scene_token.is_unique:
        raise ValueError('Duplicate scene identity')
    evaluation = []
    for row in frame.to_dict('records'):
        reference = partition['by_name'].get(row['scene_name'])
        if reference is None:
            raise ValueError(f"Unknown scene: {row['scene_name']}")
        for column in ['scene_token', 'log_token', 'log_location', 'split']:
            if column in row and row[column] != reference[column]:
                raise ValueError(f"Scene identity/role mismatch: {row['scene_name']} {column}")
        if reference['split'] != 'development':
            evaluation.append(row['scene_name'])
    if evaluation:
        raise ValueError(f'Input contains {len(evaluation)} evaluation scenes; development entry refuses to fit/score them')


def current_features(frame):
    missing = set(CLUSTERING_FEATURES) - set(frame.columns)
    if missing:
        raise ValueError(f'Outdated feature schema; missing current semantic columns: {sorted(missing)}')
    features = frame[CLUSTERING_FEATURES].apply(pd.to_numeric, errors='coerce')
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError('Non-finite or nonnumeric semantic features; repair extraction rather than fill with zero')
    return features


def validate_cluster_columns(frame):
    columns = ['cluster', 'cluster_probability', 'cluster_outlier_score']
    if not set(columns).issubset(frame.columns):
        raise ValueError('Missing clustering evidence columns')
    values = frame[columns].apply(pd.to_numeric, errors='coerce').to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Non-finite clustering evidence; do not substitute zero risk')
    if ((values[:, 0] < -1).any() or (values[:, 0] != np.floor(values[:, 0])).any()
            or (values[:, 1:] < 0).any() or (values[:, 1:] > 1).any()):
        raise ValueError('Invalid cluster labels, probabilities or outlier scores')


def load_development_features(path):
    partition = load_partition()
    frame = pd.read_csv(path)
    assert_development_frame(frame, partition)
    return frame, current_features(frame), partition


def select_development_scenes(scenes, partition, requested='', start=0, limit=700):
    if start < 0 or limit <= 0:
        raise ValueError('Invalid development batch range')
    names = [scene['name'] for scene in scenes]
    if len(set(names)) != len(names) or set(names) != set(partition['by_name']):
        raise ValueError('Scene metadata does not match frozen corpus')
    for scene in scenes:
        reference = partition['by_name'][scene['name']]
        if (scene['token'] != reference['scene_token'] or scene['log_token'] != reference['log_token']):
            raise ValueError('Scene metadata identity mismatch')
    if requested:
        selected = {name.strip() for name in requested.split(',') if name.strip()}
        if not selected or selected - set(names):
            raise ValueError('Unknown requested scene names')
        if any(partition['by_name'][name]['split'] != 'development' for name in selected):
            raise ValueError('Named evaluation scene refused by development extractor')
        return [scene for scene in scenes if scene['name'] in selected]
    available = [scene for scene in scenes if partition['by_name'][scene['name']]['split'] == 'development']
    batch = available[start:start + limit]
    if not batch:
        raise ValueError('Empty development scene batch')
    return batch


def assert_new_outputs(paths):
    for path in paths:
        if Path(path).exists():
            raise FileExistsError(f'Output already exists; use a new versioned filename: {path}')


def provenance_path(output):
    return Path(str(output) + '.manifest.json')


def preflight(stage, frame, partition, features=None):
    report = {'stage': stage, 'preflight_only': True, 'fit_scope': 'development',
              'scene_count': len(frame), 'split_sha256': partition['file']['sha256'],
              'semantic_feature_count': len(features.columns) if features is not None else None}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def write_run_manifest(output, stage, input_path, frame, partition, script, features=None, extra=None):
    assert_development_frame(frame, partition)
    path = provenance_path(output)
    assert_new_outputs([path])
    record = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'stage': stage,
        'fit_scope': 'development', 'python': sys.executable, 'command': [sys.executable, *sys.argv],
        'input': file_record(input_path), 'output': file_record(output), 'partition': partition['file'],
        'script': file_record(script), 'guard': file_record(__file__),
        'feature_schema': file_record(Path(__file__).with_name('feature_selection.py')),
        'scene_names': frame.scene_name.tolist(),
        'semantic_features': list(features.columns) if features is not None else [], 'extra': extra or {},
    }
    with path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)


def require_fit_provenance(input_path, frame, partition):
    assert_development_frame(frame, partition)
    path = provenance_path(input_path)
    if not path.exists():
        raise ValueError('Missing protected development-fit provenance; legacy clusters cannot be used as a formal run')
    record = json.loads(path.read_text(encoding='utf-8'))
    if (record.get('stage') != 'cluster_fit' or record.get('fit_scope') != 'development'
            or record['partition']['sha256'] != partition['file']['sha256']
            or record['output']['sha256'] != file_record(input_path)['sha256']
            or record.get('scene_names') != frame.scene_name.tolist()):
        raise ValueError('Invalid development-fit provenance')
    validate_cluster_columns(frame)
    return record
