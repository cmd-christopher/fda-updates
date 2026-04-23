# Feature Research

**Domain:** Drug approval tracking site for physicians (static, Fed from openFDA API)
**Researched:** 2026-04-22
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features physicians assume exist. Missing any = site feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Sortable approval table** | Physicians scanning for "what's new" need to sort by date (newest first), drug name (A-Z), and pharmacologic category. This is the entire reason to visit the site. | LOW | List.js handles this. Default sort should be date descending — "what changed this week?" is the primary question. |
| **Approval date column** | Date is the primary axis for drug approval tracking. Without it, the table is useless for time-based scanning. | LOW | Already in openFDA `submission_status_date` (YYYYMMDD format, script converts to ISO). |
| **Brand and generic name columns** | Physicians search by both. Brand names for recognition ("I heard about Dupixent"), generic names for prescribing and cross-referencing ("dupilumab — same drug, different indication"). | LOW | Already captured in `brand_name` and `generic_name` from openFDA. |
| **Type flag: New Drug vs New Indication** | Physicians need to know whether a listing represents a genuinely novel drug (NME) or a new use for an existing drug they may already prescribe. A "New Indication" for Dupixent changes clinical practice differently than a brand-new drug. | MEDIUM | Requires script change: extend `fda_approvals.py` to also fetch SUPPL submissions with efficacy classification. PROJECT.md already plans this. |
| **Pharmacologic category column** | Physicians organize knowledge by drug class. Seeing "IL-4/IL-13 antagonist" or "GLP-1 receptor agonist" provides instant context for whether a new approval is relevant to their practice. | LOW | Available as `pharm_class_epc` from openFDA. Some drugs lack this field — display as "—" gracefully. |
| **Primary indication** | "What is this drug for?" is the second question after "what's new?" Indication text must be visible in the table row, not buried in a detail page. | MEDIUM | Available from `indications_and_usage` in the label endpoint. Needs truncation logic for table view (first sentence or first N chars). |
| **Detail page per drug** | Clicking a table row must show the full prescribing information. This is what separates a tracking site from a simple list. | MEDIUM | Jinja2 template renders `index.html` + `drugs/{slug}.html` per drug. All label sections from the JSON feed into the template. |
| **Boxed warning visibility** | Black box warnings are the FDA's strongest safety signal. Physicians need to see these immediately on the detail page, not buried in scrolling. | LOW | `boxed_warning` is a top-level field in the label endpoint. Template should render it in a visually distinct callout box at the top of the detail page. |
| **Dosing & administration section** | The most-actionable prescribing information. "Start at 10mg, max 40mg, adjust for renal impairment" — physicians need this at a glance. | LOW | `dosage_and_administration` from label endpoint. May need basic HTML sanitization (label data contains embedded HTML tables). |
| **Contraindications section** | Essential safety information. "Don't use with X" is critical for prescribing decisions. | LOW | `contraindications` from label endpoint. Usually well-structured. |
| **Adverse reactions section** | Second-most-consulted section after dosing. Physicians need to know common and serious AEs. | LOW | `adverse_reactions` from label endpoint. Can be very long (large tables). Needs collapsible/expandable display. |
| **Mobile-responsive layout** | Physicians check references on phones during clinical rotations, between patients, or in hallways. A desktop-only table is useless in practice. | LOW | Pico CSS handles this with its built-in responsive tables. Add `overflow-x: auto` wrapper for the table on small screens. |
| **Dark mode** | The medupdates parent site has dark mode. Physicians reading at night (on-call) expect it. Mismatch = feels broken. | LOW | Pico CSS `data-theme="dark"` + `prefers-color-scheme` already supported. Toggle button with localStorage persistence (~20 lines of JS). |
| **Data freshness indicator** | Physicians need to know how current the information is. "Last updated: April 21, 2026" builds trust. Missing = "is this stale?" | LOW | `build.py` embeds the data fetch timestamp in the page. |
| **Link to official FDA source** | Physicians are trained to verify against primary sources. A "View on Drugs@FDA" or "View FDA label" link is expected and builds credibility. | LOW | Construct Drugs@FDA URL from `application_number` (e.g., `https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=NDA123456`). |

### Differentiators (Competitive Advantage)

