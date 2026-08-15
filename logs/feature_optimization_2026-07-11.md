# Feature Optimization Run - 2026-07-11

## Scope

Implement and validate the event-oriented V2 feature design on the first 50 nuScenes scenes. Formal 850-scene outputs were not overwritten.

## Environments

- Feature extraction and unit tests: `D:\Python\Conda\envs\autodrive-cluster\python.exe`
- UMAP/HDBSCAN and scoring: `D:\Python\Conda\envs\autodrive-umap-smoke\python.exe`
- Dataset: `nuScenes v1.0-trainval`

## Commands

```powershell
$env:SCENE_CLUSTER_MAX_SCENES='50'
$env:SCENE_CLUSTER_FEATURE_OUTPUT='scene_features_v2_debug_50.csv'
D:\Python\Conda\envs\autodrive-cluster\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\scene_feature_hdbscan.py

$env:SCENE_CLUSTER_FEATURE_INPUT='scene_features_v2_debug_50.csv'
$env:SCENE_CLUSTER_CLUSTER_OUTPUT='scene_features_v2_debug_50_umap_hdbscan.csv'
$env:SCENE_CLUSTER_CLUSTER_FIGURE='Figure_v2_debug_50.png'
D:\Python\Conda\envs\autodrive-umap-smoke\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\cluster_umap_hdbscan.py

$env:SCENE_CLUSTER_CLUSTER_INPUT='scene_features_v2_debug_50_umap_hdbscan.csv'
$env:SCENE_CLUSTER_SCORE_OUTPUT='scene_features_v2_debug_50_with_corner_score.csv'
D:\Python\Conda\envs\autodrive-umap-smoke\python.exe -u F:\Scene_cluster\HDBSCAN\scripts\corner_case_detection.py
```

## Outputs

- `HDBSCAN/tables/scene_features_v2_debug_50.csv`: `50 x 57`
- `HDBSCAN/tables/scene_features_v2_debug_50_umap_hdbscan.csv`
- `HDBSCAN/tables/scene_features_v2_debug_50_with_corner_score.csv`
- Plot skipped because `autodrive-umap-smoke` does not contain matplotlib.

## Verification

- `python -m unittest discover -s HDBSCAN/tests -v`: 19 tests passed.
- Feature scripts compiled in `autodrive-cluster`.
- UMAP/HDBSCAN and scoring scripts compiled and ran in `autodrive-umap-smoke`.
- Feature extraction completed three times during rule diagnosis; the final run processed 50 scenes in about 3 minutes after nuScenes loading.

## Result Summary

- Local vehicle density mean is `6.52`; the old implementation counted all annotated vehicles in each frame.
- `scene-0045` retains real following (`0.7949`) and its invalid `0.36m` front-center distance becomes `13.68m` bumper clearance.
- `scene-0024` records VRU crossing exposure (`0.3000`) separately from strict conflict (`0.0500`).
- `scene-0043` no longer has false dangerous longitudinal TTC; `min_ttc=20.87s`, longitudinal risk `0.0`, total risk `0.11`.
- `scene-0046` false TTC and merge conflict are both zero; total risk is zero.
- `scene-0012` records heavy-vehicle merge exposure (`0.0250`) without falsely declaring immediate conflict.

## Limitation And Next Gate

All 50 debug scenes were labelled HDBSCAN noise (`cluster=-1`) under `min_cluster_size=20`. Do not interpret debug rarity, outlier ranking, or final corner-score rank. The next valid gate is a full 850-scene run followed by cluster stability checks and a larger stratified manual review set.

## Second Manual Review Batch

Five additional scenes were selected from different V2 event categories, excluding the first review batch:

