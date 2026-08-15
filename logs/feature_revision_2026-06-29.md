# Feature Revision Log - 2026-06-29

## Scope

Revise overly broad HDBSCAN scene features before rerunning the full experiment.

Primary issues addressed:

- `intersection_flag` was too broad after adding `lane_connector` fallback.
- `car_following_ratio` and TTC were based on global x-axis filtering, not ego-frame front-vehicle logic.
- `truck_bus_ratio` counted scene-level truck/bus presence too broadly.

## Script Changes

Updated `HDBSCAN/scripts/scene_feature_hdbscan.py`:

- Added ego-frame object projection with forward/lateral distance.
- Replaced global `rel_x > 0` front-vehicle logic with ego-frame filtering:
  - forward distance: `0m` to `80m`
  - lateral distance: `<= 4m`
- Changed TTC to use the nearest ego-frame front vehicle speed instead of frame average object speed.
- Added `ttc_valid_ratio`.
- Restricted `truck_bus_ratio` to near or ego-relevant heavy vehicles.
- Added `truck_bus_dynamic_ratio`.
- Restricted bicycle/motorcycle ratios to nearby objects.
- Split map topology into:
  - `intersection_density`: only `road_segment.is_intersection`
  - `lane_connector_density`: connector topology recorded separately
- Changed `intersection_flag` to scene-level threshold:
  - `intersection_density >= 0.3`
- Added environment controls for validation:
  - `SCENE_CLUSTER_MAX_SCENES`
  - `SCENE_CLUSTER_FEATURE_OUTPUT`

Updated `HDBSCAN/scripts/corner_case_detection.py`:

- Risk score now prefers `truck_bus_dynamic_ratio` when available.
- `truck_bus_ratio` is used only as fallback for older result tables.
- Added `close_following_ratio` to risk feature candidates.

## Validation Run

Command:

```powershell
$env:SCENE_CLUSTER_MAX_SCENES='50'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_debug_50.csv'
D:\Python\Conda\envs\autodrive-cluster\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\scene_feature_hdbscan.py
```

Output:

- `HDBSCAN/tables/scene_features_debug_50.csv`
- Shape: `50 x 31`

The formal full table was not overwritten:

- `HDBSCAN/tables/scene_features.csv`
- Last modified: `2026-06-16 21:57:13`

## Debug Distribution Check

Comparison uses the first 50 rows of the current full table as `old`, and `scene_features_debug_50.csv` as `new`.

```text
feature                  old_mean  new_mean  old_median  new_median
car_following_ratio      0.8686    0.4930    0.9744      0.4429
close_following_ratio    0.3426    0.1593    0.3000      0.1013
min_ttc                  2.6900    7.7222    0.9538      1.8164
dangerous_ttc_ratio      0.4044    0.2329    0.4213      0.0662
truck_bus_ratio          0.6425    0.5493    0.7875      0.6125
intersection_flag        1.0000    0.7600    1.0000      1.0000
intersection_density     0.7850    0.5179    0.8375      0.4814
```

New diagnostic features:

```text
ttc_valid_ratio           mean 0.3398, median 0.3500
truck_bus_dynamic_ratio   mean 0.2096, median 0.0125
lane_connector_density    mean 0.7538, median 0.8000
```

## Interpretation

- Front-vehicle and TTC features are materially tighter and less likely to mark ordinary scenes as high risk.
- Dynamic heavy-vehicle exposure is much lower than broad truck/bus presence, so it should reduce false dangerous-scene ranking caused by parked or irrelevant heavy vehicles.
- Intersection features are improved but may still be broad in dense urban maps. If full-run `intersection_flag` remains too high, next threshold candidate is `intersection_density >= 0.5`.

## Next Step

Run the full 850-scene feature extraction only after accepting this revised feature definition.

## Follow-up Revision - VRU and Weighted Risk

### Additional feature changes

Updated `HDBSCAN/scripts/scene_feature_hdbscan.py` again to add conflict-oriented features:

- Added object velocity estimation through adjacent annotations.
- Added ego-frame velocity projection.
- Added VRU features:
  - `pedestrian_front_ratio`
  - `pedestrian_crossing_risk_ratio`
  - `crosswalk_pedestrian_ratio`
- Added front-vehicle distance feature:
  - `front_vehicle_min_dist`
- Added ego dynamics features:
  - `ego_decel_min`
  - `ego_hard_accel_ratio`
- Added dynamic two-wheeler feature:
  - `two_wheeler_dynamic_ratio`

Updated `HDBSCAN/scripts/cluster_umap_hdbscan.py`:

- Added environment-configurable input and output names:
  - `SCENE_CLUSTER_FEATURE_INPUT`
  - `SCENE_CLUSTER_CLUSTER_OUTPUT`
  - `SCENE_CLUSTER_CLUSTER_FIGURE`

Updated `HDBSCAN/scripts/corner_case_detection.py`:

- Added environment-configurable input and output names:
  - `SCENE_CLUSTER_CLUSTER_INPUT`
  - `SCENE_CLUSTER_SCORE_OUTPUT`
