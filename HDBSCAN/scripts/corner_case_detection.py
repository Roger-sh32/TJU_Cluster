"""Calculate grouped risk and corner-case scores for clustered scenes."""

import os
from pathlib import Path

import pandas as pd

from corner_scoring import calculate_corner_scores


SCRIPT_DIR = Path(__file__).resolve().parent
HDBSCAN_ROOT = SCRIPT_DIR.parent
TABLES_DIR = HDBSCAN_ROOT / "tables"
TABLES_DIR.mkdir(exist_ok=True)

CLUSTER_INPUT_NAME = os.getenv(
    "SCENE_CLUSTER_CLUSTER_INPUT",
    "scene_features_umap_hdbscan.csv",
)
SCORE_OUTPUT_NAME = os.getenv(
    "SCENE_CLUSTER_SCORE_OUTPUT",
    "scene_features_with_corner_score.csv",
)


def main():
    input_path = TABLES_DIR / CLUSTER_INPUT_NAME
    output_path = TABLES_DIR / SCORE_OUTPUT_NAME
    df = pd.read_csv(input_path)

    required = {"cluster"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required clustering columns: {sorted(missing)}")

    scored = calculate_corner_scores(df)
    scored.to_csv(output_path, index=False)

    display_columns = [
        column
        for column in [
            "scene_name",
            "corner_score_norm",
            "cluster",
            "risk",
            "observed_risk",
            "decision_demand",
            "longitudinal_risk",
            "interaction_risk",
            "vru_risk",
            "ego_response_risk",
            "rarity",
            "atypical_norm",
        ]
        if column in scored.columns
    ]
    print(f"Corner score saved to {output_path}")
    print("\n===== Top 20 Corner Cases =====")
    print(scored.sort_values("corner_score_norm", ascending=False).head(20)[display_columns])


if __name__ == "__main__":
    main()
