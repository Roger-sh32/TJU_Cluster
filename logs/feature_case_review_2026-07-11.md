# Feature Case Review - 2026-07-11

## Purpose

Export representative nuScenes scene GIFs to manually inspect whether the revised feature extraction logic is reasonable.

Source table:

- `HDBSCAN/tables/scene_features_debug_50_with_corner_score.csv`

Export command:

```powershell
D:\Python\Conda\envs\autodrive-cluster\python.exe -u -c "..."
```

Implementation detail:

- Loaded `nuScenes v1.0-trainval` once.
- Used `HDBSCAN/scripts/review_nuscenes_scenes.py::export_scene_gif`.
- Camera channel: `CAM_FRONT`
- GIF frequency: `2`
- Output directory: `exports/feature_check_20260711/`

## Selected Cases

| Scene | Reason | GIF |
| --- | --- | --- |
| `scene-0045` | Highest debug `corner_score_norm`; high dynamic heavy-vehicle exposure, high intersection density, close front vehicle | `exports/feature_check_20260711/scene-0045_CAM_FRONT.gif` |
| `scene-0024` | High `pedestrian_crossing_risk_ratio`; low TTC risk, useful for checking VRU false positives | `exports/feature_check_20260711/scene-0024_CAM_FRONT.gif` |
| `scene-0043` | High weighted `risk`; high dynamic heavy-vehicle exposure, intersection density, close front vehicle, and TTC risk | `exports/feature_check_20260711/scene-0043_CAM_FRONT.gif` |
| `scene-0046` | High TTC risk and close front vehicle; low VRU/heavy-vehicle exposure | `exports/feature_check_20260711/scene-0046_CAM_FRONT.gif` |
| `scene-0012` | Medium score with low TTC/VRU risk; comparison/control case | `exports/feature_check_20260711/scene-0012_CAM_FRONT.gif` |

## Key Feature Values

```text
            corner_score_norm    risk  pedestrian_crossing_risk_ratio  crosswalk_pedestrian_ratio  truck_bus_dynamic_ratio  intersection_density  front_vehicle_min_dist  dangerous_ttc_ratio  ttc_valid_ratio
scene-0045             1.0000  0.5444                          0.2051                         0.0                   0.7692                0.8205                  2.3583               0.2381           0.5385
scene-0024             0.6190  0.1817                          0.8250                         0.0                   0.0000                0.4250                 80.0000               0.0000           0.0000
scene-0043             0.5740  0.6392                          0.6154                         0.0                   1.0000                1.0000                  2.6641               0.4286           0.5385
scene-0046             0.4291  0.5164                          0.0256                         0.0                   0.0000                1.0000                  3.3683               0.6250           0.4103
scene-0012             0.6385  0.2938                          0.0750                         0.0                   0.1500                0.3750                 42.9402               0.0000           0.0750
```

## Notes

- All five GIFs exported successfully.
- These cases come from the 50-scene debug run, not the formal 850-scene rerun.
- Manual review should focus on whether front-vehicle, dynamic heavy-vehicle, pedestrian crossing, and intersection features match what is visible in CAM_FRONT.

## User Review Feedback

User manually reviewed the five GIFs and provided scene-level interpretation:

| Scene | User interpretation | Feature implication |
| --- | --- | --- |
| `scene-0045` | Following a front vehicle out of a gate, then merging into an intersection | Front-vehicle and intersection features are directionally reasonable |
| `scene-0024` | Confirmed pedestrian crossing scene | VRU crossing feature is directionally reasonable |
| `scene-0043` | Waiting at red light at an intersection; many dynamic heavy vehicles, but mostly lateral or right-turn traffic with little threat to ego | Dynamic heavy-vehicle presence should not directly imply ego-path risk |
| `scene-0046` | Waiting at red light; high TTC was likely caused by opposite/right-turn vehicles and is not a real ego threat | TTC needs same-path filtering and should exclude crossing/right-turn/opposing traffic |
| `scene-0012` | Heavy vehicle merging from a side road | Need merge/path-conflict feature, not just same-lane following |

