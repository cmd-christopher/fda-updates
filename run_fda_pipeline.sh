#!/usr/bin/env bash
# run_fda_pipeline.sh — Weekly FDA drug approval data pipeline
# Runs: fda_approvals.py → build.py → git push to Synology
# Per D-05: fail-safe — old site stays live on any failure
# Per D-07: sends Pushover notification on failure
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"
SITE_DIR="${SCRIPT_DIR}/site"
ENV_FILE="$HOME/.config/fda-pipeline/.env"

# ─── Load environment ───────────────────────────────────────────────
# Per D-07: Pushover keys and LLM API key stored in ~/.config/fda-pipeline/.env
# File contains: PUSHOVER_APP_KEY=..., PUSHOVER_USER_KEY=..., LLM_API_KEY=...
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# ─── Configuration ──────────────────────────────────────────────────
# Per D-01: Always fetch the full 2-year rolling window
DATE_FROM="$(date -d '2 years ago' +%Y-%m-%d)"
DATE_TO="$(date +%Y-%m-%d)"
OUTPUT_FILE="${DATA_DIR}/approvals.json"
PROJECT_DIR="${SCRIPT_DIR}"
PIPELINE_STEP="none"

# ─── Helper: Send Pushover notification on failure ──────────────────
# Per D-07: Pushover app key and user key from .env file
send_failure_notification() {
  local step="$1"
  local error_msg="$2"
  if [[ -z "${PUSHOVER_APP_KEY:-}" || -z "${PUSHOVER_USER_KEY:-}" ]]; then
    echo "[notification] Pushover keys not configured. Skipping notification." >&2
    return 0
  fi
  curl -s --max-time 10 \
    -F "token=${PUSHOVER_APP_KEY}" \
    -F "user=${PUSHOVER_USER_KEY}" \
    -F "title=FDA Pipeline Failed" \
    -F "message=Step '${step}' failed: ${error_msg}" \
    -F "priority=1" \
    https://api.pushover.net/1/messages.json >/dev/null 2>&1 || true
}

# ─── Step 1: Fetch data from openFDA ────────────────────────────────
echo "[1/3] Fetching FDA drug approval data (${DATE_FROM} to ${DATE_TO})"
PIPELINE_STEP="fetch"

# Per D-02/D-03: Use --cache for incremental label fetching
# Per D-01: Full 2-year window always
# --summarize: use LLM to generate concise condition names for the indication column
if ! python3 "${SCRIPT_DIR}/fda_approvals.py" \
  --from "$DATE_FROM" \
  --to "$DATE_TO" \
  --cache \
  --summarize \
  -o "$OUTPUT_FILE" 2>&1; then
  echo "[1/3] FAILED: fda_approvals.py exited with error" >&2
  send_failure_notification "fetch" "fda_approvals.py exited with non-zero status"
  exit 1
fi

if [[ ! -f "$OUTPUT_FILE" ]]; then
  echo "[1/3] FAILED: output file ${OUTPUT_FILE} not found" >&2
  send_failure_notification "fetch" "Output file not created"
  exit 1
fi

echo "[1/3] Fetch complete"

# ─── Step 2: Build static site ──────────────────────────────────────
echo "[2/3] Building static site"
PIPELINE_STEP="build"

if ! python3 "${SCRIPT_DIR}/build.py" 2>&1; then
  echo "[2/3] FAILED: build.py exited with error" >&2
  send_failure_notification "build" "build.py exited with non-zero status"
  exit 1
fi

echo "[2/3] Build complete"

# ─── Step 3: Deploy to Synology ─────────────────────────────────────
# Per D-11: Skip push if no changes
# Per D-05: Old site stays live if any step fails (we only push on success)
echo "[3/3] Deploying to Synology"
PIPELINE_STEP="deploy"

cd "$SITE_DIR"

# Per D-11: Check if there are changes to deploy
git add -A
if git diff --cached --quiet; then
  echo "[3/3] No changes to deploy. Exiting cleanly."
  exit 0
fi

# Per D-10: Commit message with date and drug count delta
# Count drugs in new data for commit message
NEW_COUNT="$(python3 -c "import json; print(json.load(open('${OUTPUT_FILE}'))['count'])" 2>/dev/null || echo "unknown")"

# Try to get previous count from the last commit message for delta
PREV_COUNT=""
if git log --oneline -1 2>/dev/null | grep -qoP '\+\d+ drugs'; then
  PREV_COUNT="$(git log --oneline -1 | grep -oP '\d+(?= drugs)')"
fi

if [[ -n "$PREV_COUNT" && "$NEW_COUNT" != "unknown" ]]; then
  DELTA=$((NEW_COUNT - PREV_COUNT))
  if [[ $DELTA -gt 0 ]]; then
    COMMIT_MSG="${DATE_TO} weekly update: +${DELTA} drugs"
  elif [[ $DELTA -lt 0 ]]; then
    COMMIT_MSG="${DATE_TO} weekly update: ${DELTA} drugs"
  else
    COMMIT_MSG="${DATE_TO} weekly update: no drug count change"
  fi
else
  COMMIT_MSG="${DATE_TO} weekly update: ${NEW_COUNT} total drugs"
fi

# Per D-12: No --amend; each weekly run gets its own commit
git commit -m "$COMMIT_MSG"

# Push to Synology
if ! git push synology-fda master 2>&1; then
  echo "[3/3] FAILED: git push to Synology failed" >&2
  send_failure_notification "deploy" "git push to synology-fda failed"
  exit 1
fi

echo "[3/3] Deploy complete"
echo "Pipeline completed successfully: ${COMMIT_MSG}"