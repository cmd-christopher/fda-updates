---
phase: 02-site-shell
plan: 01
subsystem: frontend
tags: [css, dark-mode, assets, base-template]
dependency_graph:
  requires: []
  provides: [site/css/custom.css, site/js/list.min.js, templates/base.html]
  affects: [templates/index.html, build.py]
tech_stack:
  added: [List.js v2.3.1 (local)]
  patterns: [CSS custom properties theming, data-theme toggle, responsive cards at ≤768px]
key_files:
  created: [site/css/custom.css, site/js/list.min.js]
  modified: [templates/base.html]
decisions:
  - CSS custom properties and badge styles kept inline in base.html as base palette; supplementary vars and layout moved to custom.css
  - List.js v2.3.1 downloaded locally to avoid CDN dependency per D-07
  - Dark mode toggle button uses moon/sun emoji spans; JS logic deferred to main.js (Plan 02-02)
metrics:
  duration: 5 min
  completed: 2026-04-23
---

# Phase 2 Plan 01: Site Shell — Styling & Assets Summary

Orchid & Teal custom CSS with dark mode, mobile card layout, local List.js asset, and enhanced base.html with toggle button and cross-link.

## Completed Tasks

### Task 1: Create custom.css and download List.js

**Commit:** site-repo@4e6bd82

- Created `site/css/custom.css` (215 lines) with all specified sections:
  - Supplementary CSS variables (`--teal-light`, `--orchid-light`, `--row-height`, `--card-radius`, `--card-gap`) with dark mode variants
  - Main content container styling
  - Search input styling with focus ring
  - Table styling: ~44px row height, zebra striping, hover states, sortable column indicators
  - Mobile card layout at ≤768px: table → stacked cards with `data-label` pseudo-elements
  - Dark mode toggle button styling
  - Footer cross-link styling (orchid-colored link)
  - Header enhancement with flex `.header-row` layout
  - Empty state styling
- Downloaded List.js v2.3.1 to `site/js/list.min.js` (19,487 bytes)

### Task 2: Update base.html with dark mode toggle, asset links, and cross-link

**Commit:** 82bc08a

- Added `<link rel="stylesheet" href="css/custom.css">` for local custom CSS
- Added `<script src="js/list.min.js">` and `<script src="js/main.js">` for local JS assets
- Added dark mode toggle button in header (`<button class="theme-toggle">` with moon/sun spans)
- Added cross-link to medupdates.wilmsfamily.com in footer (`<p class="cross-link">`)
- Added `{% block main_attrs %}` for List.js scoping on `<main>` element
- Wrapped header in `.header-row` flex container
- Moved layout styles (header, main, footer, empty-state) to custom.css
- Preserved all CSS custom properties and badge styles inline as base palette

## Additional Commits

- **bb8d5dc:** `feat(01): add build.py and index.html template` — committed previously untracked Phase 1 files needed for project to function

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

All 8 verification criteria passed:
1. custom.css exists with 215 lines (≥80 required) ✓
2. list.min.js exists, 19,487 bytes (≥10KB required) ✓
3. base.html references custom.css, list.min.js, main.js ✓
4. base.html has dark mode toggle button ✓
5. base.html has cross-link to medupdates.wilmsfamily.com ✓
6. CSS custom properties for --teal, --orchid etc. preserved ✓
7. Badge styles for .badge-new-drug and .badge-new-indication retained ✓
8. `python3 build.py` generates site/index.html with 210 drug approvals ✓

## Known Stubs

- `js/main.js` referenced in base.html but not yet created — will be created in Plan 02-02 with dark mode toggle logic and List.js initialization
- Dark mode toggle button renders but has no click handler yet — JS logic deferred to main.js in Plan 02-02

## Threat Flags

None — all assets are local (no CDN dependency per threat T-02-02 mitigation).