## Follow-up Filter Revision

Implemented after the user feedback:

- TTC now uses `is_same_path_lead_vehicle`.
- Same-path lead vehicle requires:
  - ego-frame forward distance within `0m ~ 80m`
  - lateral distance within `2.5m`
  - object forward speed not clearly opposing ego
  - lateral speed below crossing-traffic threshold
- Added `is_path_conflict_vehicle` to capture same-path and merge/cut-in conflicts.
- Added output features:
  - `path_conflict_vehicle_ratio`
  - `truck_bus_path_conflict_ratio`
- Corner scoring now prefers `truck_bus_path_conflict_ratio`; generic `truck_bus_dynamic_ratio` is only a weak fallback when path-conflict heavy-vehicle feature is unavailable.

## Post-filter Debug Values

After rerunning the 50-scene debug feature extraction and debug scoring:

```text
            corner_score_norm    risk  path_conflict_vehicle_ratio  car_following_ratio  front_vehicle_min_dist  dangerous_ttc_ratio  truck_bus_dynamic_ratio  truck_bus_path_conflict_ratio  pedestrian_crossing_risk_ratio  intersection_density
scene-0045             1.0000  0.4475                       0.4872               0.7949                  0.3604                  0.0                   0.7692                           0.00                          0.2051                0.8205
scene-0024             0.2712  0.1629                       0.0000               0.0000                 80.0000                  0.0                   0.0000                           0.00                          0.8250                0.4250
scene-0043             0.2755  0.4100                       0.3333               0.2308                 14.2892                  0.0                   1.0000                           0.00                          0.6154                1.0000
scene-0046             0.1939  0.1174                       0.0000               0.0000                 80.0000                  0.0                   0.0000                           0.00                          0.0256                1.0000
scene-0012             0.0852  0.2687                       0.1250               0.0750                 47.1843                  0.0                   0.1500                           0.05                          0.0750                0.3750
```

Interpretation:

- `scene-0046` false TTC risk is mostly removed.
- `scene-0043` still records intersection, pedestrian/crossing, and generic dynamic heavy-vehicle exposure, but heavy vehicles no longer count as ego-path heavy-vehicle conflicts.
- `scene-0012` now has weak merge/path-conflict signal. If side-road merge is considered a key thesis target, increase the weight of `path_conflict_vehicle_ratio` or add a dedicated `merge_conflict_ratio`.

## Event-oriented V2 Result

The feature model was revised again after tracing the false-positive frames:

- `scene-0046` false merge events came from vehicles currently behind ego; merge exposure now requires positive current forward distance.
- `scene-0012` bus trajectory is stored as heavy-vehicle merge exposure even when its predicted gap does not qualify as an immediate conflict.
- `scene-0024` VRU crossing exposure is stored separately from strict simultaneous path conflict.
- `scene-0043` false longitudinal TTC came from a vehicle at roughly `2.4m ~ 2.5m` lateral offset; the same-path TTC band was tightened to `1.8m`.
- Intersection stopping attenuates lateral conflict risk but does not remove crossing-exposure semantics from clustering.

Final V2 values from `tables/scene_features_v2_debug_50_with_corner_score.csv`:

```text
scene-0045  risk 0.1823, following 0.7949, merge exposure 0.1282
scene-0024  risk 0.0375, VRU crossing exposure 0.3000, strict VRU conflict 0.0500
scene-0043  risk 0.1100, longitudinal risk 0.0000, intersection stop 0.3590
scene-0046  risk 0.0000, merge conflict 0.0000, TTC valid ratio 0.0000
scene-0012  risk 0.0000, heavy-vehicle merge exposure 0.0250
```

The 50-scene HDBSCAN result contains only label `-1` with the current `min_cluster_size=20`. Therefore this batch validates feature behavior and grouped risk only; its rarity, outlier-based ranking, and final `corner_score` are not valid evidence of full-dataset clustering quality.
