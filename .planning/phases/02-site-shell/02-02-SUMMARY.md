---
phase: 02-site-shell
plan: 02
subsystem: ui
tags: [list.js, dark-mode, jinja2, static-site, search, sort]

# Dependency graph
requires:
  - phase: 02-site-shell/01
    provides: [site/css/custom.css, site/js/list.min.js, templates/base.html with toggle button and asset links]
provides:
  - Sortable, searchable drug approval table with List.js integration
  - Dark mode toggle with system preference + localStorage persistence
  - Data-derived last_updated timestamp in build pipeline
  - Mobile card layout with data-label attributes
affects: [phase-03-detail-pages, site/js/main.js, build.py]

# Tech tracking
tech-stack:
  added: []
  patterns: [List.js valueNames + data-timestamp for date sort, IIFE pattern for JS modules, data-derived timestamps from JSON metadata]

key-files:
  created: [site/js/main.js]
  modified: [templates/index.html, build.py]

key-decisions:
  - "Date sorting uses data-timestamp attribute (ISO date) instead of display text to prevent alphabetical date sort per PITFALLS.md"
  - "last_updated derived from data query.date_to per AUTO-05, falls back to file mtime"

patterns-established:
  - "IIFE modules in main.js: one for dark mode, one for List.js initialization"
  - "data-timestamp on td cells for custom List.js sort functions"
  - "REQUIRED_ASSETS pre-check in build.py for fail-fast on missing assets"

requirements-completed: [INDEX-01, INDEX-02, INDEX-03, INDEX-04, INDEX-05, INDEX-06, AUTO-05]

# Metrics
duration: 7min
completed: 2026-04-23
---

# Phase 2 Plan 02: Functional Index Page Summary

**Sortable, searchable drug approval table with List.js, dark mode toggle (system + localStorage), and data-derived build pipeline**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-23T15:15:16Z
- **Completed:** 2026-04-23T15:22:02Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Index page now has fully functional List.js integration with client-side sort (by date, brand name, generic name, category) and search (by drug name)
- Dark mode toggle respects system preference, allows manual override, persists via localStorage
- Build pipeline derives "Last updated" from data metadata (query.date_to) instead of current timestamp
- Mobile card layout works at ≤768px with data-label pseudo-elements

## Task Commits

Each task was committed atomically:

1. **Task 1: Update index.html with List.js integration and mobile card markup** - `9285993` (feat)
2. **Task 2: Create main.js and update build.py** - `88f41be` (feat, main repo) + `751642a` (feat, site sub-repo)

## Files Created/Modified
- `site/js/main.js` - Dark mode toggle (system detect, localStorage, click handler) + List.js initialization with custom date sort
- `templates/index.html` - List.js-compatible markup: search input, sortable headers, value classes, data-timestamp, data-label attributes
- `build.py` - Data-derived last_updated from query.date_to, REQUIRED_ASSETS pre-check, enhanced success message

## Decisions Made
- Date sorting uses `data-timestamp` attribute with ISO date values and custom List.js sortFunction — prevents alphabetical date sort bug (per PITFALLS.md)
- `last_updated` derived from `data["query"]["date_to"]` (e.g., "April 22, 2026") per AUTO-05, falling back to file mtime if unavailable
- Assets already live in `site/` output directory, so no copy step needed during build — just a pre-existence check

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Index page fully functional with sort, search, and dark mode
- Phase 3 can proceed to drug detail pages using the established template inheritance pattern
- `templates/base.html` provides `{% block content %}` for detail page template
- Data pipeline provides full `label` objects for detail content rendering

## Self-Check: PASSED

- `site/js/main.js` — FOUND
- `templates/index.html` — FOUND
- `build.py` — FOUND
- `02-02-SUMMARY.md` — FOUND
- Commit `9285993` — FOUND
- Commit `88f41be` — FOUND

---
*Phase: 02-site-shell*
*Completed: 2026-04-23*