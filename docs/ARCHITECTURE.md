<!-- generated-by: gsd-doc-writer -->

# Architecture

## System Overview

FDA Drug Approval Updates is a batch-oriented data pipeline that fetches prescription drug approval data from the openFDA API, enriches it with full prescribing information, and publishes a static website to a Synology NAS. The system follows a three-stage architecture: **fetch** (openFDA API → JSON), **build** (JSON → static HTML via Jinja2 templates), and **deploy** (git push → NAS post-receive hook). A systemd timer automates the pipeline on a weekly schedule, and Pushover notifications alert on failures.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    systemd timer                            │
│            (Mon 03:00 ET, fda-pipeline.timer)              │
└──────────────────────┬──────────────────────────────────────┘
                       │ triggers
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              run_fda_pipeline.sh                             │
│         Orchestrates the 3-step pipeline                     │
│         Sends Pushover alerts on failure                     │
└──┬─────────────────────┬──────────────────────┬─────────────┘
   │                     │                      │
   ▼                     ▼                      ▼
┌──────────┐      ┌──────────┐          ┌──────────────────┐
│  Step 1  │      │  Step 2  │          │     Step 3       │
│  Fetch   │─────▶│  Build   │─────────▶│     Deploy       │
│          │      │          │          │                  │
│ fda_     │      │ build.py │          │ git push         │
│ approvals│      │          │          │ synology-fda     │
│ .py      │      │ Jinja2 → │          │ master           │
└──┬───┬───┘      │ HTML     │          └────────┬─────────┘
   │   │          └──────────┘                   │
   │   │                                         ▼
   │   │                               ┌──────────────────┐
   │   │                               │  Synology NAS    │
   │   │                               │  post-receive    │
   │   ▼                               │  hook →          │
   │  data/                            │  /volume1/web/   │
   │  approvals.json                  │  medupdates/fda/ │
   │  .label_cache.json               └──────────────────┘
   │  .indication_
   │   summaries.json
   │
   ▼
