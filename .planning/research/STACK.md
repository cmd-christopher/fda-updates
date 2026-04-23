# Stack Research

**Domain:** Static medical information site (FDA drug approvals)
**Researched:** 2026-04-22
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python 3 + Jinja2 | 3.1.6 | Build engine: JSON → HTML | Data pipeline is already Python (`fda_approvals.py`). Jinja2 is the standard Python templating engine with template inheritance, filters, and autoescaping. Adds zero new language to the project — the weekly cron already runs Python. |
| Pico CSS | 2.0.x | CSS framework (semantic, classless) | Built-in dark mode via `data-theme` attribute and `prefers-color-scheme`. Full CSS variable system (`--pico-*`) for custom palettes — maps directly to Orchid & Teal. Semantic HTML means `<table>` renders beautifully with zero classes. Single CSS file, no build step. CDN-deliverable. |
| List.js | 2.3.1 | Client-side table sorting & search | Framework-free, 13KB minified, works on existing HTML tables. Provides search, sort, and filter on the drug approvals table without React/Vue. Initialize on an existing `<table class="list">` — perfect for server-rendered HTML. CDN-deliverable. |
| Vanilla JS (ES2020+) | N/A | Detail page interactivity | No framework needed. Accordion/expand for label sections, copy-to-clipboard for drug names, theme toggle. Write 50-100 lines of progressive enhancement. |
| systemd timer | N/A | Weekly data refresh | Already part of the deployment plan. Runs `fda_approvals.py` + `build.py` on schedule. No new infra. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Jinja2 | 3.1.6 | Template rendering (extend/filter HTML generation) | Build phase: turns JSON output into index.html + N drug detail pages |
| MarkupSafe | 3.0.3 | Autoescaping for Jinja2 (pre-installed with Jinja2) | Always — prevents XSS in drug label text |
| PyYAML | 6.0.3 | Parse YAML front matter or config if needed | Optional — if site config moves to YAML. Already installed. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `build.py` | One-command build: fetch data → render HTML → write `site/` | Replaces any SSG. ~150 lines of Python. Template inheritance keeps it DRY. |
| Python `http.server` | Local dev server (`python3 -m http.server`) | For previewing built output. No Webpack/Vite needed — this is static HTML. |
| Git (Synology post-receive hook) | Deployment | Already configured. `git push synology-fda master` → live. |

## Why This Stack (Decision Rationale)

### Why Jinja2 (Python) instead of Eleventy (Node.js)

The entire data pipeline is Python. `fda_approvals.py` writes JSON. Adding a Node.js SSG means:

1. **Two runtime languages** for a static site. Python writes JSON, Node reads JSON and templates it. Each weekly cron now requires `node` installed on the Synology.
2. **NPM dependency tree.** Eleventy + plugins = `node_modules/` for a site with ~2 pages types (index + detail).
3. **Config complexity.** Eleventy needs `eleventy.config.js`, data files in `_data/`, template format decisions (Nunjucks vs Liquid). Jinja2 needs a `templates/` directory and a 50-line build script.

With Jinja2, the build is:

```bash
python3 fda_approvals.py --from 2024-04-22 --to 2026-04-22 -o data/approvals.json
python3 build.py  # reads data/*.json, writes site/*.html
cd site/ && git add . && git commit -m "update" && git push synology-fda master
```

Three commands, one runtime, zero `node_modules`.

**When Eleventy would be better:** If this project were a blog with hundreds of markdown content files, or if the team were JavaScript-native and maintaining Python was a burden. Neither applies here.

### Why Pico CSS instead of Tailwind CSS

| Criterion | Pico CSS | Tailwind CSS |
|-----------|----------|-------------|
| Bundle size | ~15KB gzipped (single file) | ~30KB+ gzipped (purged) or 350KB+ unpurged |
| Build step required | No | Yes (PostCSS, purge config) |
| Dark mode | Built-in via `data-theme="dark"` and `prefers-color-scheme` | Requires `darkMode` config + `dark:` prefix on every class |
| Custom palette | Override `--pico-*` CSS variables (30 lines) | Configure `tailwind.config.js` (50+ lines) |
| Table styling | Automatic — `<table>` looks great | Must add classes to every `<td>`, `<th>`, `<tr>` |
| Semantic HTML | Full support — no classes needed | Requires `<div class="grid grid-cols-4 ...">` style markup |

