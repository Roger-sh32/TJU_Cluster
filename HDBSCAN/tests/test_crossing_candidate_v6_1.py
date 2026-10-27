import copy
import importlib.util
import unittest

import numpy as np

from HDBSCAN.scripts import crossing_candidate_v6 as parent


def candidate():
    if importlib.util.find_spec('HDBSCAN.scripts.crossing_candidate_v6_1'):
        from HDBSCAN.scripts import crossing_candidate_v6_1
        return crossing_candidate_v6_1
    return parent


class EpisodeContinuityTests(unittest.TestCase):
    def scene(self):
        times = np.arange(0, 10.01, .5)
        tracks = {'truck': [dict(index=i, crossing_exposure=i <= 12) for i in range(len(times))]}
        evidence = [dict(index=2, instance_token='truck', effective_conflict=True,
            state='response_protected_prediction', route_relation='potential_route_overlap',
            future_complete=True, unresolved=False, yielding_response=True,
            soft_deceleration_response=False)]
        routes = [dict(index=i, instance_token='truck', future_complete=True,
                       relation='potential_route_overlap' if i < 10 else parent.SEPARATED)
                  for i in range(13)]
        return times, times*.1, tracks, evidence, [False]*len(times), np.full(len(times), 4.), routes

    def flags(self, data):
        return candidate().local_left_interaction_flags(*data[:6], route_evidence=data[6])

    def audit(self, data):
        function = getattr(candidate(), 'local_left_interaction_audit', None)
        self.assertIsNotNone(function, 'Historical episode audit is missing')
        return function(*data[:6], route_evidence=data[6])

    def test_same_target_continuous_tail_is_retained(self):
        self.assertTrue(self.flags(self.scene())[12])

    def test_no_transfer_to_unrelated_vehicle(self):
        data = self.scene()
        data[2]['car'] = copy.deepcopy(data[2]['truck'])
        data[6].extend(dict(index=i, instance_token='car', relation=parent.SEPARATED,
                            future_complete=True) for i in range(13))
        result = self.audit(data)
        self.assertTrue(result['target_flags']['truck'][12])
        self.assertFalse(any(result['target_flags']['car']))

    def test_unknown_seed_cannot_establish_history_extension(self):
        data = self.scene()
        data[3][0]['unresolved'] = True
        self.assertFalse(self.flags(data)[12])

    def test_unknown_route_seed_cannot_establish_history_extension(self):
        data = self.scene()
        data[3][0]['route_relation'] = 'unknown'
        data[6][2]['relation'] = 'unknown'
        self.assertFalse(self.flags(data)[12])

    def test_separated_seed_cannot_restore_event(self):
        data = self.scene()
        data[3][0].update(effective_conflict=False, state='contradicted_observed_route')
        for row in data[6]:
            row['relation'] = parent.SEPARATED
        data[4][:] = [True]*len(data[4])
        self.assertFalse(any(self.flags(data)))

    def test_exposure_gap_splits_episode(self):
        data = self.scene()
        data[2]['truck'][8]['crossing_exposure'] = False
        self.assertFalse(self.flags(data)[12])

    def test_six_second_boundary_is_inclusive_not_extended(self):
        data = self.scene()
        for row in data[2]['truck']:
            row['crossing_exposure'] = True
        data[6].extend(dict(index=i, instance_token='truck', relation=parent.SEPARATED,
                            future_complete=True) for i in range(13, len(data[0])))
        result = self.flags(data)
        self.assertTrue(result[14])
        self.assertFalse(any(result[15:]))

    def test_no_backwards_propagation_from_later_seed(self):
        data = self.scene()
        data[3][0]['index'] = 11
        data[6][11]['relation'] = 'potential_route_overlap'
        data[6][9]['relation'] = parent.SEPARATED
        self.assertFalse(self.flags(data)[9])

    def test_no_label_outside_original_exposure(self):
        data = self.scene()
        self.assertFalse(any(self.flags(data)[13:]))

    def test_history_does_not_mutate_current_crossing_evidence(self):
        data = self.scene()
        before = copy.deepcopy(data[2:])
        self.flags(data)
        self.assertEqual(data[2:5], before[:3])
        self.assertEqual(data[6], before[4])

    def test_restored_flag_has_same_target_seed_trace(self):
        result = self.audit(self.scene())
        restored = next(r for r in result['restored'] if r['index'] == 12)
        self.assertEqual(restored['instance_token'], 'truck')
        self.assertEqual(restored['seed_index'], 2)
        self.assertEqual(restored['kind'], 'historical_response_episode')

    def test_nonresponse_prediction_is_not_history_seed(self):
        data = self.scene()
        data[3][0].update(state='prediction_only', yielding_response=False)
        self.assertFalse(self.flags(data)[12])

    def test_invalid_speed_even_without_exposure_fails_closed(self):
        data = self.scene()
        for row in data[2]['truck']:
            row['crossing_exposure'] = False
        data[5][3] = float('nan')
        with self.assertRaises(ValueError):
            self.flags(data)

    def test_unknown_tail_keeps_only_historical_context(self):
        data = self.scene()
        data[6][12].update(relation='unknown', future_complete=False)
        before = copy.deepcopy(data[6][12])
        self.assertTrue(self.flags(data)[12])
        self.assertEqual(data[6][12], before)

    def test_boolean_seed_index_cannot_alias_frame_one(self):
        data = self.scene()
        data[3][0]['index'] = True
        with self.assertRaises(ValueError):
            self.flags(data)

    def test_string_boolean_cannot_certify_seed_future(self):
        data = self.scene()
        data[3][0]['future_complete'] = 'False'
        with self.assertRaises(ValueError):
            self.flags(data)

    def test_boolean_route_index_cannot_alias_frame_one(self):
        data = self.scene()
        data[6][1]['index'] = True
        with self.assertRaises(ValueError):
            self.flags(data)

    def test_string_route_boolean_cannot_certify_seed_future(self):
        data = self.scene()
        data[6][2]['future_complete'] = 'False'
        with self.assertRaises(ValueError):
            self.flags(data)


if __name__ == '__main__':
    unittest.main()
