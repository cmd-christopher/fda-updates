# FDA Drug Approval Updates

## What This Is

A static website that keeps physicians informed about new FDA prescription drug approvals and new indication approvals for existing drugs. The site presents data from the openFDA API in a physician-friendly format — a sortable main table of recent approvals with full prescribing information detail pages for each drug.

## Core Value

Physicians can quickly see what new drugs and new indications have been approved and access the complete prescribing information they need to make prescribing decisions.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Main page displays a sortable table of drug approvals from the last ~2 years
- [ ] Table shows approval date, brand name, generic name, pharmacologic category, and primary indication
- [ ] Mixed list of NMEs (new drugs) and new indication approvals for existing drugs, with a type flag distinguishing them ("New Drug" vs "New Indication")
- [ ] Clicking a drug row navigates to a detail page with full structured prescribing information
- [ ] Detail page includes: indications & usage, boxed warning, dosing & administration, dosage forms & strengths, contraindications, warnings & precautions, adverse reactions, drug interactions, use in specific populations, mechanism of action, and other available label sections
- [ ] Site aesthetics match medupdates.wilmsfamily.com (Orchid & Teal palette, dark mode support, similar card/typography style)
- [ ] Static site deployed to Synology NAS, served at medupdates.wilmsfamily.com/fda/
- [ ] Data fetched weekly via systemd timer + service from openFDA API
- [ ] Data source includes both NME (Type 1) original approvals and SUPPL (supplement) approvals that represent new indications

### Out of Scope

- OTC drug approvals — this is for prescription drugs only
- Adverse event reporting integration — out of scope for v1
- Drug shortage tracking — out of scope for v1
- User accounts or authentication — this is a public read-only site
- Search engine optimization beyond basic meta tags — not needed for a LAN-served site
- Email/subscription alerts — could be added later but not v1
- Mobile app — responsive web is sufficient

## Context

- Existing `fda_approvals.py` script fetches drug approvals from the openFDA drugsfda endpoint and enriches each with full prescribing information from the label endpoint
- The script currently handles NME (Type 1 New Molecular Entity) approvals; it needs to be extended to also capture new indication approvals (SUPPL submissions with efficacy class)
- The openFDA API has a critical sort pitfall: sorting by `submissions.submission_status_date:desc` returns drugs by their most recent any submission, not original approval date. The script already post-filters on the ORIG submission date.
- The label endpoint does not support date-based searching — always start with drugsfda, then enrich with label data
- A sibling project at `/home/christopher/Repos/medical-updates-codex-standalone` runs on the same Synology NAS and serves from medupdates.wilmsfamily.com — the FDA site should match its visual style
- The `site/` folder is a separate git repo (remote: `synology-fda`) that auto-deploys via post-receive hook to `/volume1/web/medupdates/fda/`

## Constraints

- **Tech stack**: Static HTML/CSS/JS — no server-side rendering, no build framework required
- **Data source**: openFDA API (free, public, rate-limited at ~240 requests/min without API key)
- **Deployment**: Git push to Synology NAS (post-receive hook auto-deploys to web root)
- **Hosting**: Synology NAS via nginx at medupdates.wilmsfamily.com/fda/
- **Scheduling**: systemd user timer + service (not cron), running weekly
- **Aesthetics**: Must match the Orchid & Teal palette and dark-mode styling of the medupdates site

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| NMEs + new indications mixed with type flag | Physicians care about both new drugs and new indications for drugs they already prescribe — a single list with clear type differentiation is most useful | — Pending |
| Sortable table for main page | Table format lets physicians sort by date, drug name, or category — most scannable for quick reference | — Pending |
| Full structured PI on detail pages | Physicians need complete prescribing information for clinical decisions; curated summaries risk omitting critical safety data | — Pending |
| systemd timer weekly, not cron | User preference for systemd; weekly cadence matches FDA data update frequency and minimizes API calls | — Pending |
| ~2 year date window default | Physician asked for 2 years of data visibility on main page | — Pending |

---
*Last updated: 2026-04-22 after initialization*