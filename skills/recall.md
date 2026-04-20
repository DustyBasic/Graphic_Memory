---
name: recall
description: Query past observations from graphic_mem by tags, vertex, event_type, date range, or content pattern. Use when searching cross-session memory for past corrections, realizations, or patterns. Returns structured observations with relationships.
---

# recall

**When to use**: user asks "did we already handle this?", "how did we solve X last time?", "what were the corrections on this vertex?", or when the current work would benefit from prior-session context that isn't already in MEMORY.md.

**How to invoke**: call `graphic_mem.py recall` with appropriate filters.

## Parameters

- `--tags tag1,tag2` — observations must carry at least one of these tags
- `--vertex V` — filter by the observer-vertex recorded with the observation
- `--event-type T` — one of: turn, correction, lane_cross, drift, realization, pin, install, build, vertex_shift, ruler_shift, relabel, immature_absolute, earned_absolute
- `--since 7d` — window: Nd / Nh / Nw / Nm
- `--pattern "text"` — content substring match
- `--limit N` — max results (default 10)

## Output shape

Returns JSON with `count` and `observations` list. Each observation has: `id`, `timestamp`, `content`, `vertex`, `ruler`, `event_type`, `slide_position`, `tags`, `relationships_out`.

## Examples

```bash
# Find past corrections on vertex-agility
python graphic_mem.py recall --tags press-and-recover,default-vertex-collapse --limit 5

# Find drift readings in the last week
python graphic_mem.py recall --event-type drift --since 7d

# Find immature-absolute flags related to Grok
python graphic_mem.py recall --event-type immature_absolute --pattern grok

# Find observations where standing on the cognition-substrate vertex
python graphic_mem.py recall --vertex cognition-substrate --limit 20
```

## Discipline notes

- `recall` is a READ operation; it doesn't modify graphic_mem state
- Output observations in the response DO NOT need to be re-captured (that would duplicate)
- When invoking recall to answer a user query, consider whether the retrieved context is sufficient OR whether `prime` (broader context load) would be more appropriate