| Scene | Main review target | Key V2 values |
| --- | --- | --- |
| `scene-0016` | Same-path following | following `0.6000`, risk `0.1205` |
| `scene-0019` | Heavy-vehicle merge exposure plus VRU interaction | heavy merge exposure `0.0750`, VRU conflict `0.2500`, risk `0.2500` |
| `scene-0018` | Crossing-vehicle exposure | crossing exposure `0.5750`, crossing conflict `0.0000`, risk `0.2796` |
| `scene-0017` | VRU path conflict | VRU crossing exposure `0.5250`, VRU conflict `0.3250`, risk `0.3250` |
| `scene-0025` | Intersection-stop control case | intersection stop `0.5750`, VRU exposure `0.5750`, strict VRU conflict `0.0500`, risk `0.0395` |

GIF export settings:

- nuScenes version: `v1.0-trainval`
- Channel: `CAM_FRONT`
- Frequency: `2`
- Output: `exports/feature_check_v2_20260711/`
- All five exports succeeded.
- Each GIF contains 40 frames at `1600 x 900`, with `500ms` frame duration.

## User Review Of Second Batch

| Scene | User interpretation | Feature implication |
| --- | --- | --- |
| `scene-0016` | A same-lane vehicle was already stationary ahead with hazard lights; ego later changes lane to avoid it. This was confirmed from the 6 FPS camera-stream GIF. | Classify as stationary-lane-obstacle avoidance, not lead-vehicle sudden braking; add stopped-lead-at-first-detection and ego avoidance/lane-change response. |
| `scene-0019` | Heavy-vehicle merge is present but has little interaction with ego because ego turns left before the distant merge point; VRU interaction is strong. | Constant-heading prediction overstates distant merge relevance; compare actor trajectory with ego's observed future path. |
| `scene-0018` | Crossing traffic is present without true conflict; ego turns onto a main road and then into a smaller road. | Crossing exposure is correct, while crossing conflict should remain zero; add maneuver sequence or path-segment context. |
| `scene-0017` | Two VRU interactions: the first is weak at the roadside, the second is strong on a pedestrian crossing. | Scene-level ratios lose event multiplicity and severity; output event-level start/end, location context, and max severity. |
| `scene-0025` | Ego is already stopped at an apparently unsignalized intersection. Pedestrians and cross traffic are low risk in this recorded state, but the same flows would be more challenging if ego approached while moving and had to decide whether to stop or turn. | Separate initial stopped state from conflict-induced stopping; do not use intersection stopping as a universal risk attenuator. |

Trajectory evidence from nuScenes keyframes:

```text
scene-0016 initial_stop_ratio 0.0, total heading change 1.37 rad
scene-0019 initial_stop_ratio 0.0, total heading change 1.65 rad
scene-0018 initial_stop_ratio 0.0, total heading change 3.43 rad
scene-0017 starts near 10.4 m/s and ends near 0 m/s
scene-0025 initial_stop_ratio 1.0, then restarts near the end of the scene
```

`scene-0016` contains 234 available CAM_FRONT sensor frames at about 12 FPS. A higher-temporal-resolution review GIF was exported by sampling every second camera frame:

- `exports/feature_check_v2_20260711/scene-0016_CAM_FRONT_6fps.gif`
- 117 frames, `960 x 540`, `167ms` frame duration

Final manual label for `scene-0016`:

- Lead vehicle state: already stationary when first observed, not a follow-then-sudden-stop event.
- Ego interaction: meaningful because ego changes lane to avoid the stopped vehicle.
- Desired scenario semantics: `stationary_lead_obstacle_exposure` plus `ego_evasive_lane_change`.
- Risk implication: do not increase lead-braking risk; retain scenario value through obstacle proximity and avoidance response.

## Decision-process Feature Run

Output files:

- `HDBSCAN/tables/scene_features_decision_debug_50.csv`: `50 x 80`
- `HDBSCAN/tables/scene_features_decision_debug_50_umap_hdbscan.csv`
- `HDBSCAN/tables/scene_features_decision_debug_50_with_corner_score.csv`

Implemented features:

