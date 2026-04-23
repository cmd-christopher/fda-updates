---
phase: 04-automation-deployment
plan: 01
subsystem: data-pipeline
tags: [cache, incremental, labels, performance]
dependency_graph:
  requires: [data/approvals.json]
  provides: [fda_approvals.py --cache, data/.label_cache.json]
  affects: [fda_approvals.py, build.py (downstream consumer of set_id)]
tech_stack:
  added: [argparse --cache flag, json-based label cache]
  patterns: [incremental API fetching, file-based cache]
key_files:
  created:
    - test_cache.py
  modified:
    - fda_approvals.py
    - .gitignore
decisions:
  - D-02: Incremental label fetch via set_id cache (implemented)
  - D-03: Cache stored in data/.label_cache.json (implemented)
  - Cache self-heals: drugs missing set_id in cached label are re-fetched on next run
metrics:
  duration: ~22min
  completed: 2026-04-23
  tasks: 1
  files_changed: 3
  tests_added: 10
---

# Phase 04 Plan 01: Incremental Label Cache Summary

Added `--cache` flag and `set_id` field to `fda_approvals.py` for incremental label fetching. Weekly pipeline runs can now skip re-downloading label data for drugs already seen, reducing API calls from ~210 (105s delay) to only genuinely new drugs.

## Changes Made

### fda_approvals.py
- **`--cache` CLI argument**: When provided, loads previous `data/approvals.json` to reuse label data for known drugs and saves a `data/.label_cache.json` mapping after processing
- **`LABEL_CACHE_PATH` constant**: Points to `data/.label_cache.json` for persistent app_num → set_id mapping
- **`set_id` field in `fetch_label()`**: Extracts `id` from openFDA label API response (UUID like `eac65e03-3444-4d6b-acb8-ea4f7a276f03`)
- **`load_previous_approvals()` function**: Loads previous run's `approvals.json`, builds app_num → drug dict for drugs with labels; gracefully handles missing/corrupt files
- **`save_label_cache()` function**: Writes app_num → set_id mapping to `data/.label_cache.json`; creates parent directory if needed
- **Cache-aware label loop**: When `--cache` is True, reuses previous label data for drugs with matching application_number; prints `(cached)` to stderr for cached drugs
- **`--skip-labels` takes precedence**: When both flags provided, no caching occurs, no cache file written

### .gitignore
- Added `data/.label_cache.json` (derived data, not version-controlled)

### test_cache.py (NEW)
- 10 unit tests covering: load_previous_approvals (missing file, corrupt JSON, empty drugs, valid mapping), save_label_cache (set_id mapping, valid JSON, parent directory creation), LABEL_CACHE_PATH constant, --cache CLI argument

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical Functionality] Added os.makedirs() to save_label_cache()**
- **Found during:** Implementation of save_label_cache
- **Issue:** If `data/` directory doesn't exist (e.g., first run on fresh checkout), save_label_cache would crash with FileNotFoundError
- **Fix:** Added `os.makedirs(os.path.dirname(cache_path), exist_ok=True)` before opening the cache file
- **Files modified:** fda_approvals.py
- **Commit:** 2e99ed6

**2. [Prerequisite] Committed uncommitted Phase 1-3 changes to fda_approvals.py**
- **Found during:** Startup — working tree had 202 lines of uncommitted changes from Phase 1 (SUPPL support, slugify, etc.)
- **Fix:** Committed existing changes as `feat(01-02)` before starting Plan 04-01 work
- **Commit:** 20d4038

## TDD Gate Compliance

- ✅ `test(...)` commit exists: `1fd424e` — 9 failing tests for --cache, load_previous_approvals, save_label_cache
- ✅ `feat(...)` commit exists: `0e8c946` — Implementation passing all tests
- ✅ `refactor(...)` commit exists: `2e99ed6` — Added os.makedirs safety + test for directory creation

## Known Stubs

None — all data paths are wired. The previous `data/approvals.json` may lack `set_id` in its label dicts (pre-upgrade), but the cache self-heals by re-fetching those drugs on the next run.

## Threat Flags

No new threat surface beyond what was planned. The cache file (`data/.label_cache.json`) contains only public FDA data (application_number, set_id UUID) and is in .gitignore. Cache validation is handled by `load_previous_approvals()` which falls back to empty dict on corrupt/missing data.

## Self-Check: PASSED

- FOUND: fda_approvals.py
- FOUND: test_cache.py
- FOUND: 04-01-SUMMARY.md
- FOUND: 1fd424e (RED test commit)
- FOUND: 0e8c946 (GREEN feat commit)
- FOUND: 2e99ed6 (REFACTOR commit)