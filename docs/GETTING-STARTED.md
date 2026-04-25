<!-- generated-by: gsd-doc-writer -->

# Getting Started

## Prerequisites

- **Python 3** — The core fetching script (`fda_approvals.py`) uses only Python standard library modules (no external packages required for data fetching). Python 3.10+ is recommended for full `match` syntax support; Python 3.6+ works for the basic CLI.
- **pip** — For installing site-building dependencies (Jinja2, MarkupSafe).
- **Git** — Required for cloning the repository and deploying the static site.
- **Internet access** — The script queries the openFDA API (`https://api.fda.gov`).

## Installation Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/cmd-christopher/fda-updates.git
   cd fda-updates
   ```

2. Install site-building dependencies:

   ```bash
   pip install jinja2 markupsafe
   ```

3. Create the data directory (used for output and label caching):

   ```bash
   mkdir -p data
   ```

## First Run

The quickest way to verify everything works is a test fetch that skips the slow label-fetching step:

```bash
python3 fda_approvals.py --from 2026-03-01 --to 2026-04-22 --type nme --skip-labels
```

This queries the openFDA drugsfda endpoint for New Molecular Entity approvals in the given date range and prints the results to stdout as JSON. You should see progress output on stderr and a JSON object with a `drugs` array on stdout.

To fetch with full prescribing label information and save to a file:

```bash
python3 fda_approvals.py --from 2026-01-01 --to 2026-04-22 --type nme -o data/approvals.json
```

## Common Setup Issues

- **No results returned** — The openFDA API may return an empty `results` array if there are no approvals in the requested date range, or if the date range is too far in the past/future. Try adjusting the `--from` and `--to` dates to a known active period.

- **`jinja2` not found when running `build.py`** — The site builder (`build.py`) requires Jinja2 and MarkupSafe. Install them with `pip install jinja2 markupsafe`. The core fetch script (`fda_approvals.py`) does not require these packages.

- **API rate limiting** — The openFDA API has a default rate limit of 240 requests per minute per IP with no API key. The script includes a 0.5-second delay between label requests to stay within limits. If you encounter `403` errors, wait a minute and retry.

- **Missing `data/` directory** — The script stores its label cache and default output in `data/`. Create it with `mkdir -p data` if it doesn't exist.

## Next Steps

- **ARCHITECTURE.md** — Understand the system components and data flow.
- **CONFIGURATION.md** — Learn about environment variables, caching, and LLM summarization options.