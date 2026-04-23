# Phase 1: Data Pipeline - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Source:** Research + Requirements synthesis

<domain>
## Phase Boundary

Extend `fda_approvals.py` to fetch both NME (ORIG) and efficacy SUPPL approvals from openFDA, enrich each with label data, and produce a stable `data/approvals.json` that serves as the build contract for the static site. Also create a minimal `build.py` that generates skeleton HTML from the JSON to prove the data pipeline works end-to-end.

This phase does NOT build the full site UI — that's Phase 2. It produces correct data and a minimal build proof.
</domain>

<decisions>
## Implementation Decisions

### Data Pipeline Architecture
- **D-01**: Two-script pipeline pattern: `fda_approvals.py` writes JSON, `build.py` reads JSON and renders HTML. Connected by file-on-disk contract (ARCHITECTURE.md Pattern 1)
- **D-02**: Existing `fda_approvals.py` must be extended in-place (not rewritten). Add SUPPL fetching alongside existing ORIG fetching. Preserve all existing CLI arguments and behavior.
- **D-03**: Each table row represents an *approval event*, not a drug. A drug with both ORIG and SUPPL approvals appears as multiple rows with different type badges. This is the intended behavior.

### SUPPL Data Fetching
- **D-04**: Fetch SUPPL submissions from drugsfda endpoint using `submissions.submission_type:SUPPL` + `submissions.submission_status:AP`
- **D-05**: Filter SUPPL entries to efficacy-related `submission_class_code_description` values only. Non-efficacy supplements (manufacturing, labeling) must be excluded. The exact classification values must be verified against real openFDA data before implementation.
- **D-06**: Type badge: "New Drug" for ORIG/NME approvals, "New Indication" for efficacy SUPPL approvals
- **D-07**: SUPPL approval date uses the specific SUPPL submission's `submission_status_date`, NOT the drug's max submission date (sort pitfall avoidance)

### Data Integrity
- **D-08**: Always post-filter by actual ORIG/SUPPL approval date in Python. Never trust the API sort order for date-sorted display. Sort final drug list in Python before writing JSON.
- **D-09**: Missing label data (404s) produces `label: null` without crashing. The script already handles this via HTTPError catch.
- **D-10**: Prescription-only filter: check `products.marketing_status` for both `"Prescription"` and `"1"` (API returns both formats)
- **D-11**: Rate limiting: 0.5s delay between label requests (already in script)

### JSON Data Contract
- **D-12**: Output file is `data/approvals.json` — the stable contract consumed by `build.py`
- **D-13**: JSON schema includes: `brand_name`, `generic_name`, `approval_date` (ISO format), `application_number`, `submission_class`, `type_badge` (new field: "New Drug" or "New Indication"), `sponsor_name`, `manufacturer_name`, `route`, `pharm_class_epc`, `ph_class_moa`, `products`, `label`, `indication_preview` (new field: truncated first sentence)
- **D-14**: `indication_preview` truncates at the first sentence or clause boundary (~100 chars), not at an arbitrary character count

### Build Script (Minimal)
- **D-15**: `build.py` reads `data/approvals.json`, renders a minimal `site/index.html` with a plain HTML table of all drugs, no CSS framework yet. Purpose: prove the data pipeline produces correct, renderable output.
- **D-16**: `build.py` uses Jinja2 with `FileSystemLoader` and `select_autoescape` for HTML generation
- **D-17**: Slug generation for drug URLs uses `slugify(brand_name or generic_name)`, with application number suffix for collision handling

### Date Handling
- **D-18**: Dates stored and output as ISO format `"YYYY-MM-DD"` in the JSON (converted from API's `"YYYYMMDD"`)
- **D-19**: Default date range is computed relative to "today" (not hardcoded) — last 2 years

### Claude's Discretion

- Exact SUPPL efficacy classification values — must be verified against real openFDA data during implementation
- Whether to add a `--type suppl` CLI argument or fold SUPPL fetching into the default behavior
- Precise `indication_preview` truncation algorithm (sentence boundary vs. clause boundary)
- Whether `build.py` generates per-drug detail pages or just the index page (minimal proof = just index)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### API & Data
- `.skills/openfda-drug/SKILL.md` — openFDA API endpoints, fields, query syntax, date format gotchas
- `fda_approvals.py` — Current working script; all extensions build on this

### Architecture
- `.planning/research/ARCHITECTURE.md` — Two-script pipeline pattern, JSON contract, component responsibilities
- `.planning/research/STACK.md` — Tech stack decisions (Python + Jinja2, no Node.js)
- `.planning/research/PITFALLS.md` — Critical pitfalls: sort pitfall, SUPPL duplicates, label 404s

### Project
- `AGENTS.md` — Project-specific gotchas and repo structure
- `.planning/PROJECT.md` — Key decisions and constraints
</canonical_refs>

<specifics>
## Specific Ideas

- The existing script's `fetch_drugsfda_approvals()` function queries for ORIG submissions. SUPPL support needs a second query (or modified query) with `submissions.submission_type:SUPPL` and filtering for efficacy classification.
- The `submission_class_code_description` values for efficacy supplements need empirical verification. Run an API query like `/drug/drugsfda.json?search=submissions.submission_type:SUPPL+AND+submissions.submission_status:AP&limit=100` and examine the distinct values.
- The minimal `build.py` should be ~50-100 lines: read JSON, load a simple Jinja2 template, render index.html with a `<table>` of all drugs.
- The "data contract" between `fda_approvals.py` and `build.py` is the JSON schema. New fields (`type_badge`, `indication_preview`) must be computed before writing JSON so `build.py` can be simple.
</specifics>

<deferred>
## Deferred Ideas

- Full site UI (Phase 2) — CSS framework, dark mode, List.js, responsive layout
- Drug detail pages (Phase 3) — full prescribing info, collapsible sections, boxed warning callout
- Automation (Phase 4) — systemd timer, auto-push to Synology
- Label HTML sanitization — deferred to Phase 3 (detail pages) since minimal build doesn't render label HTML
- Incremental label caching — deferred; acceptable for v1 to re-fetch all labels weekly
- Pagination of results — deferred until drug count warrants it (~200+)
</deferred>

---
*Phase: 01-data-pipeline*
*Context gathered: 2026-04-23 from research + requirements synthesis*