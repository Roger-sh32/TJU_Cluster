import unittest
import pandas as pd

from HDBSCAN.scripts import audit_interaction_events as audit


def example():
    times = [i * 0.5 for i in range(12)]
    return {
        'scene_name': 'synthetic', 'scene_token': 'token', 'times': times,
        'ego_speeds': [0, 4, 3, 2, .2, .1, .2, 2, 3, 3, 3, 3],
        'stop_sign_stop_flags': [False] * 4 + [True] * 3 + [False] * 5,
        'vehicle_tracks': {
            'truck': [{'index': i, 'category': 'vehicle.truck', 'crossing_conflict': True}
                      for i in [2, 3, 4]],
            'car': [{'index': i, 'category': 'vehicle.car', 'crossing_conflict': True}
                    for i in [8, 9]],
        },
    }


class InteractionEventsTest(unittest.TestCase):
    def test_separates_actors_and_stop_phases_without_claiming_causality(self):
        events = audit.scene_events(example())
        stops = [e for e in events if e['event_type'] == 'low_speed_stop']
        self.assertEqual(len(stops), 1)
        self.assertEqual((stops[0]['start_s'], stops[0]['end_s']), (2, 3))
        self.assertTrue(stops[0]['stop_sign_context_observed'])
        self.assertEqual(stops[0]['stop_reason'], 'undetermined')
        crossing = [e for e in events if e['event_type'] == 'predicted_crossing']
        self.assertEqual([(e['instance_token'], e['phase']) for e in crossing],
                         [('truck', 'before_first_stop'), ('truck', 'during_stop'),
                          ('car', 'after_last_stop')])

    def test_first_speed_placeholder_and_brief_slowdown_are_not_stop(self):
        data = example()
        data['ego_speeds'] = [0, 3, 3, 3, .2, 3, 3, 3, 3, 3, 3, 3]
        events = audit.scene_events(data)
        self.assertTrue(all(e['event_type'] != 'low_speed_stop' for e in events))
        self.assertTrue(all(e['phase'] == 'no_stop_observed' for e in events))

    def test_first_frame_crossing_does_not_export_placeholder_speed(self):
        data = example()
        data['vehicle_tracks'] = {'car': [
            {'index': 0, 'category': 'vehicle.car', 'crossing_conflict': True}]}
        event = audit.scene_events(data)[0]
        self.assertIsNone(event['ego_speed_min'])
        self.assertIsNone(event['ego_speed_max'])
        data['vehicle_tracks']['car'].append(
            {'index': 1, 'category': 'vehicle.car', 'crossing_conflict': True})
        event = audit.scene_events(data)[0]
        self.assertEqual(event['ego_speed_min'], 4)
        self.assertEqual(event['ego_speed_max'], 4)

    def test_initial_stop_multiple_stops_and_gaps(self):
        data = example()
        data['ego_speeds'] = [0, .1, .1, .1, 3, 3, 3, .1, .1, .1, 3, 3]
        events = audit.scene_events(data)
        stops = [e for e in events if e['event_type'] == 'low_speed_stop']
        self.assertEqual(len(stops), 2)
        self.assertEqual(stops[0]['start_s'], .5)
        self.assertIn('between_stops', {e['phase'] for e in events})
        data['times'] = [0, .5, 1, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9]
        stops = [e for e in audit.scene_events(data) if e['event_type'] == 'low_speed_stop']
        self.assertEqual(len(stops), 1)

    def test_bad_evidence_is_rejected_not_filled_with_zero(self):
        for mutate in [lambda d: d['ego_speeds'].pop(),
                       lambda d: d['times'].__setitem__(2, float('nan')),
                       lambda d: d['times'].__setitem__(2, 0),
                       lambda d: d['vehicle_tracks']['truck'][0].__setitem__('index', 99)]:
            data = example()
            mutate(data)
            with self.assertRaises(ValueError):
                audit.scene_events(data)

    def test_report_rejects_evaluation_identity_mismatch_and_duplicates(self):
        data = example()
        features = pd.DataFrame([{'scene_name': 'synthetic', 'scene_token': 'token'}])
        partition = {'by_name': {'synthetic': {
            'scene_token': 'token', 'split': 'development'}}}
        self.assertIn('synthetic', audit.build_report([data], features, partition))
        with self.assertRaises(ValueError):
            audit.build_report([data, data], features, partition)
        data['scene_token'] = 'wrong'
        with self.assertRaises(ValueError):
            audit.build_report([data], features, partition)
        data['scene_token'] = 'token'
        partition['by_name']['synthetic']['split'] = 'evaluation'
        with self.assertRaises(ValueError):
            audit.build_report([data], features, partition)

    def test_markdown_does_not_claim_yield_causality(self):
        text = audit.render_markdown({'synthetic': audit.scene_events(example())})
        self.assertIn('truck', text)
        self.assertIn('car', text)
        self.assertIn('未确定', text)


if __name__ == '__main__':
    unittest.main()
