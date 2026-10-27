import copy
import importlib.util
import unittest
from unittest.mock import patch


class LongitudinalTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('HDBSCAN.scripts.longitudinal_candidate_v7'),
                             'Independent longitudinal candidate missing')
        from HDBSCAN.scripts import longitudinal_candidate_v7
        return longitudinal_candidate_v7

    def candidate(self, name='a', clearance=10.):
        return dict(index=1, instance_token=name, annotation_token='ann-'+name,
            category='vehicle.car', clearance=clearance, supported=True, on_surface=True,
            target_speed=0., target_forward_speed=0., heading_delta=2.26,
            lateral_distance=0., local_turn=.7, permanent_static=True)

    def test_filter_precedes_nearest_selection_and_finds_alternative(self):
        m = self.module()
        a, b = self.candidate('false', 5.), self.candidate('real', 10.)
        self.assertEqual(m.select_nearest([a, b], {'false'})['instance_token'], 'real')

    def test_tie_preserves_original_annotation_order(self):
        m = self.module()
        self.assertEqual(m.select_nearest([self.candidate('z'), self.candidate('a')], set())['instance_token'], 'z')

    def test_offroad_or_overlapping_candidate_not_selected(self):
        m = self.module()
        a, b = self.candidate('offroad'), self.candidate('overlap')
        a['supported'] = False
        b['clearance'] = None
        self.assertIsNone(m.select_nearest([a, b], set()))

    def test_static_opposite_turn_requires_known_route_separation(self):
        m = self.module()
        c = self.candidate()
        self.assertTrue(m.should_reject(c, 'separated_observed_route', False))
        for state in ('unknown', 'potential_route_overlap'):
            self.assertFalse(m.should_reject(c, state, False))

    def test_forward_static_obstacle_is_protected(self):
        m = self.module()
        c = self.candidate()
        c['heading_delta'] = 0.
        self.assertFalse(m.should_reject(c, 'separated_observed_route', False))

    def test_temporarily_stopped_motorcycle_is_protected(self):
        m = self.module()
        c = self.candidate()
        c.update(category='vehicle.motorcycle', target_speed=.034, permanent_static=False)
        self.assertFalse(m.should_reject(c, 'separated_observed_route', False))

    def test_existing_avoidance_context_is_protected(self):
        self.assertFalse(self.module().should_reject(self.candidate(), 'separated_observed_route', True))

    def test_missing_map_does_not_prove_separation(self):
        c = self.candidate()
        c['on_surface'] = None
        self.assertFalse(self.module().should_reject(c, 'separated_observed_route', False))

    def test_straight_motion_not_filtered_as_turn_projection(self):
        c = self.candidate()
        c['local_turn'] = .1
        self.assertFalse(self.module().should_reject(c, 'separated_observed_route', False))

    def test_selection_does_not_mutate_source(self):
        m = self.module()
        candidates = [self.candidate('a'), self.candidate('b', 20.)]
        before = copy.deepcopy(candidates)
        m.select_nearest(candidates, {'a'})
        self.assertEqual(candidates, before)

    def test_rejection_boolean_context_is_strict(self):
        with self.assertRaises(ValueError):
            self.module().should_reject(self.candidate(), 'separated_observed_route', 'False')

    def scene(self):
        track = [dict(index=i, position=[12., 0.], forward=12.-2*i, lateral=0.,
            velocity=[0., 0.], heading_delta=0., category='vehicle.car', length=4., width=2.)
                 for i in range(3)]
        audit = dict(times=[0., .5, 1.], ego_positions=[[0., 0.], [2., 0.], [4., 0.]],
            ego_yaws=[0., 0., 0.], ego_speeds=[0., 4., 4.], vehicle_tracks={'a': track},
            instance_max_speeds={'a': 0.}, bounded_stationary_instances=['a'],
            lane_targets=[dict(index=i, instance='a', supported=True, on_surface=True) for i in range(3)])
        return audit, {(i, 'a'): 'ann-a-'+str(i) for i in range(3)}

    def test_baseline_replays_ttc_and_static_following_consistently(self):
        m = self.module()
        self.assertIsNotNone(getattr(m, 'build_ledger', None))
        audit, ids = self.scene()
        ledger = m.build_ledger(audit, ids)
        fields, trace = m.summarize(audit, ledger, {})
        self.assertEqual(fields['min_ttc'], .9375)
        self.assertEqual(fields['min_ttc_target_annotation_token'], 'ann-a-2')
        self.assertEqual(fields['car_following_ratio'], 2/3)
        self.assertEqual(fields['stationary_lead_obstacle_ratio'], 1.)
        self.assertEqual(fields['following_max_duration'], 1.5)

    def test_missing_annotation_identity_is_not_invented(self):
        m = self.module()
        self.assertIsNotNone(getattr(m, 'build_ledger', None))
        audit, ids = self.scene()
        del ids[(1, 'a')]
        with self.assertRaises(ValueError):
            m.build_ledger(audit, ids)

    def test_filtering_all_targets_recomputes_no_measurement_defaults(self):
        m = self.module()
        self.assertIsNotNone(getattr(m, 'build_ledger', None))
        audit, ids = self.scene()
        ledger = m.build_ledger(audit, ids)
        fields, trace = m.summarize(audit, ledger, {}, rejected={(i, 'a') for i in range(3)})
        self.assertEqual(fields['min_ttc'], 30.)
        self.assertEqual(fields['min_ttc_scene_time'], -1.)
        self.assertEqual(fields['min_ttc_target_instance_token'], 'none')
        self.assertEqual(fields['ttc_valid_ratio'], 0.)
        self.assertEqual(fields['stationary_lead_obstacle_ratio'], 0.)
        self.assertEqual(fields['car_following_ratio'], 0.)

    def test_integrated_gate_retains_unknown_and_does_not_mutate_tracks(self):
        m = self.module()
        audit, ids = self.scene()
        for v in audit['vehicle_tracks']['a']:
            v['heading_delta'] = 2.26
        ledger = m.build_ledger(audit, ids)
        for frame in ledger:
            frame[0]['local_turn'] = .7
        before = copy.deepcopy(audit)
        evidence = [dict(index=1, instance_token='a', relation='unknown')]
        with patch.object(m.geometry, 'audit_route_relations', return_value=evidence) as query:
            rejected, relations = m.gate_candidates(audit, ledger, False)
        self.assertEqual(rejected, set())
        self.assertEqual(relations, evidence)
        self.assertTrue(query.call_args.args[3]['a'][1]['crossing_exposure'])
        self.assertEqual(audit, before)

    def test_integrated_gate_only_removes_known_separation(self):
        m = self.module()
        audit, ids = self.scene()
        ledger = m.build_ledger(audit, ids)
        for frame in ledger:
            frame[0].update(heading_delta=2.26, local_turn=.7)
        evidence = [dict(index=1, instance_token='a', relation='separated_observed_route'),
                    dict(index=2, instance_token='a', relation='potential_route_overlap')]
        with patch.object(m.geometry, 'audit_route_relations', return_value=evidence):
            rejected, _ = m.gate_candidates(audit, ledger, False)
        self.assertEqual(rejected, {(1, 'a')})

    def test_integrated_protected_context_never_queries_geometry(self):
        m = self.module()
        audit, ids = self.scene()
        ledger = m.build_ledger(audit, ids)
        for frame in ledger:
            frame[0].update(heading_delta=2.26, local_turn=.7)
        with patch.object(m.geometry, 'audit_route_relations') as query:
            self.assertEqual(m.gate_candidates(audit, ledger, True), (set(), []))
        query.assert_not_called()

    def test_real_geometry_short_future_retains_all_eligible_targets(self):
        m = self.module()
        audit, ids = self.scene()
        ledger = m.build_ledger(audit, ids)
        for frame in ledger:
            frame[0].update(heading_delta=2.26, local_turn=.7)
        rejected, relations = m.gate_candidates(audit, ledger, False)
        self.assertEqual(rejected, set())
        self.assertEqual(len(relations), 3)
        self.assertTrue(all(r['relation'] == 'unknown' and not r['future_complete'] for r in relations))


if __name__ == '__main__':
    unittest.main()
