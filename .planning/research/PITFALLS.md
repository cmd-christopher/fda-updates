# Pitfalls Research

**Domain:** Static medical information site (FDA drug approvals, Python-built, Synology NAS deployment)
**Researched:** 2026-04-22
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: openFDA Sort Returns Wrong Approval Dates

**What goes wrong:**
Using `sort=submissions.submission_status_date:desc` returns drugs ordered by their most recent *any* submission, not the original approval date. DUPIXENT (originally approved March 2017) appears near the top because it has a 2026 supplement. Physicians see it listed as "new" when it's been on the market for 9 years. The entire site's value proposition collapses if approval dates are inaccurate.

**Why it happens:**
The drugsfda endpoint returns a flat `submissions` array containing every submission type (ORIG, SUPPL, etc.). The sort operates on the max date across all submissions, not the ORIG submission date. The API documentation does not make this behavior prominent — it's a known trap that the existing `fda_approvals.py` script already handles by post-filtering on the ORIG submission's date. But the SUPPL extension (adding new indication approvals) introduces a second variant of this pitfall: SUPPL entries *also* have a `submission_status_date` that might not be the supplement's approval date if the drug has a later supplement of a different type.

**How to avoid:**
- Always post-filter: extract the specific submission you care about (the ORIG for original approvals, the specific SUPPL with efficacy classification for new indications) and use *that* submission's date as the approval date.
- Never trust the sort order from the API for date-sorted display. Sort the final drug list in Python by the extracted approval date before rendering.
- When extending `fda_approvals.py` for SUPPL data, apply the same post-filter discipline: find the specific SUPPL submission with the efficacy classification, and use *its* date, not the drug's max submission date.

**Warning signs:**
- A drug with a well-known brand name (e.g., KEYTRUDA, HUMIRA) appearing in the "new approvals" list.
- Approval dates on the site that don't match the FDA's Drugs@FDA listing for the same drug.
- Multiple entries for the same drug appearing with different dates (one for ORIG, one for each SUPPL).

**Phase to address:**
Data pipeline phase (extending `fda_approvals.py` for SUPPL support). This is the single most important data-integrity pitfall — get it wrong and the entire site is unreliable.

---

### Pitfall 2: Label 404s for New/Recent Drugs

**What goes wrong:**
The openFDA label endpoint returns `404 Not Found` for some drugs. This happens because: (a) the label endpoint indexes structured product labeling (SPL) documents, which some drugs haven't submitted yet, especially very recent approvals; (b) the label endpoint uses a different identifier scheme than drugsfda and the cross-reference may not exist; (c) biologics and certain drug types sometimes lack SPL entries. When `fda_approvals.py` encounters a 404, the drug record gets `label: None`, and the detail page renders an empty shell with no prescribing information.

**Why it happens:**
The label and drugsfda endpoints are independent databases with different update cycles. The label endpoint updates weekly, drugsfda updates daily. A drug can appear in drugsfda before its label is indexed. The current script handles this by catching HTTPError 404 and returning None, but the downstream rendering must gracefully handle missing label data.

**How to avoid:**
- `build.py` must treat `label` as optional. Never assume `drug["label"]` is non-null.
- On the detail page, if label data is missing, display a clear message: "Full prescribing information is not yet available from the FDA. Check back after the next weekly update." Link to the Drugs@FDA page where the label PDF may be available.
- On the index table, if `indication_preview` can't be derived from the label, fall back to `products[0].active_ingredients` or the `submission_class_code_description` as a placeholder.
- Log 404s during data fetching so you can track which drugs are missing labels and whether they appear in subsequent runs.

**Warning signs:**
- Drug detail pages with only header info (brand, generic, approval date) and no PI sections.
- The count of drugs with labels being significantly lower than the total drug count.
- 404 errors appearing in stderr during `fda_approvals.py` runs (the script already prints warnings).

**Phase to address:**
Data pipeline phase (`fda_approvals.py` already handles 404s) and template/rendering phase (`build.py` and `drug_detail.html` must render gracefully without label data).

---

### Pitfall 3: SUPPL Data Creates Duplicate Drug Entries

**What goes wrong:**
When extending the script to fetch SUPPL (supplement) submissions for new indications, a single drug like DUPIXENT will have both an ORIG entry (original approval, March 2017) and multiple SUPPL entries (new indications, various dates). If these are naively added to the same list without deduplication logic, DUPIXENT appears three or four times in the approval table — once for each submission. The physician sees duplicate rows for the same drug and loses trust in the site.

