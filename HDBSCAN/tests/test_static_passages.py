import copy
import json
import unittest

from HDBSCAN.scripts import audit_static_passages as audit
from HDBSCAN.tests.test_evaluation_split import workspace_tempdir


def example():
    forward = [15, 10, 5, 0, -5, -10, -15]
    return {'scene_name': 'synthetic', 'scene_token': 'token',
            'times': [i * .5 for i in range(7)],
            'ego_positions': [[15 - f, 0] for f in forward], 'ego_yaws': [0] * 7,
            'vehicle_tracks': {'parked': [
                {'index': i, 'position': [15, 3.3], 'velocity': [0, 0],
                 'forward': f, 'lateral': 3.3, 'heading_delta': 0,
                 'width': 1.8, 'length': 4.3, 'category': 'vehicle.car'}
                for i, f in enumerate(forward)]}}


def mapped(scene, row):
    return {'available': True, 'on_drivable': True, 'same_lane': True, 'same_road': True}


class StaticPassagesTest(unittest.TestCase):
    def test_complete_pass_is_diagnostic_not_evasive_maneuver(self):
        result = audit.find_passages(example(), mapped)
        event = result['candidates'][0]
        self.assertEqual(event['motion_status'], 'static_supported')
        self.assertAlmostEqual(event['lateral_clearance_m'], 1.475)
        self.assertEqual(event['path_evidence'], 'no_clear_lateral_maneuver')
        self.assertEqual(event['avoidance_cause'], 'undetermined')

    def test_parallel_parked_cars_remain_separate_instances(self):
        scene = example()
        scene['vehicle_tracks']['other'] = copy.deepcopy(scene['vehicle_tracks']['parked'])
        self.assertEqual(len(audit.find_passages(scene, mapped)['candidates']), 2)

    def test_no_passing_far_target_and_moving_vehicle_are_not_candidates(self):
        for field, value in [('forward', 10), ('lateral', 9), ('velocity', [3, 0])]:
            scene = example()
            for row in scene['vehicle_tracks']['parked']:
                row[field] = value
            self.assertEqual(audit.find_passages(scene, mapped)['candidates'], [])

    def test_offroad_other_lane_and_unknown_map_are_not_confirmed(self):
        for evidence in [dict(mapped(None, None), on_drivable=False),
                         dict(mapped(None, None), same_lane=False, same_road=False),
                         {'available': False, 'error': 'missing map'}]:
            result = audit.find_passages(example(), lambda s, r: evidence)
            self.assertEqual(result['candidates'], [])
            self.assertEqual(len(result['excluded']), 1)

    def test_small_speed_with_unbounded_drift_remains_uncertain(self):
        scene = example()
        for row in scene['vehicle_tracks']['parked']:
            row['velocity'] = [.8, 0]
            row['position'][0] += row['index'] * .4
        result = audit.find_passages(scene, mapped)
        self.assertEqual(result['candidates'][0]['motion_status'], 'low_speed_uncertain')

    def test_sustained_creep_below_half_metre_per_second_is_not_static(self):
        scene = example()
        scene['times'] = [i*.5 for i in range(41)]
        scene['ego_yaws'] = [0]*41
        rows = []
        scene['ego_positions'] = []
        for i, t in enumerate(scene['times']):
            row = copy.deepcopy(example()['vehicle_tracks']['parked'][0])
            row.update(index=i, position=[15+.4*t, 3.3], velocity=[.4, 0], forward=30-3*t)
            rows.append(row)
            scene['ego_positions'].append([row['position'][0]-row['forward'], 0])
        scene['vehicle_tracks']['parked'] = rows
        self.assertEqual(audit.find_passages(scene, mapped)['candidates'][0]['motion_status'],
                         'low_speed_uncertain')

    def test_later_motion_does_not_erase_static_passage(self):
        scene = example()
        scene['times'].append(3.5)
        scene['ego_yaws'].append(0)
        scene['ego_positions'].append([66, 0])
        row = copy.deepcopy(scene['vehicle_tracks']['parked'][-1])
        row.update(index=7, position=[16, 3.3], velocity=[2, 0], forward=-50)
        scene['vehicle_tracks']['parked'].append(row)
        events = audit.find_passages(scene, mapped)['candidates']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['motion_status'], 'static_supported')
        self.assertTrue(events[0]['motion_elsewhere_observed'])

    def test_lateral_motion_and_curve_do_not_claim_avoidance(self):
        scene = example()
        scene['ego_positions'] = [[i*5, i*.4] for i in range(7)]
        event = audit.find_passages(scene, mapped)['candidates'][0]
        self.assertEqual(event['path_evidence'], 'lateral_motion_observed')
        scene['ego_yaws'] = [i*.1 for i in range(7)]
        self.assertEqual(audit.find_passages(scene, mapped)['candidates'][0]['path_evidence'],
                         'curved_path_uncertain')

    def test_gaps_and_incomplete_track_do_not_invent_passage(self):
        scene = example()
        scene['vehicle_tracks']['parked'] = scene['vehicle_tracks']['parked'][:3]
        self.assertEqual(audit.find_passages(scene, mapped)['candidates'], [])
        scene = example()
        scene['times'] = [0, .5, 1, 5, 5.5, 6, 6.5]
        self.assertEqual(audit.find_passages(scene, mapped)['candidates'], [])

    def test_missing_dimensions_and_nonfinite_evidence_fail(self):
        for key, value in [('width', None), ('lateral', float('nan')), ('index', 999)]:
            scene = example()
            scene['vehicle_tracks']['parked'][0][key] = value
            with self.assertRaises(ValueError):
                audit.find_passages(scene, mapped)

    def test_pair_provenance_rejects_legacy_or_changed_audit(self):
        with workspace_tempdir() as root:
            features, trajectory = root / 'features.csv', root / 'trajectory.json'
            features.write_text('scene_name\nsynthetic\n', encoding='utf-8')
            trajectory.write_text('[]', encoding='utf-8')
            record = {'stage': 'feature_extraction', 'output': audit.file_record(features),
                      'extra': {'trajectory_audit': audit.file_record(trajectory)}}
            manifest = audit.provenance_path(features)
            manifest.write_text(json.dumps(record), encoding='utf-8')
            audit.validate_pair(features, trajectory)
            trajectory.write_text('[{}]', encoding='utf-8')
            with self.assertRaises(ValueError):
                audit.validate_pair(features, trajectory)
            record['extra'] = {}
            manifest.write_text(json.dumps(record), encoding='utf-8')
            with self.assertRaises(ValueError):
                audit.validate_pair(features, trajectory)


if __name__ == '__main__':
    unittest.main()
