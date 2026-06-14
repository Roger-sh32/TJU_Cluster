# KMeans baseline

This directory stores the older KMeans baseline experiment for the autonomous-driving scene clustering project.

KMeans is currently treated as a baseline or legacy comparison track. The mid-term report uses `HDBSCAN/` as the main result source, and lists KMeans comparison as future work.

## Directory layout

| Directory | Content |
| --- | --- |
| `scripts/` | KMeans baseline script |
| `tables/` | CSV outputs from feature extraction or clustering |
| `pictures/` | PCA/KMeans visualizations |
| local data directory | Local nuScenes-style data copy used by the original KMeans script |

## Current files

| Path | Description |
| --- | --- |
| `scripts/scene_feature_kmeans_baseline.py` | Baseline script for feature extraction, PCA visualization, and KMeans clustering |
| `tables/scene_features.csv` | Historical feature table from the KMeans track |
| `pictures/Figure_1.png` | Historical visualization |
| `pictures/Figure_2.png` | Historical visualization |

## Run command

Run from this directory:

```powershell
python .\scripts\scene_feature_kmeans_baseline.py
```

Expected generated outputs:

- `tables/scene_features_with_clusters_fixed.csv`
- `pictures/kmeans_pca_clusters.png`

## Notes

- The script reads data from the local nuScenes-style data directory under `Kmeans/`.
- This track has not been rerun during the 2026-06-13 cleanup and directory reorganization.
- Keep this directory for future baseline comparison against HDBSCAN.