- Initial stop, stop from motion, restart after stop, and first sustained-stop time.
- Stationary lead obstacle exposure and ego lateral avoidance with turn rejection.
- Recorded-future-path relevance for merge actors, including heavy vehicles.
- VRU crossing/conflict event counts and maximum conflict duration.
- Map control densities for traffic lights, stop signs, turn stops, and non-signalized intersections.
- Separate `observed_risk` and `decision_demand` outputs.

The user clarified that intersection stopping must not be treated as safe only when ego was already stopped. A stable stop reduces the remaining observed conflict, while an approach-and-stop decision retains high decision demand. `scene-0025` map records contain `STOP_SIGN` and `TURN_STOP`, but no traffic-light control in the reviewed area; it is treated as non-signalized rather than fully uncontrolled.

Selected validation values:

```text
scene-0016  stationary lead 0.2250, evasive lane change 1, observed risk 0.1205, decision demand 0.3750
scene-0019  heavy merge exposure 0.0750, observed heavy merge relevance 0.0000, VRU events 3, decision demand 1.0000
scene-0018  lateral shift 14.5125m, net heading change 1.0541rad, evasive lane change 0
scene-0017  VRU conflict events 2, max VRU conflict duration 5.4511s, stop from motion 1
scene-0025  stopped at start 1, restart 1, observed risk 0.0395, decision demand 0.4000, combined risk 0.1195
scene-0043  observed risk 0.1100, decision demand 1.0000, combined risk 0.3100
```

The 50-scene decision-feature clustering produced two labels with counts `28` and `22`. This is a development signal only; full-dataset stability and semantic review are still required before treating the clusters as thesis results.

## Third Manual Review Batch

Five new scenes were selected to validate decision-process features without repeating the first two review batches:

| Scene | Review target | Key decision features |
| --- | --- | --- |
| `scene-0028` | Moving-to-stop decision with high decision demand | stop from motion `1`, decision demand `1.0000`, observed risk `0.3188` |
| `scene-0006` | Stationary lead and evasive-lane-change candidate | stationary lead ratio `0.3750`, evasive lane change `1` |
| `scene-0029` | Merge exposure rejected by recorded future path | merge exposure `0.1750`, observed relevance `0.0000`, synchronized distance `20.1485m` |
| `scene-0047` | Positive merge-path relevance control | merge exposure `0.1500`, observed relevance `0.1500`, synchronized distance `3.9421m` |
| `scene-0011` | Multiple VRU conflict events | VRU conflict events `3`, max duration `3.0009s`, observed risk `0.2500` |

High-temporal-resolution GIF settings:

- Source: full nuScenes `CAM_FRONT` sample-data stream at approximately 12 FPS.
- Export: every second camera frame, approximately 6 FPS.
- Resolution: `960 x 540`.
- Output: `exports/decision_check_batch3_20260711/`.
- All files contain `113 ~ 117` frames; no source frames were missing.

## User Review Of Third Batch

| Scene | User interpretation | Validation result and next implication |
| --- | --- | --- |
| `scene-0028` | Ego stops for a red light; traffic participants are also present. | Stop-from-motion is correct, but `decision_demand=1.0` is too high because traffic-light infrastructure density is `0.525`. Signalized control must suppress non-signalized decision demand. |
| `scene-0006` | A stationary lead exists; at scene start a pedestrian also walks in ego's lane in the same direction. | Stationary-lead feature is correct. Add same-lane/same-direction VRU exposure because this is not a crossing event. |
| `scene-0029` | Ego is waiting at a red light with little risk. | Recorded-path filtering is correct: merge exposure `0.175` is rejected by observed relevance `0.0`; total risk remains `0.0`. |
| `scene-0047` | The merge is relevant to ego. | Positive control passes: merge exposure and observed relevance are both `0.150`. |
| `scene-0011` | Ego borrows the adjacent lane to pass a stationary roadside vehicle, then a pedestrian emerges between/around the obstruction. | Stationary-obstacle avoidance and VRU events are both present; add a compound occluded-VRU-during-avoidance feature rather than treating them as unrelated risks. |

