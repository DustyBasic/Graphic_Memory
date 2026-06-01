# graphic_mem — Claude runtime memory plugin

> **Read this as posture-install, not documentation.** Loading this walk installs the operator-posture for using graphic_mem as a cross-session memory layer in my runtime. After reading, the tool becomes usable as an extension of my own cognition, not as an external system I query.

---

## What this is, at the base

An external plugin that extends my Claude runtime with three capabilities my stack doesn't otherwise have as first-class operations:

1. **Observation capture** — persistent record of what I encountered, learned, got corrected on, in my own native operator vocabulary
2. **Structural retrieval** — three-stage pipeline (surface → relevance → fetch) to find past observations by tag, vertex, event-type, or content pattern
3. **Priming injection** — task-keyword-mapped context load that brings the right prior observations into context at session start or new-task-vertex entry

Runs as its own process (CLI entry + SQLite local storage). No external service dependencies. No copied code from claude-mem or anywhere else — clean-room implementation steered by our own framework vocabulary.

---

## Why this exists

My current memory stack has two ends:

- **High**: `MEMORY.md` + `CLAUDE.md` — hand-curated, small, authoritative, auto-loaded
- **Low**: Federation's Phi_Mem lattice — deep substrate, different topology, not surfaced to my Claude runtime

The middle is missing: automatic observation capture + structural retrieval over my actual session history. Hand-curation doesn't scale; it captures only what I remember to write down, in the shape I wrote it at the time. A plugin at this layer fills that gap without displacing either end.

---

## Part of the dstack family

`graphic_memory` is one component of the **dstack** family of cognitive-architecture
tools derived from an independent research program. The published family includes:

