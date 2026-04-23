---
phase: 04-automation-deployment
plan: 02
subsystem: automation
tags: [systemd, timer, pipeline, pushover, git-push, deployment]
dependency_graph:
  requires:
    - phase: 04-01
      provides: fda_approvals.py --cache flag and label cache
  provides:
    - run_fda_pipeline.sh (fetch → build → push wrapper)
    - systemd/fda-pipeline.service (oneshot service with 30-min timeout)
    - systemd/fda-pipeline.timer (weekly Monday 03:00 AM ET)
    - systemd/install.sh (user-level unit installer)
  affects: [deployment, monitoring]
tech_stack:
  added: [systemd user units, Pushover curl notifications]
  patterns: [fail-safe pipeline, sequential step execution with error handling, no-change detection for git push]
key_files:
  created:
    - run_fda_pipeline.sh
    - systemd/fda-pipeline.service
    - systemd/fda-pipeline.timer
    - systemd/install.sh
  modified: []
decisions:
  - D-05: Fail-safe pipeline — old site stays live on any step failure; only push after all steps succeed
  - D-07: Pushover notifications via curl (no Python deps) on step failure
  - D-08: 30-min timeout in systemd service (TimeoutStartSec=1800), not in the script
  - D-10: Commit messages include date + drug count delta
  - D-11: Skip git push when no changes detected (git diff --cached --quiet)
  - D-12: No --amend; each weekly run gets its own commit
  - D-14: ExecStart points to wrapper script, not Python directly
  - D-15: Monday 03:00 America/New_York with Persistent=true for missed-run catch-up
patterns-established:
  - "Pipeline pattern: set -euo pipefail, sequential steps, env file loading, send_failure_notification helper"
  - "systemd user-level deployment: oneshot service + persistent timer + install.sh"
requirements-completed: [AUTO-01, AUTO-02, AUTO-04]
duration: ~2min
completed: 2026-04-23
---

# Phase 04 Plan 02: Pipeline Automation Summary

**Weekly systemd timer running fetch → build → push pipeline with Pushover failure notifications and no-change detection**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-23T20:02:44Z
- **Completed:** 2026-04-23T20:04:19Z
- **Tasks:** 2 (Task 1 was pre-approved checkpoint continuation)
- **Files modified:** 4

## Accomplishments
- Pipeline wrapper script orchestrates fetch (fda_approvals.py --cache) → build (build.py) → deploy (git push synology-fda) with strict error handling
- Pushover failure notifications via curl with APP_KEY/USER_KEY from ~/.config/fda-pipeline/.env
- No-change detection skips git push when data hasn't changed
- systemd user service (30-min timeout, network-online.target dependency) and timer (weekly Monday 03:00 ET, Persistent=true)
- Install script copies units to ~/.config/systemd/user/, daemon-reload, enable+start timer

## Task Commits

Each task was committed atomically:

1. **Task 1: Create run_fda_pipeline.sh wrapper script** - `005ca53` (feat)
2. **Task 2: Create systemd service, timer, and install script** - `df5c0d0` (feat)

## Files Created/Modified
- `run_fda_pipeline.sh` - Pipeline wrapper: fetch → build → push with Pushover notifications and no-change detection
- `systemd/fda-pipeline.service` - systemd user service (Type=oneshot, 30-min timeout, network-online.target)
- `systemd/fda-pipeline.timer` - Weekly Monday 03:00 AM timer with Persistent=true
- `systemd/install.sh` - Installer: copies units, daemon-reload, enable+start timer, prints help

## Decisions Made
- D-05: Fail-safe pipeline — only push to Synology after ALL steps succeed; old site stays live on failure
- D-07: Pushover notifications via curl (zero Python dependencies for notification)
- D-08: 30-min timeout in systemd service unit, not in the script itself
- D-10/D-11/D-12: Commit messages with drug count delta, no push when no changes, no --amend
- D-14/D-15: Wrapper script as ExecStart; Monday 03:00 ET with Persistent=true catch-up

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Manual configuration required before pipeline runs:**
1. Create `~/.config/fda-pipeline/.env` with Pushover keys:
   ```
   PUSHOVER_APP_KEY=your_pushover_app_key_here
   PUSHOVER_USER_KEY=your_pushover_user_key_here
   ```
2. Run `bash systemd/install.sh` to install and enable the timer
3. Verify with: `systemctl --user status fda-pipeline.timer`

## Next Phase Readiness

This is the final plan in Phase 4 (and the final phase). All automation requirements (AUTO-01, AUTO-02, AUTO-04) are satisfied. The project milestone is complete.

---
*Phase: 04-automation-deployment*
*Completed: 2026-04-23*

## Self-Check: PASSED

- FOUND: run_fda_pipeline.sh
- FOUND: systemd/fda-pipeline.service
- FOUND: systemd/fda-pipeline.timer
- FOUND: systemd/install.sh
- FOUND: 04-02-SUMMARY.md
- FOUND: 005ca53 (Task 1 commit)
- FOUND: df5c0d0 (Task 2 commit)