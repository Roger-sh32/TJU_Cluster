# Experiment Rerun Log - 2026-06-14

## Scope

Rerun the current HDBSCAN main workflow after revising `intersection_flag` extraction.

Workflow target:

```powershell
Set-Location F:\Scene_cluster\HDBSCAN
D:\Python\Conda\envs\autodrive-cluster\python.exe .\scripts\scene_feature_hdbscan.py
D:\Python\Conda\envs\autodrive-cluster\python.exe .\scripts\cluster_umap_hdbscan.py
D:\Python\Conda\envs\autodrive-cluster\python.exe .\scripts\corner_case_detection.py
```

## Environment

- Python: `D:\Python\Conda\envs\autodrive-cluster\python.exe`
- Python version: `3.9.23`
- `numpy`: `1.26.4`
- `scipy`: `1.13.1`
- `scikit-learn`: `1.6.1`
- `umap-learn`: `0.5.9.post2`
- `pynndescent`: `0.5.13`
- `numba`: `0.60.0`
- `llvmlite`: `0.43.0`
- `hdbscan`: `0.8.39`

## Completed

### Feature extraction

Command:

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe .\scripts\scene_feature_hdbscan.py
```

Output:

- `HDBSCAN/tables/scene_features.csv`

Result:

- Shape: `850 x 25`
- New feature included: `intersection_density`
- `intersection_flag` distribution:
  - `1`: `834`
  - `0`: `16`
- `intersection_density` mean: about `0.8383`

Interpretation:

- The previous all-zero `intersection_flag` problem is fixed.
- The new logic is likely too broad because `lane_connector` fallback marks most scenes as near intersections.
- Before treating this as final, the intersection logic should be tightened, likely by relying more on `road_segment.is_intersection` and reducing or qualifying `lane_connector` usage.

## Blocked

### UMAP clustering

Command:

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe .\scripts\cluster_umap_hdbscan.py
```

Observed behavior:

- Script printed through `Running UMAP...`
- `python.exe` then crashed at native level.
- Windows popup reported an application exception:
  - `0xc06d007f`
- No new `scene_features_umap_hdbscan.csv` was written.
- Existing `HDBSCAN/tables/scene_features_umap_hdbscan.csv` remains the old 2026-04-03 result.

Diagnostics:

- PCA with `sklearn.decomposition.PCA` completed successfully.
- HDBSCAN on PCA output completed successfully.
- A minimal `numba.njit` function compiled successfully.
- `pynndescent.NNDescent` failed in this environment with:
  - `PermissionError: [WinError 5] Access is denied`
  - failure occurs while joblib/multiprocessing creates a pipe/queue.
- UMAP still crashed even when attempting:
  - `n_jobs=1`
  - `NUMBA_DISABLE_JIT=1`
  - precomputed sklearn KNN via `precomputed_knn`

Interpretation:

- The current blocker is not ordinary Python exception handling and not a missing feature column.
- The failure is concentrated in UMAP's native/compiled execution path, likely involving `umap-learn`, `pynndescent`, `numba`, `llvmlite`, joblib, or Windows runtime constraints.
- The current environment can extract features and run PCA/HDBSCAN, but cannot reliably run UMAP.

## Not Completed

- `cluster_umap_hdbscan.py` did not produce a new clustering table.
- `corner_case_detection.py` was not rerun because it depends on the updated clustering table.
- No new corner score table was produced.

## Next Options

1. Tighten `intersection_flag` logic before rerunning the full workflow again.
2. Repair or recreate the environment with a more conservative pinned UMAP stack.
3. Add a temporary PCA/HDBSCAN fallback script only for diagnostic comparison, not as the main thesis result.

## 2026-06-16 Follow-up Rerun

### Environment resolution

The original `autodrive-cluster` environment remained usable for nuScenes feature extraction, but UMAP continued to be unstable there.

A clean diagnostic environment was created and verified:

- Environment: `autodrive-umap-smoke`
- Python: `D:\Python\Conda\envs\autodrive-umap-smoke\python.exe`
- UMAP smoke test on 100 random rows: passed
- Installed minimum clustering dependencies: `pandas`, `hdbscan`

The successful rerun used a split workflow:

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\scene_feature_hdbscan.py
D:\Python\Conda\envs\autodrive-umap-smoke\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\cluster_umap_hdbscan.py
D:\Python\Conda\envs\autodrive-umap-smoke\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\corner_case_detection.py
```

### Script changes used for this rerun

- `scene_feature_hdbscan.py` now writes `scene_name`, `scene_token`, and `log_location` into the feature table.
- `cluster_umap_hdbscan.py` now runs UMAP with `n_jobs=1` and `low_memory=True`.
- `cluster_umap_hdbscan.py` now tolerates missing `matplotlib` and skips plotting instead of failing.
- `cluster_umap_hdbscan.py` now saves `umap_0` to `umap_9` into the clustering table.
- `corner_case_detection.py` now uses numeric feature columns only and excludes `umap_*` from atypical-distance scoring.

### Outputs regenerated

- `HDBSCAN/tables/scene_features.csv`
  - Shape: `850 x 28`
  - Includes `scene_name`, `scene_token`, `log_location`
- `HDBSCAN/tables/scene_features_umap_hdbscan.csv`
  - Shape: `850 x 39`
  - Includes `umap_0` to `umap_9` and `cluster`
- `HDBSCAN/tables/scene_features_with_corner_score.csv`
  - Includes scene identifiers, UMAP embedding columns, cluster labels, and corner score columns

Cluster count:

- `15` labels including noise cluster `-1`

Cluster distribution:

```text
-1     104
 0      70
 1      37
 2      20
 3      34
 4     200
 5      31
 6      66
 7      33
 8      33
 9      47
 10     36
 11     41
 12     37
 13     61
```

Top corner-score scenes after rerun:

```text
scene-0741
scene-0901
scene-0889
scene-0287
scene-0727
scene-0253
scene-0441
scene-0795
scene-0332
scene-0506
```

### Remaining cautions

- `intersection_flag` is no longer all zero, but the current logic is likely too broad: `834 / 850` scenes are flagged as intersections.
- `lane_connector` fallback should be tightened before using the intersection feature as a final thesis conclusion.
- `Figure_1.png` was not regenerated in the clean environment because `matplotlib` was intentionally not installed there.