This site is 90% tabular data and medical text. Pico excels at exactly this: content-heavy sites with tables, forms, and typography. Tailwind excels at component-heavy application UIs.

**The Orchid & Teal palette maps directly to Pico's variable system:**

```css
/* Orchid = primary, Teal = accent */
[data-theme="light"],
:root:not([data-theme="dark"]) {
  --pico-primary: #8B5CF6;           /* Orchid */
  --pico-primary-background: #7C3AED;
  --pico-primary-hover: #A78BFA;
  --pico-primary-hover-background: #8B5CF6;
  --pico-primary-focus: rgba(139, 92, 246, 0.375);
}

[data-theme="dark"] {
  --pico-primary: #A78BFA;           /* Lighter orchid for dark bg */
  --pico-primary-background: #7C3AED;
  --pico-primary-hover: #C4B5FD;
  --pico-primary-focus: rgba(167, 139, 250, 0.375);
  --pico-accent: #2DD4BF;           /* Teal accent */
}
```

No build pipeline. No PostCSS. No purge. Write CSS variables, ship.

### Why List.js instead of writing custom sort

The index page has one interactive element: a sortable, searchable table of ~100-200 drug approvals. List.js:

- Works on existing HTML (no virtual DOM, no hydration)
- Provides search + sort + pagination out of the box
- 13KB minified, zero dependencies
- Initialize with `new List('drug-table', { valueNames: ['name', 'date', 'type'] })`

Writing custom sort for `<table>` takes ~80 lines and handles edge cases poorly (date sorting, string vs numeric). List.js solves it in 3 lines.

**When to go custom:** If the table needs real-time API filtering, infinite scroll, or virtual scrolling for 10K+ rows. This project has ~200 rows at most — List.js is fine.

### Why no build step

| Need | Solution |
|------|----------|
| Compile templates | Jinja2 (Python runtime, no Webpack) |
| CSS processing | Pico CSS + hand-written overrides (no PostCSS) |
| JS bundling | List.js via CDN + ~100 lines inline `<script>` (no Rollup) |
| Minification | Not needed — site is ~50KB total. Synology serves gzipped. |
| Hot reload | Python `http.server` + `watchfiles` or manual refresh |

The entire site is under 50KB. There is no performance reason for a build pipeline. The Jinja2 build script runs in under 1 second.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Jinja2 (Python) | Eleventy (Node.js) | If team is JS-only and refuses Python; or if the site grows to hundreds of markdown content files where Eleventy's collection system shines |
| Jinja2 (Python) | Hand-written HTML | If there are only 1-2 drugs and updates are rare. Not viable for ~200 drugs with weekly updates. |
| Pico CSS | Tailwind CSS | If the site evolves into a complex web app with dozens of custom components. For a data table site, Pico is superior. |
| Pico CSS | Open Props + normalize.css | If you want more granular utility classes without Tailwind's build step. Open Props is excellent but lacks Pico's automatic component styling. |
| Pico CSS | Hand-written CSS | If you want absolute pixel control and are willing to write 500+ lines of CSS for tables, forms, typography, and dark mode. Pico saves this effort. |
| List.js | Custom vanilla JS sort | If you need only single-column sort with no search. The moment you want search + multi-column sort, List.js is less code. |
| List.js | SortableJS | If you need drag-and-drop row reordering (admin UI). Not needed for a read-only physician-facing table. |
| List.js | TanStack Table | If using React/Vue. Overkill for vanilla JS — requires a framework. |
| CDN delivery | npm + bundler | If you need tree-shaking or offline development. CDN is simpler and the site has only 2 JS dependencies. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| React / Vue / Svelte | Adds build complexity, bundle size, and framework lock-in for a static content site with one interactive table. | List.js (2.3.1) + vanilla JS |
| Tailwind CSS | Requires PostCSS, purge config, and class-heavy markup. Medical data tables become verbose (`<td class="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">`). Pico's semantic styling is a better fit. | Pico CSS (2.0.x) with `--pico-*` variable overrides |
| Eleventy | Adds Node.js as a required runtime on the Synology. Data pipeline is already Python — Jinja2 keeps everything in one language. | Jinja2 (3.1.6) build script |
| Webpack / Vite / Rollup | Build tools designed for applications with module graphs and code-splitting. This site has ~2 JS files. No JSX, no TypeScript, no code splitting. | No bundler. CDN + inline scripts. |
| Sass / SCSS | Requires a CSS build step. Pico's variable system does everything Sass would do (variables, nesting is in native CSS now). For 30 lines of overrides, Sass is overhead. | Native CSS with `--pico-*` variables |
| htmx | For partial page updates from the server. This is a static site with no backend — htmx adds nothing. | Static HTML generation at build time |
| Next.js / Astro / SvelteKit | Full application frameworks. A 2-page-type static site doesn't need SSR, routing, or hydration. | Jinja2 static generation |

