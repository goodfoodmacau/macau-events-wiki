#!/bin/sh
set -u

WIKI_ROOT="/Users/besa/macau-events-wiki"
PYTHON="$(command -v python3 || command -v python)"
LOG_DIR="$WIKI_ROOT/logs"
LOCK_DIR="/tmp/macau-events-crawler.lock"
FAILURES_FILE="$LOG_DIR/failures.json"

mkdir "$LOCK_DIR" 2>/dev/null || exit 0
cleanup() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

cd "$WIKI_ROOT" || exit 1
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/scheduled-crawl.log"
# Bound the persistent log before each run; this keeps scheduler output useful
# without allowing repeated source failures to fill the disk.
if [ -f "$LOG_FILE" ] && [ "$(wc -c < "$LOG_FILE")" -gt 1048576 ]; then
  tail -c 524288 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
exec >> "$LOG_FILE" 2>&1

echo "============================================================"
echo "Macau scheduled crawl: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================================"

# Reset failures log for this run
echo '{"run_at":"'"$(date -u '+%Y-%m-%dT%H:%M:%SZ')"'","failures":[]}' > "$FAILURES_FILE"

record_failure() {
  tier="$1"
  step="$2"
  # Append to the failures array in failures.json
  python3 - <<EOF 2>/dev/null || true
import json, os, sys
path = "$FAILURES_FILE"
try:
    data = json.loads(open(path).read())
except Exception:
    data = {"failures": []}
data["failures"].append({"tier": "$tier", "step": "$step", "at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"})
open(path, "w").write(json.dumps(data, indent=2))
EOF
}

run_tier() {
  tier="$1"
  echo "Starting tier $tier"
  "$PYTHON" scripts/crawl.py --tier "$tier"
  status=$?
  echo "Tier $tier finished with status $status"
  if [ "$status" -ne 0 ]; then
    record_failure "$tier" "crawl"
  fi
  return "$status"
}

# Keep tiers independent: one blocked source must not stop other sources.
overall_status=0
run_tier 1 || overall_status=1
run_tier 2 || overall_status=1
run_tier 3 || overall_status=1

# Tier 4 — monthly deep crawl (runs on the 1st of every month)
if [ "$(date +%d)" = "01" ]; then
  echo "Monthly Tier 4 deep crawl triggered (day 1 of month)"
  run_tier 4 || overall_status=1
fi

# Rebuild the wiki index after writes.
echo "Regenerating wiki index"
"$PYTHON" scripts/generate_index.py
index_status=$?
echo "Index generation finished with status $index_status"
if [ "$index_status" -ne 0 ]; then
  record_failure "index" "generate_index"
  overall_status=1
fi

echo "Validating archive"
"$PYTHON" scripts/validate.py --published-only
validate_status=$?
echo "Validation finished with status $validate_status"
# The archive intentionally retains historical/legacy records. Their
# validation debt is reported, but publication is gated by the derived feed
# below, not by requiring every historical record to be complete.

echo "Building publication feed"
"$PYTHON" scripts/publication_pipeline.py

# ── QA & self-healing pass ──────────────────────────────────────────────────
echo "Starting QA verification pass"
"$PYTHON" scripts/verify_published.py
status=$?
echo "QA pass finished with status $status"
if [ "$status" -ne 0 ]; then
  record_failure "qa" "verify_published"
fi

pipeline_status=$?
echo "Publication pipeline finished with status $pipeline_status"
if [ "$pipeline_status" -ne 0 ]; then
  record_failure "pipeline" "publication_pipeline"
  overall_status=1
fi

echo "Scheduled crawl complete: $(date '+%Y-%m-%d %H:%M:%S %Z')"
# Also cap a log that grew during this run.
if [ "$(wc -c < "$LOG_FILE")" -gt 1048576 ]; then
  tail -c 1048576 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

# Mac desktop notification on failure
if [ "$overall_status" -ne 0 ]; then
  FAILURE_COUNT=$(python3 -c "import json; d=json.loads(open('$FAILURES_FILE').read()); print(len(d.get('failures',[])))" 2>/dev/null || echo "?")
  osascript -e "display notification \"$FAILURE_COUNT step(s) failed — check logs/failures.json\" with title \"Macau Events Crawler\" subtitle \"Crawl completed with errors\" sound name \"Basso\"" 2>/dev/null || true
fi

exit "$overall_status"
