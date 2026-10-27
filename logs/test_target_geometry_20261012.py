import unittest

from shapely.geometry import Point
from logs.check_target_geometry_20261012 import oriented_footprint


class GeometryContracts(unittest.TestCase):
    def test_long_parallel_truck_is_not_its_circumscribed_circle(self):
        polygon = oriented_footprint([0, 6], 0, 2, 12)
        self.assertAlmostEqual(polygon.distance(Point(0, 0)), 5)
        self.assertAlmostEqual(polygon.area, 24)

    def test_rotation_protects_crosswise_vehicle_end(self):
        import math
        polygon = oriented_footprint([0, 6], math.pi / 2, 2, 12)
        self.assertLess(polygon.distance(Point(0, 0)), 1e-10)

    def test_invalid_dimensions_are_not_safe_evidence(self):
        with self.assertRaises(ValueError):
            oriented_footprint([0, 0], 0, 0, 12)


if __name__ == '__main__':
    unittest.main()
