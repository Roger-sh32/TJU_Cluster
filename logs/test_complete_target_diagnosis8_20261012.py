import unittest

from logs.complete_target_diagnosis8_20261012 import PolygonQueryMap, load_geometry_helpers


class ContinuationTests(unittest.TestCase):
    def test_nonpolygon_is_reported_unknown_not_sent_to_api(self):
        class Map:
            def layers_on_point(self, x, y, names):
                if 'lane_connector' in names:
                    raise ValueError('not a polygon layer')
                return {name: name + '_token' for name in names}
        result = PolygonQueryMap(Map()).layers_on_point(1, 2, ['walkway', 'lane_connector'])
        self.assertEqual(result['walkway'], 'walkway_token')
        self.assertIsNone(result['lane_connector'])

    def test_only_named_geometry_helpers_load_no_extraction(self):
        ns = load_geometry_helpers()
        self.assertNotIn('nusc', ns)
        self.assertNotIn('scene_features', ns)
        self.assertEqual(ns['ego_frame_delta']([5, 2], 1, 1, 0), (4, 1))


if __name__ == '__main__':
    unittest.main()