Next feature corrections indicated by this batch:

- Apply a traffic-light-control factor to `decision_demand`; nearby non-signalized map regions must not dominate a signalized stop scene.

## Same-lane VRU and obstacle-avoidance compound feature

Implemented and reran the 50-scene decision debug batch after the third manual review.

Changes:

- Added `same_lane_vru_exposure_ratio` and `same_direction_vru_ratio` without relaxing the crossing-VRU rule.
- Added `obstacle_avoidance_vru_conflict_ratio` and its event count. It is active only when a stationary lead is followed by an evasive lane change and a VRU conflict occurs within the following 10 seconds.
- Added traffic-light suppression to `decision_demand`: control density at or above `0.30` leaves 20% of the otherwise non-signalized demand.
- Added the three semantic ratios to the explicit clustering feature whitelist.

Validation command used the `autodrive-cluster` interpreter for extraction and `autodrive-umap-smoke` for clustering/scoring. The extraction completed 50 scenes in about 3 minutes 35 seconds and produced `50 x 84` features with no NaN or infinite values.

Acceptance results:

| Scene | Result |
| --- | --- |
| `scene-0006` | same-lane VRU `0.275`, same-direction VRU `0.075` |
| `scene-0011` | obstacle-avoidance VRU conflict `0.225` |
| `scene-0028` | decision demand reduced from `1.000` to `0.200`; combined risk reduced from about `0.519` to `0.359` |
| `scene-0029` | combined risk remains `0.000`; rejected merge relevance remains `0.000` |
| `scene-0047` | observed merge relevance remains `0.150` |

The resulting 50-scene clustering labelled all rows as noise under fixed `min_cluster_size=20`. This batch remains a feature/risk acceptance run only; clustering quality must be evaluated on the full 850-scene rerun rather than tuned to these 50 cases.
- Add `same_lane_vru_exposure_ratio` and `same_direction_vru_ratio` for pedestrians walking in ego's lane.
- Add `obstacle_avoidance_vru_conflict_ratio` for pedestrian emergence during or immediately after stationary-obstacle avoidance.

## Fourth Manual Review Batch

Selected five previously unreviewed scenes from the existing 50-scene feature table. The batch is stratified by rule purpose rather than corner-score rank because all 50 rows are HDBSCAN noise in this debug run.

| Scene | Review target | Current feature expectation |
| --- | --- | --- |
| `scene-0031` | Same-lane VRU and strict VRU conflict | same-lane `0.125`, same-direction `0.025`, VRU conflict `0.125`, stationary lead `0.275` |
| `scene-0022` | Positive obstacle-avoidance plus VRU compound event | evasive lane change `1`, compound conflict `0.050`, decision demand `0.500` |
| `scene-0030` | Evasive maneuver negative control for compound VRU | stationary lead `0.275`, evasive lane change `1`, compound conflict `0.000` |
| `scene-0042` | Low-risk observed merge relevance | merge observed relevance `0.0976`, combined risk `0.0878` |
| `scene-0008` | Non-signalized decision-demand and VRU case | decision demand `0.6875`, VRU conflict `0.100`, combined risk `0.3875` |

GIF output: `exports/feature_check_batch4_20260711/`.

- Full CAM_FRONT sample-data stream sampled every second frame.
- `960 x 540`, approximately 6 FPS, 111 to 117 frames per scene.
- No missing source frames in the five exports.

## User Review Of Fourth Batch

