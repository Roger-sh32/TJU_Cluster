# Interaction Feature Tightening Implementation Plan

**Goal:** Reduce false same-lane VRU, VRU conflict, and merge classifications while preserving previously validated interactions.

**Architecture:** Keep pure temporal and geometry decisions in `scene_feature_rules.py`. The nuScenes extraction script supplies map-layer membership, lane-centerline geometry, actor trajectories, and ego trajectories; scoring consumes only scene-level summaries.

**Constraints:** Use existing nuScenes maps and annotations only. Do not overwrite the formal 850-scene outputs. Treat missing annotations as a data-quality boundary.

## Task 1: Pure rule boundaries

- Add tests for walkway exclusion, lane-centerline lateral distance, sustained same-direction events, stricter positive-forward merge candidates, and oncoming classification.
- Implement minimal pure helpers in `HDBSCAN/scripts/scene_feature_rules.py`.
- Run `HDBSCAN/tests/test_scene_feature_rules.py`.

## Task 2: Extraction integration

- Add map-based VRU lane relation with a conservative fallback flag.
- Record VRU trajectory candidates and calculate synchronized observed relevance after the scene loop.
- Build obstacle-avoidance VRU events from observed relevance rather than predicted conflict.
- Record oncoming traffic and summarize it inside a detected avoidance window.
- Add new semantic fields to `feature_selection.py`.

## Task 3: Risk scoring

- Add a failing scoring test proving distant predicted VRU exposure does not saturate risk when observed relevance is absent.
- Prefer observed VRU relevance and duration when the new columns exist; retain fallback compatibility with historical tables.

## Task 4: Verification

- Run all unit tests and compile changed scripts.
- Regenerate only `scene_features_decision_debug_50*.csv`.
- Check the five fourth-batch acceptance scenes and four prior regression scenes.
- Record exact results in `logs/feature_optimization_2026-07-11.md` and update the HDBSCAN README/wiki if behavior differs from the design.
