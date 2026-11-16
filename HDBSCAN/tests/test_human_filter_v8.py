import unittest
from HDBSCAN.scripts import human_filter_v8 as m


class HumanFilterTests(unittest.TestCase):
    def audit(self):
        return dict(times=[i*.5 for i in range(30)], ego_speeds=[0.]+[4.]*29)

    def test_separated_unresponsive_candidate_can_be_suppressed(self):
        a = self.audit()
        self.assertFalse(m.response_protected(a, 6, False))
        self.assertTrue(m.should_suppress(False, 'separated_observed_route', False))

    def test_observed_unknown_and_response_are_preserved(self):
        self.assertFalse(m.should_suppress(True, 'separated_observed_route', False))
        self.assertFalse(m.should_suppress(False, 'unknown', False))
        self.assertFalse(m.should_suppress(False, 'separated_observed_route', True))
        self.assertTrue(m.response_protected(self.audit(), 1, False))
        self.assertTrue(m.response_protected(self.audit(), 6, True))

    def test_stop_and_soft_deceleration_are_protected(self):
        a = self.audit()
        a['ego_speeds'][8] = .2
        self.assertTrue(m.response_protected(a, 6, False))
        a = self.audit()
        a['ego_speeds'][8:12] = [1.5]*4
        self.assertTrue(m.response_protected(a, 6, False))

    def test_one_removed_target_does_not_clear_other_target_frame(self):
        anchors = [dict(index=1, instance_token='a', closest_distance_m=5., time_s=.5,
                        closest_relative_time_s=1.),
                   dict(index=1, instance_token='b', closest_distance_m=3., time_s=.5,
                        closest_relative_time_s=1.)]
        values = m.aggregate(anchors, [0., .5, 1.], [False, True, False], {(1, 'a')})
        self.assertEqual(values['vru_path_conflict_ratio'], 1/3)
        self.assertEqual(values['vru_observed_min_distance'], 3.)
        values = m.aggregate(anchors, [0., .5, 1.], [False, True, False], {(1, 'a'), (1, 'b')})
        self.assertEqual(values['vru_path_conflict_ratio'], 0.)
        self.assertEqual(values['vru_observed_min_distance'], 30.)
        self.assertEqual(values['vru_observed_min_distance_time'], -1.)
