# Project Research Summary

**Project:** FDA Drug Approval Updates
**Domain:** Static medical information site (Python-built, deployed to Synology NAS)
**Researched:** 2026-04-22
**Confidence:** HIGH

## Executive Summary

This project is a static site that presents FDA prescription drug approval data to physicians — a curated, scannable, mobile-friendly alternative to Drugs@FDA. The domain is well-established: static site generators for structured data, semantic CSS frameworks for content-heavy sites, and client-side table enhancement libraries. Experts build these as static HTML generated from a data pipeline, not as dynamic web apps. The recommended approach is a two-script Python pipeline (`fda_approvals.py` fetches data, `build.py` renders templates) producing static HTML served by nginx on a Synology NAS, with a weekly systemd timer for data refresh. No framework, no build step, no Node.js — just Python + Jinja2 + Pico CSS + List.js.

The core differentiator is showing **New Drug vs. New Indication** approvals together with clear visual badges — something no existing site does well. This requires enriching `fda_approvals.py` to fetch SUPPL submissions alongside ORIG approvals, which is the single most important data pipeline change and must be completed before any site rendering work. The key risks are: (1) the openFDA sort pitfall returning wrong approval dates (mitigated by post-filtering in Python), (2) label HTML sanitization to prevent broken layouts, and (3) SUPPL deduplication to avoid duplicate drug entries. Each of these must be tested with real FDA data before considering a phase complete.

## Key Findings

### Recommended Stack

The stack is deliberately minimal: Python (already in use for data fetching) plus Jinja2 for templating, Pico CSS for semantic styling with built-in dark mode, and List.js for client-side table interactivity. No JavaScript frameworks, no CSS preprocessors, no bundlers. This keeps the project in a single runtime (Python), eliminates `node_modules`, and matches the project's scale — two page types (index + detail) serving ~200 drug entries.

**Core technologies:**
- **Python 3 + Jinja2 (3.1.6):** Data pipeline + HTML generation — stays in one language, template inheritance handles shared layout, autoescaping prevents XSS from label data
- **Pico CSS (2.0.x):** Styling framework — classless semantic HTML, built-in dark mode via `data-theme`, `--pico-*` variables map directly to Orchid & Teal palette, zero build step
- **List.js (2.3.1):** Table sorting & search — 13KB, works on existing HTML tables, progressive enhancement pattern, CDN-optional
- **Vanilla JS (ES2020+):** Detail page interactivity — dark mode toggle, collapsible sections, ~50-100 lines total
- **systemd timer:** Weekly data refresh — runs fetch → build → push pipeline, existing pattern from sibling project

### Expected Features

**Must have (table stakes):**
- Sortable approval table with date, brand name, generic name — core value proposition
- Type flag (New Drug vs. New Indication) — the differentiator that sets this apart from Drugs@FDA
- Pharmacologic category in table — physicians organize knowledge by drug class
- Indication preview in table row — saves one click per drug assessment
- Detail page with full structured PI (boxed warning prominent, collapsible sections) — what separates a tracking site from a list
- Mobile-responsive layout — physicians check references on phones
- Dark mode matching medupdates — visual consistency with parent site
- Data freshness indicator — "Last updated: [date]" builds trust
- Link to official FDA source — credibility verification
- SUPPL data enrichment in fda_approvals.py — required for the type flag differentiator

**Should have (competitive):**
- Drug name search in table — List.js built-in, easy addition
- Dosage forms & strengths summary — data already available, template addition
- Mechanism of action highlight — data already available, template addition
- Approval type classification badges — richer type info beyond binary flag
- Category filter dropdown — useful for specialty physicians
- Atom/RSS feed — 20 lines of Jinja2, zero operational cost

**Defer (v2+):**
- Drug comparison view — physicians can open two tabs
- Print-friendly detail page — CSS-only addition
- Related drugs by class — requires pharm_class cross-referencing
- Bookmarkable searches — URL query params for saved filter state

### Architecture Approach

The architecture is a two-script Python pipeline connected by a JSON data contract. `fda_approvals.py` fetches drug data from the openFDA API and writes `data/approvals.json`. `build.py` reads that JSON, computes derived fields (slugs, type badges, indication previews), renders Jinja2 templates, and writes static HTML to `site/`. The `site/` directory is a separate git repo deployed via `git push` to the Synology NAS. A systemd timer runs the full pipeline weekly. The site is static HTML with progressive JS enhancement — tables render without JavaScript, List.js adds sorting/search on top.