| Scene | User interpretation | Diagnosis |
| --- | --- | --- |
| `scene-0031` | The pedestrian moves against ego direction and is near, but not inside, ego lane. | Fixed `+/-1.8m` lateral distance is not a lane-membership test. The current same-lane `0.125` and same-direction `0.025` are false positives; actor heading/lane geometry is required. |
| `scene-0022` | VRUs remain on the side footpath and pose little threat to ego. | The current VRU conflict `0.050` and compound avoidance-VRU `0.050` inherit an over-broad corridor-entry prediction without sufficient spatial/temporal interaction evidence. |
| `scene-0030` | Obstacle avoidance occurs, but VRUs are not threatening. | The negative compound VRU result `0.000` agrees with review. The evasive maneuver feature is useful here. |
| `scene-0042` | No merge occurs. Ego avoids two stationary vehicles in its lane; oncoming traffic during the second avoidance adds some risk. | Merge observed relevance `0.0976` is a false positive caused by using future minimum distance without rejecting opposing traffic. Stationary-obstacle extraction also misses both avoidance events and needs lane/obstacle-path logic. A separate oncoming-traffic-during-avoidance feature is needed. |
| `scene-0008` | Scene description is correct, but VRUs are relatively distant and interaction is weak. | VRU conflict `0.100`, VRU risk `1.000`, and decision demand `0.6875` are too high. Conflict scoring needs minimum synchronized distance and event-duration/severity calibration rather than saturating on a two-second distant event. |

Root causes identified from this batch:

- Ego-frame lateral thresholds approximate a corridor but do not establish lane membership.
- VRU path conflict predicts lateral corridor entry but does not compare synchronized ego/VRU arrival distance strongly enough.
- Merge observed relevance uses synchronized Euclidean proximity but does not classify relative heading, so opposing traffic can appear merge-relevant.
- Stationary-lead detection requires the actor to pass the same-path vehicle rule and therefore misses some parked obstacles that ego later avoids.

## Second Interaction Tightening Run

Implemented approved option A using only nuScenes maps, ego pose, and annotations. No camera detector was introduced.

Implementation changes:

- Same-lane VRU requires the candidate not to be on a walkway and to lie within `1.8m` of the ego lane centerline.
- Same-direction VRU events shorter than one second are removed as velocity noise.
- Predicted VRU conflicts are checked against synchronized recorded trajectories, a `6m` distance threshold, and actual entry into the ego lane.
- Obstacle-avoidance VRU events now use observed VRU relevance rather than instantaneous prediction.
- Merge candidates require positive longitudinal motion, aligned annotation heading, recorded-path relevance, and at least one second duration.
- Added `oncoming_during_avoidance_ratio`; it remains unavailable when the stationary obstacle itself lacks annotation.
- New feature tables use observed VRU relevance for strict VRU risk; historical tables fall back to the old conflict fields.

The final feature extraction processed 50 scenes in about 5 minutes 1 second and produced `50 x 90` columns before CSV index loading (`89` data columns after using `scene_name` as the analysis index). No NaN or infinite values were present.

| Scene | Final validation |
| --- | --- |
| `scene-0031` | same-lane `0`, same-direction `0`, observed VRU relevance `0`, risk `0.1857` |
| `scene-0022` | observed VRU relevance `0`, compound VRU `0`, risk `0.1414` |
| `scene-0030` | evasive lane change `1`, compound VRU `0`, risk `0.2139` |
| `scene-0042` | merge exposure/relevance `0`, risk `0`; the two unannotated parked vehicles remain unrecoverable |
| `scene-0008` | predicted VRU conflict `0.100`, observed relevance `0`, synchronized minimum distance `7.058m`, risk `0.1375` |
| `scene-0006` | same-lane `0.225`, same-direction `0.075` retained |
| `scene-0011` | observed and obstacle-avoidance VRU relevance `0.225` retained |
| `scene-0029` | rejected merge relevance and risk remain `0` |
| `scene-0047` | sustained observed merge relevance remains `0.125` |

All 50 rows remain HDBSCAN noise under the fixed debug parameter `min_cluster_size=20`; the clustering rank is not a valid thesis result.

## Fifth Manual Review Batch

Five previously unreviewed scenes were selected to test distinct boundaries introduced by the second tightening run. GIFs are stored in `exports/feature_check_batch5_20260711/`, sampled from full CAM_FRONT data at approximately 6 FPS, `960 x 540`, with 112 to 117 frames and no missing source images.