┌──────────────┐     ┌──────────────────┐
│  openFDA     │     │  LLM Service     │
│  drugsfda    │─────│  (Ollama Cloud)  │
│  API         │     │  indication      │
│              │     │  summarization   │
│  openFDA     │     └──────────────────┘
│  label API   │
└──────────────┘
```

## Data Flow

A typical pipeline run moves data through three stages:

1. **Fetch** (`fda_approvals.py`) — Queries the openFDA drugsfda endpoint for original approvals (NME, Type 2, Type 4) and efficacy supplements within a 2-year rolling window. Paginates through results, filters for prescription-only drugs, and deduplicates entries.
2. **Label enrichment** — For each drug, queries the openFDA label endpoint (with a 0.5s delay between requests and 5 concurrent threads) to pull full prescribing information (indications, boxed warnings, dosing, contraindications, etc.). Reuses cached label data from the previous run when `--cache` is passed.
3. **LLM summarization** (optional, `--summarize`) — Batches drugs and sends their verbose FDA indication text to an LLM service to produce concise 1–4 word condition summaries (e.g., "moderate plaque psoriasis"). Results are cached in `data/.indication_summaries.json`.
4. **Build** (`build.py`) — Reads `data/approvals.json`, resolves slug collisions, renders the Jinja2 templates (`templates/index.html` for the drug table, `templates/drug_detail.html` for per-drug pages), and writes static HTML to `site/`.
5. **Deploy** — The pipeline script git-commits the `site/` directory and pushes to the `synology-fda` remote. A post-receive hook on the NAS deploys to `<!-- VERIFY: /volume1/web/medupdates/fda/ on the Synology -->`, served at `<!-- VERIFY: medupdates.wilmsfamily.com/fda/ -->`.

## Key Abstractions

| Abstraction | File | Description |
|---|---|---|
| `fetch_drugsfda_approvals()` | `fda_approvals.py:266` | Fetches original (ORIG) drug approvals from the drugsfda endpoint with date range and submission type filtering |
| `fetch_suppl_approvals()` | `fda_approvals.py:369` | Fetches efficacy supplement (SUPPL) approvals with deduplication across multiple submissions per drug |
| `fetch_label()` | `fda_approvals.py:472` | Retrieves full prescribing information for a single drug from the label endpoint, extracting 17 key fields |
| `extract_short_indication()` | `fda_approvals.py:51` | Heuristic parser that extracts concise indication text from verbose FDA label prose using cascading regex patterns |
| `slugify()` | `fda_approvals.py:41` | Converts drug names to URL-safe slugs with Unicode normalization and hyphen substitution |
| `summarize_indications_batch()` | `fda_approvals.py:179` | Batch LLM client that sends indication text for condensation into 1–4 word summaries, with caching |
| `format_pi_text()` | `build.py:165` | Three-stage pipeline (pre-process → split at sub-sections → post-process) that converts FDA prescribing information text into readable HTML |
| `sanitize_html()` | `build.py:13` | Strips dangerous HTML (script, style, iframe, event handlers) while preserving safe structural tags |
| `load_previous_approvals()` | `fda_approvals.py:523` | Loads prior run data for incremental label caching — avoids re-fetching unchanged labels |

## Directory Structure Rationale

```
fda-updates/
├── fda_approvals.py      # Main data-fetching script (openFDA API client + label enrichment + LLM summarization)
├── build.py              # Static site generator (JSON → HTML via Jinja2 templates)
├── run_fda_pipeline.sh   # Orchestration script: fetch → build → deploy, with Pushover failure alerts
├── AGENTS.md             # Project context and API gotchas for AI coding assistants
├── data/                 # Runtime data — fetched JSON, caches
│   ├── approvals.json               # Primary output: all drug approval records with labels
│   ├── .label_cache.json            # Application-number → set-id mapping for incremental label fetching
│   └── .indication_summaries.json   # LLM-generated concise indication summaries (cached)
├── templates/            # Jinja2 HTML templates for site generation
│   ├── base.html         # Shared layout: CSS variables, dark mode toggle, navigation shell
│   ├── index.html        # Drug approvals table with search/sort (List.js)
│   └── drug_detail.html  # Per-drug prescribing information page
├── site/                 # Built static website (separate git repo, deployed to Synology)
│   ├── index.html        # Generated drug approval listing
│   ├── css/custom.css    # Site styles
│   ├── js/main.js        # Client-side: dark mode toggle, sorting helpers
│   ├── js/list.min.js    # List.js library for client-side search and sort
│   └── drugs/            # Per-drug detail pages (e.g., drugs/cosentyx.html)
├── systemd/              # systemd user units for automated weekly execution
│   ├── fda-pipeline.service  # One-shot service that runs the pipeline
│   ├── fda-pipeline.timer     # Weekly Monday 03:00 ET trigger
│   └── install.sh         # Installer: copies units to ~/.config/systemd/user and enables timer
└── test_*.py             # Unit tests for core functions (slugify, cache, label fetching, LLM)
```

The project uses two independent git repositories: the **main repo** tracks the pipeline scripts and templates, while the **`site/` sub-repo** tracks only the built static website and pushes to the Synology NAS remote for deployment. This separation ensures the deploy target never receives raw data or pipeline code.

## External Dependencies

| Service | Purpose | Configuration |
|---|---|---|
| openFDA drugsfda API | Drug approval records (dates, application numbers, submission types) | `https://api.fda.gov/drug/drugsfda.json` — no API key required |
| openFDA label API | Full prescribing information per drug | `https://api.fda.gov/drug/label.json` — no API key required |
| Ollama Cloud LLM | Indication text summarization (1–4 word condition names) | `LLM_API_URL` + `LLM_MODEL` constants in `fda_approvals.py`; API key via `LLM_API_KEY` env var |
| Pushover | Failure notification alerts | `PUSHOVER_APP_KEY` + `PUSHOVER_USER_KEY` in `~/.config/fda-pipeline/.env` |
| Synology NAS | Static site hosting via git post-receive hook | Remote: `synology-fda` → `ssh://wilms@192.168.1.11:2022/volume1/git/fda.git` <!-- VERIFY: SSH host and port for Synology --> |