**Major components:**
1. **`fda_approvals.py`** (existing, needs SUPPL extension) — Fetches drug approval data from openFDA API, enriches with label data, writes JSON
2. **`data/approvals.json`** — JSON data contract between fetch and build scripts; the schema must be stable and documented
3. **`build.py`** (new) — Reads JSON, renders Jinja2 templates, writes static HTML; computes derived fields (slugs, badges, truncation)
4. **Templates (`base.html`, `index.html`, `drug_detail.html`)** — Shared layout with template inheritance; index has table, detail has full PI
5. **`site/css/custom.css`** + **`site/js/main.js`** — Orchid & Teal palette overrides, dark mode toggle, List.js init, accordion controls

### Critical Pitfalls

1. **openFDA sort returns wrong approval dates** — `sort=submissions.submission_status_date:desc` sorts by most recent *any* submission, not the original approval. KEYTRUDA from 2014 appears "new." Always post-filter on the specific ORIG/SUPPL submission's date in Python.
2. **SUPPL data creates duplicate drug entries** — A drug like DUPIXENT has ORIG + multiple SUPPLs. Must design for *approval events* not *drugs*, and filter for efficacy supplements only.
3. **Label HTML contains malformed markup** — FDA label data has broken tables, stray tags, and inline styles. Must sanitize before rendering: whitelist safe tags, strip `<script>`, `<style>`, `onclick`, and `style` attributes. Never use `| safe` without sanitization.
4. **systemd timer failure goes unnoticed** — If the weekly pipeline fails silently, the site shows stale data with no warning. Add `OnFailure` notification, fail-loud exits, and a staleness banner on the site.
5. **Boxed warning must be prominent** — Hiding the FDA's strongest safety signal in a collapsible section is a medical content error. Display it at the top of the detail page in a visually distinct callout.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Data Pipeline Extension
**Rationale:** The type flag (New Drug vs. New Indication) is the core differentiator. Without SUPPL data enrichment, the site is just a date-filtered Drugs@FDA. This must come first because all rendering depends on the data structure.
**Delivers:** Enhanced `fda_approvals.py` that fetches both ORIG and efficacy SUPPL submissions; stable JSON schema for `approvals.json`; verified data integrity with real FDA data.
**Addresses:** Sortable approval table, type flag, SUPPL data pipeline, approval date column, pharmacologic category, brand/generic names
**Avoids:** Wrong approval dates (sort pitfall), duplicate entries (SUPPL dedup), missing label handling (404s)

### Phase 2: Site Shell & Index Page
**Rationale:** With the data pipeline producing correct JSON, build the shared layout and the primary page physicians land on. This delivers the MVP — a scannable, sortable table of drug approvals.
**Delivers:** `build.py` (minimal), `templates/base.html`, `templates/index.html`, `site/css/custom.css`, `site/js/main.js` with List.js, Pico CSS integration with Orchid & Teal palette, dark mode toggle, mobile-responsive table.
**Addresses:** Sortable table, dark mode, mobile responsiveness, data freshness indicator, FDA source links
**Avoids:** Mobile-unfriendly table (Pico CSS responsive), date sorting errors (ISO dates in data-sort), CDN dependency (download assets locally)

### Phase 3: Drug Detail Pages
**Rationale:** The detail page is what makes this a prescribing reference rather than a simple list. It requires label data handling (sanitization, collapsible sections) and is the most template-intensive page.
**Delivers:** `templates/drug_detail.html`, HTML sanitization in `build.py`, boxed warning callout, collapsible PI sections, dosage forms & strengths summary, mechanism of action highlight, indication preview rendering, graceful handling of missing labels.
**Uses:** Jinja2 autoescaping, Pico CSS callout components, `<details>` elements for collapsible sections
**Avoids:** Label HTML breaking page layout (sanitization), hidden boxed warnings (prominent callout), slug collisions (uniqueness check)

### Phase 4: Automation & Deployment
**Rationale:** The static site is manually buildable after Phase 3. Automation (systemd timer, deployment pipeline) is the final step to make it self-sustaining.
**Delivers:** `systemd/fda-updates.service`, `systemd/fda-updates.timer`, end-to-end pipeline script (fetch → build → commit → push), failure notification, staleness banner on the site.
**Avoids:** Silent timer failures (OnFailure), git push conflicts (pull --rebase), stale data without warning (freshness JS check)

