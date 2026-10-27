import unittest

import pandas as pd


class FeatureSelectionTest(unittest.TestCase):
    def test_new_route_context_is_selected_but_target_ids_are_not(self):
        from HDBSCAN.scripts.feature_selection import select_clustering_features
        columns = ['adjacent_lane_intrusion_ratio', 'side_entry_candidate_ratio',
                   'crossing_route_conflict_ratio', 'stop_sign_stop_candidate']
        frame = pd.DataFrame({name: [0.0] for name in columns})
        frame['side_entry_candidate_instances'] = 'target-token'
        self.assertEqual(list(select_clustering_features(frame)), columns)

    def test_only_semantic_context_and_interaction_features_are_selected(self):
        from HDBSCAN.scripts.feature_selection import select_clustering_features

        df = pd.DataFrame({
            "scene_name": ["scene-0001"],
            "frame_count": [40],
            "avg_vehicle_count": [5.0],
            "neighbor_density_std": [1.0],
            "intersection_density": [0.5],
            "intersection_stop_ratio": [0.4],
            "blocked_path_obstacle_ratio": [0.2],
            "obstacle_induced_route_deviation_flag": [1],
            "route_deviation_decision_demand": [1.0],
            "crossing_vehicle_exposure_ratio": [0.6],
            "merge_exposure_ratio": [0.3],
            "merge_conflict_ratio": [0.2],
            "min_ttc": [1.0],
            "dangerous_ttc_frame_ratio": [0.5],
            "front_vehicle_min_dist": [80.0],
            "ego_hard_brake_ratio": [0.1],
            "map_available": [1],
        })

        selected = select_clustering_features(df)

        self.assertEqual(
            list(selected.columns),
            [
                "avg_vehicle_count",
                "neighbor_density_std",
                "merge_exposure_ratio",
                "crossing_vehicle_exposure_ratio",
                "blocked_path_obstacle_ratio",
                "obstacle_induced_route_deviation_flag",
                "route_deviation_decision_demand",
                "intersection_density",
                "intersection_stop_ratio",
            ],
        )

    def test_raises_when_no_supported_features_exist(self):
        from HDBSCAN.scripts.feature_selection import select_clustering_features

        with self.assertRaisesRegex(ValueError, "No supported clustering features"):
            select_clustering_features(pd.DataFrame({"frame_count": [40]}))


if __name__ == "__main__":
    unittest.main()
