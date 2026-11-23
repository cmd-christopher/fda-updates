<!-- generated-by: gsd-doc-writer -->

# Configuration

This project has two layers of configuration: **CLI flags** for the Python scripts and **environment variables** for the automated pipeline's Pushover credentials. There are no config files beyond environment variables and command-line arguments.

## Environment Variables

Environment variables are used by the automated pipeline (`run_fda_pipeline.sh`) for Pushover notifications. They are loaded from `~/.config/fda-pipeline/.env` when running via the pipeline script or systemd timer. Local Ollama summarization does not require credentials.

| Variable | Required | Default | Description |
|---|---|---|---|
| `PUSHOVER_APP_KEY` | Optional | _(unset)_ | Pushover application key for failure notifications sent by `run_fda_pipeline.sh`. |
| `PUSHOVER_USER_KEY` | Optional | _(unset)_ | Pushover user key for failure notifications sent by `run_fda_pipeline.sh`. |
| `PATH` | Set by systemd | `system default` | The systemd service unit overrides `PATH` to `/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin` to ensure Homebrew-installed Python is available. |

### Environment file

The pipeline reads environment variables from `~/.config/fda-pipeline/.env` (auto-loaded via `set -a; source` in `run_fda_pipeline.sh`). Create this file with the following format:

```bash
PUSHOVER_APP_KEY=your_app_key
PUSHOVER_USER_KEY=your_user_key
```

This file is **not** tracked in the repository. The `.env` pattern is gitignored at the project root.

## Config File Format

This project does not use a configuration file (JSON, YAML, TOML, or otherwise). All runtime behavior is controlled via:

1. **CLI arguments** — see `python3 fda_approvals.py --help` and `python3 build.py`
2. **Environment variables** — see table above
3. **Hardcoded constants** — see Defaults section below

## Required vs Optional Settings

No environment variable causes the application to fail on startup if absent. Behavior when variables are missing:

- **`PUSHOVER_APP_KEY`** or **`PUSHOVER_USER_KEY`** missing: the pipeline logs a notification that Pushover keys are not configured and skips the failure alert. The pipeline still fails with a non-zero exit code on error, just without sending a notification.

The only truly **required** inputs are the CLI date arguments (`--from` and `--to`), which cause `argparse` to exit with an error if omitted.

## Defaults

The following runtime defaults are hardcoded as module-level constants in `fda_approvals.py`:

| Constant | Default | Location | Description |
|---|---|---|---|
| `API_BASE` | `https://api.fda.gov/drug/` | `fda_approvals.py:24` | Base URL for the openFDA API. |
| `REQUEST_DELAY` | `0.5` | `fda_approvals.py:25` | Seconds to wait between label API requests to respect rate limits. |
| `LABEL_CACHE_PATH` | `data/.label_cache.json` | `fda_approvals.py:26` | Path to the label set-ID cache for incremental fetching. Resolved relative to the script directory. |
| `INDICATION_SUMMARIES_PATH` | `data/.indication_summaries.json` | `fda_approvals.py:27` | Path to the LLM-generated indication summary cache. |
| `LLM_API_URL` | `http://192.168.1.6:11434/api/chat` | `fda_approvals.py:61` | Local Ollama API on the Mac Studio. |
| `LLM_MODEL` | `flint:40b-a2b-qat-int4` | `fda_approvals.py:62` | Local model for indication summarization. |
| `LLM_NUM_CTX` | `65536` | `fda_approvals.py:63` | Context window passed to Ollama for each request. |
| `LLM_NUM_PREDICT` | `16384` | `fda_approvals.py:64` | Maximum generated tokens per request. Each approval is sent separately. |
| `LLM_TIMEOUT` | `300` | `fda_approvals.py:65` | Request timeout in seconds. |
| `EFFICACY_SUPPL_CODES` | `{"EFFICACY"}` | `fda_approvals.py:32` | Set of submission class codes considered efficacy supplements. |

CLI argument defaults in `fda_approvals.py`:

| Argument | Default | Description |
|---|---|---|
| `--type` | `all` | Filter type: `nme`, `suppl`, or `all` (both ORIG + SUPPL). |
| `--limit` | `100` | Max results per drugsfda API query page. |
| `--output` | stdout | Output destination; `-o file.json` writes to a file instead. |

Defaults in `build.py`:

| Constant | Default | Location | Description |
|---|---|---|---|
| `DATA_PATH` | `data/approvals.json` | `build.py:351` | Input JSON file path for drug approval data. |
| `TEMPLATE_DIR` | `templates` | `build.py:352` | Directory containing Jinja2 HTML templates. |
| `OUTPUT_DIR` | `site` | `build.py:353` | Directory where the built static site is written. |

Defaults in `run_fda_pipeline.sh`:

| Setting | Default | Location | Description |
|---|---|---|---|
| Date range | 2-year rolling window (2 years ago → today) | `run_fda_pipeline.sh:24-25` | Automatically computed; always fetches the full 2-year window. |

## Per-Environment Overrides

This project does not use `.env.development`, `.env.production`, or `.env.test` files. The pipeline has a single environment file (`~/.config/fda-pipeline/.env`) read by `run_fda_pipeline.sh`.

The systemd service unit (`systemd/fda-pipeline.service`) sets a custom `PATH` and `WorkingDirectory` but does not define additional `Environment=` directives beyond `PATH`. No `NODE_ENV`-style environment switching exists.

For manual ad-hoc runs, enable local indication summarization with `--summarize`:

```bash
python3 fda_approvals.py --from 2026-01-01 --to 2026-04-22 --summarize

# Skip label fetching entirely
python3 fda_approvals.py --from 2026-01-01 --to 2026-04-22 --skip-labels
```

There is no mechanism to override `API_BASE`, local Ollama settings, or `REQUEST_DELAY` without editing the source code.
