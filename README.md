<!-- generated-by: gsd-doc-writer -->

# FDA Drug Approval Updates

A CLI tool and static site pipeline that fetches FDA prescription drug approval data from the openFDA API and publishes it as a searchable website.

## Installation

This project requires Python 3 with no external packages for core data fetching (uses only stdlib). Site building requires Jinja2 and MarkupSafe.

```bash
# Clone the repository
git clone https://github.com/cmd-christopher/fda-updates.git
cd fda-updates

# Install site-building dependencies (required for build.py)
pip install jinja2 markupsafe
```

## Quick Start

1. Fetch NME drug approvals for a date range:

   ```bash
   python3 fda_approvals.py --from 2026-01-01 --to 2026-04-22 --type nme -o data/approvals.json
   ```

2. Build the static site from the fetched data:

   ```bash
   python3 build.py
   ```

3. Deploy to Synology (requires configured `synology-fda` git remote):

   ```bash
   cd site/ && git add . && git commit -m "update" && git push synology-fda master
   ```

## Usage Examples

**Fetch all approval types (NMEs, new active ingredients, new combinations, and efficacy supplements):**

```bash
python3 fda_approvals.py --from 2026-01-01 --to 2026-04-22 --type all -o data/approvals.json
```

**Quick test run skipping slow label fetching:**

```bash
python3 fda_approvals.py --from 2026-03-01 --to 2026-04-22 --type nme --skip-labels
```

**Incremental fetch reusing cached labels with LLM-powered indication summaries:**

```bash
python3 fda_approvals.py --from 2025-04-24 --to 2026-04-22 --type all --cache --summarize -o data/approvals.json
```

## Pipeline Automation

The project includes a fully automated weekly pipeline:

- `run_fda_pipeline.sh` — Runs the full fetch → build → deploy pipeline with fail-safe behavior (old site stays live on failure) and Pushover notifications on errors.
- `systemd/` — Contains a systemd timer (`Mon *-*-* 03:00:00 America/New_York`) and service unit for running the pipeline weekly via systemd.

## License

No license file found in this repository.