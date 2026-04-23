# Plan 02 Summary: build.py + Templates

## What was done

Created `build.py` and Jinja2 templates that read `data/approvals.json` and generate a static HTML page with a drug approvals table.

## Key implementation details

1. **`build.py`** (~80 lines) — Reads `data/approvals.json`, validates required fields (`brand_name`, `generic_name`, `approval_date`, `application_number`, `type_badge`, `slug`), renders `templates/index.html` via Jinja2, writes to `site/index.html`. Exits with non-zero status on missing or malformed JSON. Uses `select_autoescape(['html', 'xml'])`.

2. **`format_date` filter** — Converts `"YYYY-MM-DD"` to `"Mon DD, YYYY"` format (e.g., `"2026-04-17"` → `"Apr 17, 2026"`).

3. **`templates/base.html`** — Semantic HTML5 with header (title + "Last updated" timestamp), `<main>` content block, and footer (openFDA attribution). CSS variables for Orchid & Teal color system with dark mode support via `data-theme`. Badge classes: `.badge-new-drug` (teal), `.badge-new-indication` (orchid/purple).

4. **`templates/index.html`** — Extends `base.html`. Table with columns: Date, Type, Brand Name, Generic Name, Category, Indication. Brand name links to `drugs/{{ drug.slug }}.html` (detail pages are Phase 3). Date cells have `data-sort` attribute for future List.js integration. Empty state: "No drug approvals found for this period." message when drugs list is empty.

5. **Category display** — Extracts first `pharm_class_epc` entry, strips the ` [EPC]` suffix. Falls back to `&mdash;` if no EPC class.

## Verification results

- `site/index.html` generated successfully with 210 drug rows
- Contains table with type badges, dates, drug names, categories, indication previews
- "Last updated" timestamp present in header
- openFDA attribution in footer
- Empty-data state renders "No drug approvals found" message
- Build.py exits non-zero on missing or malformed JSON

## End-to-end pipeline verified

- `fda_approvals.py --from 2026-01-01 --to 2026-04-22 -o data/approvals.json` → produces valid JSON with 210 entries
- `python3 build.py` → generates `site/index.html`
- All 5 Phase 1 success criteria from ROADMAP.md verified