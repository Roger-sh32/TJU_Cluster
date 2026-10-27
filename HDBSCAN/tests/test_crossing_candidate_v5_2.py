from HDBSCAN.tests import test_crossing_candidate_v5_1 as _v51


class CrossingV52Tests(_v51.CrossingV51Tests):
    def audit(self, data):
        from HDBSCAN.scripts.crossing_candidate_v5_2 import crossing_candidate_audit
        return crossing_candidate_audit(*data)

    def test_real_bracketing_frame_covers_irregular_horizon(self):
        data = self.scene()
        data[1][-2:] = [5.7, 6.3]
        item = self.audit(data)[0]
        self.assertTrue(item['future_complete'])
        self.assertFalse(item['unresolved'])
        self.assertEqual(item['state'], 'contradicted_synchronized_turn')

    def test_far_bracket_with_observation_gap_remains_unknown(self):
        data = self.scene()
        data[1][-1] = 7.
        item = self.audit(data)[0]
        self.assertFalse(item['future_complete'])
        self.assertTrue(item['unresolved'])

    def test_invalid_bracket_proximity_cannot_confirm_horizon_event(self):
        data = self.scene()
        data[1][-1] = 7.
        data[4]['actor'][-1]['position'] = data[0][-1].tolist()
        item = self.audit(data)[0]
        self.assertEqual(item['state'], 'unknown_future')
        self.assertFalse(item['effective_conflict'])

    def test_valid_bracket_proximity_after_horizon_is_prediction_only(self):
        data = self.scene()
        data[1][-2:] = [5.7, 6.3]
        data[4]['actor'][-1]['position'] = data[0][-1].tolist()
        item = self.audit(data)[0]
        self.assertTrue(item['future_complete'])
        self.assertEqual(item['state'], 'prediction_only')

    def test_unknown_bracket_geometry_keeps_valid_within_horizon_proximity(self):
        data = self.scene()
        data[1][-2:] = [5.7, 6.3]
        data[4]['actor'][6]['position'] = data[0][6].tolist()
        data[4]['actor'][-1]['width'] = None
        item = self.audit(data)[0]
        self.assertEqual(item['state'], 'observed_proximity')
        self.assertTrue(item['effective_conflict'])
        self.assertTrue(item['unresolved'])
