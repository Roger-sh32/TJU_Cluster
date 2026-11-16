import unittest

from HDBSCAN.scripts.target_obstruction_v8 import obstruction_episodes
from HDBSCAN.scripts import target_obstruction_v8 as candidate


class TargetObstructionTests(unittest.TestCase):
    def test_distinct_targets_cannot_accumulate_duration(self):
        rows = obstruction_episodes(['a', 'b', 'c', 'd'], [0., .5, 1., 1.5])
        self.assertEqual([r['observed_duration'] for r in rows], [0.] * 4)

    def test_same_target_retains_observed_span(self):
        rows = obstruction_episodes(['a', 'a', 'a'], [0., .5, 1.])
        self.assertEqual(rows[0]['observed_duration'], 1.)
        self.assertEqual(rows[0]['indices'], [0, 1, 2])

    def test_absence_and_identity_switch_break_episode(self):
        rows = obstruction_episodes(['a', None, 'a', 'b', 'a'], [0., .5, 1., 1.5, 2.])
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r['observed_duration'] == 0 for r in rows))

    def test_sampling_gap_breaks_same_target_episode(self):
        rows = obstruction_episodes(['a', 'a', 'a'], [0., .5, 2.])
        self.assertEqual([r['indices'] for r in rows], [[0, 1], [2]])

    def test_single_frame_keeps_evidence_without_inventing_duration(self):
        self.assertEqual(obstruction_episodes(['a'], [0.])[0]['indices'], [0])
        self.assertEqual(obstruction_episodes(['a'], [0.])[0]['observed_duration'], 0.)

    def test_invalid_inputs_rejected(self):
        for ids, times in [(['a'], []), (['a', 'a'], [0., 0.]),
                           (['a'], [float('nan')]), ([''], [0.]), ([1], [0.])]:
            with self.assertRaises(ValueError):
                obstruction_episodes(ids, times)
        for gap in [0., -1., float('inf'), True]:
            with self.assertRaises(ValueError):
                obstruction_episodes(['a'], [0.], maximum_gap=gap)

    def test_empty_observations(self):
        self.assertEqual(obstruction_episodes([], []), [])

    def history(self):
        return dict(times=[0., .5, 1., 1.5], ego_positions=[[0., 0.]]*4,
                    ego_yaws=[0., 0., .3, .5], vehicle_tracks={'a': [
                        dict(index=i, position=[10., 8.], heading_delta=-yaw,
                             width=2., length=4.)
                        for i, yaw in enumerate([0., 0., .3, .5])]})

    def test_history_requires_real_target_and_ego_bracketing(self):
        a = self.history()
        result = candidate.target_history_evidence(a, 'a', 3)
        self.assertTrue(result['complete'])
        self.assertAlmostEqual(result['clearance'], 6.)
        self.assertFalse(candidate.target_history_evidence(a, 'a', 1)['complete'])
        a['vehicle_tracks']['a'].pop(1)
        self.assertFalse(candidate.target_history_evidence(a, 'a', 3)['complete'])

    def test_history_gap_is_unknown(self):
        a = self.history()
        a['times'] = [0., .2, 1.1, 1.5]
        self.assertFalse(candidate.target_history_evidence(a, 'a', 3)['complete'])

    def test_history_uses_both_bracketing_headings(self):
        a = self.history()
        a['times'] = [0., .6, 1., 1.5]
        a['ego_yaws'][1] = .5
        a['vehicle_tracks']['a'][1]['heading_delta'] = -.5
        self.assertLess(candidate.target_history_evidence(a, 'a', 3)['clearance'], 6.)

    def test_held_heading_geometry_uses_body_not_center_only(self):
        evidence = candidate.held_heading_clearance([10., 3.], 0., 0., 2., 4., 2.)
        self.assertAlmostEqual(evidence['lateral_body_clearance'], 1.)
        self.assertAlmostEqual(evidence['forward'], 10.)

    def test_rotated_long_body_can_overlap_corridor(self):
        import math
        evidence = candidate.held_heading_clearance([10., 3.], 0., math.pi/2, 2., 8., 2.)
        self.assertAlmostEqual(evidence['lateral_body_clearance'], -2.)

    def test_raw_release_requires_all_evidence_and_no_response(self):
        base = dict(raw_protected=True, strict_avoidance=False, supported_deviation=False,
                    target_sustained=False, history_complete=True, historical_clearance=3.,
                    route_relation='separated_observed_route', eligible_static_opposite=True)
        self.assertTrue(candidate.can_release_raw_protection(**base))
        for key in ['strict_avoidance', 'supported_deviation', 'target_sustained']:
            self.assertFalse(candidate.can_release_raw_protection(**{**base, key: True}))
        for key in ['history_complete', 'eligible_static_opposite']:
            self.assertFalse(candidate.can_release_raw_protection(**{**base, key: False}))
        for value in [None, float('nan'), 1., -.1]:
            self.assertFalse(candidate.can_release_raw_protection(**{**base, 'historical_clearance': value}))
        self.assertFalse(candidate.can_release_raw_protection(**{**base, 'route_relation': 'unknown'}))
