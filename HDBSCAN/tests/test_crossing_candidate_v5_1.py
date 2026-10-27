import unittest
import numpy as np

from HDBSCAN.tests import test_crossing_candidate_v5 as _v5


class CrossingV51Tests(_v5.CrossingV5Tests):
    def audit(self, data):
        from HDBSCAN.scripts.crossing_candidate_v5_1 import crossing_candidate_audit
        return crossing_candidate_audit(*data)

    def test_near_horizon_bracketing_sample_is_not_missing_future(self):
        data = self.scene()
        data[1][-1] += .0002
        data[-1][0]['future_complete'] = False
        item = self.audit(data)[0]
        self.assertTrue(item['future_complete'])
        self.assertEqual(item['state'], 'contradicted_synchronized_turn')

    def test_sustained_soft_deceleration_preserves_rolling_yield_candidate(self):
        data = self.scene()
        data[-1][0]['index'] = 1
        data[3][-5:] = 1.5
        item = self.audit(data)[0]
        self.assertTrue(item['soft_deceleration_response'])
        self.assertEqual(item['state'], 'response_protected_prediction')

    def test_one_frame_speed_dip_is_not_sustained_soft_response(self):
        data = self.scene()
        data[-1][0]['index'] = 1
        data[3][6] = 1.5
        item = self.audit(data)[0]
        self.assertFalse(item['soft_deceleration_response'])

    def test_wait_then_release_link_protects_same_target_not_later_other_target(self):
        from HDBSCAN.scripts.crossing_candidate_v5_1 import local_left_interaction_flags
        times = np.arange(0, 14.01, .5)
        speeds = np.full(len(times), 3.)
        speeds[:4] = 2.5
        speeds[4:18] = .1
        speeds[0] = 0
        yaws = np.maximum(0, np.minimum(times-9, 2))*.5
        tracks = {'bus': [{'index': i, 'crossing_exposure': True} for i in range(5)],
                  'later': [{'index': i, 'crossing_exposure': True} for i in range(25, 28)]}
        flags = local_left_interaction_flags(times, yaws, tracks, [], [False]*len(times), speeds)
        self.assertTrue(any(flags[:5]))
        self.assertFalse(any(flags[25:28]))

    def test_no_link_to_stop_beyond_response_horizon(self):
        from HDBSCAN.scripts.crossing_candidate_v5_1 import local_left_interaction_flags
        times = np.arange(0, 15.01, .5)
        speeds = np.full(len(times), 3.)
        speeds[18:22] = .1
        yaws = np.maximum(times-11, 0)*.5
        tracks = {'bus': [{'index': i, 'crossing_exposure': True} for i in range(4)]}
        flags = local_left_interaction_flags(times, yaws, tracks, [], [False]*len(times), speeds)
        self.assertFalse(any(flags))

    def test_placeholder_initial_speed_cannot_anchor_a_left_turn(self):
        from HDBSCAN.scripts.crossing_candidate_v5_1 import local_left_interaction_flags
        times = np.arange(0, 6.01, .5)
        tracks = {'actor': [{'index': 0, 'crossing_exposure': True}]}
        flags = local_left_interaction_flags(times, times*.1, tracks, [], [True]+[False]*12,
                                            [0]+[4]*12)
        self.assertFalse(any(flags))

    def test_local_v51_unknown_and_other_target_are_not_anchors(self):
        from HDBSCAN.scripts.crossing_candidate_v5_1 import local_left_interaction_flags
        data = self.scene(1.5)
        flags = local_left_interaction_flags(data[1], data[2], data[4], self.audit(data),
                                            [False]*len(data[1]), data[3])
        self.assertFalse(any(flags))
        times = np.arange(0, 20.01, .5)
        tracks = {'a': [{'index': i, 'crossing_exposure': True} for i in range(8)],
                  'b': [{'index': i, 'crossing_exposure': True} for i in range(25, 36)]}
        evidence = [{'instance_token': 'a', 'index': 2, 'effective_conflict': True}]
        flags = local_left_interaction_flags(times, times*.1, tracks, evidence,
                                            [False]*len(times), np.full(len(times), 4.))
        self.assertTrue(any(flags[:8]))
        self.assertFalse(any(flags[25:36]))

    def test_protection_does_not_erase_incomplete_future(self):
        data = self.scene(3)
        data[-1][0]['index'] = 1
        data[3][3:] = 1.5
        item = self.audit(data)[0]
        self.assertEqual(item['state'], 'response_protected_prediction')
        self.assertTrue(item['effective_conflict'])
        self.assertTrue(item['unresolved'])
        self.assertFalse(item['future_complete'])

    def test_unbracketed_tail_is_unknown_not_contradicted(self):
        data = self.scene()
        data[1][-1] = 5.8
        item = self.audit(data)[0]
        self.assertFalse(item['future_complete'])
        self.assertTrue(item['unresolved'])
        self.assertFalse(item['contradicted'])

    def test_selection_refuses_over_limit_or_outside_fixed_names(self):
        from HDBSCAN.scripts.crossing_candidate_v5_1 import validate_candidate_selection
        names = ['scene-'+str(i) for i in range(30)]
        with self.assertRaises(ValueError):
            validate_candidate_selection(names, 29, names)
        with self.assertRaises(ValueError):
            validate_candidate_selection(names[:1], 29, names[1:])
        validate_candidate_selection(names[:5], 29, names)


if __name__ == '__main__':
    unittest.main()
