import unittest
from HDBSCAN.scripts.human_route_v8 import route_evidence


class HumanRouteTests(unittest.TestCase):
    def scene(self, y=10.):
        times = [i*.5 for i in range(21)]
        ego = dict(times=times, ego_positions=[[i*2., 0.] for i in range(21)],
                   ego_yaws=[0.]*21)
        human = [dict(index=i, translation=[10., y, 0.], rotation=[1., 0., 0., 0.],
                      size=[.5, .5, 1.7]) for i in range(21)]
        return ego, human

    def test_separated_complete_passage(self):
        ego, human = self.scene()
        self.assertEqual(route_evidence(ego, human, 0)['relation'], 'separated_observed_route')

    def test_path_overlap_not_removed(self):
        ego, human = self.scene(0.)
        self.assertEqual(route_evidence(ego, human, 0)['relation'], 'potential_route_overlap')

    def test_missing_target_and_short_future_stay_unknown(self):
        ego, human = self.scene()
        for track in [human[:8], human[:4]+human[5:]]:
            self.assertEqual(route_evidence(ego, track, 0)['relation'], 'unknown')

    def test_stopped_ego_does_not_prove_completed_passage(self):
        ego, human = self.scene()
        ego['ego_positions'] = [[0., 0.]]*21
        self.assertEqual(route_evidence(ego, human, 0)['relation'], 'unknown')
