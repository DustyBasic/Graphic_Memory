#!/usr/bin/env bash
# on_session_end.sh — graphic_mem session close + summary generation
#
# Fires at session end. Closes the session record with optional summary,
# and emits a pattern-density report so the next session's priming has
# up-to-date failure-mode counts.
#
# Usage:
#   on_session_end.sh SESSION_ID [summary_text]

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: $0 SESSION_ID [SUMMARY]" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="${SCRIPT_DIR}/../graphic_mem.py"

SESSION_ID="$1"
SUMMARY="${2:-}"

ARGS=(end-session --session-id "$SESSION_ID")
if [ -n "$SUMMARY" ]; then
    ARGS+=(--summary "$SUMMARY")
fi

python "$ENGINE" "${ARGS[@]}"

echo "--- pattern density since 30d ---"
for PATTERN in default_vertex_collapse ruler_shift_miss immature_absolute any_correction; do
    echo ""
    echo "[$PATTERN]"
    python "$ENGINE" find-pattern --type "$PATTERN" --since 30d
done

echo ""
echo "--- drift scan since 7d ---"
python "$ENGINE" drift-scan --since 7d