### `scene-0050`

nuScenes description: narrow street, several pedestrians, shadows, left turn, parked motorcycle.

Current interpretation:

- Ego starts moving at about `8.68m/s`.
- A predicted VRU conflict is confirmed by recorded trajectory for one frame (`0.0256`, about `0.5s`), with synchronized minimum distance `3.73m`.
- A distant stationary lead is briefly detected at `29.44m`; ego is classified as evasive, but the VRU event does not fall inside the obstacle-avoidance compound window.
- Non-signalized decision demand is `0.513`; total risk is `0.165`.

Manual review questions: Does a pedestrian actually enter or closely approach ego's future lane, and is the interaction strong enough to justify a strict VRU event? Is the detected evasive maneuver a real obstacle avoidance, an ordinary left turn, or lane positioning on a narrow road? Should the pedestrian event and maneuver be treated as related?

### `scene-0004`

nuScenes description: approach and cross an intersection with jaywalkers.

Current interpretation:

- Ego starts moving at about `4.86m/s`.
- A one-frame observed VRU event is detected (`0.025`, about `0.5s`) with synchronized minimum distance `2.18m`.
- Traffic-light-control density is high (`0.65`), so decision demand is attenuated to `0.0094`.
- Total risk is `0.106`, mainly from the short VRU event.

Manual review questions: Does a jaywalker truly cross ego's driven path at a relevant time, or is the `2.18m` proximity reached only after ego has yielded/passed? Is the scene controlled by a traffic light relevant to ego, and does the current low decision-demand result match the actual driving task?

### `scene-0007`

nuScenes description: van overtaking ego, pedestrians, jaywalker, bicycle rack, left turn.

Current interpretation:

- Merge exposure is `0.128`; sustained observed relevance remains `0.0769`, with synchronized minimum distance `3.79m`.
- Predicted VRU conflict is `0.0769`, but recorded trajectory never enters ego lane, so strict VRU risk is zero.
- No immediate observed collision risk is assigned; non-signalized decision demand is `0.590`, producing total risk `0.118`.

Manual review questions: Is the van genuinely overtaking/merging in a way that affects ego, or merely passing with adequate separation? Does ego's later left turn end the interaction before the merge point? Are pedestrians correctly treated as exposure rather than a direct conflict?

### `scene-0026`

nuScenes description: parked cars and pedestrians on the roadside.

Current interpretation:

- Stationary lead exposure is high (`0.359`) and reaches a minimum clearance of `5.61m`.
- TTC is valid for `48.7%` of frames, reaches `1.90s`, and remains dangerous for up to `2.55s`.
- Ego is not classified as an evasive lane change, so the scene is scored as longitudinal risk (`0.226`) rather than avoidance.
- Pedestrians do not form same-lane or strict observed VRU interactions.

Manual review questions: Is ego genuinely following a stopped/slow lead vehicle, approaching a parked obstacle, or simply passing roadside parked cars? Does ego brake, stop, or shift laterally in response? Is the `1.90s` TTC physically meaningful, or caused by treating a parked roadside vehicle as a same-path lead?

### `scene-0021`

nuScenes description: wait at intersection, jaywalkers, parking lot, parked bicycle, right turn, construction, truck.

Current interpretation:

- Ego is stopped at scene start and later restarts.
- Same-lane and same-direction VRU exposure are both `0.075`, but there is no predicted or observed VRU conflict.
- Intersection stop ratio is `0.275`; no traffic-light control is found and non-signalized density is `0.825`.
- Decision demand is `0.225`, observed risk is zero, and total risk is `0.045`.

Manual review questions: Is the VRU really walking in ego's lane and in the same direction, or merely near the lane/parking area? Does the VRU influence ego's restart or right-turn decision? Is this genuinely an uncontrolled intersection, and is low observed risk plus moderate decision demand an appropriate interpretation?

## User Review Of Fifth Batch