### Phase Ordering Rationale

- **Phase 1 must come first** because all rendering depends on data structure. The JSON schema is the keystone contract between `fda_approvals.py` and `build.py`. The SUPPL extension changes this schema (adds type badges, indication previews). Building templates before the schema is finalized leads to rework.
- **Phase 2 before Phase 3** because the index page is the primary entry point and simpler to build (one table). The detail page inherits `base.html` and reuses the CSS/JS setup from Phase 2. Building detail pages without the shared layout and table page ready means debugging in isolation.
- **Phase 4 last** because there's no point automating a pipeline that hasn't been tested manually. The cron deployment should wrap a proven pipeline, not bootstrap an untested one.
- **Phases 2 and 3 could overlap** — `base.html` and CSS can be built with mock data while Phase 1 is being tested, as noted in ARCHITECTURE.md's build order.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Data Pipeline):** SUPPL filtering logic is complex — `submission_class_code_description` values for efficacy supplements need verification against real FDA data. Run `gsd-research-phase` to explore the openFDA SUPPL response structure before implementing.
- **Phase 3 (Detail Pages):** HTML sanitization strategy needs testing against real label data. The `adverse_reactions` field frequently contains malformed tables. Research how other projects (DailyMed, Drugs.com) handle this.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Index Page):** Pico CSS + List.js + Jinja2 templating is well-documented with high-confidence sources. Standard patterns apply.
- **Phase 4 (Automation):** systemd timer + Synology deployment follows an exact pattern from the sibling `medical-updates-codex` project. No research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies (Jinja2, Pico CSS, List.js) verified with official docs via Context7. Python data pipeline already exists and works. No novel integrations. |
| Features | HIGH | Feature set derived from direct analysis of four competitor sites (Drugs@FDA, Drugs.com, Medscape, DailyMed) and the existing `fda_approvals.py` script. MVP scope is clear. |
| Architecture | HIGH | Two-script pipeline pattern is proven in sibling project. Template inheritance for a 2-page site is straightforward. Data contract is well-specified. |
| Pitfalls | HIGH | Critical pitfalls identified from direct API experience (sort behavior, 404s, SUPPL duplicates) and open-source medical content patterns (label HTML). Verification steps are concrete. |

**Overall confidence:** HIGH — the domain is well-understood, the technologies are proven, the architecture is simple, and the pitfalls are identified with specific mitigation strategies.

### Gaps to Address

- **SUPPL efficacy classification values:** The exact `submission_class_code_description` strings that indicate efficacy supplements (vs. manufacturing or labeling supplements) need verification against real openFDA data. During Phase 1 planning, run actual API queries to enumerate these values.
- **Label HTML sanitization scope:** The variety and severity of malformed HTML in FDA labels needs empirical testing. During Phase 3 planning, fetch 20+ real labels and catalog the types of HTML issues encountered before writing the sanitization function.
- **Orchid & Teal palette specifics:** The exact color values and their dark mode variants should be pulled from the medupdates parent site during Phase 2 to ensure visual consistency.
- **Synology deployment path:** The exact nginx configuration and post-receive hook setup should be verified on the target NAS during Phase 4.

## Sources

### Primary (HIGH confidence)
- Context7 `/pallets/jinja` — Jinja2 templating, FileSystemLoader, autoescaping, template inheritance
- Context7 `/websites/picocss` — Pico CSS 2.0 dark mode variables, `data-theme`, `--pico-*` customization
- openFDA API (api.fda.gov) — Endpoint structure, rate limits, date formats; verified in existing `fda_approvals.py`
- Drugs@FDA, Drugs.com, Medscape, DailyMed — Direct competitor analysis; confirmed feature gaps
- `fda_approvals.py` source code — First-party verification of API usage, 404 handling, pagination
- `medical-updates-codex` sibling project — Confirmed systemd timer, Synology deployment, two-repo pattern

### Secondary (MEDIUM confidence)
- List.js official site (listjs.com) — v2.3.1 features, table integration, CDN availability
- Pico CSS community patterns — Semantic HTML table styling, responsive breakpoints
- Static site generation pitfalls — HTML sanitization, date sorting, mobile table responsiveness

### Tertiary (LOW confidence)
- None — all findings are supported by direct observation or verified documentation

---
*Research completed: 2026-04-22*
*Ready for roadmap: yes*