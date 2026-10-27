import copy
import unittest

import numpy as np


class CrossingV5Tests(unittest.TestCase):
    def scene(self, duration=6):
        times = np.arange(0, duration + .01, .5)
        yaws = times * .1
        track = [{'index': i, 'position': [16 + 4*t, 6], 'width': 2., 'length': 10.,
                  'heading_delta': -yaws[i], 'crossing_exposure': True,
                  'crossing_conflict': i == 0, 'raw_crossing_conflict': i == 0}
                 for i, t in enumerate(times)]
        evidence = [{'index': 0, 'instance_token': 'actor', 'rejected_turning_projection': False,
                     'future_complete': duration >= 6, 'yielding_response': False,
                     'heading_change': float(yaws[-1])}]
        return np.column_stack([times*4, times*0]), times, yaws, np.full(len(times), 4.), {'actor': track}, evidence

    def audit(self, data):
        from HDBSCAN.scripts.crossing_candidate_v5 import crossing_candidate_audit
        return crossing_candidate_audit(*data)

    def test_spatial_overlap_without_simultaneous_arrival_is_contradicted(self):
        item = self.audit(self.scene())[0]
        self.assertEqual(item['state'], 'contradicted_synchronized_turn')
        self.assertFalse(item['effective_conflict'])
        self.assertGreater(item['modeled_clearance_lower_m'], 1.)

    def test_crosswise_long_vehicle_end_protects_actual_proximity(self):
        data = self.scene()
        for r in data[4]['actor']:
            r.update(position=[8, 6], length=12., heading_delta=np.pi/2-data[2][r['index']])
        item = self.audit(data)[0]
        self.assertEqual(item['state'], 'observed_proximity')
        self.assertTrue(item['effective_conflict'])

    def test_short_future_is_unknown_not_negative_or_confirmed(self):
        item = self.audit(self.scene(1.5))[0]
        self.assertEqual(item['state'], 'unknown_future')
        self.assertTrue(item['unresolved'])
        self.assertFalse(item['effective_conflict'])
        self.assertFalse(item['contradicted'])

    def test_low_speed_or_braking_protection_survives_spatial_miss(self):
        for duration in (1.5, 6):
            data = self.scene(duration)
            data[-1][0]['yielding_response'] = True
            item = self.audit(data)[0]
            self.assertEqual(item['state'], 'response_protected_prediction')
            self.assertTrue(item['effective_conflict'])

    def test_unknown_geometry_does_not_certify_separation(self):
        data = self.scene()
        data[4]['actor'][3]['width'] = None
        item = self.audit(data)[0]
        self.assertEqual(item['state'], 'unknown_geometry')
        self.assertTrue(item['unresolved'])
        self.assertFalse(item['contradicted'])

    def test_missing_actor_frame_cannot_clear_candidate(self):
        data = self.scene()
        data[4]['actor'].pop(3)
        data[-1][0]['future_complete'] = False
        self.assertEqual(self.audit(data)[0]['state'], 'unknown_future')

    def test_straight_driving_prediction_not_cleared_by_turn_filter(self):
        data = self.scene()
        data[2][:] = 0
        data[-1][0]['heading_change'] = 0
        item = self.audit(data)[0]
        self.assertEqual(item['state'], 'prediction_only')
        self.assertTrue(item['effective_conflict'])

    def test_old_projection_rejection_remains_explicit(self):
        data = self.scene()
        data[-1][0]['rejected_turning_projection'] = True
        self.assertEqual(self.audit(data)[0]['state'], 'contradicted_turning_projection')

    def test_inputs_are_not_mutated(self):
        data = self.scene()
        before = copy.deepcopy(data[4:])
        self.audit(data)
        self.assertEqual(data[4:], before)

    def test_invalid_ego_timeline_fails_closed(self):
        data = self.scene()
        data[1][2] = data[1][1]
        with self.assertRaises(ValueError):
            self.audit(data)

    def test_between_frame_close_pass_cannot_be_cleared_by_distant_endpoints(self):
        data = self.scene()
        for r in data[4]['actor']:
            r.update(position=[4*data[1][r['index']], 8 if r['index'] % 2 else -8],
                     width=2., length=2.)
        item = self.audit(data)[0]
        self.assertEqual(item['state'], 'prediction_only')
        self.assertEqual(item['modeled_clearance_lower_m'], 0)
        self.assertTrue(item['effective_conflict'])

    def test_legacy_rejection_cannot_override_between_frame_uncertainty(self):
        data = self.scene()
        for r in data[4]['actor']:
            r.update(position=[4*data[1][r['index']], 8 if r['index'] % 2 else -8],
                     width=2., length=2.)
        data[-1][0]['rejected_turning_projection'] = True
        item = self.audit(data)[0]
        self.assertFalse(item['contradicted'])
        self.assertTrue(item['effective_conflict'])

    def test_legacy_rejection_with_unknown_heading_stays_unknown(self):
        data = self.scene()
        data[4]['actor'][2]['heading_delta'] = None
        data[-1][0]['rejected_turning_projection'] = True
        self.assertEqual(self.audit(data)[0]['state'], 'unknown_geometry')

    def test_observed_near_end_is_not_downgraded_to_unknown_future(self):
        data = self.scene(1.5)
        for r in data[4]['actor']:
            r['position'] = [4*data[1][r['index']], 1]
        self.assertEqual(self.audit(data)[0]['state'], 'observed_proximity')

    def test_unknown_heading_cannot_certify_separation(self):
        data = self.scene()
        data[4]['actor'][2]['heading_delta'] = float('nan')
        self.assertEqual(self.audit(data)[0]['state'], 'unknown_geometry')

    def test_left_interaction_does_not_leak_to_another_target_or_late_episode(self):
        from HDBSCAN.scripts.crossing_candidate_v5 import local_left_interaction_flags
        times = np.arange(0, 20.01, .5)
        yaws = times*.1
        tracks = {'a': [{'index': i, 'crossing_exposure': True} for i in range(8)],
                  'b': [{'index': i, 'crossing_exposure': True} for i in range(25, 36)]}
        evidence = [{'instance_token': 'a', 'index': 2, 'effective_conflict': True}]
        result = local_left_interaction_flags(times, yaws, tracks, evidence, [False]*len(times))
        self.assertTrue(any(result[:8]))
        self.assertFalse(any(result[25:36]))

    def test_unknown_candidate_is_not_an_interaction_anchor(self):
        from HDBSCAN.scripts.crossing_candidate_v5 import local_left_interaction_flags
        data = self.scene(1.5)
        evidence = self.audit(data)
        result = local_left_interaction_flags(data[1], data[2], data[4], evidence, [False]*len(data[1]))
        self.assertFalse(any(result))

    def test_heading_after_anchor_horizon_cannot_relabel_earlier_exposure(self):
        from HDBSCAN.scripts.crossing_candidate_v5 import local_left_interaction_flags
        times = np.arange(0, 13.01, .5)
        yaws = np.maximum(times-11, 0.)
        tracks = {'a': [{'index': i, 'crossing_exposure': True} for i in range(13)]}
        evidence = [{'instance_token': 'a', 'index': 0, 'effective_conflict': True}]
        result = local_left_interaction_flags(times, yaws, tracks, evidence, [False]*len(times))
        self.assertFalse(any(result))


if __name__ == '__main__':
    unittest.main()
