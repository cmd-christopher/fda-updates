# Phase 4: Automation & Deployment - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Source:** Derived from discuss-phase, ROADMAP.md, REQUIREMENTS.md, prior phase decisions, and codebase patterns

<domain>
## Phase Boundary

This phase sets up weekly automation to run the data fetch + build pipeline and automatically deploy the updated site to the Synology NAS via git push. After this phase, the site updates itself weekly with no manual intervention, and failures are visible via logs and notifications.

**In scope:**
- Wrapper shell script that runs the full pipeline: `fda_approvals.py` → `build.py` → git push
- Incremental label fetching (skip labels where `set_id` hasn't changed)
- systemd user service + timer for weekly execution
- Fail-safe deployment: old site stays live on failure
- Pushover notification on pipeline failure
- Skip push when no data has changed
- Commit messages with date + drug count delta

**Out of scope:**
- Email notifications (Pushover chosen instead)
- Partial/partial-result deploys
- Incremental page regeneration (build.py always does full rebuild — decided in Phase 3)
- Changes to `fda_approvals.py` fetch logic beyond set_id dedup
- Changes to site UI or templates
</domain>

<decisions>
## Implementation Decisions

### Date Range Handling
- D-01: Always fetch the full rolling 2-year window (`--from` = today minus 2 years, `--to` = today) — FDA sometimes posts drugs to the database after their approval date, so a narrower window could miss late-posted entries
- D-02: Optimize label enrichment by skipping drugs whose `set_id` hasn't changed since the previous fetch — this avoids re-downloading label details for unchanged drugs while still catching label updates (set_id changes when FDA updates the label)
- D-03: Previous set_ids stored in `data/.label_cache.json` — maps `set_id → drug_slug` for quick lookup. On each run, compare new set_ids against this file to determine which labels need fetching
- D-04: `build.py` always does a full rebuild (already decided in Phase 3) — only the FDA data fetch is optimized

### Failure Handling & Logging
- D-05: Fail-safe: if any step in the pipeline fails (fetch, build, or push), the old site stays live untouched — new data only pushes after the full pipeline completes successfully
- D-06: All pipeline output goes to systemd journal (`journalctl --user -u fda-pipeline.service`)
- D-07: On failure, send a Pushover notification with the step that failed and the error message. Pushover app key and user key stored in a `~/.config/fda-pipeline/.env` file (NOT in the repo)
- D-08: Pipeline timeout: 30 minutes — systemd `TimeoutSec=1800` on the service unit. Generous for ~210 drugs with 0.5s label delay
- D-09: The wrapper script exits with non-zero on any step failure, so systemd registers the service as failed (which triggers the OnFailure notification path)

### Deployment Commit Strategy
- D-10: Automated git commit messages follow format: `YYYY-MM-DD weekly update: +N drugs` (e.g., `2026-04-23 weekly update: +3 drugs`). Delta shows how many drugs were added since the previous run. If only label updates changed (no new drugs), format is: `2026-04-23 weekly update: label updates`
- D-11: Skip the entire git push if `build.py` produces no changes from the previous run (i.e., `git diff --quiet` after `build.py` and `git add` — if no changes, exit cleanly without pushing)
- D-12: The `--amend` flag is NOT used — each weekly run produces its own commit on the `master` branch of the site sub-repo

### Pipeline Script Design (planner's discretion)
- D-13: Follow the sibling project pattern: a shell script wrapper (`run_fda_pipeline.sh`) that invokes each step sequentially, loads env vars from a `.env` file, and handles errors with `set -euo pipefail`
- D-14: The systemd service ExecStart points to the wrapper script, not to Python directly
- D-15: Weekly schedule: `OnCalendar=Mon *-*-* 03:00:00` (Monday 3 AM local time — low-traffic period)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Guidelines
- `AGENTS.md` — Project overview, deploy command (`cd site/ && git add . && git commit -m "update" && git push synology-fda master`), two-repo structure, API gotchas
- `.planning/research/PITFALLS.md` — API pitfalls and edge cases
- `.planning/research/ARCHITECTURE.md` — Two-script pipeline pattern, deployment pattern (git push + post-receive hook)

### Established Patterns (from completed phases)
- `fda_approvals.py` — Data fetching script with `--from`, `--to`, `--type`, `-o`, `--skip-labels` flags; 0.5s delay between label requests
- `build.py` — Static site generator; reads `data/approvals.json`, renders Jinja2 templates, outputs to `site/`
- `site/` — Separate git repo with `synology-fda` remote (ssh://wilms@192.168.1.11:2022/volume1/git/fda.git, branch: master)
- Sibling project systemd pattern — `run_codex_pipeline.sh` wrapper with env file loading and error handling

### Data Contract
- `data/approvals.json` — Full drug dataset; each drug has a `label` dict with `set_id` field
- `data/.label_cache.json` — (new) maps set_id → drug_slug for incremental label dedup

</canonical_refs>

<specifics>
## Specific Ideas

- The Pushover notification script should be a small helper (a few lines of curl) invoked by the wrapper script on failure — no dependency on notification libraries
- The `.env` file at `~/.config/fda-pipeline/.env` contains: `PUSHOVER_APP_KEY`, `PUSHOVER_USER_KEY`
- `set_id` field on each drug's label data identifies the label version — if the set_id matches what's in `.label_cache.json`, skip the label enrichment call for that drug
- The wrapper script computes `--from` as `$(date -d '2 years ago' +%Y-%m-%d)` and `--to` as `$(date +%Y-%m-%d)`
- The wrapper script handles the "no changes" case by checking `git diff --quiet` in the `site/` directory after running `build.py` — if clean, exit 0 without pushing
- For commit messages with drug count delta: compare `len(data['drugs'])` in old vs new `approvals.json`, or simpler: `git diff --numstat site/index.html site/drugs/ | wc -l` — the planner can choose the simpler approach
</specifics>

<deferred>
## Deferred Ideas

- Email notification support (Pushover is sufficient)
- Incremental page regeneration (full rebuild is fast enough for ~210 pages)
- Automated health check / uptime monitoring (the site either updates or the old version stays live)
- Rollback mechanism (the site sub-repo has git history — manual rollback is trivial)
- Dashboard or status page showing last successful update time
</deferred>

---

*Phase: 04-automation-deployment*
*Context gathered: 2026-04-23*