Features that set this site apart from Drugs@FDA, Drugs.com, Medscape, and DailyMed.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Curated time window (~2 years)** | Drugs@FDA shows ALL drugs since 1939. Drugs.com shows only the latest handful. A 2-year window is the sweet spot — recent enough to be clinically relevant, focused enough to scan quickly. | LOW | Script `--from` date parameter already supports this. Default view shows 2 years. |
| **New Drug / New Indication differentiation** | No other site clearly separates NMEs from new indication approvals in a single unified list. Drugs@FDA requires separate report views. Drugs.com groups them but doesn't clearly flag the type. This is the core differentiator. | MEDIUM | Requires SUPPL data enrichment. The type flag ("New Drug" badge vs "New Indication" for existing drug) is visually distinctive and immediately actionable. |
| **Scannable table with indication preview** | Drugs@FDA requires clicking into each drug to see its indication. Drugs.com shows indication on detail pages but not in the listing. Putting the primary indication right in the table row — even truncated — saves physicians a click for every drug they need to assess. | MEDIUM | Requires smart truncation of `indications_and_usage` (first clause up to ~100 chars). Template skill, not data skill. |
| **Full prescribing information in structured sections** | Drugs@FDA links to PDF labels. Drugs.com reformats labels but buries them behind ads and navigation. DailyMed has structured labels but poor navigation. Displaying the full PI with section-level navigation, collapsible sections, and a table of contents — in a clean, ad-free page — is meaningfully better. | MEDIUM | All label sections are already fetched by the script. Template work: section navigation sidebar or anchor links, collapsed-by-default for long sections, expanded-by-default for key sections (boxed warning, indications, dosing). |
| **Orchid & Teal visual identity matching medupdates** | Visual consistency with the parent site signals "this is from the same trustworthy source." Unique color palette makes the site instantly recognizable and differentiated from the blue-and-white FDA style. | LOW | Pico CSS variable overrides (already specified in STACK.md). ~30 lines of CSS. |
| **Ad-free, distraction-free design** | Every competitor (Drugs.com, Medscape) is ad-supported and visually noisy. A clean, fast, single-purpose page respects physician time and attention. | LOW | It's a static site with no ads. The lack of clutter IS the feature. Ensure no visual noise in template design. |
| **Dosage forms & strengths summary** | Physicians need to know available formulations. "Available as 10mg, 20mg, 40mg tablets" and "injection: 100mg/mL vial" at a glance saves them from reading the full label for basic prescribing questions. | LOW | `dosage_forms_and_strengths` from label endpoint, plus `products` array from drugsfda for available formulations. Display as a highlighted summary section. |
| **Mechanism of action (concise)** | Physicians learning a new drug want the MOA in one sentence. "Selective IL-4 and IL-13 antagonist" communicates more than 5 paragraphs of clinical pharmacology. | LOW | `mechanism_of_action` from label endpoint. Usually 1-3 sentences. Display prominently on detail page. |
| **Approval type classification badges** | Beyond "New Drug" vs "New Indication," classify NMEs with clearer labels: "New Molecular Entity" (novel), "New Biologic" (BLA), and supplements with the supplement type (efficacy, safety, labeling). This is richer than Drugs@FDA's raw submission codes. | MEDIUM | Requires parsing `submission_class_code_description` from drugsfda and `submission_type` + classification from SUPPL data. Some API mapping needed. |
| **Drug name search/filter in table** | Physicians looking for a specific drug ("did Dupixent get a new indication?") need instant text search, not page-by-page browsing. | LOW | List.js built-in search. Initialize with `searchClass: 'search'` and a search input above the table. Instant, client-side, no reload. |
| **Category filter in table** | Physicians in specialty practice want to see only drugs relevant to them. Filtering by pharmacologic category ("Show me only oncology drugs") is more useful than scanning 200 rows. | MEDIUM | List.js doesn't natively support category dropdown filters. Requires ~30 lines of vanilla JS: a `<select>` that shows/hides rows by `data-category` attribute. Or filter with List.js's `filter()` method. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for this project.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Adverse event reporting integration** | "Show me the safety signals for this drug" seems like a natural extension. | FAERS data is unstructured, cannot establish causation, is subject to reporting bias, and would turn a clean prescribing reference into a medico-legal minefield. Suggesting "this drug has 500 liver injury reports" without context is dangerous. | Explicitly out of scope (PROJECT.md). Link to FAERS on FDA.gov for physicians who want to investigate. |
| **Drug shortage tracking** | "If I'm going to prescribe it, is it in stock?" | Shortage data is in a different openFDA endpoint (`/drug/shortages.json`), changes daily, requires real-time updates (not weekly), and is operationally different from approval data. Mixing approval tracking with shortage tracking conflates two distinct clinical questions. | Out of scope for v1. Could be a future separate section or page if demand exists. |
| **Email/RSS alert subscriptions** | "Let me know when something new is approved." | Requires a server-side component (email sender or RSS feed generator), which contradicts the static-site architecture. Also requires managing subscriptions, bounces, and deliverability — a whole operational burden for a personal project. | Out of scope per PROJECT.md. Weekly rebuild + static site means data is always current. Physicians can bookmark and check weekly. A future `atom.xml` feed is 20 lines of Jinja2 — zero operational cost. |
| **User accounts / saved preferences** | "Let me save my specialty filter preference." | Requires auth infrastructure, a database, session management — the entire complexity of a dynamic web app. This is a static read-only site. | Out of scope per PROJECT.md. Browser localStorage can persist filter/sort preferences (3 lines of JS) without accounts. |
| **Drug interaction checker** | "I want to check if this new drug interacts with my patient's meds." | Drug interaction databases are proprietary (Micromedex, Lexicomp). The openFDA API doesn't provide interaction data. Building this requires licensing commercial data or scraping DailyMed interaction tables — legally and technically problematic. | Link to Drugs.com interaction checker for physicians who need it. Never try to build this from openFDA data. |
| **Comparison mode (side-by-side)** | "Let me compare two drugs in the same class." | Sounds useful but requires interactive UI with synchronized scroll, column alignment, and significant JS complexity for a static site. The ROI is low — physicians can open two tabs. | Defer indefinitely. If data has `pharm_class_epc`, a future "show drugs in same class" link is easy. Side-by-side comparison is a different product. |
| **Real-time FDA API queries from the browser** | "Always show the latest data!" | openFDA has a 240 req/min rate limit without an API key. Direct browser queries would expose the API to abuse, add latency, and contradict the static-site model. The weekly cron is the correct architecture. | Static site rebuilt weekly. Data is at most 7 days stale — appropriate for approval tracking (approvals don't change within a week). |
| **AI summaries of prescribing information** | "Summarize the PI for me." | LLM-generated medical summaries introduce liability (what if the summary misses a contraindication?), require ongoing API costs, and conflict with the "show the full PI, let the physician decide" philosophy from PROJECT.md. | Show the structured PI sections. Physicians are trained to read PIs — they don't need AI summaries. The indication preview in the table is truncation, not interpretation. |

## Feature Dependencies

```
[Approval Table (sortable)]
    └──requires──> [Type Flag: New Drug vs New Indication]
                         └──requires──> [SUPPL data in fda_approvals.py]

[Detail Page per Drug]
    └──requires──> [Label data from openFDA label endpoint]
    └──requires──> [Structured PI section rendering]
    └──enhances──> [Boxed Warning callout]
    └──enhances──> [Section-level navigation/anchor links]

[Table Search & Filter]
    └──requires──> [List.js integration]
    └──requires──> [Pharmacologic category in data]

[Dark Mode Toggle]
    └──requires──> [Pico CSS data-theme attribute]
    └──requires──> [localStorage persistence]
    └──enhances──> [Orchid & Teal palette for dark mode]

[Indication Preview in Table]
    └──requires──> [Label data (indications_and_usage field)]
    └──requires──> [Smart truncation logic]

[Data Freshness Indicator]
    └──requires──> [Build timestamp in generated HTML]

[Approval Type Classification Badges]
    └──requires──> [SUPPL data enrichment]
    └──requires──> [submission_class_code_description parsing]

[Category Filter Dropdown]
    └──requires──> [pharm_class_epc data per drug]
    └──conflicts──> [(nothing — enhances search)]
```

### Dependency Notes

- **Approval Table requires Type Flag:** The core value proposition is showing NMEs and new indications together with clear differentiation. Without the type flag, the table is just Drugs@FDA with a date filter — unremarkable.
- **Detail Page requires Label data:** The `fda_approvals.py` script already fetches labels when `--skip-labels` is not used. The template system must render all available PI sections.
- **SUPPL data enrichment** is the critical data pipeline change: the current script only fetches ORIG submissions. New indications come from SUPPL (supplement) submissions with efficacy classification. This must be added before the site is useful.
- **Orchid & Teal palette enhances Dark mode:** The color variables for dark mode must use lighter orchid (#A78BFA) against dark backgrounds, as specified in STACK.md. These are complementary, not conflicting.
- **Category Filter requires pharm_class_epc:** Many drugs have this field from openFDA, but some don't. The filter should show "Unclassified" for drugs missing this field rather than hiding them.

## MVP Definition

### Launch With (v1)

Minimum needed to validate that physicians find the site useful.

- [ ] **Sortable approval table with date, brand name, generic name** — core value; without this there's no product
- [ ] **Type flag (New Drug vs New Indication)** — the differentiator; without this the site is undifferentiated from Drugs@FDA
- [ ] **Pharmacologic category in table** — essential scannability; physicians organize by drug class
- [ ] **Indication preview in table row** — saves one click per drug; the "should I read more?" decision point
- [ ] **Detail page with full structured PI** — boxed warning prominent, sections with anchor navigation, collapsible long sections
- [ ] **Mobile-responsive design** — physicians check references on phones
- [ ] **Dark mode matching medupdates** — visual consistency with parent site
- [ ] **Data freshness indicator** — "Last updated: [date]" builds trust
- [ ] **Link to official FDA source** — credibility and source verification
- [ ] **SUPPL data in fda_approvals.py** — required to show new indication approvals

### Add After Validation (v1.x)

Features to add once core is working and physicians are using the site.

- [ ] **Drug name search in table** — List.js built-in, easy addition once table is rendered
- [ ] **Dosage forms & strengths summary on detail page** — data already available, template addition
- [ ] **Mechanism of action highlight on detail page** — data already available, template addition
- [ ] **Approval type classification badges** — richer type information beyond binary flag
- [ ] **Category filter dropdown** — useful for specialty physicians
- [ ] **Atom/RSS feed** — 20 lines of Jinja2 template, zero operational cost, enables passive monitoring

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Drug comparison view** — only if physicians explicitly request it; open-two-tabs is fine for now
- [ ] **Print-friendly detail page** — `@media print` CSS for physicians who want to print a PI page
- [ ] **Permalinks for individual PI sections** — `#boxed-warning`, `#dosing` anchor links for sharing specific sections
- [ ] **Related drugs by class** — "Other IL-4/IL-13 antagonists" links on detail pages
- [ ] **Bookmarkable searches** — URL query params for saved filter state (`?category=oncology&sort=date`)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Sortable approval table | HIGH | LOW | P1 |
| Approval date column | HIGH | LOW | P1 |
| Brand & generic name columns | HIGH | LOW | P1 |
| Type flag: New Drug vs New Indication | HIGH | MEDIUM | P1 |
| Pharmacologic category in table | HIGH | LOW | P1 |
| Detail page with full PI | HIGH | MEDIUM | P1 |
| Boxed warning prominence | HIGH | LOW | P1 |
| Mobile-responsive layout | HIGH | LOW | P1 |
| Dark mode (Orchid & Teal) | HIGH | LOW | P1 |
| Data freshness indicator | MEDIUM | LOW | P1 |
| Link to FDA source | MEDIUM | LOW | P1 |
| Indication preview in table row | HIGH | MEDIUM | P1 |
| SUPPL data pipeline in script | HIGH | MEDIUM | P1 |
| Drug name search in table | MEDIUM | LOW | P2 |
| Dosage forms & strengths summary | MEDIUM | LOW | P2 |
| Mechanism of action highlight | MEDIUM | LOW | P2 |
| Category filter dropdown | MEDIUM | MEDIUM | P2 |
| Approval type badges | LOW | MEDIUM | P2 |
| Atom/RSS feed | LOW | LOW | P2 |
| Print-friendly page | LOW | LOW | P3 |
| Section anchor links | MEDIUM | LOW | P3 |
| Related drugs by class | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch — site is not useful without these
- P2: Should have, add when possible — enhances usability significantly
- P3: Nice to have, future consideration — marginal improvement

## Competitor Feature Analysis

| Feature | Drugs@FDA (FDA official) | Drugs.com New Drugs | Medscape | DailyMed | Our Approach |
|---------|--------------------------|---------------------|----------|----------|--------------|
| **Listing scope** | All drugs since 1939 (overwhelming) | Latest ~20 new approvals per page (too narrow) | Comprehensive but requires login and buried in navigation | All SPL documents (overwhelming for approval tracking) | ~2 years, mixed NMEs + new indications (curated sweet spot) |
| **New Drug vs New Indication flag** | No — requires separate "Original NDA" vs "Supplemental" report views | Partially — groups by approval type but mixes in listing | No clear differentiation | No — shows current label only, not approval history | Clear badges: "New Drug" and "New Indication" on every row |
| **Indication in listing** | No — must click into each drug | Yes, as short description | Partially — in drug monograph, not listing | No — must open full label | Yes — truncated indication in table row, full text on detail page |
| **Full prescribing info** | Links to PDF (unusable on phone) | Reformatted but buried behind ads and navigation clutter | Comprehensive but requires login and multiple clicks | Structured but poor navigation, dense formatting | Structured HTML, collapsible sections, mobile-friendly, ad-free |
| **Boxed warning** | In PDF only | Shown but surrounded by ads | Yes, in monograph | In full label, not highlighted | Highlighted at top of detail page in distinctive callout |
| **Drug class / MOA** | Available but not in listing | Available on detail page | Yes, in monograph | Available in label text | Shown in table row AND detail page |
| **Search/filter** | Basic text search, very slow | Good search | Good search, but requires login | Advanced search, cumbersome | Client-side search + category filter, instant |
| **Mobile experience** | Poor — government site, not mobile-optimized | Decent but ad-heavy | App-dependent or poor mobile web | Poor — academic site, not mobile-friendly | Mobile-first responsive, clean, ad-free |
| **Dark mode** | No | No | No | No | Yes — matching medupdates parent site |
| **Update freshness** | Daily (but hard to find new approvals) | Updated regularly | Updated regularly | Updated when labels change | Weekly — appropriate cadence for approval tracking |
| **Speed** | Slow (government site, heavy) | Slow (ad-heavy, many scripts) | Slow (login wall, heavy) | Moderate (NLM infrastructure) | Fast — static HTML, no server-side rendering, CDN-friendly |

## Sources

- **Drugs@FDA** (accessdata.fda.gov/scripts/cder/daf/) — Analyzed directly. Confirmed: no clear NME vs supplement differentiation in listing, requires separate monthly reports, PDF-only labels, no mobile optimization. (HIGH confidence — direct observation)
- **Drugs.com New Drugs** (drugs.com/newdrugs/) — Analyzed directly. Confirmed: shows ~20 recent approvals per page, mixed new drugs and new indications without clear type flags, reformatted labels behind ads, good but ad-heavy mobile experience. (HIGH confidence — direct observation)
- **Medscape Drug Reference** (medscape.com/druginfo) — Analyzed landing page. Requires login for full prescribing info, buried behind navigation, comprehensive but poor scannability for "what's new." (MEDIUM confidence — login wall limited full analysis)
- **DailyMed** (dailymed.nlm.nih.gov/) — Analyzed directly. Confirmed: complete SPL data but overwhelming for quick lookups, no "recent approvals" view, poor navigation structure, dense formatting. (HIGH confidence — direct observation)
- **openFDA API** (api.fda.gov) — Analyzed via script and documentation. Confirmed: `drugsfda` endpoint has approval dates, submission types, product details; `label` endpoint has all PI sections. Limitations: label endpoint has no date search; must start from drugsfda. (HIGH confidence — verified in existing fda_approvals.py script)
- **medupdates.wilmsfamily.com** — Analyzed directly. Confirmed Orchid & Teal palette, dark mode support, card-based layout, specialty-tagged content, clean typography. (HIGH confidence — direct observation)
- **Physician workflow**: Based on clinical practice patterns — physicians need rapid scannability (table), quick identification of what's new (date + type flag), fast access to actionable info (indication + dosing), and trustworthy source links. The "between-patient lookup" pattern dominates (5-30 seconds per query).

---
*Feature research for: FDA Drug Approval Updates static site*
*Researched: 2026-04-22*