#!/usr/bin/env bash
# on_correction.sh — high-signal capture of press-and-recover events
#
# Fires when a user correction is detected (press-and-recover cycle).
# These are the highest-signal observations: they represent moments
# where default-vertex collapse or immature-absolute statements were
# caught and corrected. Capturing them makes future priming stronger.
#
# Usage:
#   on_correction.sh SESSION_ID "content of the correction" [vertex] [ruler] [tags_csv]
#
# Example:
#   on_correction.sh sess-abc123 "stated 'v3 regressed' as absolute without elimination" \
#       "code-verification" "content-check" "immature-absolute-flag,press-and-recover"

set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "usage: $0 SESSION_ID CONTENT [VERTEX] [RULER] [TAGS_CSV]" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="${SCRIPT_DIR}/../graphic_mem.py"

SESSION_ID="$1"
CONTENT="$2"
VERTEX="${3:-}"
RULER="${4:-}"
TAGS="${5:-press-and-recover}"

ARGS=(note
      --content "$CONTENT"
      --event-type correction
      --session-id "$SESSION_ID"
      --tags "$TAGS")

if [ -n "$VERTEX" ]; then
    ARGS+=(--vertex "$VERTEX")
fi
if [ -n "$RULER" ]; then
    ARGS+=(--ruler "$RULER")
fi

python "$ENGINE" "${ARGS[@]}"
