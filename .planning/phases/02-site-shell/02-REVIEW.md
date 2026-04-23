---
phase: 02-site-shell
reviewed: 2026-04-23T11:30:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - templates/base.html
  - templates/index.html
  - site/css/custom.css
  - site/js/main.js
  - build.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-04-23T11:30:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the static site shell — templates, CSS, JS, and build script. Autoescaping is correctly enabled in Jinja2 (no XSS risk), but two bugs affect functionality: date sorting is broken due to a misplaced `data-timestamp` attribute, and the em-dash fallback renders as literal `&mdash;` text due to double-escaping. There are also dead links to drug detail pages that don't exist yet.

## Warnings

### WR-01: Date sorting is broken — `data-timestamp` on `<td>` instead of `<tr>`

**File:** `templates/index.html:26`
**Issue:** List.js is configured with `valueNames: [{ data: ['timestamp'] }]` which reads `data-timestamp` from the list item element (`<tr>`, since `<tbody class="list">` makes each `<tr>` a list item). However, the template places `data-timestamp` on the inner `<td>` element:
```html
<td class="date" data-label="Date" data-timestamp="{{ drug.approval_date }}">
```
List.js calls `getAttribute(e.elm, "data-timestamp")` where `e.elm` is the `<tr>`, which has no such attribute. The custom sort function falls back to `''` for all items, making every date compare as equal. Clicking the Date column header to re-sort will produce incorrect/same order every time.

**Fix:** Move `data-timestamp` to the `<tr>` element:
```html
<!-- In templates/index.html, line 25 -->
<tr data-timestamp="{{ drug.approval_date }}">
    <td class="date" data-label="Date">{{ drug.approval_date | format_date }}</td>
```

### WR-02: `&mdash;` fallback renders as literal text (double-escaping)

**File:** `templates/index.html:35-37`
**Issue:** Three template expressions use `or "&mdash;"` as a fallback for missing data:
- Line 35: `{{ drug.generic_name or "&mdash;" }}`
- Line 36: `{{ drug.pharm_class_epc[0].split(' [EPC]')[0] if drug.pharm_class_epc else "&mdash;" }}`
- Line 37: `{{ drug.indication_preview or "&mdash;" }}`

Jinja2's `select_autoescape(["html", "xml"])` correctly auto-escapes output. The string `"&mdash;"` gets escaped to `&amp;mdash;`, which the browser renders as the literal text `&mdash;` instead of the em dash character `—`. Confirmed in the built output: 107 instances of `&amp;mdash;` appear in `site/index.html`.

**Fix:** Use the Unicode character directly and let autoescape handle it safely, or use Jinja2's `|safe` filter for trusted HTML entities:
```html
<!-- Option A: Use the Unicode character (recommended — simpler and safe) -->
{{ drug.generic_name or "—" }}
{{ drug.pharm_class_epc[0].split(' [EPC]')[0] if drug.pharm_class_epc else "—" }}
{{ drug.indication_preview or "—" }}

<!-- Option B: Mark trusted entity as safe -->
{{ drug.generic_name or "&mdash;"|safe }}
```
Option A is preferred because it avoids mixing `|safe` with user data in the same expression (even though `|safe` only applies to the `&mdash;` literal here, explicit is better than implicit).

### WR-03: Dead links to non-existent drug detail pages

**File:** `templates/index.html:34`
**Issue:** The template generates links like `<a href="drugs/cosentyx.html">` but `build.py` only builds `site/index.html`. The `site/drugs/` directory does not exist, and no drug detail pages are generated. Every brand name link is a 404.

**Fix:** Either (a) stub the links as non-navigable for now, or (b) build drug detail pages in a future phase:
```html
<!-- Option A: Remove link until detail pages exist -->
<td class="name" data-label="Brand Name">{{ drug.brand_name or drug.generic_name or "Unknown" }}</td>

<!-- Option B: Keep link but add a comment that detail pages are TODO -->
<td class="name" data-label="Brand Name"><a href="drugs/{{ drug.slug }}.html">{{ drug.brand_name or drug.generic_name or "Unknown" }}</a></td>
<!-- TODO: Build drug detail pages (Phase 3) -->
```

## Info

### IN-01: `line-height: var(--row-height)` on `td` uses pixel value for line-height

**File:** `site/css/custom.css:76`
**Issue:** `line-height: var(--row-height)` where `--row-height: 44px`. When text wraps in a cell, each wrapped line will be 44px tall (extremely tall). The intent appears to be setting a minimum row height, but `line-height` doesn't enforce minimum height — `min-height` on `<tr>` or `<td>` would. This isn't causing visible problems currently because drug names and categories are typically short enough not to wrap, but it's misleading CSS.

**Fix:** Use `min-height` for row sizing and a normal `line-height`:
```css
td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--border);
  line-height: 1.5;
  vertical-align: middle;
}
```

### IN-02: `build.py` only regenerates `index.html` — static assets must persist

**File:** `build.py:74-90`
**Issue:** `build.py` verifies that `REQUIRED_ASSETS` (CSS, JS) exist before building, but it never copies or regenerates them. If someone runs `rm -rf site/ && python3 build.py`, only `site/index.html` is created — `site/css/` and `site/js/` are missing and the build succeeds (because the required-assets check runs against the source paths before the `site/` dir is cleaned). This is by design (assets are version-controlled in the `site/` sub-repo), but the `REQUIRED_ASSETS` check is checking paths relative to the project root, not the output directory. If the assets were moved or removed from `site/`, the check would still pass as long as the source files exist at the project root level.

**Fix:** If this becomes a problem, change `REQUIRED_ASSETS` to check paths under `OUTPUT_DIR` instead, or add the asset paths as build outputs to be copied. For now this is informational since the `site/` sub-repo manages these files.

---

_Reviewed: 2026-04-23T11:30:00Z_
_Reviewer: gsd-code-reviewer_
_Depth: standard_