"""Finish sidecar diagnostics after the map point-query limitation; never re-extract."""

import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from logs.diagnose_review8_20261012 import (NAMES, FEATURES, BASELINE, PROTOCOL, REPORT,
    TRAJECTORY, STATUS, EXTRACTOR, diagnose, exact_rows, verify_records, write_json)
from logs.build_semantic_review_pack_20261001 import record
from HDBSCAN.scripts.experiment_partition import load_partition, assert_development_frame, assert_new_outputs
from HDBSCAN.scripts.frozen_model import require_feature_provenance, source_hashes
from HDBSCAN.scripts.scene_feature_rules import (classify_mapped_vru_lane_relation,
    is_vru_path_conflict, distance_to_polyline, synchronized_path_closest_approach)

AMENDMENT = ROOT / 'HDBSCAN/tables/target_diagnosis8_continuation_protocol_20261012.json'
FAILED_STATUS = ROOT / 'logs/review8_target_diagnosis_20261012_failed_status.json'


class PolygonQueryMap:
    """Diagnostic-only adapter: non-geometric connector point occupancy is unknown."""

    def __init__(self, source):
        self.source = source

    def __getattr__(self, name):
        return getattr(self.source, name)

    def layers_on_point(self, x, y, names):
        result = self.source.layers_on_point(x, y, [n for n in names if n != 'lane_connector'])
        if 'lane_connector' in names:
            result['lane_connector'] = None
        return result


def load_geometry_helpers():
    # Load only five trusted definitions; no imports, CLI, data load, loops or file writes.
    names = {'compute_ann_velocity_xy', 'ego_frame_delta', 'ego_frame_vector',
             'mapped_actor_lane_geometry', 'mapped_vru_lane_relation'}
    tree = ast.parse(EXTRACTOR.read_text(encoding='utf-8'))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in selected} != names:
        raise ValueError('Frozen helper definitions missing')
    namespace = {'np': np, 'classify_mapped_vru_lane_relation': classify_mapped_vru_lane_relation,
        'is_vru_path_conflict': is_vru_path_conflict, 'distance_to_polyline': distance_to_polyline,
        'synchronized_path_closest_approach': synchronized_path_closest_approach}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(EXTRACTOR), 'exec'), namespace)
    return namespace


def main():
    assert_new_outputs([REPORT, AMENDMENT, FAILED_STATUS])
    old = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    verify_records(old['inputs'])
    if source_hashes() != old['source_hashes']:
        raise ValueError('Frozen sources changed')
    frame = pd.read_csv(FEATURES, float_precision='round_trip')
    reference = pd.read_csv(BASELINE, float_precision='round_trip')
    exact_rows(frame, reference)
    require_feature_provenance(FEATURES, frame)
    partition = load_partition()
    assert_development_frame(frame, partition)
    if set(frame.scene_name) != set(NAMES) or len(frame) != 8:
        raise ValueError('Continuation scope changed')
    quality_path = Path(str(FEATURES) + '.quality.json')
    quality = json.loads(quality_path.read_text())
    invalid = [r for r in quality['nonfinite_cells'] if r['kind'] != 'positive_inf'
               or r['column'] not in {'merge_observed_min_distance', 'vru_observed_min_distance'}]
    if quality['query_exception_count'] or invalid:
        raise ValueError('Replay quality is not clear')
    failed = json.loads(STATUS.read_text())
    if failed['phase'] != 'failed' or 'lane_connector is not a polygon layer' not in failed['error']:
        raise ValueError('Unexpected continuation state; do not start a duplicate job')
    write_json(FAILED_STATUS, failed)
    bound = [record(p) for p in [PROTOCOL, FEATURES, TRAJECTORY, quality_path,
        Path(str(FEATURES) + '.manifest.json'), FAILED_STATUS, Path(__file__),
        ROOT / 'logs/test_complete_target_diagnosis8_20261012.py']]
    write_json(AMENDMENT, {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'reason': 'lane_connector has no point polygon; diagnose only, do not re-extract eight completed rows',
        'command': [sys.executable, *sys.argv], 'inputs': bound, 'parent_protocol': record(PROTOCOL),
        'source_hashes': source_hashes(), 'non_geometric_point_query': {'lane_connector': 'unknown_not_queried'},
        'helper_loading': 'Only five trusted frozen function AST definitions; no extractor main executed',
        'feature_rules_or_existing_outputs_changed': False})
    write_json(STATUS, {'phase': 'continuing_diagnostics', 'pid': os.getpid(), 'amendment': record(AMENDMENT)}, False)
    try:
        from nuscenes import NuScenes
        from nuscenes.map_expansion.map_api import NuScenesMap
        namespace = load_geometry_helpers()
        namespace['nusc'] = NuScenes(version='v1.0-trainval', dataroot=str(ROOT / 'nuScenes'), verbose=True)
        locations = sorted(set(partition['by_name'][n]['log_location'] for n in NAMES))
        namespace['map_cache'] = {location: (PolygonQueryMap(NuScenesMap(
            dataroot=str(ROOT / 'nuScenes'), map_name=location)), None) for location in locations}
        findings = diagnose(namespace, frame)
        verify_records(old['inputs'])
        verify_records(bound)
        write_json(REPORT, {'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'command': [sys.executable, *sys.argv], 'protocol': record(PROTOCOL), 'continuation': record(AMENDMENT),
            'features': record(FEATURES), 'trajectory': record(TRAJECTORY), 'quality': record(quality_path),
            'scenes': findings, 'exact_candidate_rows_reproduced': True,
            'query_exception_count': quality['query_exception_count'],
            'nonfinite_diagnostic_cell_count': quality['nonfinite_cell_count'],
            'non_geometric_point_query': {'lane_connector': 'unknown_not_queried'},
            'evaluation_used': False, 'production_rules_changed': False, 'semantic_acceptance': False})
        write_json(STATUS, {'phase': 'completed_diagnostics_requires_review', 'pid': os.getpid(),
            'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'report': record(REPORT)}, False)
        print('COMPLETED: existing eight rows reused, all target diagnostics finished.', flush=True)
    except Exception as exc:
        write_json(STATUS, {'phase': 'continuation_failed', 'pid': os.getpid(),
                           'error': f'{type(exc).__name__}: {exc}'}, False)
        raise


if __name__ == '__main__':
    main()
