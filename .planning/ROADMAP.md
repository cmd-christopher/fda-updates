# Roadmap: FDA Drug Approval Updates

## Overview

This project delivers a static website that keeps physicians informed about new FDA drug approvals and new indication approvals. The journey starts by extending the data pipeline to capture both NME and SUPPL approvals (the core differentiator), then builds the index page with sortable table and site shell, adds drug detail pages with full prescribing information, and finally automates the weekly refresh and deployment cycle. Each phase delivers a coherent, verifiable capability that builds on the previous one.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Pipeline** - Extend fda_approvals.py to fetch both NME and SUPPL approvals and produce a stable JSON data contract
- [x] **Phase 2: Site Shell & Index Page** - Build the shared layout and sortable approval table that physicians land on
- [x] **Phase 3: Drug Detail Pages** - Add full prescribing information pages for each drug with prominent boxed warnings and collapsible sections
- [ ] **Phase 4: Automation & Deployment** - Set up weekly systemd timer and automated git push deployment to Synology NAS

## Phase Details

### Phase 1: Data Pipeline
**Goal**: The complete drug approval dataset (both new drugs and new indications) is correctly fetched, enriched, and structured for site rendering
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08, DATA-09, AUTO-03
**Success Criteria** (what must be TRUE):
  1. Running fda_approvals.py produces a valid `data/approvals.json` containing both NME approvals and efficacy SUPPL approvals
  2. Each approval record carries a correct type badge ("New Drug" or "New Indication") based on its submission type
  3. Approval dates reflect the actual ORIG/SUPPL approval date, not the most recent submission date (sort pitfall avoided)
  4. Missing label data (404s) produces null label fields without crashing the script
  5. Running build.py generates skeleton HTML from the JSON data file
**Plans**: 2 plans in 2 waves
- [x] 01-01-PLAN.md — SUPPL data extension: fetch ORIG + efficacy SUPPL approvals, add type badges, indication preview, slug
- [x] 01-02-PLAN.md — Build skeleton + pipeline validation: create build.py, Jinja2 templates, end-to-end verification

### Phase 2: Site Shell & Index Page
**Goal**: Physicians can browse a sortable, mobile-friendly table of recent drug approvals with clear type badges
**Depends on**: Phase 1
**Requirements**: INDEX-01, INDEX-02, INDEX-03, INDEX-04, INDEX-05, INDEX-06, SITE-01, SITE-02, SITE-03, SITE-04, SITE-05, AUTO-05
**Success Criteria** (what must be TRUE):
  1. Physician sees a sortable table of drug approvals spanning ~2 years on the main page
  2. Table columns show approval date, brand name, generic name, pharmacologic category, and intelligently truncated indication preview
  3. Each row has a visible type badge distinguishing "New Drug" from "New Indication"
  4. Site displays in Orchid & Teal palette with dark mode support and mobile-responsive layout
  5. "Last updated" freshness indicator and cross-link to medupdates.wilmsfamily.com are visible on every page
**Plans**: 2 plans in 2 waves
- [x] 02-01-PLAN.md — Site shell: custom.css (Orchid & Teal table/card/dark mode), List.js asset, base.html (toggle + cross-link)
- [x] 02-02-PLAN.md — Index page: List.js sort/search, mobile card markup, main.js (dark mode + List.js init), build.py updates
**UI hint**: yes

### Phase 3: Drug Detail Pages
**Goal**: Physicians can view complete, well-structured prescribing information for any drug from the index page
**Depends on**: Phase 2
**Requirements**: DETAIL-01, DETAIL-02, DETAIL-03, DETAIL-04, DETAIL-05, DETAIL-06
**Success Criteria** (what must be TRUE):
  1. Clicking a drug row on the index page navigates to a dedicated detail page showing full prescribing information
  2. Detail page displays all available structured PI sections (indications, boxed warning, dosing, contraindications, warnings, adverse reactions, drug interactions, specific populations, mechanism of action, dosage forms & strengths)
  3. Boxed warning appears prominently at the top in a distinct callout style (never hidden in a collapsed section by default)
  4. Long PI sections are collapsible/expandable for scanability
  5. Navigation back to the index page is always available, and key metadata (approval date, type badge, manufacturer, route, dosage form) is visible on the detail page
**Plans**: 2 plans in 2 waves
- [x] 03-01-PLAN.md — Build pipeline: HTML sanitizer, slug collision check, detail page generation
- [x] 03-02-PLAN.md — Detail template: full PI sections, boxed warning callout, collapsible sections, metadata bar, CSS

**UI hint**: yes

### Phase 4: Automation & Deployment
**Goal**: The site updates itself weekly without manual intervention, with visible failure handling
**Depends on**: Phase 3
**Requirements**: AUTO-01, AUTO-02, AUTO-04
**Success Criteria** (what must be TRUE):
  1. A systemd timer runs the data fetch + build pipeline automatically on a weekly schedule
  2. After a successful build, changes are automatically committed and pushed to the Synology NAS, deploying the updated site
  3. Pipeline failures produce visible errors (non-zero exit code, no silent stale data)
**Plans**: 2 plans in 2 waves
- [ ] 04-01-PLAN.md — Incremental label fetching: add --cache flag and set_id to fda_approvals.py, create label cache
- [ ] 04-02-PLAN.md — Pipeline automation: run_fda_pipeline.sh wrapper, systemd service + timer, Pushover failure notification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Pipeline | 2/2 | Complete | 2026-04-23 |
| 2. Site Shell & Index Page | 2/2 | Complete | 2026-04-23 |
| 3. Drug Detail Pages | 2/2 | Complete | 2026-04-23 |
| 4. Automation & Deployment | 0/2 | Planned | - |