# Architecture Research

**Domain:** Static drug approval tracking site for physicians (Python-built, deployed to Synology NAS)
**Researched:** 2026-04-22
**Confidence:** HIGH

## System Overview

```
                         ┌──────────────────────────────┐
                         │        openFDA API            │
                         │  (drugsfda + label endpoints) │
                         └──────────────┬───────────────┘
                                        │ HTTPS GET
                                        ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      DATA PIPELINE (Python)                          │
│                                                                       │
│  ┌─────────────────────┐    ┌──────────────────────────────────────┐ │
│  │  fda_approvals.py   │───▶│  data/approvals.json                 │ │
│  │  ─ Fetches drugsfda │    │  ─ Full drug objects with labels     │ │
│  │  ─ Enriches w/label │    │  ─ Query metadata (date range, type) │ │
│  └─────────────────────┘    └──────────────┬───────────────────────┘ │
│                                            │ read by                   │
│                                            ▼                          │
│                             ┌──────────────────────────────────────┐ │
│                             │  build.py                             │ │
│                             │  ─ Reads data/approvals.json         │ │
│                             │  ─ Renders Jinja2 templates          │ │
│                             │  ─ Writes site/index.html             │ │
│                             │  ─ Writes site/drugs/{slug}.html     │ │
│                             └──────────────┬───────────────────────┘ │
└──────────────────────────────────────────────┼───────────────────────┘
                                               │ writes
                                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     STATIC SITE (site/)                              │
│                                                                       │
│  ┌──────────────────┐  ┌───────────────────────┐  ┌───────────────┐ │
│  │  index.html      │  │  drugs/renflexis.html │  │  drugs/...    │ │
│  │  ─ Sortable table │  │  ─ Full PI sections   │  │  ─ 1 per drug │ │
│  │  ─ Search & filter│ │  ─ Boxed warning       │  │              │ │
│  │  ─ Type badges    │  │  ─ Dosing & admin     │  │              │ │
│  └──────────────────┘  └───────────────────────┘  └──────────────┘ │
│                                                                       │
│  ┌──────────────────┐  ┌───────────────────────────────────────────┐ │
│  │  css/pico.min.css │  │  js/main.js                               │ │
│  │  ─ Pico base      │  │  ─ List.js sort/search init               │ │
│  │  ─ Orchid overrides│ │  ─ Dark mode toggle (+ localStorage)      │ │
│  │  ─ Dark mode vars │  │  ─ Accordion expand/collapse              │ │
│  └──────────────────┘  └───────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
                        │
                        │ git push synology-fda master
                        ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT (Synology NAS)                          │
│                                                                       │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐ │
│  │  Post-receive hook           │  │  nginx serves                 │ │
│  │  ─ checkout to web root     │  │  medupdates.wilmsfamily.com   │ │
│  │  ─ /volume1/web/medupdates/  │  │  /fda/ → static HTML          │ │
│  │    fda/                      │  │                               │ │
│  └──────────────────────────────┘  └──────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────┐
                    │    SYSTEMD TIMER (weekly)     │
                    │  fda-updates.timer            │
                    │  ─ OnCalendar=*-*-* 03:00     │
                    │       America/New_York        │
                    │  ─ Runs: fda-updates.service   │
                    │  ─ ExecStart: pipeline script  │
                    │  ─ Type=oneshot                │
                    └──────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `fda_approvals.py` | Fetch drug approval data from openFDA API; filter for prescription; enrich with full label data | Python 3 script using `urllib` (stdlib). Writes JSON. Already exists and working. |
| `data/approvals.json` | Persistent data store between pipeline runs. Contains all drug objects with labels + query metadata. | JSON file on disk. Read by `build.py`. Replaced weekly. |
| `build.py` | Read JSON data; render Jinja2 templates into static HTML files; write to `site/` directory. | Python 3 script (~150 lines). Uses Jinja2 FileSystemLoader, template inheritance, autoescaping. Creates `index.html` + `drugs/*.html`. |
| `templates/base.html` | Shared layout: `<head>`, Pico CSS import, dark mode toggle, header, footer, nav. | Jinja2 base template with `{% block %}` regions. All pages extend this. |
| `templates/index.html` | Main approval table page with search, sort, filter. | Extends `base.html`. Contains drug table markup, List.js init script, Pico CSS overrides. |
| `templates/drug_detail.html` | Full prescribing information for a single drug. | Extends `base.html`. Sections: boxed warning, indications, dosing, contraindications, warnings, adverse reactions, interactions, populations, MOA. Collapsible `<details>` for long sections. |
| `site/css/pico.min.css` | Base Pico CSS framework (downloaded or CDN). Provides semantic HTML styling, dark mode, responsive tables. | Single CSS file. Unmodified — overrides go in `site/css/custom.css`. |
| `site/css/custom.css` | Orchid & Teal palette overrides, dark mode variables, layout tweaks. | ~30-50 lines of `--pico-*` variable overrides + custom `.badge`, `.warning-box` classes. Loaded after Pico. |
| `site/js/main.js` | Client-side interactivity: List.js init, dark mode toggle, accordion controls. | Vanilla JS (~50-100 lines). No framework dependencies. |
| `systemd/fda-updates.service` | Run the weekly data pipeline. | systemd unit file. `ExecStart` runs `fda_approvals.py` then `build.py` then `git push`. |
| `systemd/fda-updates.timer` | Schedule weekly execution. | systemd timer. Weekly at 03:00 ET. Follows pattern from sibling `medical-updates-codex` project. |

## Recommended Project Structure

```
fda-updates/
├── .gitignore                    # Excludes site/, data/, .skills/, __pycache__
├── AGENTS.md                    # Project context for AI agents
├── fda_approvals.py              # Data pipeline: openFDA API → JSON
├── build.py                      # Build pipeline: JSON + Jinja2 → HTML
├── data/                          # Generated data (gitignored)
│   └── approvals.json             # Current week's drug approval data
├── templates/                     # Jinja2 templates
│   ├── base.html                  # Shared layout (head, nav, footer, CSS, JS)
│   ├── index.html                 # Main sortable table page
│   └── drug_detail.html           # Per-drug prescribing info page
├── systemd/                       # Deployment automation
│   ├── fda-updates.service        # Service unit for weekly pipeline
│   ├── fda-updates.timer          # Timer unit (weekly schedule)
│   └── install_systemd_user.sh    # Install timer for user-level systemd
site/                              # Built output (separate git repo, gitignored from main)
│   ├── .git/                      # Separate repo: remote = synology-fda
│   ├── index.html                 # Generated main page
│   ├── drugs/                     # Generated detail pages
│   │   ├── dupixent.html
│   │   ├── renflexis.html
│   │   └── ...
│   ├── css/
│   │   ├── pico.min.css           # Pico CSS (downloaded, not CDN)
│   │   └── custom.css             # Orchid & Teal overrides
│   └── js/
│       ├── list.min.js            # List.js (downloaded, not CDN)
│       └── main.js                # Custom interactivity
```

### Structure Rationale

- **`fda_approvals.py` in root**: Already exists there. It's the single entry point for data fetching. Touch it only to extend (add SUPPL support), don't restructure.
- **`build.py` in root**: Parallel to `fda_approvals.py`. Both are top-level scripts invoked by systemd. No package structure needed — this is two scripts, not a framework.
- **`data/`**: Generated JSON output. Gitignored from main repo. Created by `fda_approvals.py`, consumed by `build.py`. This is the data contract between the two scripts.
- **`templates/`**: Jinja2 templates. The `base.html` template establishes the shared layout; `index.html` and `drug_detail.html` extend it. Template inheritance is the right pattern here — three templates with shared chrome (header, footer, CSS, dark mode toggle).
- **`site/`**: Separate git repo with its own remote. This is the deployment artifact. `build.py` writes all generated HTML here. The post-receive hook on the Synology deploys from this repo.
- **`site/css/` and `site/js/`**: Static assets. Pico CSS and List.js are downloaded (not CDN) so the site works on the LAN without internet access. `custom.css` and `main.js` are the project's own code.
- **`systemd/`**: Timer and service unit files, following the exact pattern from the sibling `medical-updates-codex` project.

## Architectural Patterns

### Pattern 1: Two-Script Pipeline (Fetch → Build)

**What:** The data pipeline and build pipeline are separate Python scripts connected by a JSON file on disk.

**When to use:** Always — this is the core architecture.

**Trade-offs:**
- ✅ Simple to understand and debug. Each script does one thing.
- ✅ Can run `fda_approvals.py` without rebuilding (data refresh only).
- ✅ Can run `build.py` without re-fetching (template iteration during dev).
- ✅ JSON on disk is inspectable — check data without running code.
- ⚠️ Two scripts means two places for errors. The data contract (JSON schema) must be stable.

**Example:**
```bash
# Weekly cron runs both:
python3 fda_approvals.py --from 2024-04-22 --to 2026-04-22 -o data/approvals.json
python3 build.py  # reads data/approvals.json, writes site/*.html
cd site/ && git add . && git commit -m "weekly update" && git push synology-fda master
```

### Pattern 2: Jinja2 Template Inheritance

**What:** `base.html` defines the shared layout (header, footer, CSS imports, dark mode toggle). `index.html` and `drug_detail.html` extend it with `{% extends "base.html" %}` and `{% block content %}`.

**When to use:** For all page types — there are only two (table and detail).

**Trade-offs:**
- ✅ DRY: shared nav, footer, theme toggle written once.
- ✅ Change one file (base.html) to update all pages.
- ✅ Jinja2's autoescaping prevents XSS from drug label HTML.
- ⚠️ Three templates is the right number. Don't over-abstract. If a "third page type" appears, add a third template — don't create a template engine within the template engine.

**Example:**
```python
# build.py
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# Index page
index_template = env.get_template("index.html")
index_html = index_template.render(
    drugs=drugs,
    last_updated=build_timestamp,
)

# Detail pages — one per drug
detail_template = env.get_template("drug_detail.html")
for drug in drugs:
    slug = slugify(drug["brand_name"] or drug["generic_name"])
    detail_html = detail_template.render(drug=drug)
    write_file(f"site/drugs/{slug}.html", detail_html)
```

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}FDA Drug Approvals{% endblock %}</title>
    <link rel="stylesheet" href="css/pico.min.css">
    <link rel="stylesheet" href="css/custom.css">
</head>
<body>
    <header>...</header>
    <main>{% block content %}{% endblock %}</main>
    <footer>...</footer>
    <script src="js/list.min.js"></script>
    <script src="js/main.js"></script>
</body>
</html>
```

### Pattern 3: JSON as Data Contract

**What:** `fda_approvals.py` writes a specific JSON schema to `data/approvals.json`. `build.py` reads this schema and renders it into HTML.

**When to use:** Always — this is how data flows from pipeline to site.

**Trade-offs:**
- ✅ Decouples fetching from rendering. Change templates without touching the data pipeline.
- ✅ Inspectable: you can read `approvals.json` to verify data before building.
- ✅ Replayable: re-run `build.py` to iterate on templates without burning API calls.
- ⚠️ The JSON schema is the contract. If `fda_approvals.py` changes the schema, `build.py` must match. Document the schema explicitly.

**Example schema** (what `build.py` expects):
```json
{
  "query": {
    "date_from": "2024-04-22",
    "date_to": "2026-04-22",
    "submission_type_filter": "all"
  },
  "count": 42,
  "drugs": [
    {
      "brand_name": "DUPIXENT",
      "generic_name": "dupilumab",
      "all_brand_names": ["DUPIXENT"],
      "all_generic_names": ["dupilumab"],
      "approval_date": "2026-04-17",
      "application_number": "BLA761055",
      "submission_class": "Type 1 - New Molecular Entity",
      "review_priority": "PRIORITY",
      "sponsor_name": "sanofi-aventis U.S. LLC",
      "manufacturer_name": ["sanofi-aventis U.S. LLC"],
      "route": ["SUBCUTANEOUS"],
      "pharm_class_epc": ["Interleukin-4 Receptor alpha Antagonist [EPC]"],
      "pharm_class_moa": ["Interleukin-4 Receptor alpha Antagonist [MOA]"],
      "products": [...],
      "rxcui": [...],
      "unii": [...],
      "label": {
        "indications_and_usage": "...",
        "boxed_warning": "...",
        "dosage_and_administration": "...",
        "contraindications": "...",
        "warnings_and_cautions": "...",
        "adverse_reactions": "...",
        "drug_interactions": "...",
        "use_in_specific_populations": "...",
        "mechanism_of_action": "...",
        "dosage_forms_and_strengths": "..."
      }
    }
  ]
}
```

### Pattern 4: Static-First, Enhance with JS

**What:** The site works as pure HTML. JavaScript adds sorting, search, dark mode toggle, and accordion behavior on top of already-rendered content.

**When to use:** Always — this is the entire frontend architecture.

**Trade-offs:**
- ✅ Works without JavaScript (search/sort won't work, but table content is visible).
- ✅ Fast: no hydration, no client-side rendering. HTML arrives fully formed.
- ✅ SEO-friendly (though not critical for a LAN site on a NAS).
- ✅ CDN-optional: download Pico and List.js to `site/` for offline LAN use.
- ⚠️ Must ensure progressive enhancement: the table must be semantically complete HTML before List.js attaches.

**Example:**
```html
<!-- index.html — table works without JS, List.js enhances -->
<div id="drug-table">
    <input class="search" placeholder="Search by drug name..." />
    <table class="list">
        <thead>
            <tr>
                <th class="sort" data-sort="date">Approval Date</th>
                <th class="sort" data-sort="type">Type</th>
                <th class="sort" data-sort="name">Brand Name</th>
                <th class="sort" data-sort="generic">Generic Name</th>
                <th class="sort" data-sort="category">Category</th>
                <th>Indication</th>
            </tr>
        </thead>
        <tbody class="list">
            {% for drug in drugs %}
            <tr>
                <td class="date">{{ drug.approval_date }}</td>
                <td class="type">{{ drug.type_badge }}</td>
                <td class="name"><a href="drugs/{{ drug.slug }}.html">{{ drug.brand_name }}</a></td>
                <td class="generic">{{ drug.generic_name }}</td>
                <td class="category">{{ drug.category }}</td>
                <td>{{ drug.indication_preview }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
<script>
    // Progressive enhancement: List.js adds sort/search on top of rendered HTML
    new List('drug-table', {
        valueNames: ['date', 'type', 'name', 'generic', 'category'],
        searchClass: 'search',
        sortClass: 'sort'
    });
</script>
```

### Pattern 5: Two-Repo Deployment

**What:** Main repo (`github.com/cmd-christopher/fda-updates`) tracks source code. `site/` is a separate git repo (`synology-fda` remote) that tracks only built output. The Synology post-receive hook auto-deploys `site/` to the web root.

**When to use:** Always — this is how deployment works.

**Trade-offs:**
- ✅ Clean separation: source code in main repo, deployable output in `site/` repo.
- ✅ The Synology only needs git, not Python or Jinja2 — it serves static files.
- ✅ Rollback = `git revert` in `site/` and push.
- ⚠️ Two repos means two commit histories. The weekly cron commits built output with timestamp messages. That's fine — `site/` history is deployment history, not development history.
- ⚠️ Never manually edit files in `site/` — they're always overwritten by `build.py`. If you need to change HTML, change the template and rebuild.

## Data Flow

### Weekly Pipeline Flow

```
systemd timer (weekly, 03:00 ET)
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 1: Fetch data from openFDA        │
│                                         │
│  fda_approvals.py                       │
│  ├─ Query drugsfda for ORIG approvals   │
│  │  in date range (2 years)             │
│  ├─ Filter for prescription-only drugs  │
│  ├─ Query drugsfda for SUPPL            │
│  │  approvals with efficacy class       │
│  │  (NEW INDICATIONS — to be added)     │
│  ├─ For each drug, fetch label data     │
│  │  (0.5s delay between requests)       │
│  └─ Write data/approvals.json           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Step 2: Build static site               │
│                                         │
│  build.py                               │
│  ├─ Read data/approvals.json            │
│  ├─ Compute derived fields:             │
│  │  • slug (URL-safe drug name)         │
│  │  • type_badge ("New Drug" /          │
│  │    "New Indication")                 │
│  │  • indication_preview (truncated)    │
│  │  • category (pharm_class_epc first)  │
│  ├─ Render index.html (full table)      │
│  ├─ Render drugs/{slug}.html per drug  │
│  ├─ Embed build timestamp in pages      │
│  └─ Write all files to site/            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Step 3: Deploy to Synology              │
│                                         │
│  cd site/                               │
│  git add .                              │
│  git commit -m "weekly update [date]"    │
│  git push synology-fda master           │
│                                         │
│  ┌───────────────────────────────┐      │
│  │  Synology post-receive hook   │      │
│  │  git checkout -f →             │      │
│  │  /volume1/web/medupdates/fda/  │      │
│  └───────────────────────────────┘      │
└─────────────────────────────────────────┘
```

### Browser Data Flow

```
Physician opens medupdates.wilmsfamily.com/fda/
    │
    ▼
nginx serves site/index.html (static file, no server processing)
    │
    ▼
Browser renders HTML table (Pico CSS styles, semantic elements)
    │
    ▼
List.js initializes (sort, search, filter on existing DOM)
    │
    ├── Physician clicks a drug row
    │       │
    │       ▼
    │   Browser navigates to drugs/dupilumab.html
    │       │
    │       ▼
    │   nginx serves static detail page
    │       │
    │       ▼
    │   Browser renders full PI with collapsible sections
    │
    └── Physician uses search/sort/filter
            │
            ▼
        List.js filters DOM in-place (no server round-trip)
            │
            ▼
        Table updates instantly
```

### Key Data Flows

1. **API → JSON:** `fda_approvals.py` queries openFDA `drugsfda` endpoint, fetches matching drugs, then for each drug queries the `label` endpoint. Each drug record is enriched with its full label data. The result is written as a single JSON file containing all drugs and their labels.

2. **JSON → HTML:** `build.py` reads the JSON, computes derived fields (slug for URLs, truncated indication previews, type badges), and renders Jinja2 templates. Each drug gets its own detail page. The index page contains the full table data inline (no AJAX needed — the data is static and ~50-200 items).

3. **HTML → Browser:** Static files served by nginx. No server-side processing. List.js provides client-side interactivity (sort, search). Dark mode toggle writes to `localStorage` and sets `data-theme` on `<html>` — no server round-trip.

4. **Weekly → Live:** The systemd timer triggers the pipeline. The entire build takes seconds (fetch ~200 drugs with labels = ~3-4 minutes at 0.5s delay; build = <1 second; git push = <1 second). The data on the site is at most 7 days stale, which is appropriate for approval tracking — approvals don't change retroactively.

### Slug Generation Strategy

Drug detail page URLs must be stable, unique, and human-readable.

```python
import re
from unicodedata import normalize

def slugify(name):
    """Generate URL-safe slug from drug name."""
    slug = name.lower().strip()
    slug = normalize('NFKD', slug).encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')
    return slug
```

**Collision handling:** If two drugs slugify to the same string (rare but possible — e.g., same brand name for different NDAs), append the application number: `{slug}-{app_num_suffix}.html`. The `build.py` script must check for uniqueness.

**Rejection of alternatives:**
- Using `application_number` as URL (e.g., `/drugs/NDA123456.html`) — unrecognizable to physicians, not bookmarkable by drug name.
- Using IDs (e.g., `/drugs/42.html`) — worse than app numbers for no benefit.
- slugify is the standard pattern and produces readable URLs like `/drugs/dupilumab.html`.

## Scalability Considerations

| Concern | At ~50 drugs (current) | At ~200 drugs (2 years) | At ~1000+ drugs |
|---------|------------------------|------------------------|------------------|
| Index page HTML size | ~30KB — instant load | ~120KB — still fast, gzipped to ~20KB | ~600KB — needs pagination or lazy rendering |
| Number of detail pages | 50 files | 200 files | 1000+ files — manageable on NAS |
| API fetch time | ~1 minute (0.5s × ~50 labels + ~50 drugs) | ~3-4 minutes | ~8-10 minutes — still fine for weekly |
| Build time | <1 second | ~1-2 seconds | ~5-10 seconds — still fine |
| List.js performance | Instant (50 rows) | Fast (200 rows) | Slower (1000 rows) — consider pagination or MiniSearch |

### Scaling Priorities

1. **First bottleneck (~200+ drugs): Index page size.** A single HTML table with 200+ rows including truncated indications becomes a large page. Solution: Jinja2 pagination — generate `index.html` (latest 100) + `page/2.html`, etc. List.js paginates client-side with its built-in pagination plugin.

2. **Second bottleneck (~500+ drugs): API fetch time.** Each drug requires a separate label request. At 500 drugs, that's ~4 minutes of API calls. Solutions: (a) fetch only drugs approved in the date range (already done), (b) consider an API key for higher rate limits (240/min → unrestricted), (c) cache label data incrementally — only fetch labels for newly approved drugs, reuse cached labels for existing drugs.

3. **Not a bottleneck: static file serving.** nginx serving static HTML on a NAS handles this trivially. No concern at any projected scale.

## Anti-Patterns

### Anti-Pattern 1: Client-Side Data Fetching from openFDA

**What people do:** Write JavaScript in the browser that calls `api.fda.gov` directly to display drug data.
**Why it's wrong:** Exposes the API key (if you get one) to the public, depends on openFDA's uptime for site availability, adds 2-5 seconds of latency per page load, hits rate limits (240/min without key), and makes the site completely dependent on a third-party service for every single visit.
**Do this instead:** Weekly cron fetches data, builds static pages. The site works even if openFDA is down. Physicians get sub-100ms page loads.

### Anti-Pattern 2: Single-Page Application Architecture

**What people do:** Build a React/Vue/Svelte app with client-side routing, where clicking a drug loads data dynamically.
**Why it's wrong:** For a site with two page types (index + detail), an SPA adds build complexity, larger bundles, worse SEO (irrelevant on LAN but still), slower initial load, and framework lock-in — all for zero user benefit. Physicians click a link and get a fully rendered page instantly. An SPA would make the same click wait for JS hydration + data fetch.
**Do this instead:** Static HTML pages per drug (`drugs/dupilumab.html`). Click = instant navigation. No framework needed.

### Anti-Pattern 3: Embedding Raw Label HTML Without Sanitization

**What people do:** Inject the `indications_and_usage` HTML from the label endpoint directly into the page with `{{ drug.label.indications_and_usage | safe }}`.
**Why it's wrong:** openFDA label data contains HTML tables, line breaks, and formatting tags — but it's still user-provided content (from drug manufacturers). While it's FDA-curated, it can contain malformed HTML that breaks page layout or, in worst cases, script injection. Jinja2's autoescaping exists specifically to prevent this.
**Do this instead:** Use Jinja2's autoescaping (enabled via `select_autoescape`). For label sections that contain safe structural HTML (tables, paragraphs), use `Markup()` to explicitly mark trusted content while still escaping dangerous content. The label data is FDA-structured HTML, not arbitrary user input — but still apply `bleach` or a whitelist approach if concerned.

### Anti-Pattern 4: Building the Entire Site on Every Page Visit

**What people do:** Use a server-side framework (Flask, Django) that renders pages on each request.
**Why it's wrong:** Requires a running server process on the Synology NAS, adds Python web server dependency, consumes resources on the NAS, and adds latency to each request. The site changes once per week — there's no reason to rebuild it for every visitor.
**Do this instead:** Build once per week, serve static files. The Synology already runs nginx for web serving. Adding a Python web server for a weekly-updated site is unnecessary complexity.

### Anti-Pattern 5: Over-Abstracting the Build System

**What people do:** Create a plugin system, configurable themes, or a generic static site generator when there are only two page types.
**Why it's wrong:** Two templates (index + detail) do not need an abstraction layer. An `AbstractPageBuilder` with `SiteGenerator` and `TemplateEngine` factories adds complexity without benefit. YAGNI.
**Do this instead:** A flat `build.py` script that reads JSON, loads templates, renders HTML, and writes files. ~150 lines. No classes needed. If a third page type is needed, add a third template and a third render call in `build.py`. When you have five page types, consider extracting a helper function. When you have ten, consider a simple data-driven template mapper. Never build a plugin system for a two-page site.

### Anti-Pattern 6: Mixing Data Concerns into Templates

**What people do:** Put truncation logic, URL generation, and type classification directly in Jinja2 templates with complex `{% if %}` and `{% set %}` blocks.
**Why it's wrong:** Templates become hard to test and debug. Business logic (how to truncate an indication, what makes a "New Drug" badge) should live in Python where it's unit-testable.
**Do this instead:** Compute all derived fields in `build.py` before passing to templates. Templates receive `drug.type_badge`, `drug.indication_preview`, and `drug.slug` — pre-computed strings. Templates only do formatting and HTML structure, never data transformation.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| openFDA drugsfda API | HTTP GET from `fda_approvals.py`, 0.5s rate limiting, pagination support | Rate limit: 240 req/min without API key (40 req/min without). Current script handles this. Adding SUPPL queries doubles API calls. |
| openFDA label API | HTTP GET per drug, queried by `application_number`, 0.5s delay | No date search on label endpoint — always query by app number from drugsfda results. Returns 404 for some drugs (no label available). |
| Synology nginx | Static file serving from `/volume1/web/medupdates/fda/` | Already configured. Post-receive hook handles deployment. |
| CDN (Pico CSS, List.js) | Download CSS/JS to `site/css/` and `site/js/` during build | Don't use CDN <link> — the site must work on LAN without internet. Download assets at build time. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `fda_approvals.py` → `data/approvals.json` | File write (JSON) | The JSON schema is the data contract. Changes to the schema must be backward-compatible or both scripts must be updated simultaneously. |
| `data/approvals.json` → `build.py` | File read (JSON) | `build.py` reads the JSON and renders templates. If JSON is missing or malformed, `build.py` should fail with a clear error, not produce partial output. |
| `build.py` → `site/` | File write (HTML, CSS, JS) | All files in `site/` are generated. Never edit `site/` files directly — they will be overwritten on next build. |
| `site/` git repo → Synology | `git push synology-fda master` | Post-receive hook on Synology checks out to web root. This is the deployment mechanism. |
| `systemd timer` → full pipeline | Process execution (bash script or direct commands) | Timer triggers `fda_approvals.py` then `build.py` then `git push`. If any step fails, the pipeline stops and the old site remains live. |

### Data Contract: JSON Schema for `approvals.json`

The JSON written by `fda_approvals.py` and read by `build.py` must follow this contract. `build.py` should document the fields it requires:

```python
# build.py expects each drug object to have these fields:
REQUIRED_FIELDS = {
    "brand_name": str | None,          # Primary brand name
    "generic_name": str | None,         # Primary generic name
    "approval_date": str,               # ISO date "YYYY-MM-DD"
    "application_number": str,          # e.g., "NDA123456" or "BLA761055"
    "submission_class": str,            # e.g., "Type 1 - New Molecular Entity"
    "sponsor_name": str,                # e.g., "sanofi-aventis U.S. LLC"
    "pharm_class_epc": list[str],       # e.g., ["Interleukin-4 Receptor alpha Antagonist [EPC]"]
    "pharm_class_moa": list[str],       # Mechanism of action classes
    "route": list[str],                  # e.g., ["SUBCUTANEOUS"]
    "products": list,                   # Prescription products with dosage forms
    "label": dict | None,              # Label data (may be None for 404s)
}
```

`build.py` should validate this on read and exit with an error if required fields are missing, rather than producing broken pages.

## Build Order (Suggested Phase Sequence)

Based on the architectural dependencies and the principle of "ship something that works as early as possible":

| Build Order | Component | Depends On | Rationale |
|-------------|-----------|------------|-----------|
| 1 | `fda_approvals.py` SUPPL extension | Existing script | Must add new indication data before any meaningful site can be built. Without type differentiation, the site is undifferentiated. |
| 2 | `data/` JSON contract | Step 1 | Define and document the JSON schema that `build.py` will consume. Both scripts must agree on field names. |
| 3 | `templates/base.html` + `site/css/custom.css` | Nothing (can start early) | The shared layout, Pico CSS overrides for Orchid & Teal, and dark mode toggle. Can be built with static mock data while the SUPPL extension is in progress. |
| 4 | `templates/index.html` (table only) | Steps 2, 3 | The sortable table with drug data. This is the MVP page. Build it with List.js. |
| 5 | `build.py` (minimal) | Steps 2, 3, 4 | Renders `base.html` + `index.html`. Initially just writes `site/index.html` with the drug table. No detail pages yet. |
| 6 | `templates/drug_detail.html` | Steps 2, 3 | The full PI page with collapsible sections, boxed warning callout, and section navigation. |
| 7 | `build.py` (full) | Steps 2, 6 | Extends `build.py` to also generate `drugs/*.html` per drug. Computes slugs, truncation, type badges. |
| 8 | `site/js/main.js` | Steps 4, 6 | List.js init, dark mode toggle, accordion behavior for detail pages. |
| 9 | `systemd/fda-updates.{service,timer}` | Steps 5, 7 | Weekly automation. Test the full pipeline end-to-end first. Install timer last. |

**Why this order:**
- Steps 3 and 4 can overlap with Step 1 (design templates with mock data while the SUPPL extension is being built).
- The JSON contract (Step 2) is the keystone — both scripts must agree on it. Define it explicitly before building `build.py`.
- The systemd timer is last because there's no point automating a pipeline that hasn't been tested manually.
- Each step produces a functional checkpoint: Step 5 gives you a table you can see in a browser. Step 7 gives you full detail pages. Step 9 gives you automation.

## Sources

- **openFDA API documentation** (api.fda.gov) — Endpoint structure, rate limits, date formats, drugsfda vs label. Verified in existing `fda_approvals.py` and `SKILL.md`. (HIGH confidence)
- **Jinja2 documentation** via Context7 (`/pallets/jinja`) — FileSystemLoader, template inheritance, autoescaping, block system. (HIGH confidence)
- **Pico CSS documentation** via Context7 (`/websites/picocss`) — Dark mode `data-theme` attribute, `--pico-*` CSS variable system, semantic table styling. (HIGH confidence)
- **medupdates.wilmsfamily.com** — Analyzed directly. Confirmed Orchid & Teal palette, CSS variable system, dark mode implementation, card/typography patterns. (HIGH confidence — direct observation of sibling project)
- **medical-updates-codex-standalone** — Analyzed project structure. Confirmed systemd timer pattern, build script pattern, separate git repos for source vs output. (HIGH confidence — sibling project)
- **List.js v2.3.1** — Client-side table sorting and search. Verified on listjs.com. 13KB minified, zero dependencies, works on existing HTML tables. (MEDIUM confidence — verified on official site, not Context7)
- **openFDA skill** (`SKILL.md`) — Endpoint structure, fields, submission types (ORIG, SUPPL), marketing status codes, label section names. (HIGH confidence)

---
*Architecture research for: FDA Drug Approval Updates static site*
*Researched: 2026-04-22*