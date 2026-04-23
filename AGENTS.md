# AGENTS.md

## Project Overview

This project fetches FDA prescription drug approval data from the openFDA API and will eventually serve it as a static website on a Synology NAS.

## Key Commands

```bash
# Run the FDA approval fetching script
python3 fda_approvals.py --from 2026-01-01 --to 2026-04-22 --type nme -o output.json

# Quick test (skip slow label fetching)
python3 fda_approvals.py --from 2026-03-01 --to 2026-04-22 --type nme --skip-labels

# Deploy site to Synology
cd site/ && git add . && git commit -m "update" && git push synology-fda master
```

## Repo Structure

- `fda_approvals.py` — Main script: fetches drug approvals from drugsfda, then enriches each with full prescribing info from the label endpoint
- `site/` — Static website (separate git repo, deployed to Synology, **gitignored from the main repo**)
- `.skills/openfda-drug/` — Skill definition for querying openFDA API (**gitignored**)

## Two Git Repos

This directory contains two independent git repos:

1. **Main repo** (origin: `github.com/cmd-christopher/fda-updates`) — tracks only `fda_approvals.py` and `.gitignore`. `site/` and `.skills/` are gitignored.
2. **`site/` sub-repo** (remote: `synology-fda` → `ssh://wilms@192.168.1.11:2022/volume1/git/fda.git`, branch: `master`) — the deployable website, auto-deploys via post-receive hook to `/volume1/web/medupdates/fda/` on the Synology, served at `medupdates.wilmsfamily.com/fda/`

## openFDA API Gotchas

- **Sort pitfall**: `sort=submissions.submission_status_date:desc` returns drugs sorted by their *most recent any submission*, not the original approval. A drug with a 2026 supplement but 2015 original approval will appear near the top. Fix: always post-filter on the ORIG submission's date, or add a date range filter.
- **Date format**: `submission_status_date` is `"YYYYMMDD"` (e.g., `"20260401"`), not `"YYYY-MM-DD"`.
- **drugsfda vs label**: drugsfda has approval dates and application info; label has full prescribing info (indications, dosing, warnings, adverse reactions). The label endpoint does not support date-based searching — always start with drugsfda, then enrich with label.
- **URL encoding**: Spaces in search values (like `"Type 1 - New Molecular Entity"`) must be URL-encoded. The script handles this via `urllib.parse.quote`.

## Script Design Notes

- The script filters for prescription-only drugs (skips OTC/discontinued)
- `--type nme` filters for `"Type 1 - New Molecular Entity"` only; `--type all` returns all original approvals including generics
- Output JSON goes to stdout by default; use `-o file.json` to write to file
- The script has a 0.5s delay between label requests to respect API rate limits