import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from HDBSCAN.tests.test_evaluation_split import workspace_tempdir


class RegressionContracts(unittest.TestCase):
    def test_actual_entry_preflight_accepts_fixed_subset_and_refuses_scope_escape(self):
        from logs import crossing_v5_1_regression_20261013 as recipe
        fixed = recipe.selection()[0]
        with workspace_tempdir() as directory:
            env = {**os.environ, **recipe.environment(fixed[:1]),
                   'SCENE_CLUSTER_FEATURE_OUTPUT': str(directory/'candidate.csv'),
                   'SCENE_CLUSTER_AUDIT_OUTPUT': str(directory/'tracks.json')}
            command = [sys.executable, str(recipe.EXTRACTOR), '--preflight']
            result = subprocess.run(command, env=env, cwd=recipe.ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            frame = pd.read_csv('HDBSCAN/tables/evaluation_split_20260924.csv')
            outside = frame.loc[(frame.split == 'development') & ~frame.scene_name.isin(fixed), 'scene_name'].iloc[0]
            env['SCENE_CLUSTER_SCENE_NAMES'] = outside
            result = subprocess.run(command, env=env, cwd=recipe.ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('fixed development29', result.stderr)

    def test_diff_refuses_unrelated_change(self):
        from logs.crossing_v5_1_regression_20261013 import compare_frames
        a = pd.DataFrame([{'scene_name': 'a', 'scene_token': 't', 'min_ttc': 5.}])
        b = a.copy()
        b['min_ttc'] = 2.
        with self.assertRaisesRegex(ValueError, 'Unrelated'):
            compare_frames(b, a)

    def test_diff_keeps_allowed_change_and_rejects_order_drift(self):
        from logs.crossing_v5_1_regression_20261013 import compare_frames
        a = pd.DataFrame([{'scene_name': 'a', 'scene_token': 't', 'crossing_vehicle_conflict_ratio': .1}])
        b = a.copy()
        b['crossing_vehicle_conflict_ratio'] = 0.
        self.assertEqual(len(compare_frames(b, a)), 1)
        b['scene_token'] = 'different'
        with self.assertRaises(ValueError):
            compare_frames(b, a)

    def test_uncertainty_inclusion_is_not_dropped_from_comparison(self):
        from logs.crossing_v5_1_regression_20261013 import recompute_crossing_row
        row = {'ego_first_stop_time': -1, 'traffic_light_control_density': 0,
               'crossing_vehicle_exposure_ratio': .5, 'intersection_stop_ratio': 0,
               'blocked_path_obstacle_ratio': 0}
        audit = {'times': [0, .5, 1.], 'crossing_route_flags': [False]*3,
                 'obstacle_induced_route_deviation_candidate': False}
        summary = recompute_crossing_row(row, audit, [False, True, False], [False]*3)
        self.assertAlmostEqual(summary['crossing_vehicle_conflict_ratio'], 1/3)
        self.assertEqual(summary['crossing_conflict_max_duration'], .5)

    def test_current_formal_fitter_refuses_candidate_manifest(self):
        from HDBSCAN.scripts.frozen_model import require_feature_provenance
        frame = pd.read_csv('HDBSCAN/tables/scene_features_development_candidate700_20261001.csv').iloc[:1]
        with workspace_tempdir() as directory:
            path = Path(directory)/'candidate.csv'
            frame.to_csv(path, index=False)
            Path(str(path)+'.manifest.json').write_text(json.dumps({'stage': 'candidate_feature_extraction'}))
            with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
                require_feature_provenance(path, frame)

    def test_publication_uses_actual_grouped_risk_column(self):
        from logs import crossing_v5_1_regression_20261013 as recipe
        from HDBSCAN.scripts.corner_scoring import calculate_grouped_risk
        frame = pd.read_csv('HDBSCAN/tables/scene_features_development_candidate700_20261001.csv').iloc[:1]
        score = frame[['scene_name', 'scene_token']].copy()
        for prefix in ('v4', 'v5_resolved', 'v5_with_unresolved'):
            for column, values in calculate_grouped_risk(frame).items():
                score[prefix+'_'+column] = values.to_numpy()
        score['unresolved_crossing_ratio'] = 0.
        name = frame.iloc[0].scene_name
        report = {'changed_scenes': [], 'changes': [], 'clustering_changes': [],
                  'nonfinite_diagnostic_cells': 0, 'unresolved_by_scene': {name: 0.}}
        with workspace_tempdir() as directory:
            document, pending = directory/'summary.md', directory/'pending.md'
            with patch.object(recipe, 'DOCUMENT', document), patch.object(recipe, 'PENDING', pending):
                recipe.publish(frame, score, report, {name: []})
            self.assertIn(name, document.read_text(encoding='utf-8'))

    def test_changed_prepared_protocol_is_refused_before_launch(self):
        from logs import crossing_v5_1_regression_20261013 as recipe
        from logs.build_semantic_review_pack_20261001 import record
        with workspace_tempdir() as directory:
            protocol, status = directory/'protocol.json', directory/'status.json'
            protocol.write_text(json.dumps({'environment': {'SCENE_CLUSTER_SCENE_NAMES': 'original'}}))
            status.write_text(json.dumps({'phase': 'prepared', 'protocol': record(protocol)}))
            protocol.write_text(json.dumps({'environment': {'SCENE_CLUSTER_SCENE_NAMES': 'changed'}}))
            with patch.object(recipe, 'PROTOCOL', protocol), patch.object(recipe, 'STATUS', status):
                with self.assertRaisesRegex(ValueError, 'Bound source changed'):
                    recipe.load_bound_protocol()

    def test_frozen_runtime_mismatch_is_refused(self):
        from logs import crossing_v5_1_regression_20261013 as recipe
        runtime = recipe.runtime_record()
        recipe.validate_runtime(runtime)
        runtime['python'] = 'incompatible'
        with self.assertRaisesRegex(ValueError, 'runtime'):
            recipe.validate_runtime(runtime)

    def test_positive_control_gate_refuses_lost_yield_and_preserves_input(self):
        from logs.crossing_v5_1_regression_20261013 import check_positive_controls
        frame = pd.read_csv('HDBSCAN/tables/scene_features_development_candidate700_20261001.csv')
        frame = frame.set_index('scene_name').loc[['scene-0068','scene-0552','scene-0453']].reset_index()
        check_positive_controls(frame)
        frame.loc[frame.scene_name == 'scene-0068', 'left_turn_cross_traffic_interaction_ratio'] = 0.
        with self.assertRaisesRegex(ValueError, 'positive control'):
            check_positive_controls(frame)


if __name__ == '__main__':
    unittest.main()
