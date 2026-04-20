#!/usr/bin/env bash
# on_session_start.sh — graphic_mem session lifecycle hook
#
# Fires at session start. Initialises a new session record in graphic_mem
# and emits a priming-context block relevant to the current task keywords.
#
# Usage (invoked by Claude Code session-start hook wiring):
#   on_session_start.sh [task_description]
#
# Environment variables respected:
#   GRAPHIC_MEM_SESSION_ID   override auto-generated session id
#   GRAPHIC_MEM_TASK         fallback task description if no arg given
#   GRAPHIC_MEM_PRIME_LIMIT  max priming observations to surface (default 5)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="${SCRIPT_DIR}/../graphic_mem.py"

TASK="${1:-${GRAPHIC_MEM_TASK:-general}}"
SESSION_ID="${GRAPHIC_MEM_SESSION_ID:-}"
LIMIT="${GRAPHIC_MEM_PRIME_LIMIT:-5}"

# Start the session (idempotent — INSERT OR IGNORE semantics in engine)
if [ -n "$SESSION_ID" ]; then
    python "$ENGINE" init-session --session-id "$SESSION_ID"
else
    python "$ENGINE" init-session
fi

echo "--- graphic_mem priming for task: $TASK ---"
python "$ENGINE" prime --task "$TASK" --limit "$LIMIT"
