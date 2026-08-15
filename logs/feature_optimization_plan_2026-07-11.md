# Event-oriented Feature Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce false dangerous-scene detections by separating scene context, interaction events, and physically meaningful risk.

**Architecture:** Add a pure, testable rules module for ego-frame interaction classification and temporal event summaries. Keep dataset traversal in the existing extraction script, restrict clustering to an explicit scenario-feature whitelist, and calculate grouped risk scores with fixed physical thresholds.

**Tech Stack:** Python 3, NumPy, pandas, scikit-learn, UMAP, HDBSCAN, nuScenes devkit, `unittest`.

## Global Constraints

- Do not overwrite the formal 850-scene result tables during validation.
- Run feature extraction with `autodrive-cluster` and UMAP/HDBSCAN with `autodrive-umap-smoke`.
- Preserve `scene_name`, `scene_token`, and `log_location` in every result table.
- Record commands, inputs, outputs, and case-review results in `logs/`.

---

### Task 1: Pure interaction rules

**Files:**
- Create: `HDBSCAN/scripts/scene_feature_rules.py`
- Create: `HDBSCAN/tests/test_scene_feature_rules.py`

**Interfaces:**
- Produces `classify_vehicle_interaction(...)`, `is_vru_path_conflict(...)`, `summarize_events(...)`, and `wrapped_heading_change(...)`.

- [ ] Write tests for same-path, merge, crossing exposure/conflict, stopped-ego filtering, VRU crossing, event duration, and yaw wraparound.
- [ ] Run `python -m unittest HDBSCAN.tests.test_scene_feature_rules -v` and verify failures are caused by the missing module.
- [ ] Implement the minimal pure rules and rerun the tests to green.

### Task 2: Feature extraction integration

**Files:**
- Modify: `HDBSCAN/scripts/scene_feature_hdbscan.py`
- Extend: `HDBSCAN/tests/test_scene_feature_rules.py`

**Interfaces:**
- Consumes the Task 1 rules.
- Produces separate ratios for following, merge conflict, crossing exposure/conflict, VRU path conflict, intersection stop, and dangerous-TTC frame duration.

- [ ] Add failing tests for local-object filtering and valid front-clearance filtering.
- [ ] Restrict neighborhood statistics to objects within 50 m and vehicle categories where appropriate.
- [ ] Use sample timestamps for ego speed/acceleration and wrapped heading change.
- [ ] Replace the broad pedestrian crossing shortcut and append frame-level event flags.
- [ ] Keep legacy columns where useful for comparison, but add explicit new event columns.
- [ ] Run unit tests and syntax compilation.

### Task 3: Scenario-only clustering

**Files:**
- Modify: `HDBSCAN/scripts/cluster_umap_hdbscan.py`
- Create: `HDBSCAN/tests/test_feature_selection.py`

**Interfaces:**
- Produces `select_clustering_features(df)` and output columns `cluster_probability`, `cluster_outlier_score`.

- [ ] Write a failing test proving identifiers, frame count, TTC, braking outcomes, sentinels, and redundant features are excluded.
- [ ] Implement an explicit semantic feature whitelist and HDBSCAN diagnostic outputs.
- [ ] Run the feature-selection tests and syntax compilation.

### Task 4: Grouped physical risk score

**Files:**
- Create: `HDBSCAN/scripts/corner_scoring.py`
- Modify: `HDBSCAN/scripts/corner_case_detection.py`
- Create: `HDBSCAN/tests/test_corner_scoring.py`

**Interfaces:**
- Produces `calculate_grouped_risk(df)` with longitudinal, merge/crossing, VRU, and ego-response sub-scores.

- [ ] Write failing tests proving no-valid-TTC is not risky, TTC above 6 seconds contributes zero, red-light cross-traffic exposure alone is not risky, and sustained VRU/merge conflicts are risky.
- [ ] Implement fixed-threshold grouped scores without per-batch MinMax risk normalization.
- [ ] Use HDBSCAN outlier score for atypicality and treat noise rows individually rather than as one rare cluster.
- [ ] Run scoring tests and syntax compilation.

### Task 5: 50-scene validation and documentation

**Files:**
- Update: `HDBSCAN/README.md`
- Update: `logs/feature_case_review_2026-07-11.md`
- Create: `logs/feature_optimization_2026-07-11.md`

- [ ] Run the 50-scene feature extraction to new `*_v2_debug_50.csv` files.
- [ ] Run clustering and scoring without overwriting formal outputs.
- [ ] Compare distributions, cluster diagnostics, and the five labelled cases against the prior debug tables.
- [ ] Record limitations and whether a full 850-scene rerun is justified.
