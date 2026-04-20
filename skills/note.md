---
name: note
description: Capture a targeted observation into graphic_mem outside the hook-auto-capture flow. Use when something specific is worth preserving: a correction received, a realization, a pattern noticed, a decision point, an immature-absolute flag caught. Captured observations feed future priming and pattern-detection across sessions.
---

# note

**When to use**: you've just experienced a moment worth remembering — a press-and-recover correction, a genuine ruler-shift discovered, an earned absolute locked in, a lane-crossing caught, a drift reading observed. Capture it now; hook-auto-capture may miss the nuance. Also use at session-end to commit the session's key realizations to cross-session memory.

**Discipline**: IN-RAM RULE applies — only capture what a future session or pattern-detector will read. Don't capture in-session scratch. Don't capture what's already obvious from MEMORY.md.

## Parameters

- `--content "text"` — the observation content (required)
- `--event-type T` — choose from: turn, correction, lane_cross, drift, realization, pin, install, build, vertex_shift, ruler_shift, relabel, immature_absolute, earned_absolute (default: turn)
- `--vertex V` — the observer-vertex the observation was made from (optional, but load-bearing for later pattern-detection)
- `--ruler R` — the ruler/framing being applied (optional)
- `--slide N` — if the observation is a drift reading, the slide-rule position (0.0–1.0)
- `--tags tag1,tag2` — classification tags; use framework-native tags when applicable:
  - `press-and-recover` — the event came from user correction
  - `default-vertex-collapse` — caught standing on inherited vertex
  - `ruler-shift-miss` — treated relabel as genuine ruler-shift
  - `immature-absolute-flag` — stated absolute before elimination
  - `earned-absolute` — absolute earned via completed elimination
  - `lane-crossing` — carrier-class misalignment detected
  - `ownership-rule-check` — OWNERSHIP RULE evaluation point
  - `in-ram-check` — IN-RAM RULE evaluation point
  - `vertex-shift-catch` — successfully stepped from one vertex to another
- `--session-id SID` — ties to current session (default: "default" if no session explicitly started)

## Examples

```bash
# Capture a realization
python graphic_mem.py note \
  --content "The scribe tool's slide-rule maps 1:1 to the epistemic model of commitment-at-threshold" \
  --event-type realization \
  --vertex cognition-substrate \
  --tags earned-absolute,vertex-agility

# Capture a correction received
python graphic_mem.py note \
  --content "Jumped to conclusion on 'v3 regressed' without eliminating alternatives" \
  --event-type correction \
  --vertex strict-code-verification \
  --ruler content-check \
  --tags immature-absolute-flag,press-and-recover

# Capture a drift reading
python graphic_mem.py note \
  --content "Slide 0.44 on vertex-shift v1→v2, genuine by value-mismatches even though structural match" \
  --event-type drift \
  --slide 0.44 \
  --tags drift-scan,vertex-shift-catch
```

## Discipline notes

- Use explicit `event_type` when possible; "turn" is the default but less useful for pattern-detection
- Vertex + ruler pair is high-signal for future priming; include them when known
- Tags are free-form but converge on the native vocabulary for cross-session pattern aggregation
- If the observation references another observation (e.g., a correction OF an earlier immature absolute), follow up with `link` (not yet a CLI command in v0.1 — manual SQL or v0.2 feature)
