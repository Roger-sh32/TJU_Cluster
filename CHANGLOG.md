# CHANGLOG.md

This file records project-container changes at the repository root.

Note: the filename follows the requested spelling `CHANGLOG.md`.

## 2026-06-14

### Changed

- Added root `README.md` as the GitHub-facing project entrypoint.
- Updated Markdown entry documents after Git initialization.
- Clarified ignored local data directories and current HDBSCAN caution notes.
- Fixed mojibake in repository-level Markdown references.

### Existing Content Recognized

- `environment.yml` records the reproducible `autodrive-cluster` environment.
- `activate_project.ps1` provides a local PowerShell activation helper.
- `HDBSCAN/logs.md` records the 2026-06-14 `intersection_flag` feature extraction change.

### Not Done

- No experiment was rerun.
- No result table was regenerated.
- No dataset file was added to Git.

## 2026-06-13

### Changed

- Initialized the repository as an AI-native project container.
- Added `AGENTS.md` as the main collaboration entrypoint.
- Added project-wide process log directory `logs/`.
- Added reusable knowledge directory `knowledge/wiki/`.
- Clarified placement rules for `knowledge/sources/`, `knowledge/wiki/`, `logs/`, and `outputs/`.
- Cleaned obsolete temporary files after checking `outputs/中期/中期报告初始大纲.md`.
- Added `logs/cleanup_2026-06-13.md` to record retained evidence and deleted temporary files.
- Reorganized `HDBSCAN/` into `scripts/`, `tables/`, and `pictures/`.
- Updated HDBSCAN script default paths and documentation references after the reorganization.
- Reorganized `Kmeans/` into `scripts/`, `tables/`, and `pictures/`.
- Added `Kmeans/README.md` and `Kmeans/logs.md`.

### Existing Content Recognized

- `knowledge/sources/` already contains original reference materials.
- `outputs/开题/` already contains proposal-stage deliverables.
- `HDBSCAN/` already contains clustering scripts, result files, analysis workbooks, and local documentation.

### Not Done

- No experiment was rerun.
- No dataset files were moved.
- No existing analysis outputs were reorganized.
- No HDBSCAN result table, figure, workbook, or script was deleted.
- No KMeans experiment was rerun.
