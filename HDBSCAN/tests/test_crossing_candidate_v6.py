import copy
import importlib.util
import unittest

import numpy as np

from HDBSCAN.scripts import crossing_candidate_v5_2 as parent


def candidate():
    if importlib.util.find_spec('HDBSCAN.scripts.crossing_candidate_v6'):
        from HDBSCAN.scripts import crossing_candidate_v6
        return crossing_candidate_v6
    return parent


class RouteRelevanceTests(unittest.TestCase):
    def scene(self, duration=12):
        times = np.arange(0, duration + .01, .5)
        positions = np.column_stack((4 * times, 0 * times))
        yaws = np.zeros(len(times))
        tracks = {'actor': [dict(index=i, position=[4*t, 8], width=2., length=4.,
            heading_delta=0., crossing_exposure=True, crossing_conflict=i == 0,
            raw_crossing_conflict=i == 0) for i, t in enumerate(times)]}
        old = [dict(index=0, instance_token='actor', yielding_response=True,
                    heading_change=.6, rejected_turning_projection=False)]
        return positions, times, yaws, np.full(len(times), 4.), tracks, old

    def audit(self, data):
        return candidate().crossing_candidate_audit(*data)

    def route(self, data):
        function = getattr(candidate(), 'audit_route_relations', None)
        self.assertIsNotNone(function, 'Independent route relevance audit is missing')
        return function(data[0], data[1], data[2], data[4])

    def test_unrelated_parallel_vehicle_cannot_use_response_protection(self):
        item = self.audit(self.scene())[0]
        self.assertEqual(item['state'], 'contradicted_observed_route')
        self.assertFalse(item['effective_conflict'])

    def test_prospective_route_overlap_preserves_successful_yield(self):
        data = self.scene()
        data[0][:, 0] = np.maximum(data[1] - 3, 0) * 3
        for row in data[4]['actor']:
            t = data[1][row['index']]
            row.update(position=[8, 6*t-6], heading_delta=np.pi/2, length=4.)
        item = self.audit(data)[0]
        self.assertEqual(item['state'], 'response_protected_prediction')
        self.assertTrue(item['effective_conflict'])
        self.assertEqual(item.get('route_relation'), 'potential_route_overlap')

    def test_short_future_cannot_clear_protected_prediction(self):
        item = self.audit(self.scene(2))[0]
        self.assertTrue(item['effective_conflict'])
        self.assertTrue(item['unresolved'])

    def test_missing_actor_observation_cannot_certify_route_separation(self):
        data = self.scene()
        data[4]['actor'].pop(3)
        item = self.audit(data)[0]
        self.assertTrue(item['effective_conflict'])
        self.assertEqual(self.route(data)[0]['relation'], 'unknown')

    def test_ego_gap_after_response_remains_unknown(self):
        data = self.scene()
        data[1][-1] += 1.
        self.assertEqual(self.route(data)[0]['relation'], 'unknown')

    def test_stationary_route_does_not_prove_completed_passage(self):
        data = self.scene()
        data[0][:] = 0
        data[3][:] = 0
        item = self.audit(data)[0]
        self.assertTrue(item['effective_conflict'])
        self.assertEqual(self.route(data)[0]['relation'], 'unknown')

    def test_known_proximity_is_not_removed(self):
        data = self.scene()
        for row in data[4]['actor']:
            row['position'][1] = 2.5
        self.assertTrue(self.audit(data)[0]['effective_conflict'])

    def test_local_left_cannot_reintroduce_separated_target(self):
        data = self.scene()
        data[2][:] = np.minimum(data[1], 2) * .3
        for row in data[4]['actor']:
            row.update(position=[0, 20],
                       heading_delta=-data[2][row['index']],
                       crossing_exposure=row['index'] <= 2)
        routes = self.route(data)
        evidence = self.audit(data)
        flags = candidate().local_left_interaction_flags(data[1], data[2], data[4],
            evidence, [True]*len(data[1]), data[3], route_evidence=routes)
        self.assertFalse(any(flags))

    def test_inputs_are_not_mutated(self):
        data = self.scene()
        before = copy.deepcopy(data[4:])
        self.audit(data)
        self.assertEqual(data[4:], before)

    def test_swept_envelope_contains_rotating_resizing_body(self):
        function = getattr(candidate(), 'swept_envelope', None)
        self.assertIsNotNone(function, 'Swept oriented-body envelope is missing')
        p = np.array([[0., 0.], [2., 1.]])
        yaw = np.array([0., 2.8])
        dimensions = np.array([[2., 4.], [3., 12.]])
        envelope = function(p, yaw, dimensions)
        for t in np.linspace(0, 1, 101):
            box = parent._box(p[0]*(1-t)+p[1]*t, yaw[0]*(1-t)+yaw[1]*t,
                              *(dimensions[0]*(1-t)+dimensions[1]*t))
            self.assertTrue(envelope.buffer(1e-9).covers(box))

    def test_rotation_shortest_angle_across_pi(self):
        function = getattr(candidate(), 'swept_envelope', None)
        self.assertIsNotNone(function)
        result = function([[0, 0], [1, 0]], [3.13, -3.13], [[2, 4], [2, 4]])
        self.assertLess(result.area, 11)

    def test_invalid_dimensions_remain_unknown(self):
        data = self.scene()
        data[4]['actor'][2]['width'] = None
        self.assertEqual(self.route(data)[0]['relation'], 'unknown')

    def test_missing_route_evidence_cannot_bypass_local_gate(self):
        data = self.scene()
        with self.assertRaises(ValueError):
            candidate().local_left_interaction_flags(data[1], data[2], data[4],
                self.audit(data), [True]*len(data[1]), data[3], route_evidence=[])

    def test_instance_renaming_does_not_change_decision(self):
        data = self.scene()
        first = self.audit(data)[0]
        data[4]['renamed'] = data[4].pop('actor')
        data[5][0]['instance_token'] = 'renamed'
        second = self.audit(data)[0]
        for key in ('state', 'effective_conflict', 'route_relation', 'unresolved'):
            self.assertEqual(first[key], second[key])

    def test_duplicate_target_frame_fails_closed(self):
        data = self.scene()
        data[4]['actor'].insert(2, copy.deepcopy(data[4]['actor'][2]))
        with self.assertRaises(ValueError):
            self.route(data)

    def test_malformed_yaw_shape_rejected(self):
        function = getattr(candidate(), 'swept_envelope', None)
        self.assertIsNotNone(function)
        with self.assertRaises(ValueError):
            function([[0, 0], [1, 0]], [[0], [0]], [[2, 4], [2, 4]])

    def test_tiny_rotation_does_not_erase_connecting_hull(self):
        function = getattr(candidate(), 'swept_envelope', None)
        self.assertIsNotNone(function)
        envelope = function([[0, 0], [10, 0]], [0, 1e-8], [[2, 4], [2, 4]])
        midpoint = parent._box([5, 0], 5e-9, 2, 4)
        self.assertTrue(envelope.buffer(1e-9).covers(midpoint))

    def test_fast_between_frame_encounter_cannot_be_cleared(self):
        data = self.scene()
        data[0][:, 0] = 20*data[1]
        data[2][:] = np.arange(len(data[1])) * 1e-8
        for row in data[4]['actor']:
            row.update(position=[5, 0], length=2., heading_delta=-data[2][row['index']])
        item = self.audit(data)[0]
        self.assertTrue(item['effective_conflict'])
        self.assertNotEqual(item['route_relation'], 'separated_observed_route')


if __name__ == '__main__':
    unittest.main()
