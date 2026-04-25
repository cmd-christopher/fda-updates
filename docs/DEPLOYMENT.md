<!-- generated-by: gsd-doc-writer -->
# Deployment

## Deployment Targets

The project deploys a static website to a **Synology NAS** via a git push workflow. There is one deployment target:

- **Synology NAS** — The `site/` directory is a separate git repository with a remote (`synology-fda`) pointing to a Gitea instance on the NAS. A post-receive hook on the NAS auto-deploys the pushed content to the web root.
  - Remote: `synology-fda` → `ssh://wilms@192.168.1.11:2022/volume1/git/fda.git`
  - Branch: `master`
  - Web root on NAS: `/volume1/web/medupdates/fda/` <!-- VERIFY: NAS web root path -->
  - Public URL: `medupdates.wilmsfamily.com/fda/` <!-- VERIFY: Public URL -->

No containerization (Dockerfile), serverless, or cloud platform config is used.

## Build Pipeline

The deployment pipeline is automated via a **systemd user timer** that runs a weekly shell script. There is no CI/CD platform (no GitHub Actions or similar) — the pipeline runs directly on the developer's machine.

### Pipeline steps (in `run_fda_pipeline.sh`)

1. **Fetch data** — `python3 fda_approvals.py --from <2 years ago> --to <today> --cache --summarize -o data/approvals.json`
   - Queries the openFDA drugsfda and label endpoints
   - Uses `--cache` for incremental label fetching (reuses previously fetched labels)
   - Uses `--summarize` to generate concise indication names via LLM

2. **Build static site** — `python3 build.py`
   - Reads `data/approvals.json` and Jinja2 templates from `templates/`
   - Outputs `site/index.html` and `site/drugs/<slug>.html` detail pages
   - Requires pre-existing static assets: `site/css/custom.css`, `site/js/list.min.js`, `site/js/main.js`

3. **Deploy to Synology** — `git push synology-fda master`
   - Stages all changes in `site/`, commits with a drug-count-delta message, and pushes
   - Skips push if no changes detected (`git diff --cached --quiet`)
   - Each weekly run produces a separate commit (no `--amend`)

### Timer schedule

- **Trigger**: Every Monday at 03:00 AM America/New_York (systemd `OnCalendar=Mon *-*-* 03:00:00 America/New_York`)
- **Timeout**: 30 minutes (`TimeoutStartSec=1800` in service unit)
- **Persistence**: `Persistent=true` — if the machine was off at scheduled time, the timer runs on next boot

### Failure handling

- The pipeline uses `set -euo pipefail` — any step failure exits immediately
- **Fail-safe design**: the old site stays live if any step fails (the git push only happens after all steps succeed)
- **Pushover notifications**: on failure, a Pushover alert is sent with the failing step name and error message (requires `PUSHOVER_APP_KEY` and `PUSHOVER_USER_KEY` in `~/.config/fda-pipeline/.env`)

## Environment Setup

The deployment requires the following environment configuration. See [CONFIGURATION.md](CONFIGURATION.md) for the full variable reference.

**Required for deployment:**

| Variable | Location | Purpose |
|---|---|---|
| `PUSHOVER_APP_KEY` | `~/.config/fda-pipeline/.env` | Pushover app token for failure notifications |
| `PUSHOVER_USER_KEY` | `~/.config/fda-pipeline/.env` | Pushover user key for failure notifications |
| `LLM_API_KEY` | `~/.config/fda-pipeline/.env` | API key for the LLM service (Ollama Cloud) used by `--summarize` |

<!-- VERIFY: Pushover and LLM API key names and env file location -->

Pushover variables are optional — if absent, notifications are silently skipped. `LLM_API_KEY` is required for the `--summarize` step; without it, indication summaries fall back to brand names.

**SSH access** to the Synology NAS must be configured for the `synology-fda` git remote (key-based auth to `ssh://wilms@192.168.1.11:2022`). <!-- VERIFY: SSH connection details -->

**System prerequisites on the deployment machine:**
- Python 3 with `jinja2` and `markupsafe` packages
- `git` (with access to both the main repo and the Synology remote)
- `curl` (for Pushover notifications)
- Network access to `api.fda.gov` and the LLM API endpoint

## Rollback Procedure

Since each weekly pipeline run creates a separate git commit in the `site/` repository, rollback is straightforward:

1. SSH into the Synology NAS or work from the local `site/` repository
2. Identify the last known-good commit: `git log --oneline -5`
3. Revert to the previous commit:
   ```bash
   cd site/
   git revert HEAD
   git push synology-fda master
   ```
   Or to reset to a specific commit:
   ```bash
   git reset --hard <commit-hash>
   git push synology-fda master --force
   ```

The post-receive hook on the NAS will auto-deploy the reverted content to the web root. <!-- VERIFY: Post-receive hook behavior on force push -->

For a quicker fix without git operations, you can also manually re-deploy a previous pipeline run's output by re-running the pipeline with a known-good date range.

## Monitoring

The project uses **Pushover** for failure notifications — there is no APM, log aggregation, or uptime monitoring service.

- **Failure alerts**: The pipeline sends a Pushover notification with `priority=1` when any step fails, including the step name and error message
- **Pipeline logs**: Viewable via systemd journal:
  ```bash
  journalctl --user -u fda-pipeline.service       # View logs
  journalctl --user -u fda-pipeline.service -f     # Follow logs
  ```
- **Timer status**: Check if the weekly timer is active:
  ```bash
  systemctl --user status fda-pipeline.timer
  systemctl --user list-timers
  ```
- **Manual run**: Trigger a pipeline run outside the schedule:
  ```bash
  systemctl --user start fda-pipeline.service
  ```

No Sentry, Datadog, New Relic, or OpenTelemetry integration is present. The `site/` web content itself is served by the Synology NAS web server — monitoring of the served site is outside the scope of this project. <!-- VERIFY: Synology NAS web server monitoring -->