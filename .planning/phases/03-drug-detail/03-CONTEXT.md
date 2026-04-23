# Phase 3: Drug Detail Pages - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Source:** Derived from ROADMAP.md requirements, REQUIREMENTS.md, and project-level research

<domain>
## Phase Boundary

This phase adds full prescribing information detail pages for each drug. Physicians click a drug row on the index page and navigate to a dedicated page showing structured PI sections, a prominent boxed warning callout, and collapsible long sections. The detail page extends the `base.html` layout established in Phase 2.

**In scope:**
- Drug detail template (`drug_detail.html`) with all available label sections
- HTML content sanitization for label data in `build.py`
- Boxed warning prominent callout styling
- Collapsible/expandable long PI sections
- Navigation breadcrumb/detail page metadata (approval date, type badge, manufacturer, route, dosage form)
- Build pipeline updates to generate per-drug detail pages (`site/drugs/{slug}.html`)
- Graceful handling of drugs with null labels or missing sections

**Out of scope:**
- Table of contents/anchor navigation within detail pages (v2: ENHD-01)
- Direct link to FDA label PDF (v2: ENHD-02)
- Category filter on index page (v2: SRCH-02)
- Date range filter (v2: SRCH-03)
- Search/filter bar on index page (v2: SRCH-01)
</domain>

<decisions>
## Implementation Decisions

### Template & Rendering
- D-01: Detail page extends `base.html` using Jinja2 template inheritance (consistent with Phase 2 pattern)
- D-02: All label section values are lists (1-item arrays) in the JSON data — template must access `section[0]` to get the string content
- D-03: The API field is `warnings_and_cautions` (NOT `warnings_and_precautions`) — template must use the actual key name from the data
- D-04: Label content is plain text (no HTML tags found in current dataset), but sanitization must still be applied as a safety measure per PITFALLS.md Pitfall 4
- D-05: Use `<details>` HTML elements for collapsible sections — no JS framework needed, native browser behavior, accessible by default
- D-06: Boxed warning uses `<details open>` — always visible by default, never hidden in a collapsed section per DETAIL-03

### Section Organization
- D-07: Key sections (indications, dosing, boxed warning) default to expanded (`<details open>`). Long sections (adverse reactions, clinical studies, clinical pharmacology, etc.) default to collapsed (`<details>`)
- D-08: Display ALL available label sections from the data, not a hardcoded subset — the data varies per drug and some have sections others don't
- D-09: The primary PI section order on the detail page follows FDA label numbering: Indications (1), Dosage & Admin (2), Dosage Forms (3), Contraindications (4), Warnings (5), Adverse Reactions (6), Drug Interactions (7), Specific Populations (8), Overdosage (10), Description (11), MOA (12.1), Clinical Pharmacology (12), Clinical Studies (14), Nonclinical Toxicology (13)
- D-10: Drugs with null labels get a "Prescribing information not yet available" message with a link to Drugs@FDA, per PITFALLS.md Pitfall 2

### Sanitization
- D-11: HTML sanitization uses a Python whitelist approach in `build.py` — strip `<script>`, `<style>`, `<iframe>`, event attributes (`onclick`, `onerror`), and `style` attributes; preserve structural tags (`<table>`, `<tr>`, `<td>`, `<th>`, `<p>`, `<br>`, `<ul>`, `<ol>`, `<li>`, `<b>`, `<i>`, `<strong>`, `<em>`, `<h1>`-`<h6>`, `<sub>`, `<sup>`)
- D-12: Sanitized content rendered with `| safe` in Jinja2 after passing through the sanitizer function — autoescaping is still globally enabled for all other content

### Navigation & Metadata
- D-13: Detail page shows a "← Back to Drug Approvals" link at the top linking to `../index.html` (detail pages are in `site/drugs/` subdirectory)
- D-14: Key metadata shown in a summary bar at the top of the detail page: approval date, type badge, manufacturer name, route, dosage form (from products[0].dosage_form)
- D-15: Brand page title format: `{brand_name} — FDA Prescribing Information`

### Build Pipeline
- D-16: `build.py` generates `site/drugs/{slug}.html` for each drug in the JSON data
- D-17: Slug uniqueness check: if two drugs share a slug, append `-{application_number_suffix}` (digits only from application_number)

### the agent's Discretion
- Exact CSS styling for boxed warning callout (color, border, padding) — as long as it's visually prominent and distinct
- Whether to show section numbers (1, 2, 3...) alongside section headings
- Whether to add a "Last updated" section or freshness indicator on detail pages
- Minor UX polish (font sizes, spacing, responsive breakpoints)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Guidelines
- `AGENTS.md` — Project overview, API gotchas, two-repo structure, script design notes
- `.planning/research/PITFALLS.md` — Critical pitfalls including label HTML sanitization (Pitfall 4), label 404s (Pitfall 2), boxed warning visibility (UX Pitfall)

### Established Patterns (from completed phases)
- `templates/base.html` — Shared layout with header, footer, dark mode toggle, CSS variables, badge styles
- `templates/index.html` — Template inheritance pattern, drug data rendering, badge usage
- `build.py` — Current build pipeline for index.html, Jinja2 Environment setup, format_date filter, REQUIRED_ASSETS pattern
- `site/css/custom.css` — CSS variable system, Orchid & Teal palette, dark mode variables, responsive card layout
- `site/js/main.js` — Dark mode toggle IIFE pattern, List.js initialization

### Data Contract
- `data/approvals.json` — JSON schema with drug objects containing `label` dict; label values are 1-item lists of strings; key name is `warnings_and_cautions` (NOT `warnings_and_precautions`)

</canonical_refs>

<specifics>
## Specific Ideas

- Boxed warning callout should use a red/amber accent color distinct from the Orchid & Teal palette — this is a safety-critical element that must stand out
- Section headings should use the FDA-standard numbering where available (e.g., "1. Indications & Usage", "6. Adverse Reactions")
- The detail page URL structure is `drugs/{slug}.html` relative to the site root — index page links already point here
- The `products[0].dosage_form` field provides the dosage form for the metadata bar (e.g., "INJECTABLE", "TABLET")
- The `products[0].route` field provides the route (e.g., "INJECTION", "ORAL")
- The top-level `route` field is a list (e.g., `["SUBCUTANEOUS"]`) — use first entry for display
- The `manufacturer_name` field is a list — join with ", " for display
</specifics>

<deferred>
## Deferred Ideas

- Table of contents / anchor navigation within detail page (ENHD-01 — v2)
- Direct link to the official FDA label PDF (ENHD-02 — v2)
- Print-friendly detail page CSS (`@media print`)
- Permalinks for individual PI sections (`#boxed-warning`, `#dosing`)
- "Related drugs by class" links on detail pages
</deferred>

---

*Phase: 03-drug-detail*
*Context gathered: 2026-04-23*