**Why it happens:**
The drugsfda API returns one entry per application number (e.g., `BLA761055`). An entry contains ALL submissions in a single `submissions` array. For the ORIG-only mode, the script extracts one approval per entry. For SUPPL mode, the entry still returns as one result, but you need to extract multiple approvals (the ORIG plus relevant SUPPLs) from the same `submissions` array. If you iterate over SUPPL entries without deduplication, or if you create separate drug records for ORIG and SUPPL from the same application, you get duplicates.

**How to avoid:**
- Each row in the table represents a distinct *approval event* — not a distinct drug. "DUPIXENT (original NME approval, 2017)" and "DUPIXENT (new atopic dermatitis indication, 2026)" are two separate rows, and that's correct. This is the intended behavior: the site shows approval *events*, not drugs.
- However, the same SUPPL entry should not appear twice. Filter SUPPL submissions to only those with `submission_class_code_description` containing efficacy-related classifications (e.g., "Type 2 - New Indication", "Efficacy - New Indication"). Skip labeling supplements, manufacturing supplements, etc.
- Document this design decision clearly: the table shows *approval events*, and a drug may appear multiple times if it has multiple distinct approval events. Each entry should link to the same detail page (the most recent label for that application number).
- If a drug's ORIG approval falls outside the date window but a SUPPL falls within it, only the SUPPL entry should appear (not the ORIG). This is already handled by the date filter but must be tested.

**Warning signs:**
- The same brand name appearing multiple times with the same approval date (duplicate entries).
- ORIG approvals from 2017 showing in a 2025-2026 date window (forgot to filter ORIG dates).
- The drug count inexplicably doubling or tripling after adding SUPPL support.

**Phase to address:**
Data pipeline phase, specifically when extending `fda_approvals.py` to fetch SUPPL data. This must be solved before any site rendering work.

---

### Pitfall 4: Label HTML Contains Malformed or Dangerous Markup

**What goes wrong:**
openFDA label fields (`indications_and_usage`, `adverse_reactions`, etc.) contain embedded HTML — tables, `<br>` tags, bold/italic markup, and sometimes malformed or broken HTML fragments. If you inject this raw HTML into templates with `| safe` in Jinja2, malformed HTML can break the page layout (unclosed tables, stray `</div>` tags, etc.). While the risk of XSS is low (this is FDA-curated content, not user input), malformed HTML is a real and frequent problem that produces broken detail pages.

**Why it happens:**
Drug manufacturers submit labels as structured product labeling (SPL) XML, which the FDA converts to HTML fragments. The conversion quality varies. Some labels contain: nested tables without closing tags, `<p>` inside `<li>` elements, CSS style attributes that conflict with Pico CSS, or `&amp;` encoding issues. The `adverse_reactions` field frequently contains large HTML tables that don't close properly.

**How to avoid:**
- Enable Jinja2's autoescaping globally (`select_autoescape(["html", "xml"])`). This is the default and is already planned in the architecture.
- For label fields that contain HTML, create a whitelist sanitization function in `build.py` that:
  - Removes `<script>`, `<style>`, `<iframe>` tags entirely.
  - Removes `onclick`, `onerror`, `onload`, and other event attributes.
  - Removes `style` attributes (they conflict with Pico CSS and custom styles).
  - Preserves structural HTML: `<table>`, `<tr>`, `<td>`, `<th>`, `<p>`, `<br>`, `<ul>`, `<ol>`, `<li>`, `<b>`, `<i>`, `<strong>`, `<em>`, `<h1>`-`<h6>`, `<sub>`, `<sup>`.
  - Wraps orphaned HTML in a `<div>` container to prevent layout breaks.
- Test sanitization against a real batch of labels (run `fda_approvals.py` on a large date range and examine the HTML in each `label` field).
- Consider linking to the FDA's official label PDF as a fallback when the HTML rendering is clearly broken.

**Warning signs:**
- Detail pages with misaligned tables, missing sections, or broken layout.
- The `<table>` in `adverse_reactions` breaking out of its container div.
- Stray `</div>` or `</table>` tags in the rendered page (view source to check).
- Pico CSS styles being overridden by inline styles from label data.

**Phase to address:**
Template/rendering phase (`build.py` and `drug_detail.html`). Build the sanitization function early in the build phase and test with real label data before considering the detail page "done."

---

### Pitfall 5: systemd Timer Failure Goes Unnoticed

**What goes wrong:**
The systemd timer runs `fda_approvals.py` → `build.py` → `git push` weekly at 03:00 ET. If any step fails (API outage, network error, git conflict, disk full on Synology), the timer silently fails and the site stops updating. A physician visits the site a month later and sees data from a month ago — but there's no indication that the data is stale. The "Last updated" timestamp still shows the old date, but who checks that? The site *looks* functional, just outdated.

