"""Small contract tests for the bounded development review recipe."""

import unittest

from logs.build_development_media_review_20261012 import select_frames, timing, validate_members


class ReviewContracts(unittest.TestCase):
    def test_reject_evaluation(self):
        with self.assertRaises(ValueError):
            validate_members(['scene-0002'], {'scene-0002': {
                'split': 'evaluation', 'scene_token': 'a'}},
                {'scene-0002': {'scene_token': 'a'}})

    def test_reject_wrong_identity(self):
        with self.assertRaises(ValueError):
            validate_members(['scene-0002'], {'scene-0002': {
                'split': 'development', 'scene_token': 'a'}},
                {'scene-0002': {'scene_token': 'b'}})

    def test_nearest_sampling_preserves_last_and_order(self):
        pool = [{'token': str(i), 'timestamp': i * 83333} for i in range(240)]
        chosen = select_frames(pool)
        self.assertEqual(chosen[0], pool[0])
        self.assertEqual(chosen[-1], pool[-1])
        self.assertEqual(len(chosen), len({r['token'] for r in chosen}))
        self.assertTrue(all(a['timestamp'] < b['timestamp'] for a, b in zip(chosen, chosen[1:])))

    def test_cumulative_gif_timing(self):
        pool = [{'timestamp': 123456789 + round(i * 1000000 / 6)} for i in range(118)]
        durations = timing(pool)
        span = (pool[-1]['timestamp'] - pool[0]['timestamp']) / 1000
        self.assertLessEqual(abs(sum(durations[:-1]) - span), 5)
        self.assertTrue(all(d > 0 and d % 10 == 0 for d in durations))


if __name__ == '__main__':
    unittest.main()
