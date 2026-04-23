# Requirements: FDA Drug Approval Updates

**Defined:** 2026-04-22
**Core Value:** Physicians can quickly see what new drugs and new indications have been approved and access the complete prescribing information they need to make prescribing decisions.

## v1 Requirements

### Data Pipeline

- [ ] **DATA-01**: Script fetches NME (Type 1 New Molecular Entity) original approvals from openFDA drugsfda endpoint
- [ ] **DATA-02**: Script fetches SUPPL (supplemental) approvals representing new indications (efficacy-class supplements) from openFDA drugsfda endpoint
- [ ] **DATA-03**: Script enriches each drug with full prescribing information from the openFDA label endpoint
- [ ] **DATA-04**: Script filters for prescription-only drugs, excluding OTC and discontinued
- [ ] **DATA-05**: Script post-filters by actual ORIG/SUPPL approval date to avoid the sort pitfall (drugs with recent supplements appearing at top)
- [ ] **DATA-06**: Each approval record has a type badge: "New Drug" for NME originals, "New Indication" for efficacy supplements
- [ ] **DATA-07**: Script outputs a JSON data file (data/approvals.json) that serves as the build contract
- [ ] **DATA-08**: Script handles missing label data gracefully (404s return null label, not a crash)
- [ ] **DATA-09**: Script respects openFDA rate limits with appropriate delays between requests

### Index Page

- [ ] **INDEX-01**: Main page displays a sortable table of drug approvals spanning ~2 years
- [ ] **INDEX-02**: Table columns include: approval date, brand name, generic name, pharmacologic category, and indication preview (~100 chars)
- [ ] **INDEX-03**: Each row shows a type badge distinguishing "New Drug" vs "New Indication"
- [ ] **INDEX-04**: Table is sortable by date (default), brand name, and pharmacologic category
- [ ] **INDEX-05**: Indication preview text is truncated intelligently (first sentence, not arbitrary character cutoff)
- [ ] **INDEX-06**: Clicking a drug row navigates to that drug's detail page

### Detail Pages

- [ ] **DETAIL-01**: Each drug has a dedicated detail page showing full prescribing information
- [ ] **DETAIL-02**: Detail page includes sections: Indications & Usage, Boxed Warning, Dosage & Administration, Dosage Forms & Strengths, Contraindications, Warnings & Precautions, Adverse Reactions, Drug Interactions, Use in Specific Populations, Mechanism of Action, and any other available label sections
- [ ] **DETAIL-03**: Boxed warning is visually prominent with a distinct callout style
- [ ] **DETAIL-04**: Long sections are presented in collapsible/expandable format for scanability
- [ ] **DETAIL-05**: Navigation back to the main index page is always available
- [ ] **DETAIL-06**: Detail page shows approval date, type badge (New Drug / New Indication), and key metadata (manufacturer, route, dosage form)

### Site Shell

- [ ] **SITE-01**: Site uses Orchid & Teal color palette matching medupdates.wilmsfamily.com
- [ ] **SITE-02**: Dark mode support via CSS variables and `prefers-color-scheme`
- [ ] **SITE-03**: Mobile-responsive layout that works on phones, tablets, and desktops
- [ ] **SITE-04**: "Last updated" freshness indicator visible on every page
- [ ] **SITE-05**: Cross-link to medupdates.wilmsfamily.com in the site header or footer

### Automation

- [ ] **AUTO-01**: systemd user service runs the data fetch script on a weekly schedule
- [ ] **AUTO-02**: systemd timer triggers the service weekly
- [ ] **AUTO-03**: Build script (build.py) generates static HTML from the JSON data file
- [ ] **AUTO-04**: Automated git push to Synology after successful build
- [ ] **AUTO-05**: Site shows "last updated" date derived from the data file timestamp

## v2 Requirements

### Search & Filter

- **SRCH-01**: Main page has a search/filter bar for drug name or category
- **SRCH-02**: Category filter dropdown (e.g., Oncology, Cardiology, Endocrinology)
- **SRCH-03**: Date range filter on the main page

### Enhanced Detail Pages

- **ENHD-01**: Table of contents / anchor navigation within the detail page
- **ENHD-02**: Direct link to the official FDA label PDF for each drug

## Out of Scope

| Feature | Reason |
|---------|--------|
| Adverse event integration | FAERS data is complex, doesn't prove causation, and introduces liability concerns |
| Drug interaction checker | Requires proprietary data beyond what openFDA provides |
| Comparison mode | Useful but adds significant complexity to static site architecture |
| User accounts/authentication | Public read-only site; no need for personalization |
| Mobile app | Responsive web is sufficient |
| Email/subscription alerts | Could be added later but not core to physician quick-scan workflow |
| AI summaries of labels | Liability risk; physicians should read the full PI |
| OTC drug approvals | Project scope is prescription drugs only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| DATA-06 | Phase 1 | Pending |
| DATA-07 | Phase 1 | Pending |
| DATA-08 | Phase 1 | Pending |
| DATA-09 | Phase 1 | Pending |
| AUTO-03 | Phase 1 | Pending |
| INDEX-01 | Phase 2 | Pending |
| INDEX-02 | Phase 2 | Pending |
| INDEX-03 | Phase 2 | Pending |
| INDEX-04 | Phase 2 | Pending |
| INDEX-05 | Phase 2 | Pending |
| INDEX-06 | Phase 2 | Pending |
| SITE-01 | Phase 2 | Pending |
| SITE-02 | Phase 2 | Pending |
| SITE-03 | Phase 2 | Pending |
| SITE-04 | Phase 2 | Pending |
| SITE-05 | Phase 2 | Pending |
| AUTO-05 | Phase 2 | Pending |
| DETAIL-01 | Phase 3 | Complete |
| DETAIL-02 | Phase 3 | Complete |
| DETAIL-03 | Phase 3 | Pending |
| DETAIL-04 | Phase 3 | Pending |
| DETAIL-05 | Phase 3 | Pending |
| DETAIL-06 | Phase 3 | Pending |
| AUTO-01 | Phase 4 | Pending |
| AUTO-02 | Phase 4 | Pending |
| AUTO-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 after initial definition*