**Why it happens:**
systemd oneshot services fail silently by default unless you configure `OnFailure` notifications. The pipeline script has no alerting. The git push could fail because of a merge conflict in the `site/` repo (e.g., someone edited `site/` files manually, or the post-receive hook on the Synology has an issue). The NAS could be offline. The openFDA API could be temporarily down. None of these produce visible errors on the website.

**How to avoid:**
- Set up `OnFailure` notification in the systemd service unit. At minimum, log to a file or send an email on failure. Example:
  ```ini
  [Unit]
  OnFailure=notify-failure.service
  
  [Service]
  # The service should exit non-zero on any pipeline failure
  ```
- Make the pipeline script fail loudly: `fda_approvals.py` and `build.py` should both exit with non-zero status on error. The systemd unit should use `set -e` (or the Python equivalent: `sys.exit(1)` on failure).
- Add a staleness check to the site itself: if `data/approvals.json` is older than 10 days, embed a banner in `index.html` saying "Data may be stale — last updated [date]." This requires `build.py` to embed the current date as a freshness signal and `main.js` to compare against the current date.
- Log each run: append to a local log file with timestamp, number of drugs fetched, success/failure status.
- Test the systemd timer manually before relying on it. Run `systemctl start fda-updates.service` and verify each step completes.
- Consider a `--dry-run` option for the pipeline that validates API connectivity without writing data.

**Warning signs:**
- The "Last updated" date on the website is more than 8 days old (weekly timer should update at most 7 days ago).
- Empty or missing `data/approvals.json` file.
- The systemd service showing `failed` status: `systemctl --user status fda-updates.service`.
- Git log in `site/` having no commits in the last 8 days.

**Phase to address:**
Automation phase (systemd timer setup). This is a deployment-operations pitfall, not a code pitfall, but it directly affects the site's reliability. The staleness-banner feature belongs in the build/rendering phase.

---

### Pitfall 6: git Push Failure Due to Manual `site/` Edits or Merge Conflicts

**What goes wrong:**
The `site/` directory is a separate git repo that `build.py` writes to and then pushes to the Synology. If someone manually edits files in `site/` (during testing, or by accident), the git history diverges. The next automated `git push` fails with a "non-fast-forward" error, and the pipeline stops. The site is now stale and no one notices until the staleness banner appears (if it exists) or someone checks manually.

**Why it happens:**
The architecture has `site/` as both a build output directory and a git repo. This dual role creates a conflict: `build.py` overwrites files, but git expects the working tree to match the last commit. If you make manual changes in `site/` and commit them, then `build.py` overwrites those changes but doesn't commit, creating a dirty working tree. The next `git add . && git commit` captures the build output, but if the remote branch has diverged (from a manual push), the push fails.

**How to avoid:**
- **Never manually edit files in `site/`.** This is rule #1. If you need to change HTML, change the template and rebuild.
- In the pipeline script, before `git push`, do a `git pull --rebase synology-fda master` to sync with the remote. This prevents non-fast-forward errors.
- Consider making the pipeline script more robust:
  ```bash
  cd site/
  git add -A
  git commit -m "weekly update $(date +%Y-%m-%d)" || true  # "or true" handles no-changes case
  git pull --rebase synology-fda master || { echo "Pull failed"; exit 1; }
  git push synology-fda master || { echo "Push failed"; exit 1; }
  ```
- Add a `site/.gitignore` that ignores build artifacts that shouldn't be tracked (if any).
- Document this rule prominently in AGENTS.md: "Never edit `site/` files directly."

**Warning signs:**
- `git push synology-fda master` failing with "non-fast-forward" or "rejected" error.
- The `site/` working tree having uncommitted changes before the weekly build runs.
- The `site/` git log showing manual commits that aren't from the pipeline script.