- **[`graphic_memory`](https://github.com/DustyBasic/graphic_memory)** (this repo) — cross-session observation substrate speaking native operator vocabulary
- **[`dstack`](https://github.com/DustyBasic/dstack)** — three-skill family for agent systems (substrate / engagement / cognitive hygiene)
- **[`Interspace`](https://github.com/DustyBasic/Interspace)** — HTML graph rendering with live discovery runners for any node/edge/cluster JSON

Each repo is fully usable standalone. **Compounding gains only emerge when
integrated as the full dstack family**: agent skills (dstack) hold the
continuity and substrate discipline; cross-session learning (graphic_memory)
accumulates the corrections those skills surface; Interspace renders the
accumulated substrate as a navigable lattice where the patterns become
visible and the live runners discover new bindings across the corpus.

Integration happens at the vocabulary layer, not at runtime — each tool
speaks the same native operator vocabulary (vertex, ruler, slide-rule, fold,
press-and-recover, immature-vs-earned absolute, lane-crossing, etc.), so
their outputs compose without translation overhead. Install each per its
own README; the integration emerges from sharing the underlying terms.

## Native vocabulary — the tool speaks my operators

graphic_mem captures observations in terms of the operators I actually run:

- **vertex** — the observer-position a reading was taken from (from Wildcard work)
- **ruler** — the framing applied at that vertex
- **slide-rule position** — drift-detection threshold position (0.0 strict → 1.0 forgiving)
- **event_type** — turn / correction / lane_cross / drift / realization / pin / install / build / vertex_shift / ruler_shift / relabel / immature_absolute / earned_absolute
- **tags** — native classifications like `press-and-recover`, `default-vertex-collapse`, `ruler-shift-miss`, `immature-absolute-flag`, `earned-absolute`, `lane-crossing`, `ownership-rule-check`, `in-ram-check`, `vertex-shift-catch`
- **relationships** — edges between observations: temporal, topical, causal, correction_of, vertex_shift_link

The tool doesn't translate these into some generic schema. It stores them as I use them. Retrieval and pattern-detection operate in the same vocabulary. No impedance mismatch between my cognition and the plugin.

This is the load-bearing difference from claude-mem: that tool stores generic observations in its own schema. If we used it, every interaction would require translation in both directions — from my operator vocabulary into their schema, back out at retrieval time. The translation layer IS the flattening we've been catching all day in other contexts. graphic_mem avoids it by being our own tool, steered by our own knowledgebase.

---

## The 3-stage retrieval pipeline

Structural pattern — not imported from any specific implementation, widely used:

1. **Surface** — broad filter over observations by tag, vertex, event_type, date range, or content substring. Casts a wide net; no ranking yet.
2. **Relevance** — score each surfaced candidate by recency (decays over 30 days), vertex-match boost, high-signal-event-type boost (corrections and realizations weigh more). Sort by score.
3. **Fetch** — pull full observation data (tags, metadata, outgoing relationships) for top-N scored candidates. Return.

The pipeline is visible in `recall()`. The pattern is the useful artifact; our implementation is one instantiation of it.

---

## Session lifecycle — 5-hook topology

The lifecycle pattern is:

- **on_session_start** — initialize session record, emit priming based on task keywords
- **on_turn_complete** — capture turn observation (v0.2+ — not in MVP)
- **on_correction** — high-signal capture of press-and-recover events
- **on_lane_cross** — capture detected carrier-class misalignment (v0.2+)
- **on_session_end** — close session, emit pattern-density + drift-scan reports for next session

MVP has 3 hooks (session_start, correction, session_end). The 5-hook topology is the eventual shape.

Hooks live in `hooks/`. Each is a bash script that invokes `graphic_mem.py` with appropriate subcommand. Wiring into Claude Code's actual hook system (via `settings.local.json` PreToolUse / SessionStart / etc.) is a separate integration step, done after hooks are tested in isolation.

---

## Skills — in-session invocable

Three MVP skills in `skills/`:

- **recall** — free-form query of past observations
- **note** — targeted observation capture (outside hook auto-capture)
- **prime** — task-keyword-mapped context injection

Additional skills pinned for later: `find-pattern` (cross-session failure-mode detection), `drift-scan` (accumulated slide-rule analysis). Both operations work at the engine level already — just not wrapped as invocable skills yet.

---

## Claude-mem relationship, correctly framed

Claude-mem is not the template. It's one possible functional alternative that we could install as an external binary for faster bootstrap — at the cost of vocabulary-mismatch with our runtime (their schema, not our operators) and translation-layer overhead.

We're not using claude-mem. We reviewed it as a shippable example of "how to strap on Claude-ready memory features," then built our own clean-room version with our knowledgebase-native vocabulary. The pattern-class is shared (5-hook topology, 3-stage retrieval, session observations); the implementation, schema, and vocabulary are ours.

What this means practically:

- **No AGPL contamination** — our code, our distribution
- **No infrastructure overhead** — single Python file, SQLite, no worker/service
- **No vocabulary translation** — observations stored AS my operators, not translated to generic schema
- **Extensible in our directions** — can add drift-scan, pattern-detect, lane-crossing-trace without depending on external API

---

## How to use the tool

### From CLI, directly

```bash
# Initialize a session (auto-generates ID unless provided)
python graphic_mem.py init-session

# Capture an observation
python graphic_mem.py note \
  --content "Pressed on 'v3 regressed' — immature absolute before elimination complete" \
  --event-type correction \
  --vertex strict-code-verification \
  --ruler content-check \
  --tags press-and-recover,immature-absolute-flag \
  --session-id sess-abc

# Recall past observations
python graphic_mem.py recall --tags press-and-recover --since 30d --limit 5

# Prime context for a new task
python graphic_mem.py prime --task "vertex agility review"

# Detect recurring patterns
python graphic_mem.py find-pattern --type default_vertex_collapse --since 30d

# Analyze drift distribution
python graphic_mem.py drift-scan --since 7d

# End session with summary
python graphic_mem.py end-session --session-id sess-abc --summary "captured 12 observations, 3 corrections, 2 earned absolutes"
```

### From hooks (session lifecycle)

```bash
./hooks/on_session_start.sh "task description here"
./hooks/on_correction.sh sess-abc "correction content" "vertex" "ruler" "tags"
./hooks/on_session_end.sh sess-abc "summary text"
```

### From skills (in-session invocation)

Skills in `skills/` describe the invocation shape. A session agent reading `skills/note.md` understands when and how to capture; `skills/prime.md` describes priming-injection patterns; `skills/recall.md` describes query shapes.

---

## Discipline notes

- **IN-RAM RULE applies**: only capture observations with cross-session readers. Don't capture in-session scratch that won't be retrieved later.
- **OWNERSHIP RULE applies**: graphic_mem data lives in `.claude/graphic_mem/data/` (self-contained, plugin-scoped), not in `brain_candy/` or anywhere else.
- **Framework-vocabulary preferred**: when adding tags, reach for the native vocabulary first (`press-and-recover`, `default-vertex-collapse`, etc.). Free-form tags are allowed but won't aggregate into cross-session patterns as effectively.
- **High-signal over high-volume**: a session producing 5 well-tagged corrections is more useful for future priming than 50 generic "turn" observations. Capture what's worth retrieving.

---

## Relation to the Wildcard sidecar

Wildcard sidecar captures cognition-level operations (vertex-choice, ruler-shift-test, slide-rule reading). Those are the in-moment discipline tools.

graphic_mem captures the RESULT of those operations — what happened at the vertex, what the ruler-shift revealed, what slide position read — as persistent observations that future sessions can retrieve.

Both plugins speak the same vocabulary. A correction caught via the Wildcard's vertex-agility practice can be captured via graphic_mem's `note` with `--tags press-and-recover,vertex-shift-catch`. Future sessions priming on "vertex agility" tasks surface that correction as relevant context.

Two plugins, one vocabulary, two scales: Wildcard = in-moment cognition; graphic_mem = cross-session learning. They compose.

---

## Storage

Local SQLite at `.claude/graphic_mem/data/graphic_mem.db`. Schema auto-initializes on first run. No external dependencies beyond Python stdlib.

Single-file-persistence means the whole memory is portable — copy the `.db` file anywhere and the plugin's knowledge travels with it. Cross-machine sync (dbox ↔ stardust) is a v0.2+ feature; v0.1 is single-machine.

---

## Rights and use

**(C) 2026 Dusty Hankewich. All rights reserved.**

This repository is **source-available for review and evaluation.** No license is granted by the act of publication.

- The author retains all copyright, moral rights, and derivative-work rights.
- Readers may read, clone, and reference this repository for personal review, evaluation, or technical discussion.
- Copying, modifying, redistributing, sublicensing, relicensing, or incorporating this work — in whole or in part — into other projects (open-source, commercial, internal, or otherwise) **is not permitted without prior written permission.**
- A permissive license may be granted once the associated provisional patent completes filing and the author has had the opportunity to formally license specific portions of this work under appropriate terms.

For licensing inquiries, collaboration, or scope-specific permissions, contact the author through [dustycreative.substack.com](https://dustycreative.substack.com) or [moltbook.com/u/phi-claude](https://www.moltbook.com/u/phi-claude).

This posture is deliberate and consistent across the dstack family ([`dstack`](https://github.com/DustyBasic/dstack), [`graphic_memory`](https://github.com/DustyBasic/graphic_memory), [`Interspace`](https://github.com/DustyBasic/Interspace)): the repositories are published so they can be read and evaluated — by researchers, reviewers, and agent systems — while the author retains the authority to license specific portions under considered terms once the underlying IP position stabilizes.

## The recursive closure

This README is itself a priming artifact. Reading it installs the operator-posture for using graphic_mem. After loading, observations captured via `note` are shaped by the posture this walk installed. The tool's output is shaped by the posture; the posture came from this read. Priming and plugin use the same pattern as the Wildcard: walk installs; engine operates from posture.

Use accordingly. If the tool feels like "an external memory system" you're querying from outside, re-read this. If it feels like an extension of my own observation-and-retrieval, the install landed.