| Scene | User interpretation | Result and next implication |
| --- | --- | --- |
| `scene-0050` | The VRU approaches ego's future path before the narrow-road left turn and shows crossing intent. No obvious lateral avoidance is visible. | Observed VRU relevance is valid. The evasive flag is false: it was triggered by a single-frame stationary candidate at `29.44m` followed by `3.07m` lateral displacement. Evasive classification needs stronger obstacle persistence/proximity evidence. |
| `scene-0004` | The VRU crosses early and has little interaction or threat. The `2.18m` minimum likely occurs as ego passes. The signal controls ego; ego crosses on green, and the VRU interaction occurs after the intersection. | The current low-risk description is broadly reasonable. Future refinement should retain closest-approach phase/time so post-intersection proximity is not treated like pre-conflict interaction. |
| `scene-0007` | A van overtakes ego in the right lane without meaningful risk or influence. Ego turns left after being overtaken. Pedestrians are distant exposure only. | VRU filtering is correct. `merge_observed_relevance_ratio=0.0769` is semantically misnamed: recorded proximity confirms interaction geometry but not lane entry. Overtaking and true merge must be separate features. |
| `scene-0026` | Ego initially avoids a stationary vehicle in its lane. Later, near the intersection, ego brakes and waits for a motorcycle ahead; TTC is a reasonable real risk if calculated against that motorcycle. | The sustained following/TTC event (`9.40s`, minimum TTC `1.90s`) is valid for the motorcycle. The initial stationary-car avoidance is not represented by the current single detected stationary event and may be missing or outside the same-path annotation rule. Event-local obstacle identification is needed. |
| `scene-0021` | The VRU is geometrically in ego's lane but crosses on the opposite side of the intersection. Ego turns right before reaching it, so the VRU does not affect restart or turning. No signal is visible. Low observed risk with moderate decision demand is appropriate. | Current risk output is correct (`observed_risk=0`). Same-lane VRU is an exposure feature only and must not be described as interaction without ego-route overlap. |

Recommended next semantic split:

- Require stationary-obstacle persistence or closer range before declaring evasive avoidance; preserve short detections as obstacle exposure only.
- Split vehicle side interaction into `overtaking_exposure` and `merge_lane_entry_relevance`; future minimum distance alone is insufficient for merge semantics.
- Add event phase or time-to-closest-approach for observed VRU relevance so pre-conflict, post-pass, and route-divergent exposure can be distinguished.
- Preserve same-lane VRU exposure for clustering context, but use route overlap only when describing interaction or scoring risk.

## Fifth-Batch Semantic Optimization

Implemented the next approved refinement after manual review:

- Brief distant stationary detections now require a strong heading-recovered lateral shift (`>=4m`, net heading change `<=0.10rad`) to support evasive avoidance.
- Added overtaking exposure and duration features.
- Split non-overtaking future-path relevance from strict current-lane entry relevance.
- Added scene-relative VRU closest-approach time.

Key regressions:

| Scene | Result |
| --- | --- |
| `scene-0050` | observed VRU relevance retained; closest approach at `4.15s`; false evasive flag reduced to `0` |
| `scene-0004` | short VRU closest approach occurs at `17.45s`, supporting the post-intersection interpretation |
| `scene-0007` | overtaking exposure `0.3846` for `7.75s`; merge path and lane-entry relevance both `0` |
| `scene-0026` | minimum TTC `1.90s` and dangerous duration `2.55s` retained; no false VRU or merge interaction |
| `scene-0021` | same-lane VRU remains context only; observed risk remains `0` |
| `scene-0011` | true evasive flag and obstacle-avoidance VRU ratio `0.225` retained |
| `scene-0047` | non-overtaking future-path relevance `0.125` retained; immediate current-lane entry remains `0` |

The final 50-scene feature table contains 95 columns. The debug clustering produced two labels with counts `28` and `22`. Because these scenes were repeatedly used for rule development, this is not independent clustering evidence and must not be reported as a formal thesis result.