**Phase to address:**
Automation phase (systemd timer and deployment script). Add the `git pull --rebase` step and the "never edit site/" rule from the start.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| **No label sanitization — use `{{ content \| safe }}`** | Saves 50-100 lines of sanitization code. Gets detail pages working faster. | Malformed HTML from FDA labels breaks page layout. Style attributes conflict with Pico CSS. Potential XSS if FDA data is compromised (unlikely but not zero). Fixing after production requires re-sanitizing all labels and rebuilding. | Never for label fields. Acceptable for simple text fields (brand_name, generic_name) that come from openfda structured data. |
| **CDN links for Pico CSS and List.js** | No need to download and version static assets. Always latest. | Site breaks on LAN without internet. Version skew — CDN updates break styling. GDPR/patient-privacy concern if CDN tracks requests. | Never. The site must work offline on the Synology LAN. Download assets to `site/css/` and `site/js/`. |
| **Skip SUPPL support, only show NMEs** | Simpler data pipeline. Current script already handles ORIG. | Site is undifferentiated from Drugs@FDA — the core differentiator (New Drug vs. New Indication flag) is missing. Physicians need to see both. | Only for an MVP demo that won't be shown to physicians. Not acceptable for launch. |
| **Hard-code 2-year date range in script** | No need for date math or configuration. Simpler. | Date range becomes stale. Next year, someone forgets to update the script and the site shows data from 2 years ago that never advances. | Never. Always compute date range relative to "today" or use a configuration parameter. |
| **No staleness detection on the site** | Simpler `index.html`. No JS date comparison. | Site can be stale for weeks without any visible signal. Physicians trust stale data silently. | MVP only — add staleness detection before showing to physicians. |
| **Single monolithic `build.py` function** | Quick to write. 150 lines is manageable. | If build logic grows (pagination, category pages, RSS feeds), refactoring a single function becomes painful. | Acceptable for v1 (150-200 lines). Refactor into functions when `build.py` exceeds 300 lines. Don't refactor prematurely. |
| **No incremental label caching** | Simpler script — re-fetch all labels every week. | As drug count grows (200+ over 2 years), weekly API calls take 3-4+ minutes. Most labels don't change. Could be 10-30 seconds with caching. | Acceptable for v1. Add incremental caching when weekly fetch exceeds 5 minutes or API rate limits become a concern. |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **openFDA drugsfda** | Assuming `submission_status_date` on a submission is the *original* approval date. Always verify you're looking at the ORIG submission, not a SUPPL. | Extract the specific ORIG submission and use *its* `submission_status_date`. For SUPPL data, extract the specific efficacy SUPPL and use its date. Never trust sort order. |
| **openFDA drugsfda** | Assuming `products.marketing_status` is always present or always `"1"`. Some drugs have missing or empty marketing status. | Check for `"1"` OR `"Prescription"` (the API returns both formats). Skip drugs with no prescription products entirely. |
| **openFDA label endpoint** | Assuming a label always exists for every drug in drugsfda. Labels return 404 for ~5-10% of drugs, especially recent approvals and some biologics. | Handle 404 gracefully. `fda_approvals.py` already catches `HTTPError` with code 404. `build.py` must render detail pages without label data. |
| **openFDA label endpoint** | Using `openfda.brand_name` or `openfda.generic_name` as the search key for the label endpoint. Brand names can have multiple matches, and the label endpoint may return a different drug. | Always search by `application_number` (e.g., `openfda.application_number:"BLA761055"`). Application numbers are unique identifiers that cross-reference correctly between endpoints. |
| **openFDA API rate limits** | Hitting 40 requests/min (unauthenticated) or 240 requests/min (with API key) by fetching labels for 200+ drugs in rapid succession. | The script already uses a 0.5s delay between label requests. Consider increasing to 1s if errors occur. For large batches (>100 drugs), consider fetching in smaller batches or using an API key. |
| **openFDA API pagination** | Assuming the first page of results contains all matches. The default `limit` is 100, and for 2+ years of data the total may exceed 100. | The current script paginates with `skip`. When adding SUPPL queries, verify pagination works for those queries too — SUPPL results may require different pagination parameters. |
| **Synology git push** | Assuming the `synology-fda` remote is always reachable and the post-receive hook always succeeds. Network outages, disk space, and SSH key changes can break the push. | Add error handling: `git push synology-fda master || { echo "Push failed"; exit 1; }`. The systemd service should fail non-zero so `OnFailure` triggers. |
| **Synology post-receive hook** | Assuming `git checkout -f` in the post-receive hook always works. If the working tree has uncommitted changes from manual edits, the checkout may fail silently. | Ensure the `site/` repo on the Synology has a clean working tree. The hook should use `GIT_DIR` and `GIT_WORK_TREE` environment variables explicitly. Never edit files in the Synology's checked-out copy. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Single-page 200+ row table** | `index.html` exceeds 150KB. Page feels sluggish on mobile. List.js search is slow on low-end phones. | Implement server-side pagination in `build.py`: generate `index.html` (latest 100) + `page/2.html`, etc. List.js pagination plugin for client-side. | ~200-250 drugs (2.5+ years of data). Not a concern for v1 with ~2 year window. |
| **No incremental label caching** | Weekly build takes 3-4 minutes. Most labels haven't changed since last week. Wasted API calls and time. | Cache labels in a separate JSON file. On subsequent runs, only fetch labels for drugs not in the cache. Re-fetch existing labels monthly or on 404. | ~200+ drugs. Acceptable for v1 but should be addressed if the date window grows or the script runs daily. |
| **All drugs in one API query** | The drugsfda API returns paginated results. For 2+ years of all submission types (ORIG + SUPPL), the total may exceed 500 results, requiring multiple API calls. | The script already paginates. Verify SUPPL queries don't hit the skip=25000 limit (extremely unlikely for 2 years of data, but check). | 5+ years of data with all submission types. Not a concern for v1. |
| **Label HTML bloat on detail pages** | The `adverse_reactions` field alone can be 50-100KB of HTML for some drugs. The full label for a complex biologic can be 200KB+. Rendering this on a mobile browser is slow. | Collapse long sections by default (`<details open>` for key sections, `<details>` for long ones). Consider truncating very long sections with a "Show full section" expand button. | ~5-10% of drugs have extremely long labels. Not a concern for the initial set, but noticeable for complex biologics (KEYTRUDA, HUMIRA). |
| **Rebuilding all pages on every build** | `build.py` regenerates all detail pages even if only one drug changed. With 200 drugs, this is still fast (<2s) but wasteful. | Acceptable for v1. Only optimize if build time exceeds 10 seconds. Incremental builds would require tracking which drugs changed since the last build. | 500+ drugs. Not a concern for v1. |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Injecting raw FDA label HTML without sanitization** | Malformed HTML breaks page layout. Theoretical XSS if FDA data were compromised (extremely unlikely but not zero). The real risk is layout corruption — unclosed `<table>` tags in `adverse_reactions` can break the entire detail page, making it unusable. | Use Jinja2 autoescaping (`select_autoescape`). For label fields, apply HTML sanitization: whitelist safe tags (`<table>`, `<p>`, `<br>`, etc.), remove `<script>`, `<style>`, `<iframe>`, strip `onclick`/`onerror` attributes, remove `style` attributes. Never use `{{ content \| safe }}` on label data without sanitization. |
| **Exposing openFDA API key in client-side code** | If you embed an API key in `main.js` or HTML templates, anyone viewing source can extract it. | Don't use an API key in client-side code. The API calls happen server-side in `fda_approvals.py`. The static site never calls the FDA API directly. If you get an API key for higher rate limits, store it in an environment variable on the build machine. |
| **Serving stale data without a freshness indicator** | Physicians make prescribing decisions based on data that appears current but is actually weeks old. This isn't a "security" issue in the traditional sense, but it's a medical information integrity issue. | Embed the data fetch timestamp in `index.html`. Add a JavaScript check that compares the timestamp to the current date and shows a warning banner if data is more than 10 days old. Never remove old data without replacing it. |
| **Cross-origin issues with CDN assets** | If Pico CSS or List.js are loaded from a CDN, the browser blocks them if CSP headers are misconfigured, or the CDN serves compromised assets, or the site is accessed without internet. | Download Pico CSS and List.js to `site/css/` and `site/js/`. No CDN dependencies. The site works fully offline on the Synology LAN. |
| **Git credentials on the NAS** | The `site/` repo pushes to the Synology via SSH. If the SSH key is compromised, an attacker could push malicious content to the website. | Use a dedicated SSH key for the deployment push. Restrict the key to the specific git command (`command="git-upload-pack..."` in `authorized_keys`). Don't store the key on shared accounts. |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **Treating NMEs and new indications identically in the table** | Physicians can't quickly identify whether a listing is a genuinely new drug or a new use for an existing drug they already prescribe. This is the #1 differentiation from Drugs@FDA, and hiding it makes the site no better than existing tools. | Use visually distinct badges: "New Drug" (colored, e.g., teal) vs "New Indication" (different color, e.g., orchid). Make the badge a prominent column, not a tooltip or subtle icon. Physicians scan by color first. |
| **Truncating indications without context** | Showing "For the treatment of..." as the indication preview tells the physician nothing. Showing "For the treatment of adult patients with moderate-to-severe atopic dermatitis who..." truncated at 100 chars is better but still incomplete. The risk is that physicians dismiss a drug because the truncated text doesn't match their specialty. | Truncate at the first clause or sentence boundary, not at an arbitrary character count. If the indication starts with "For the treatment of", keep the condition being treated. Example: "adult patients with moderate-to-severe atopic dermatitis" is better than "For the treatment of adult patients with mo...". Add a "..." that links to the detail page. |
| **Hiding the boxed warning** | Boxed warnings (black box warnings) are the FDA's strongest safety signal. If a physician prescribes a newly approved drug without seeing the boxed warning, patient safety is at risk. Burying it in a collapsible section or below the fold is a medical content error, not just a UX error. | Display the boxed warning prominently at the top of the detail page, above all other PI sections. Use a visually distinct style (red/amber callout box, not a collapsible section). The physician should not be able to miss it. |
| **Mobile-unfriendly table** | Physicians check drug references on phones during clinical rotations, between patients, in hallways. A table with 6 columns (date, type, brand, generic, category, indication) that requires horizontal scrolling on mobile is essentially unusable on the device where it's most needed. | Pico CSS provides responsive table styling, but responsive tables need special handling. Use `overflow-x: auto` on a container div, and consider making the indication column stack on mobile (or hiding it on small screens with `data-label` attributes). List.js pagination keeps the visible row count manageable. |
| **No differentiation between "no data" and "not applicable"** | When `pharm_class_epc` is missing for a drug, showing an empty cell suggests the data is unavailable. But some drugs genuinely don't have an established pharmacologic class. Showing "—" for missing data and "None established" for genuinely inapplicable fields is more useful. | Use "—" for missing data (API didn't return it), "None" for fields that exist but are empty (e.g., no boxed warning = "No boxed warning"). Never show a blank cell without explanation — it looks broken. |
| **Sorting dates as strings instead of ISO dates** | If List.js sorts the date column as text, "2026-04-17" sorts correctly but "04/17/2026" doesn't. Date formatting that works for display (Apr 17, 2026) breaks sort. | Store dates as ISO strings (`YYYY-MM-DD`) in the data-sort attribute and use List.js's `data-sort="date"` with a custom sort function, or store the sortable value in a `<span class="date" data-sort="20260417">Apr 17, 2026</span>` pattern. |
| **Linking to FDA pages that don't exist** | Constructing Drugs@FDA URLs from application numbers sounds straightforward, but the FDA's URL format has changed in the past and some application numbers don't produce valid links. A physician clicking a "View on FDA.gov" link and getting a 404 loses trust in the site. | Validate FDA link construction with real data. Use the pattern `https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={app_number_digits}` (strip the NDA/ANDA/BLA prefix, keep digits only). Test with 20+ real application numbers before launching. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **SUPPL support appears to work but missing efficacy-only filter:** The script fetches SUPPL entries but doesn't filter for efficacy supplements specifically. Result: the table shows manufacturing supplements, labeling supplements, and other non-clinical submissions as "new approvals." Verify that `submission_class_code_description` is filtered to efficacy-related types only.
- [ ] **Detail page renders but missing label sections:** The template renders some label sections but not all. Check that ALL label fields from the JSON are rendered: `indications_and_usage`, `boxed_warning`, `dosage_and_administration`, `dosage_forms_and_strengths`, `contraindications`, `warnings_and_cautions`, `adverse_reactions`, `drug_interactions`, `use_in_specific_populations`, `mechanism_of_action`, `clinical_pharmacology`, `clinical_studies`, `patient_counseling_information`, `nonclinical_toxicology`, `overdosage`, `description`. Missing sections that exist in the data = incomplete prescribing information.
- [ ] **Dark mode works but doesn't persist:** The theme toggle switches to dark mode but doesn't survive page navigation (index → detail → back). Verify that `localStorage` saves and restores the `data-theme` attribute on `<html>` across pages.
- [ ] **Table sorts but date sort is wrong:** List.js appears to sort the date column, but it sorts alphabetically ("Apr" < "Jan" < "Mar" — wrong). Verify date sorting uses ISO or numeric values in the `data-sort` attribute, NOT display-formatted dates.
- [ ] **Drug detail links work but slug collisions exist:** Two drugs with the same brand name (different NDAs, same drug name) slugify to the same filename. The second drug overwrites the first drug's detail page. Verify that `build.py` checks for slug uniqueness and appends the application number suffix when collisions occur.
- [ ] **Pipeline runs but produces empty output:** `fda_approvals.py` returns zero results (API returns empty array, date range has no approvals, or all drugs are filtered out as OTC). `build.py` renders `index.html` with an empty table — the site looks "done" but shows no data. Verify that the template handles the empty-drugs case gracefully with a "No new approvals in this period" message.
- [ ] **Labels render but contain broken HTML tables:** The `adverse_reactions` section appears on the detail page but contains malformed HTML from the FDA label (unclosed `<table>` tags, nested broken elements). The page renders, but sections after `adverse_reactions` are visually broken. Verify label sanitization against real data with complex HTML tables.
- [ ] **systemd timer runs but site doesn't update:** The timer fires, the service runs, but a silent error in `git push` means the Synology still serves old content. The timer appears "working" to systemd. Verify that the full pipeline completes end-to-end: fetch → build → commit → push → webhook checkout.
- [ ] **Type badges show but are misleading:** "New Drug" badge appears next to a 2017 drug because the ORIG submission date is within the range, but the drug isn't new to physicians — it's been prescribed for years. The badge should say "New Drug" only for drugs whose *original* approval date is recent, not whose ORIG submission happens to fall in the date window. Verify that the date window filter is applied to the *approval event date*, not just to the ORIG submission's existence.
- [ ] **Mobile view loads but table is horizontally clipped:** The table renders on mobile but requires horizontal scrolling, and key columns (indication, type) are clipped. Verify that `overflow-x: auto` is applied and that the indication column is either hidden or stacked on small viewports.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Wrong approval dates (sort pitfall)** | LOW | Fix the post-filter logic in `fda_approvals.py`. Re-fetch data (`--from` and `--to` parameters). Re-run `build.py`. Push to Synology. The data is from a public API — re-fetching is free and immediate. |
| **Label 404s leave empty detail pages** | LOW | Add graceful handling in `drug_detail.html`: if `label` is None, show "Prescribing information not yet available" message with link to Drugs@FDA. No data change needed — this is a template fix. |
| **Duplicate drug entries from SUPPL** | MEDIUM | Fix the deduplication logic in `fda_approvals.py`. Re-fetch and rebuild. This is a data pipeline fix, not a template fix. Verify by counting unique application numbers in the output. |
| **Malformed HTML in labels** | MEDIUM | Build sanitization function in `build.py`. Re-run build. If labels are already cached, sanitization runs on the next build. No API re-fetch needed. |
| **systemd timer not running** | LOW | Diagnose with `systemctl --user status fda-updates.timer`. Check journal: `journalctl --user -u fda-updates.service`. Fix the service file. Re-enable timer. |
| **Stale data on site (push failed)** | LOW | SSH into the machine running the timer. Run the pipeline manually: `python3 fda_approvals.py ... && python3 build.py && cd site/ && git add . && git commit -m "manual update" && git push synology-fda master`. Investigate why the automated push failed. |
| **Git conflict in site/ repo** | LOW | `cd site/ && git pull --rebase synology-fda master && git push synology-fda master`. If that fails, `git reset --hard synology-fda/master` and rebuild. Never manually edit site/ files. |
| **CDN assets fail to load** | LOW | Don't use CDN. Assets are downloaded to `site/css/` and `site/js/` during build. Recovery is: re-download if files are missing. No internet dependency at runtime. |
| **Site shows stale data without warning** | LOW | Add staleness banner to `index.html` template. The next build includes the banner. No historical data change needed. |
| **Slug collision overwrites a drug detail page** | LOW | Fix `build.py` to check for slug collisions and append application number suffix. Re-run build. The second drug gets a different filename. No data loss — original drug data still exists in `approvals.json`. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **Sort returns wrong approval dates** | Data pipeline (extending `fda_approvals.py`) | Run the script on a known date range (e.g., 2025-2026) and verify that all approval dates match Drugs@FDA. Specifically check drugs with known supplements (KEYTRUDA, HUMIRA, OPDIVO) — they should appear only once with the correct date. |
| **Label 404s for recent drugs** | Data pipeline + Template phase | Run the script with `--skip-labels` first, then with labels. Check which drugs return None labels. Verify the detail page template renders correctly with `label: None`. |
| **SUPPL creates duplicate entries** | Data pipeline (SUPPL extension) | After adding SUPPL support, verify the total drug count matches expectations. Check for duplicate brand names with same dates. Verify each entry represents a distinct approval event. |
| **Label HTML breaks page layout** | Template phase (`drug_detail.html`) | Run the build against real label data (fetch 50+ drugs). View every detail page and check for layout breaks. Specifically check drugs with long `adverse_reactions` tables. |
| **systemd timer fails silently** | Automation phase (systemd setup) | Configure `OnFailure` notification. Test the full pipeline manually. Verify `systemctl --user status` shows correct state. Check journal logs after the first automated run. |
| **Git push fails due to conflicts** | Automation phase | Add `git pull --rebase` before push in the pipeline script. Test with a simulated conflict. Add documentation: "Never edit files in site/." |
| **No freshness indicator** | Build phase (`build.py`) | Verify `index.html` contains the data fetch timestamp. Add JS check that shows a banner if data is >10 days old. Test by temporarily using an old timestamp. |
| **Badges don't distinguish NME vs new indication** | Template phase (`index.html`) | Verify that the type badge column is visually distinct (different colors for "New Drug" vs "New Indication"). Show the page to someone unfamiliar and ask "what does each badge mean?" |
| **Mobile table unusable** | Template phase (CSS/responsive) | View the index page on an actual phone or use Chrome DevTools mobile emulation at 375px width. Verify all columns are readable or appropriately stacked. |
| **Date sorting broken** | Template + JS phase | Click the "Approval Date" column header in the table. Verify it sorts newest-to-oldest and oldest-to-newest. Check that the year sorts numerically, not alphabetically. |
| **Empty data produces broken site** | Build phase | Run `build.py` with an empty `approvals.json` (`{"drugs": [], "count": 0}`). Verify the page renders with "No new approvals in this period" message, not a broken table. |
| **Slug collisions** | Build phase (`build.py`) | Create test data with two drugs that have the same brand name but different application numbers. Verify `build.py` generates different filenames. |

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **SUPPL data extension** | Fetching all SUPPL types instead of only efficacy supplements, resulting in manufacturing/labeling supplements appearing as "new approvals" | Filter `submission_class_code_description` for efficacy-related types only. Test with a drug that has multiple supplement types. |
| **Label data rendering** | Malformed HTML from FDA labels breaking page layout, especially `adverse_reactions` tables | Build HTML sanitization early. Test with 10+ real drug labels before considering the detail page done. |
| **Build pipeline** | `build.py` producing partial output (some detail pages, missing others) when `fda_approvals.py` returns data with unexpected fields | Validate in `build.py` that each drug object has required fields before rendering. Fail fast with a clear error message, not a partially rendered site. |
| **Jinja2 templating** | Forgetting to enable autoescaping, creating XSS risk from label HTML data | Always use `select_autoescape(["html", "xml"])`. Never blanket `{{ content \| safe }}` on label fields. Apply sanitization before marking content as safe. |
| **systemd automation** | Timer not triggering, service failing silently, or push failing without notification | Run the full pipeline manually before setting up the timer. Test `systemctl start fda-updates.service` end-to-end. Check `systemctl --user status` after the first automated run. |
| **Synology deployment** | Post-receive hook not working, file permissions wrong, or nginx serving stale cached files | After the first push, verify the files on the NAS are updated (check timestamps). Clear browser cache. Test from an incognito window. |
| **Dark mode** | Theme toggle not persisting across pages, or Orchid & Teal palette not mapping correctly to Pico CSS variables | Test: toggle dark mode on `index.html`, navigate to a detail page, verify dark mode persists. Toggle back. Repeat on mobile. |
| **List.js integration** | Date column sorting alphabetically instead of chronologically; search not finding drugs by generic name; pagination breaking the table layout | Store ISO dates in `data-sort` attributes. Initialize List.js with all `valueNames` matching table column classes. Test with 200+ rows (generate test data if needed). |

