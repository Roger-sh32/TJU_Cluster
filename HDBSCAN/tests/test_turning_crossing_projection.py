import unittest


class TurningCrossingProjectionTest(unittest.TestCase):
    def timeline(self):
        import numpy as np
        times = np.arange(0, 7.01, .5)
        positions = np.column_stack([times, np.zeros(len(times))])
        yaws = times / 6
        speeds = np.full(len(times), 4.)
        speeds[0] = 0.
        track = [{'index': i, 'position': [t, 8.], 'width': 1., 'length': 2.,
                  'category': 'vehicle.car', 'crossing_conflict': i == 0}
                 for i, t in enumerate(times)]
        return positions, times, yaws, speeds, {'actor': track}

    def audit(self, data):
        from HDBSCAN.scripts.scene_feature_rules import turning_crossing_projection_audit
        return turning_crossing_projection_audit(*data)[0]

    def test_full_track_rejects_projection_ignoring_initial_speed_placeholder(self):
        evidence = self.audit(self.timeline())
        self.assertTrue(evidence['future_complete'])
        self.assertFalse(evidence['yielding_response'])
        self.assertTrue(evidence['rejected_turning_projection'])

    def test_low_speed_or_hard_brake_preserves_successful_yield(self):
        for speed in (1., 2.):
            data = self.timeline()
            data[3][4] = speed
            evidence = self.audit(data)
            self.assertTrue(evidence['yielding_response'])
            self.assertFalse(evidence['rejected_turning_projection'])

    def test_actor_gap_or_short_future_is_not_negative_evidence(self):
        for remove in ((4, 5), (12,)):
            data = self.timeline()
            data[4]['actor'] = [r for r in data[4]['actor'] if r['index'] not in remove]
            evidence = self.audit(data)
            self.assertFalse(evidence['future_complete'])
            self.assertFalse(evidence['rejected_turning_projection'])

    def test_ego_gap_is_not_negative_evidence(self):
        data = self.timeline()
        data[1][4:] += 1.
        evidence = self.audit(data)
        self.assertFalse(evidence['future_complete'])
        self.assertFalse(evidence['rejected_turning_projection'])

    def test_invalid_timeline_fails_explicitly(self):
        from HDBSCAN.scripts.scene_feature_rules import turning_crossing_projection_audit
        data = self.timeline()
        data[1][4] = data[1][3]
        with self.assertRaisesRegex(ValueError, 'timeline'):
            turning_crossing_projection_audit(*data)

    def test_long_crosswise_bus_footprint_is_not_cleared_by_center_distance(self):
        data = self.timeline()
        for row in data[4]['actor']:
            row.update(position=[row['position'][0], 4.], width=2.5, length=12.)
        self.assertFalse(self.audit(data)['rejected_turning_projection'])

    def test_braking_into_first_candidate_is_not_ignored(self):
        data = self.timeline()
        data[3][1] = 6.
        for row in data[4]['actor']:
            row['crossing_conflict'] = row['index'] == 2
        self.assertTrue(self.audit(data)['yielding_response'])
        self.assertFalse(self.audit(data)['rejected_turning_projection'])

    def test_single_missing_actor_keyframe_is_not_complete_future(self):
        data = self.timeline()
        data[4]['actor'] = [r for r in data[4]['actor'] if r['index'] != 4]
        self.assertFalse(self.audit(data)['future_complete'])
        self.assertFalse(self.audit(data)['rejected_turning_projection'])

    def test_nonfinite_actor_position_preserves_candidate(self):
        data = self.timeline()
        data[4]['actor'][4]['position'][0] = float('nan')
        self.assertFalse(self.audit(data)['rejected_turning_projection'])

    def test_missing_or_unknown_dimension_preserves_candidate(self):
        for key, value in [('width', None), ('length', None)]:
            data = self.timeline()
            data[4]['actor'][0][key] = value
            self.assertFalse(self.audit(data)['rejected_turning_projection'])
        data = self.timeline()
        del data[4]['actor'][4]['length']
        self.assertFalse(self.audit(data)['rejected_turning_projection'])

    def test_turning_path_misses_actor_without_yielding(self):
        from HDBSCAN.scripts.scene_feature_rules import is_turning_crossing_projection
        self.assertTrue(is_turning_crossing_projection(1.0, 3.9, .6, False, True))

    def test_actual_route_intersection_is_retained(self):
        from HDBSCAN.scripts.scene_feature_rules import is_turning_crossing_projection
        self.assertFalse(is_turning_crossing_projection(.68, .52, 1.8, False, True))

    def test_successful_yield_is_not_erased_by_observed_route(self):
        from HDBSCAN.scripts.scene_feature_rules import is_turning_crossing_projection
        self.assertFalse(is_turning_crossing_projection(1.0, 8.0, 2.0, True, True))

    def test_straight_driving_prediction_is_not_filtered(self):
        from HDBSCAN.scripts.scene_feature_rules import is_turning_crossing_projection
        self.assertFalse(is_turning_crossing_projection(.22, 14.2, 2.0, False, True))

    def test_wide_actor_footprint_near_route_is_retained(self):
        from HDBSCAN.scripts.scene_feature_rules import is_turning_crossing_projection
        self.assertFalse(is_turning_crossing_projection(1.0, 3.5, 2.5, False, True))

    def test_incomplete_or_unknown_future_is_not_negative_evidence(self):
        from HDBSCAN.scripts.scene_feature_rules import is_turning_crossing_projection
        self.assertFalse(is_turning_crossing_projection(1.0, 8.0, 1.0, False, False))
        self.assertFalse(is_turning_crossing_projection(1.0, float('inf'), 1.0, False, True))


if __name__ == '__main__':
    unittest.main()