## Stack Patterns by Variant

**If the site grows to 500+ drugs with complex search:**
- Replace List.js with a client-side search library like MiniSearch (3KB) for full-text search of drug names and indications
- Keep everything else the same
- Jinja2 templates handle pagination by generating paginated index pages (`/page/2/`, etc.)

**If real-time FDA updates are needed (sub-hour freshness):**
- Add a lightweight cron entry that pulls the openFDA API more frequently
- The build script can run incrementally (only rebuild changed drug pages)
- Still no framework — just more frequent builds

**If the site needs client-side routing between drug pages:**
- Don't. Generate static HTML pages per drug (`/drugs/drug-name.html`). Search engines index them. Physicians bookmark them. No SPA routing needed.

**If dark mode toggle must persist across pages:**
- Use `localStorage` + `data-theme` attribute on `<html>`. ~20 lines of vanilla JS. Pico CSS honors `data-theme` natively.

**If physicians request accessible drug comparison:**
- Add a "compare" selection mode (checkboxes on the table, comparison overlay). Pure vanilla JS. No framework needed.

## Version Compatibility

| Package | Compatible With | Notes |
|---------|----------------|-------|
| Python 3.12+ | Jinja2 3.1.6 | Jinja2 3.1.x requires Python 3.7+;MarkupSafe 3.0.x requires Python 3.9+ |
| Jinja2 3.1.6 | MarkupSafe 3.0.3 | Auto-installed as Jinja2 dependency |
| Pico CSS 2.0.x | All modern browsers | IE not supported (irrelevant for physician audience) |
| List.js 2.3.1 | All modern browsers | No IE; requires ES5+ (every browser since 2009) |
| systemd timer | Linux (Synology DSM) | Synology uses systemd-compatible task scheduler. Use `synoservice` or cron if systemd unavailable. |

## Build & Deploy Architecture

```
Weekly cron/systemd timer
         │
         ▼
┌─────────────────────┐
│  fda_approvals.py   │  ← Fetches from openFDA API
│  (Python, existing)  │
└────────┬────────────┘
         │ writes data/approvals.json
         ▼
┌─────────────────────┐
│  build.py            │  ← Jinja2 templates + JSON → HTML
│  (Python, new)       │
└────────┬────────────┘
         │ writes site/index.html
         │ writes site/drugs/*.html
         ▼
┌─────────────────────┐
│  git push → Synology │  ← Existing post-receive hook auto-deploys
└─────────────────────┘
```

**No Node.js involved at any stage.** The Synology only needs Python 3 for the cron job.

## Installation

```bash
# Core (Python — already has Python 3.12+, Jinja2 now installed)
pip3 install --user jinja2   # Includes MarkupSafe

# No npm install needed — Pico CSS and List.js load from CDN
# For offline development, download them:
mkdir -p site/css site/js
curl -o site/css/pico.min.css https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css
curl -o site/js/list.min.js https://cdn.jsdelivr.net/npm/list.js@2.3.1/dist/list.min.js
```

## Sources

- Context7 `/pallets/jinja` — Jinja2 templating, FileSystemLoader, autoescaping, template inheritance (HIGH confidence)
- Context7 `/websites/picocss` — Pico CSS 2.0 dark mode variables, `data-theme` attribute, `--pico-*` customization system (HIGH confidence)
- Context7 `/11ty/eleventy` — Eleventy data pipeline, global data, pagination, configuration (HIGH confidence)
- List.js official site (listjs.com) — v2.3.1 features, table example, CDN availability (MEDIUM confidence — verified on official site)
- Python 3.12+ standard library — `http.server`, `json`, `argparse` (HIGH confidence)
- openFDA API (api.fda.gov) — Existing `fda_approvals.py` already handles this (HIGH confidence)

---
*Stack research for: FDA Drug Approval Updates static site*
*Researched: 2026-04-22*