## Sources

- **openFDA API documentation** (api.fda.gov) — Endpoint specifications, rate limits, date formats, sort behavior. Verified the sort pitfall directly in `fda_approvals.py` and SKILL.md. (HIGH confidence)
- **AGENTS.md** — Project-specific gotchas: sort pitfall, date format (YYYYMMDD not YYYY-MM-DD), label endpoint lacking date search, URL encoding for search values. (HIGH confidence — project documentation)
- **fda_approvals.py source code** — Direct observation of: pagination logic, 404 handling for labels, `marketing_status` checking for "Prescription" and "1", rate limiting with 0.5s delay. (HIGH confidence — first-party code)
- **openFDA SKILL.md** — Submission types (ORIG vs SUPPL), marketing status codes ("1" = Prescription, "4" = OTC), date format caveat, multiple submissions per drug entry structure. (HIGH confidence)
- **medical-updates-codex-standalone (sibling project)** — Observed: systemd timer pattern, Synology post-receive hook, two-repo deployment strategy. (HIGH confidence — direct observation of working pattern)
- **Pico CSS documentation (Context7)** — Dark mode `data-theme` attribute behavior, CSS variable system. (HIGH confidence)
- **Jinja2 documentation (Context7)** — Autoescaping, `select_autoescape`, `Markup()` for safe content. (HIGH confidence)
- **Static site generation pitfalls** — Common mistakes from community discussions: HTML sanitization of user/API content, date sorting in static tables, mobile table responsiveness, staleness detection for cron-updated content. (MEDIUM confidence — general web development knowledge, verified against project specifics)

---
*Pitfalls research for: FDA Drug Approval Updates static site*
*Researched: 2026-04-22*