- Changed risk score from equal-weight averaging to weighted risk components.
- Changed `corner_score` weights to:
  - `rarity = 0.25`
  - `atypical_norm = 0.25`
  - `risk = 0.50`
- Added `atypical_positive` and `atypical_norm` to prevent raw cluster-distance z-scores from dominating risk ranking.

### Second debug validation

Feature extraction command:

```powershell
$env:SCENE_CLUSTER_MAX_SCENES='50'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_debug_50.csv'
D:\Python\Conda\envs\autodrive-cluster\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\scene_feature_hdbscan.py
```

Debug feature output:

- `HDBSCAN/tables/scene_features_debug_50.csv`
- Shape: `50 x 38`

Selected debug feature distributions:

```text
pedestrian_front_ratio           mean 0.4141, median 0.3670
pedestrian_crossing_risk_ratio   mean 0.3107, median 0.2500
crosswalk_pedestrian_ratio       mean 0.0275, median 0.0000
front_vehicle_min_dist           mean 13.6759, median 5.8209
ego_decel_min                    mean -3.1462, median -3.1823
ego_hard_accel_ratio             mean 0.0495, median 0.0513
two_wheeler_dynamic_ratio        mean 0.1068, median 0.0000
truck_bus_dynamic_ratio          mean 0.2096, median 0.0125
ttc_valid_ratio                  mean 0.3398, median 0.3500
```

Debug clustering command:

```powershell
$env:SCENE_CLUSTER_FEATURE_INPUT='scene_features_debug_50.csv'
$env:SCENE_CLUSTER_CLUSTER_OUTPUT='scene_features_debug_50_umap_hdbscan.csv'
$env:SCENE_CLUSTER_CLUSTER_FIGURE='Figure_debug_50.png'
D:\Python\Conda\envs\autodrive-umap-smoke\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\cluster_umap_hdbscan.py
```

Debug clustering output:

- `HDBSCAN/tables/scene_features_debug_50_umap_hdbscan.csv`
- Cluster count: `2`

Debug scoring command:

```powershell
$env:SCENE_CLUSTER_CLUSTER_INPUT='scene_features_debug_50_umap_hdbscan.csv'
$env:SCENE_CLUSTER_SCORE_OUTPUT='scene_features_debug_50_with_corner_score.csv'
D:\Python\Conda\envs\autodrive-umap-smoke\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\corner_case_detection.py
```

Debug scoring output:

- `HDBSCAN/tables/scene_features_debug_50_with_corner_score.csv`

Top debug scenes:

```text
scene-0045
scene-0035
scene-0012
scene-0024
scene-0043
```

### Current status

- The latest scripts pass syntax checks.
- The latest scripts complete a 50-scene debug end-to-end run.
- The formal 850-scene CSV outputs have not been overwritten by this debug validation.
- A full rerun is still required before using the revised features as thesis results.

## 2026-07-11 Manual Case Feedback Revision

Manual GIF review identified a remaining false-positive pattern:

- `scene-0043`: red-light waiting at an intersection; many dynamic heavy vehicles are lateral/right-turn traffic and not direct ego threats.
- `scene-0046`: red-light waiting at an intersection; high TTC was caused by opposite/right-turn vehicles rather than ego-path front vehicles.
- `scene-0012`: heavy vehicle merging from a side road should be treated as a merge/path-conflict pattern, not as simple same-lane following.

Feature script updates:

- Added `is_same_path_lead_vehicle`.
- Added `is_path_conflict_vehicle`.
- TTC now excludes crossing, opposing, and right-turn traffic by requiring:
  - tighter lateral distance: `FRONT_TTC_LATERAL_LIMIT = 2.5`
  - object forward speed not clearly opposing ego
  - object lateral speed below `CROSS_TRAFFIC_LATERAL_SPEED`
  - ego speed above `EGO_TTC_MIN_SPEED`
- Added:
  - `path_conflict_vehicle_ratio`
  - `truck_bus_path_conflict_ratio`

Scoring script updates:

- Added `path_conflict_vehicle_ratio` as a weighted risk component.
- Prefer `truck_bus_path_conflict_ratio` over `truck_bus_dynamic_ratio`.
- `truck_bus_dynamic_ratio` is now only a weak fallback when path-conflict heavy-vehicle data is unavailable.

Post-filter five-case check:

```text
scene-0045  dangerous_ttc_ratio 0.0, path_conflict_vehicle_ratio 0.4872
scene-0024  pedestrian_crossing_risk_ratio 0.8250, path_conflict_vehicle_ratio 0.0
scene-0043  dangerous_ttc_ratio 0.0, truck_bus_path_conflict_ratio 0.0
scene-0046  dangerous_ttc_ratio 0.0, path_conflict_vehicle_ratio 0.0
scene-0012  path_conflict_vehicle_ratio 0.1250, truck_bus_path_conflict_ratio 0.05
```

Remaining design note:

- `scene-0012` now has merge/path-conflict signal but the normalized score remains low in the 50-scene debug run. If side-road merging is a priority scenario category, add a dedicated merge feature or increase path-conflict weighting before the full rerun.
