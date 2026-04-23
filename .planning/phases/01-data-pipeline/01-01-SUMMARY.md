# Plan 01 Summary: SUPPL Extension + Derived Fields

## What was done

Extended `fda_approvals.py` to fetch both ORIG (original approval) and efficacy SUPPL (supplement) entries from the openFDA drugsfda endpoint, with computed derived fields.

## Key implementation details

1. **`fetch_suppl_approvals()`** — New function that queries drugsfda for `submission_type:SUPPL + submission_status:AP + submission_class_code:EFFICACY`. Applies date-range filter in the API query for efficiency (reduces results from ~1985 to date-window subset), then post-filters each SUPPL submission's `submission_status_date` within the Python range (avoids the sort pitfall).

2. **Efficacy SUPPL classification** — Verified against real API data. The only SUPPL classification code for efficacy is `EFFICACY` (description: "Efficacy"). TYPE 1-10 codes are all `submission_type: ORIG`, not SUPPL. Non-efficacy SUPPL types (LABELING, MANUF/CMC, REMS, BIOEQUIV, BIOSIMILAR) are excluded.

3. **`--type` CLI** — Changed from `nme`/`all` to `nme`/`suppl`/`all`. Default is `all` (ORIG + efficacy SUPPL). `nme` returns only Type 1 NME originals. `suppl` returns only efficacy supplements.

4. **`type_badge`** — `"New Drug"` for all ORIG submissions, `"New Indication"` for efficacy SUPPL submissions.

5. **`slugify()`** — Python's `unicodedata.normalize` + regex for URL-safe slugs from brand_name (preferred) or generic_name.

6. **`truncate_indication()`** — Strips HTML tags, removes "N INDICATIONS AND USAGE" section header prefix, truncates at sentence/clause boundary or max_length (100 chars). Falls back to `submission_class` when label is null.

7. **Deduplication** — After combining ORIG + SUPPL results (sorted by date desc), deduplicates on `(application_number, approval_date, type_badge)` tuples. Drugs with same name but different NDA numbers (e.g., different dosage forms) are kept as distinct entries.

8. **Date range API filter** — Added `submission_status_date:[YYYYMMDD TO YYYYMMDD]` to both ORIG and SUPPL queries, dramatically reducing the result set from the API before post-filtering.

## Verification results

- 210 entries (157 New Drug + 53 New Indication) for 2026-01-01 to 2026-04-22
- 0 duplicate keys
- 0 OTC leaks
- 0 out-of-range dates
- 0 null labels in this data window
- 207/210 non-empty indication previews
- 0 previews with HTML tags
- 0 previews over 120 chars
- NME-only regression: 9 drugs, all "New Drug" badges

## Decisions

- **D-12**: Only `EFFICACY` classification code represents new-indication supplements. TYPE 1-10 are all ORIG submission types. No other SUPPL efficacy codes exist in the current API.
- **D-13**: Added date-range filter to API queries for efficiency (reduces 1985 total EFFICACY SUPPL to ~651 for 2025-2026 window). Post-filtering still required (sort pitfall).
- **D-14**: Indication preview strips the "N INDICATIONS AND USAGE" section header that FDA includes in the raw `indications_and_usage` field.