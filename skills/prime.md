---
name: prime
description: Load relevant context from graphic_mem for a task-class at session start or mid-session when a new task-vertex is entered. Injects the prior-corrections and realizations most relevant to the named task. Not a free-form search — targeted priming keyed to task keywords.
---

# prime

**When to use**: at session start, or mid-session when the active work shifts to a new task-class. Priming loads the prior observations most relevant to how THAT specific task-class has failed or succeeded in past sessions.

**Difference from recall**: `recall` is free-form query. `prime` is task-keyword-mapped injection of curated-relevance observations — it's scoped to a named task class and returns a compact, load-bearing set rather than a broad search result.

## Parameters

- `--task "description"` — free-text task description; keywords are matched against known priming categories (required)
- `--limit N` — max observations per matched category (default 5)

## Known priming categories

Keywords in the task description activate these categories:

| Keyword | Loads observations tagged/typed as |
|---|---|
| `vertex` | default-vertex-collapse, vertex-shift-catch |
| `ruler` | ruler-shift-miss, relabel-as-shift |
| `absolute` | immature_absolute, earned_absolute |
| `drift` | drift observations (slide-rule positions) |
| `ownership` | ownership-rule-check, lane-crossing |
| `bloat` | in-ram-check, carrier-class-mismatch |

If no keyword matches, `default` category loads: recent corrections, realizations, and earned absolutes — high-signal baseline.

## Examples

```bash
# Starting a session that involves code-review
python graphic_mem.py prime --task "code review with vertex agility practice" --limit 5

# Entering a task about absolute statements
python graphic_mem.py prime --task "verify claims about absolute states" --limit 3

# Generic session start
python graphic_mem.py prime --task "morning development session" --limit 5
```

## Output shape

Returns JSON with `task`, `matched_categories`, `priming_count`, and `observations`. Observations ready to be read by the agent as pre-context for the session.

## Discipline notes

- Prime OUTPUT is context that goes INTO the session — it's a read, not a write
- Priming is not a substitute for MEMORY.md load — it's complementary, fills the middle-operational layer
- If `prime` returns nothing, that's data: no relevant prior observations exist for this task class yet; consider whether the current work is worth `note`-ing as it progresses
- Pattern: on entering a new task-vertex mid-session, `prime --task "<new vertex description>"` surfaces the priors relevant to that vertex specifically
