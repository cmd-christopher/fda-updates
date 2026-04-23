# Phase 2: Site Shell & Index Page - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the shared site layout (Orchid & Teal palette, dark mode, responsive shell) and the sortable approval table with type badges, search, and mobile-friendly card layout. This phase produces a fully functional index page that physicians can browse, sort, and search on any device.

This phase does NOT include drug detail pages (Phase 3) or automation (Phase 4).
</domain>

<decisions>
## Implementation Decisions

### Table Layout & Mobile
- **D-01:** Desktop table uses comfortable row height (~44px, ~20 visible rows) with all 6 columns (Date, Type, Brand Name, Generic Name, Category, Indication).
- **D-02:** Mobile (≤768px) converts the table into a stacked card layout — each drug becomes a card with the key fields arranged vertically. This provides the best mobile experience at the cost of more CSS work.
- **D-03:** Type badges ("New Drug" teal, "New Indication" orchid/purple) are visually prominent and always visible in both table and card views.

### Dark Mode
- **D-04:** Dark mode uses CSS custom properties (already started in `base.html`) with `data-theme="light"` / `data-theme="dark"` on the `<html>` element.
- **D-05:** System preference (`prefers-color-scheme`) is respected by default. A manual toggle (moon/sun icon) overrides the system preference and persists in `localStorage`. This matches the medupdates site pattern.
- **D-06:** Pico CSS is NOT used as a framework. The existing base.html already has custom CSS vars and styles. The site uses its own minimal CSS — custom properties for theming, no external CSS framework dependency.

### CSS & Styling
- **D-07:** No CDN dependencies for CSS or JS. All assets (List.js, custom CSS) are downloaded to `site/css/` and `site/js/` so the site works fully offline on the Synology LAN.
- **D-08:** The Orchid & Teal color palette already exists in `base.html` as CSS custom properties. Phase 2 extends this with table/card styling, not a replacement.
- **D-09:** Cross-link to medupdates.wilmsfamily.com appears in the site footer (already partially in base.html). Header shows "Last updated" timestamp.

### List.js Integration
- **D-10:** List.js provides client-side sorting and search on the table. Date sorting uses `data-sort` attributes with ISO date values (already in the Phase 1 template).
- **D-11:** Search input filters by brand name and generic name. No category filter dropdown in Phase 2 (that's v2 scope per REQUIREMENTS.md SRCH-02).

### build.py
- **D-12:** build.py already exists from Phase 1 with basic template rendering. Phase 2 extends it to download Pico CSS (if we switch) or add custom styles, and to copy List.js into `site/js/`.
- **D-13:** The existing `templates/base.html` and `templates/index.html` are extended, not replaced. The current table structure with `data-sort` attributes is the foundation.

### Claude's Discretion
- Exact breakpoint for mobile card layout (768px vs custom)
- Whether to use Pico CSS as a base or go fully custom (currently going custom since base.html already has the vars)
- List.js pagination vs infinite scroll vs no pagination for initial <200 rows
- Whether the card layout uses a full card with shadow/border or a simple stacked list

### Folded Todos
None.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### API & Data
- `.skills/openfda-drug/SKILL.md` — openFDA API endpoints, fields, query syntax
- `fda_approvals.py` — Current working script with SUPPL support, type_badge, slug, indication_preview
- `data/approvals.json` — Current data contract (210 drugs with labels for 2026-01-01 to 2026-04-22)

### Architecture
- `.planning/research/ARCHITECTURE.md` — Two-script pipeline pattern, JSON contract, component responsibilities, build order
- `.planning/research/STACK.md` — Tech stack decisions (Python + Jinja2, no Node.js)
- `.planning/research/PITFALLS.md` — Critical pitfalls: sort pitfall (solved), label HTML sanitization (Phase 3), mobile table (addressed here)

### Phase 1 Context
- `.planning/phases/01-data-pipeline/01-CONTEXT.md` — Data pipeline decisions (type badges, SUPPL logic, indication preview, slug format)

### Existing Code
- `templates/base.html` — Current base template with CSS vars for Orchid & Teal, dark mode, badge classes
- `templates/index.html` — Current table template with data-sort attributes
- `build.py` — Current build script with Jinja2 rendering
- `site/index.html` — Current generated output (210 drug rows)

### Sibling Project
- `/home/christopher/Repos/medical-updates-codex-standalone/` — Reference for Orchid & Teal palette, dark mode toggle, card styling patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `templates/base.html`: Already has CSS custom properties for --teal, --orchid, --bg, --text, --muted, --border, --surface. Has header, main, footer. Dark mode vars via `[data-theme="dark"]`. Badge classes `.badge-new-drug` and `.badge-new-indication` already styled.
- `templates/index.html`: Extends base.html. Has table with data-sort attributes on date cells. Links to `drugs/{{ drug.slug }}.html`. `format_date` filter for human-readable dates. `&mdash;` fallback for empty fields.
- `build.py`: Reads `data/approvals.json`, validates required fields, renders templates, writes `site/index.html`. ~80 lines. Uses Jinja2 with `select_autoescape` and `format_date` custom filter.

### Established Patterns
- Jinja2 template inheritance: base.html → index.html (will also extend to drug_detail.html in Phase 3)
- CSS custom properties for theming (not a CSS framework)
- Data contract: JSON → Jinja2 template variables (drugs list, last_updated)

### Integration Points
- `build.py` writes to `site/index.html` (currently the only output; Phase 2 may add `site/css/custom.css` and `site/js/list.min.js`)
- `site/` is a separate git repo; `build.py` must not overwrite `.git/` or other files in `site/`
- Current `site/index.html` is the Phase 1 output that will be replaced by the Phase 2 enhanced version

</code_context>

<specifics>
## Specific Ideas

- The current `site/index.html` already works and shows 210 drug rows. Phase 2 enhances it with proper CSS, dark mode toggle, List.js sorting/search, and mobile card layout.
- The medupdates site uses a specific Orchid & Teal palette that should be matched — reference the sibling project for exact color values and card styling patterns.
- Type badges ("New Drug" in teal, "New Indication" in orchid) are the core differentiator and must be visually prominent. The current `.badge-new-drug` and `.badge-new-indication` classes in base.html are a good starting point but need Phase 2 polish.

</specifics>

<deferred>
## Deferred Ideas

- Drug detail pages (Phase 3) — full prescribing information with collapsible sections and boxed warning callout
- Search/filter bar with category dropdown (v2 scope per REQUIREMENTS.md SRCH-01/02)
- Pagination for 200+ drugs (architectural note in ARCHITECTURE.md, but not needed for ~200 rows)
- Pico CSS as a full framework (going custom only, no external CSS framework)

</deferred>

---

*Phase: 02-site-shell*
*Context gathered: 2026-04-23*