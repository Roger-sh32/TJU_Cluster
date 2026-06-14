# AGENTS.md

## Project

This is an AI-native research and engineering container for an autonomous-driving scene clustering thesis project.

The core research question is how to improve autonomous-driving road-test efficiency by extracting scene-level features from nuScenes, clustering scenarios, and identifying high-value or safety-critical scenes for review and testing prioritization.

Current technical focus:

- Dataset: `nuScenes v1.0-trainval`
- Main method track: scene feature engineering + UMAP/HDBSCAN clustering + corner case scoring
- Baseline/legacy track: KMeans clustering experiments
- Thesis outputs: Tongji MEM proposal, mid-term materials, technical route documents, and later dissertation materials

## How AI Should Collaborate

- Start from existing files. Inspect the relevant directory before changing code, docs, or results.
- Keep edits scoped. Do not reorganize datasets or move large experiment outputs unless explicitly requested.
- Preserve provenance. When generating new results, record the script, input file, environment, date, and output path.
- Separate raw materials, reusable knowledge, process logs, and final deliverables.
- Do not treat old CSV/XLSX results as current truth without checking timestamps, scripts, and columns.
- Prefer reproducible commands over manual steps. If a result is regenerated, document the exact command in `logs/`.
- Keep Chinese thesis context intact. Use English only where code, libraries, or standard names require it.

## Where To Look First

For GitHub-facing project orientation:

- `README.md`

For AI collaboration rules and content placement:

- `AGENTS.md`

For HDBSCAN feature extraction, clustering, corner scoring, and scene review:

- `HDBSCAN/`
- Start with `HDBSCAN/README.md`
- Then inspect `HDBSCAN/scripts/scene_feature_hdbscan.py`, `HDBSCAN/scripts/cluster_umap_hdbscan.py`, `HDBSCAN/scripts/corner_case_detection.py`, and `HDBSCAN/scripts/review_nuscenes_scenes.py`

For KMeans baseline and older clustering experiments:

- `Kmeans/`
- Start with `Kmeans/README.md`
- Then inspect `Kmeans/scripts/scene_feature_kmeans_baseline.py`

For source dataset and nuScenes metadata/images:

- `nuScenes/`
- Treat this as source data. Do not edit files here.

For literature, standards, thesis references, and original materials:

- `knowledge/sources/`

For distilled, reusable project knowledge:

- `knowledge/wiki/`

For execution notes, failed runs, experiment records, review feedback, and AI work logs:

- `logs/`

For final outputs that are meant to be read, submitted, presented, or shared:

- `outputs/`

For temporary scene preview exports:

- `exports/`
- This is for generated review assets such as GIFs and images, not final thesis deliverables.

## Content Placement Rules

### `knowledge/sources/`

Use this for original, externally sourced, or user-provided materials.

Examples:

- Papers, standards, reports, course materials, thesis templates
- Original PDFs, DOC/DOCX, PPT/PPTX, CAJ files
- Raw reference material from PEGASUS, ENABLE-S3, ISO 34502, i-VISTA, C-ICAP, C-NCAP, Euro NCAP, or similar sources

Do not summarize or rewrite source materials in this directory. Put summaries in `knowledge/wiki/`.

### `knowledge/wiki/`

Use this for reusable knowledge distilled from sources or experiments.

Examples:

- Feature taxonomy for scene clustering
- Standard-to-feature mapping notes
- Definitions of TTC, headway, VRU, intersection scenarios, ODD, and corner cases
- Lessons learned from comparing cluster results with scene playback

### `logs/`

Use this for process records.

Examples:

- Experiment runs and commands
- Errors and fixes
- Model/AI session notes
- User or expert feedback
- Data quality issues, such as missing nuScenes image files

### `outputs/`

Use this for final or near-final deliverables.

Examples:

- Proposal reports
- Presentation slides
- Dissertation drafts
- Final figures/tables prepared for thesis writing
- Exported analysis packages intended for sharing

## Known Current State

- `knowledge/sources/` already contains real source materials.
- `outputs/开题/` already contains proposal-stage deliverables.
- `outputs/中期/` contains the current mid-term outline.
- `HDBSCAN/` contains scripts, result tables, analysis workbooks, and a local `README.md`.
- `Kmeans/` contains the baseline/legacy KMeans track.
- `knowledge/wiki/` is initialized as a place for reusable knowledge, but no full wiki article has been added yet.
- `logs/` is initialized and in use as the project-wide process log area.

## Current Cautions

- Some HDBSCAN CSV results may not exactly match the latest script versions. Check timestamps and `HDBSCAN/README.md` before using them as reproducible results.
- Existing HDBSCAN feature tables do not reliably include `scene_token` / `scene_name`, which limits direct traceability back to nuScenes scenes.
- `intersection_flag` extraction was revised on 2026-06-14, but historical CSV results have not yet been regenerated.
- OpenCV in the current environment may have `GUI: NONE`; scene playback may fall back to GIF export.
- Some nuScenes camera files may be missing locally, so scene review exports can fail for affected scenes.
- `nuScenes/`, `exports/`, and `Kmeans/聚类/` are intentionally ignored by Git.
