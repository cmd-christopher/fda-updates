# Phase 3 — UI Review

**Audited:** 2026-04-23
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists)
**Screenshots:** Not captured (Playwright browser not installed; dev server at localhost:8080 but CLI screenshots unavailable)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | FDA label text renders as massive walls of run-on text; 528/530 pages have PDF artifacts like "1.1 P" that break subsection detection |
| 2. Visuals | 3/4 | Clear focal point (boxed warning + drug name), good hierarchy with h1/h3/h4, but section content lacks visual breathing room |
| 3. Color | 3/4 | Consistent CSS variable system; boxed warning uses appropriate red accent (#d32f2f); 7 hardcoded hex colors in CSS are all for appropriate distinct accents |
| 4. Typography | 2/4 | 26 distinct font sizes across CSS; body text (section-content) has no explicit font-size at desktop, inheriting system default; sub-section headings are too small relative to body |
| 5. Spacing | 3/4 | Consistent rem-based spacing scale; no arbitrary values; but section-content padding is too tight for medical text readability |
| 6. Experience Design | 2/4 | No loading/error/empty states for dynamic content; 447/530 pages have 5000+ char single-paragraph walls; collapsible sections help but content inside is unreadable |

**Overall: 15/24**

---

## Top 3 Priority Fixes

1. **Rewrite `format_pi_text` regex to handle FDA PDF artifacts** — The `(?=(?:^|\s)(\d+(?:\.\d+)+\s+[A-Z]))` split regex produces phantom headings like "1.1 P" (single-letter PDF artifacts) that are then discarded by `len(m.group(2)) > 2`, causing the subsequent full heading "1.1 Plaque Psoriasis" to also be consumed as body text — Fix by preprocessing the `N.N X N.N FullTitle` artifact pattern before splitting: replace `\d+\.\d+\s+[A-Z]\s+(?=\d+\.\d+)` with empty string to strip the single-letter remnant, then split. This will allow the real heading "1.1 Plaque Psoriasis" to be detected correctly.

2. **Parse indications lead-in paragraphs into `<ul>` bullet lists** — 206 pages have the pattern `indicated for the treatment of: ... (1.1) ... (1.2) ...` where each parenthetical cross-ref marks a separate indication. Currently this renders as a single `<p>` with inline xrefs, creating an unreadable run-on sentence — Fix by detecting the `indicated for.*:` lead-in pattern and splitting at `(N.N)` cross-reference boundaries into `<li>` items, producing a proper `<ul class="pi-list">`.

3. **Break long body paragraphs into multiple `<p>` blocks** — 447 of 530 pages have at least one `<p>` block exceeding 5,000 characters; the KEYTRUDA indications section is a single 25,571-char `<p>` — Fix by splitting body text at sentence boundaries when a paragraph exceeds ~2,000 characters, or at the next detected sub-section heading pattern within the body.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**Critical: `format_pi_text` parser fails on FDA PDF artifacts (build.py:75)**

The core text formatting function in `build.py` line 75 splits raw FDA text at sub-section headings using:
```python
re.split(r"(?=(?:^|\s)(\d+(?:\.\d+)+\s+[A-Z]))", text, flags=re.MULTILINE)
```

This produces phantom headings from FDA PDF artifacts. The FDA label data contains patterns like:
- `"1.1 P 1.1 Plaque Psoriasis"` — the `"P"` is a PDF artifact (first letter of "Plaque")
- `"1.3 A 1.3 Ankylosing Spondylitis"` — the `"A"` is a PDF artifact (first letter of "Ankylosing")
- `"2.1 T 2.1 Testing and Procedures"` — the `"T"` is a PDF artifact

The heading match regex on line 86 (`len(m.group(2)) > 2`) correctly rejects single-letter headings, but the split regex on line 75 has already consumed the delimiter, so the real heading ("Plaque Psoriasis") becomes body text instead of an `<h4>`.

**Quantified impact:**
- 528/530 drug detail pages (99.6%) have the PDF artifact pattern
- 206 pages have 2+ cross-references in their indications lead-in that should be bullet lists
- The Cosentyx indications section renders 1,943 chars in a single `<p>` with zero `<h4>` subsection headings — all six subsections (1.1 through 1.6) are lost as body text
- KEYTRUDA's 25,571-char indications section renders as 10 `<p>` blocks with 9 `<h4>` headings — some subsections are found, but many are still missed

**Specific file evidence:**
- `build.py:75` — split regex captures PDF artifact headings
- `build.py:87` — `len(m.group(2)) > 2` rejects short headings but doesn't recover the real heading
- `site/drugs/cosentyx-125504.html` — indications `<div class="section-content">` contains a single `<p>` with 1,943 chars and 0 `<h4>` headings
- `site/drugs/keytruda.html` — 25,571-char indications section

**Copywriting positives:**
- Empty state for null labels is well-written: "Prescribing Information Not Yet Available" with a link to Drugs@FDA (drug_detail.html:97-101)
- Navigation label "← Back to Drug Approvals" is clear and descriptive (drug_detail.html:7)
- Section titles use human-readable names ("Indications & Usage", "Warnings & Precautions") rather than raw API keys

### Pillar 2: Visuals (3/4)

**Visual hierarchy is structurally sound:**
- `<h1>` for drug brand name — clear focal point (drug_detail.html:13)
- `<h3>` for boxed warning — safety-critical element stands out
- `<h4 class="pi-subsection">` for sub-section headings (when they render correctly)
- `.section-number` spans provide numeric context (e.g., "1.", "2.")

**Issues:**
- When subsection headings fail to render (see Pillar 1), the visual hierarchy collapses inside `<details>` sections — there's no visual break between subsections, making 1,000+ char blocks appear as identical-weight text
- The `<summary>` elements for PI sections use `font-weight: 600` and are visually prominent, but the content *inside* collapsed sections lacks any focal points when headings fail
- Icon-only elements: the theme toggle button uses emoji (🌙/☀️) instead of SVG icons — functional but not production-quality. Has `aria-label="Toggle dark mode"` and `title` attribute for accessibility.

### Pillar 3: Color (3/4)

**CSS variable system is well-structured:**
- `--teal`, `--teal-dark`, `--orchid`, `--orchid-dark` defined in base.html:9-12
- `--bg`, `--text`, `--muted`, `--border`, `--surface` for theming
- Dark mode variants for all custom properties via `[data-theme="dark"]`

**Boxed warning color usage is appropriate:**
- `#d32f2f` red border-left — distinct from Orchid & Teal palette, appropriate for safety-critical content
- `#fff5f5` light red background; `#2a1215` dark mode variant
- Warning h3 uses `#d32f2f` (light) / `#ef5350` (dark)

**Hardcoded hex colors (7 total in custom.css):**
- `#d32f2f` — boxed warning border/h3 (appropriate - safety red)
- `#fff5f5` — boxed warning background (appropriate)
- `#ef5350` — boxed warning dark mode (appropriate)
- `#2a1215` — boxed warning dark mode bg (appropriate)
- `#ccfbf1`, `#134e4a` — teal-light variants (appropriate, extend palette)
- `#f3e8ff`, `#3b0764` — orchid-light variants (appropriate, extend palette)
- Badge colors in base.html also use hardcoded hex but are all theme-appropriate

**No accent overuse found.** Teal is used for links and interactive highlights. Orchid is used for navigation links and hover states. Red is exclusively used for the boxed warning callout.

**Minor concern:** Cross-reference styling (`.xref`) uses `var(--muted)` at `0.85rem` — these are visually subdued, which is appropriate for reference markers, but they're the only indication of the original FDA section numbering that readers may rely on.

### Pillar 4: Typography (2/4)

**26 distinct font-size values in custom.css:**
- 0.7rem, 0.75rem, 0.8rem, 0.85rem, 0.9rem, 0.95rem, 1rem, 1.1rem, 1.2rem, 1.25rem, 1.4rem, 1.5rem, 2rem
- This is 13 unique desktop sizes plus mobile overrides — exceeds the recommended 4-size scale for abstract standards

**Font weights: 4 distinct values (600, 500, 700, 400)**
- This is within the recommended 2-weight limit plus 2 supporting weights

**Key typography issues:**
- `.section-content` has no explicit `font-size` — it inherits the body's system default (16px typically). Medical text at 16px with `line-height: 1.7` is readable but doesn't differentiate itself from navigation/UI text.
- `.pi-subsection` is `font-size: 0.95rem` — barely larger than body text and easily missed
- `.warning-content` at `font-size: 0.9rem` is actually *smaller* than body text despite being safety-critical
- `.xref` at `font-size: 0.85rem` makes cross-references very small

**Recommended type scale consolidation:**
| Element | Current | Recommendation |
|---------|---------|----------------|
| Drug h1 | 2rem | Keep |
| Section summary | 1rem | Keep |
| Subsection h4 | 0.95rem | Increase to 1.05rem for visibility |
| Body (section-content) | inherited (16px) | Explicitly set 0.95rem for medical text |
| Warning content | 0.9rem | Increase to 0.95rem (match body) |
| Meta labels | 0.7rem | Keep |
| Meta values | 0.9rem | Keep |

### Pillar 5: Spacing (3/4)

**Consistent rem-based spacing:**
- No arbitrary `[px]` or `[rem]` Tailwind-style values found
- All spacing uses standard `rem` values (0.15, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.75, 0.85, 1, 1.25, 1.5, 2, 4 rem)
- Well-structured responsive breakpoints at 768px and 480px

**Specific spacing concerns:**
- `.section-content` padding is `0.75rem 0.25rem 1rem 0.25rem` — the `0.25rem` horizontal padding makes the text nearly flush with the section edges, leaving no breathing room for long medical text
- `.pi-subsection` margin is `1.25rem 0 0.5rem 0` — adequate top margin, but the heading itself has no left padding, so it doesn't visually separate from adjacent body text
- `.section-content p` margin-bottom `0.85rem` is adequate for paragraph separation

**Positive:** The `.drug-detail` max-width of 900px and `.section-content` max-width of 850px provide excellent line-length constraints for readability. The metadata bar grid (`repeat(auto-fit, minmax(150px, 1fr))`) adapts well across breakpoints.

### Pillar 6: Experience Design (2/4)

**State coverage analysis:**

| State | Present | Notes |
|-------|---------|-------|
| Empty (null label) | ✅ | drug_detail.html:96-102 — clear message + Drugs@FDA link |
| Empty (no drugs) | ✅ | index.html:43-47 — "No drug approvals found" message |
| Loading | ❌ | Static site — no loading states needed (build-time rendering) |
| Error | ❌ | No error boundary for malformed label data; build.py exits on malformed data but generated pages have no runtime error handling |
| Confirmation (destructive) | N/A | No destructive actions on site |
| Disabled states | N/A | No form submissions or interactive actions beyond search/sort |

**Critical UX problem: Wall-of-text readability (447/530 pages affected)**

The most severe experience design failure is that **84.5% of drug detail pages contain at least one `<p>` block exceeding 5,000 characters.** This means a physician scanning a detail page for dosing information or a specific warning will encounter massive unbroken paragraphs that require horizontal scrolling or mental parsing to navigate.

**Specific examples of problematic rendering:**
- **Cosentyx indications**: The entire indications section (1,943 chars of lead-in text + 6 subsections that should render as `<h4>` + body pairs) renders as a **single `<p>`** with zero visual breaks
- **KEYTRUDA indications**: 25,571 chars renders as 10 `<p>` blocks — better than Cosentyx because the regex catches some subsections, but many are still missed
- **EPKINLY dosing**: Preparation instructions with numbered steps (1., 2., 3., 4., 5.) render as a single `<p>` without proper ordered list formatting
- **PIASKY dosing**: IV preparation instructions and storage tables render as continuous text

**Collapsible sections are structurally correct:**
- `<details>` elements work natively, no JS required
- Key sections default to open (Indications, Dosing, Contraindications, Warnings) — appropriate defaults
- Long sections default to collapsed (Adverse Reactions, Clinical Studies) — appropriate
- Boxed warning is always visible (never in a `<details>`) — safety-critical, correct

**Missing interaction patterns:**
- No "expand all / collapse all" toggle for managing 14 sections
- No intra-page table of contents for navigating between sections within a single drug page
- No "back to top" link after long sections
- No print stylesheet (`@media print`)

---

## Files Audited

- `build.py` — Core formatting logic (`format_pi_text` function, lines 41-166; `sanitize_html`, lines 13-38; `format_date`, lines 180-187; main build loop, lines 190-289)
- `templates/drug_detail.html` — Detail page template (105 lines)
- `templates/base.html` — Base layout with CSS variables, dark mode, header/footer (84 lines)
- `templates/index.html` — Index page template (48 lines)
- `site/css/custom.css` — All CSS styles (459 lines)
- `site/js/main.js` — Dark mode toggle + List.js initialization (82 lines)
- `site/drugs/cosentyx-125504.html` — Generated Cosentyx page (representative of PDF artifact problem)
- `site/drugs/keytruda.html` — Generated KEYTRUDA page (representative of very long sections)
- `site/drugs/epkinly.html` — Generated EPKINLY page (representative of numbered-step formatting failure)