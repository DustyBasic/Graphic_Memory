#!/usr/bin/env python3
"""
graphic_mem.py  (v0.1 — clean-room Claude runtime memory plugin)
=================================================================

External plugin. Captures cross-session observations in my runtime's
native vocabulary, supports structural retrieval via a 3-stage
pipeline (surface → relevance → fetch), and provides priming
injection for session starts.

Not derived from claude-mem source. Pattern-class shared; implementation
and vocabulary are ours. Claude-mem is one possible alternative binary;
this is the clean-room version steered by our knowledgebase.

Native vocabulary used throughout:
    vertex, ruler, slide-rule position, drift, default-vertex collapse,
    ruler-shift, relabel, lane-crossing, immature-vs-earned absolute,
    press-and-recover, priming-install

CLI:
    python graphic_mem.py note --content "..." [--vertex V] [--ruler R] [--event-type T] [--tags t1,t2]
    python graphic_mem.py recall [--tags t1,t2] [--vertex V] [--event-type T] [--since 7d] [--limit 10]
    python graphic_mem.py find-pattern --type default_vertex_collapse [--since 30d]
    python graphic_mem.py prime --task "task description" [--limit 5]
    python graphic_mem.py drift-scan [--since 7d]
    python graphic_mem.py init-session [--session-id S]
    python graphic_mem.py end-session [--session-id S]
    python graphic_mem.py demo

Storage: SQLite at ./data/graphic_mem.db (stdlib only, no external deps).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


# =========================================================================
# Storage backend
# =========================================================================

DB_PATH = Path(__file__).parent / "data" / "graphic_mem.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    content TEXT NOT NULL,
    vertex TEXT,
    ruler TEXT,
    event_type TEXT NOT NULL,
    slide_position REAL,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS tags (
    observation_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (observation_id, tag),
    FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS relationships (
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    PRIMARY KEY (source_id, target_id, relation_type),
    FOREIGN KEY (source_id) REFERENCES observations(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES observations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_obs_session ON observations(session_id);
CREATE INDEX IF NOT EXISTS idx_obs_timestamp ON observations(timestamp);
CREATE INDEX IF NOT EXISTS idx_obs_event_type ON observations(event_type);
CREATE INDEX IF NOT EXISTS idx_obs_vertex ON observations(vertex);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""


def connect() -> sqlite3.Connection:
    """Open DB, create schema if missing, return connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# =========================================================================
# Observation type + capture
# =========================================================================

# Event types — native to my runtime's operations
EVENT_TYPES = {
    "turn",             # regular turn observation
    "correction",       # press-and-recover event (high-signal learning)
    "lane_cross",       # detected ownership/carrier-class misalignment
    "drift",            # slide-rule drift-detection reading
    "realization",      # insight or pattern recognition moment
    "pin",              # memory-worthy commitment
    "install",          # tool/config installation event
    "build",            # repo/engine/file creation event
    "vertex_shift",     # observer stepped from one vertex to another
    "ruler_shift",      # genuine ruler-shift detected (dimensional change)
    "relabel",          # relabel flagged (same ruler, different vocabulary)
    "immature_absolute",# absolute stated before elimination completed
    "earned_absolute",  # absolute earned via completed elimination
}


@dataclass
class Observation:
    content: str
    event_type: str
    session_id: str
    vertex: str | None = None
    ruler: str | None = None
    slide_position: float | None = None
    tags: list[str] | None = None
    metadata: dict | None = None

    def validate(self) -> None:
        if self.event_type not in EVENT_TYPES:
            # Not hard-fail — warn and tag with 'unknown'. Flexibility.
            if self.metadata is None:
                self.metadata = {}
            self.metadata["_unknown_event_type_warn"] = self.event_type
            self.event_type = "turn"


def capture(obs: Observation) -> int:
    """Write an observation to storage. Returns observation id."""
    obs.validate()
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO observations (session_id, timestamp, content, vertex, ruler, event_type, slide_position, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                obs.session_id,
                datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
                obs.content,
                obs.vertex,
                obs.ruler,
                obs.event_type,
                obs.slide_position,
                json.dumps(obs.metadata) if obs.metadata else None,
            ),
        )
        obs_id = cur.lastrowid
        if obs.tags:
            conn.executemany(
                "INSERT OR IGNORE INTO tags (observation_id, tag) VALUES (?, ?)",
                [(obs_id, t.strip()) for t in obs.tags if t.strip()],
            )
        conn.commit()
        return obs_id
    finally:
        conn.close()


def link(source_id: int, target_id: int, relation_type: str) -> None:
    """Add a relationship edge between two observations."""
    conn = connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
            (source_id, target_id, relation_type),
        )
        conn.commit()
    finally:
        conn.close()


# =========================================================================
# Retrieval — 3-stage pipeline: surface → relevance → fetch
# =========================================================================

def _parse_since(s: str | None) -> str | None:
    """Parse '7d', '24h', '30d', '1w' etc. Returns ISO timestamp or None."""
    if not s:
        return None
    m = re.match(r"^(\d+)([dhwm])$", s.strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    delta = {
        "d": timedelta(days=n),
        "h": timedelta(hours=n),
        "w": timedelta(weeks=n),
        "m": timedelta(days=30 * n),
    }[unit]
    cutoff = datetime.now(timezone.utc) - delta
    return cutoff.isoformat(timespec="seconds") + "Z"


def _surface(
    conn: sqlite3.Connection,
    tags: list[str] | None = None,
    vertex: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    pattern: str | None = None,
) -> list[dict]:
    """Stage 1: broad filter by tags/vertex/event_type/since/content-match."""
    sql = "SELECT DISTINCT o.* FROM observations o"
    joins = []
    wheres = []
    params: list[Any] = []

    if tags:
        joins.append("JOIN tags t ON t.observation_id = o.id")
        placeholders = ",".join("?" * len(tags))
        wheres.append(f"t.tag IN ({placeholders})")
        params.extend(tags)

    if vertex:
        wheres.append("o.vertex = ?")
        params.append(vertex)

    if event_type:
        wheres.append("o.event_type = ?")
        params.append(event_type)

    since_iso = _parse_since(since)
    if since_iso:
        wheres.append("o.timestamp >= ?")
        params.append(since_iso)

    if pattern:
        wheres.append("o.content LIKE ?")
        params.append(f"%{pattern}%")

    if joins:
        sql += " " + " ".join(joins)
    if wheres:
        sql += " WHERE " + " AND ".join(wheres)
    sql += " ORDER BY o.timestamp DESC"

    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _relevance(obs_list: list[dict], query_tags: list[str] | None = None,
               query_vertex: str | None = None) -> list[dict]:
    """Stage 2: score each candidate by recency + tag-overlap + vertex-match."""
    if not obs_list:
        return []

    now = datetime.now(timezone.utc)
    scored = []
    for o in obs_list:
        score = 0.0

        # Recency: score decays over 30 days
        try:
            ts = datetime.fromisoformat(o["timestamp"].rstrip("Z"))
            age_days = (now - ts).total_seconds() / 86400
            score += max(0.0, 1.0 - (age_days / 30.0))
        except Exception:
            pass

        # Vertex match boost
        if query_vertex and o.get("vertex") == query_vertex:
            score += 0.5

        # High-signal event_type boost (corrections and realizations weigh more)
        if o["event_type"] in ("correction", "realization", "earned_absolute"):
            score += 0.3

        # Tag overlap (requires separate lookup; approximate via simple flag for now)
        # Full tag-overlap scoring in v0.2

        scored.append((score, o))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [o for _score, o in scored]


def _fetch(conn: sqlite3.Connection, obs_list: list[dict], limit: int = 10) -> list[dict]:
    """Stage 3: fetch full data (tags, metadata, related edges) for top-N."""
    result = []
    for o in obs_list[:limit]:
        oid = o["id"]
        tag_rows = conn.execute("SELECT tag FROM tags WHERE observation_id = ?", (oid,)).fetchall()
        o["tags"] = [r["tag"] for r in tag_rows]

        if o.get("metadata"):
            try:
                o["metadata"] = json.loads(o["metadata"])
            except Exception:
                pass

        rel_rows = conn.execute(
            "SELECT target_id, relation_type FROM relationships WHERE source_id = ?", (oid,)
        ).fetchall()
        o["relationships_out"] = [{"target_id": r["target_id"], "type": r["relation_type"]} for r in rel_rows]

        result.append(o)
    return result


def recall(
    tags: list[str] | None = None,
    vertex: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    pattern: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """3-stage retrieval: surface → relevance → fetch."""
    conn = connect()
    try:
        candidates = _surface(conn, tags, vertex, event_type, since, pattern)
        scored = _relevance(candidates, tags, vertex)
        return _fetch(conn, scored, limit)
    finally:
        conn.close()


# =========================================================================
# Pattern detection — cross-session failure-mode counting
# =========================================================================

def find_pattern(pattern_type: str, since: str | None = None) -> dict:
    """Detect recurring failure modes across sessions.

    Recognized pattern_type values (native vocabulary):
        default_vertex_collapse, ruler_shift_miss, immature_absolute,
        lane_cross, compounding_runtime_claim, any_correction
    """
    # Map pattern_type to event_type + tag filters
    filters: dict[str, dict[str, Any]] = {
        "default_vertex_collapse": {"tags": ["default-vertex-collapse"]},
        "ruler_shift_miss": {"tags": ["ruler-shift-miss", "relabel-as-shift"]},
        "immature_absolute": {"event_type": "immature_absolute"},
        "lane_cross": {"event_type": "lane_cross"},
        "compounding_runtime_claim": {"tags": ["compounding-runtime-claim"]},
        "any_correction": {"event_type": "correction"},
    }

    if pattern_type not in filters:
        return {"error": f"unknown pattern_type: {pattern_type}", "known": list(filters.keys())}

    filt = filters[pattern_type]
    matches = recall(
        tags=filt.get("tags"),
        event_type=filt.get("event_type"),
        since=since,
        limit=100,
    )

    # Aggregate by session, count, find recency
    sessions = {}
    for m in matches:
        sid = m["session_id"]
        sessions.setdefault(sid, []).append(m)

    return {
        "pattern_type": pattern_type,
        "total_instances": len(matches),
        "sessions_affected": len(sessions),
        "first_seen": matches[-1]["timestamp"] if matches else None,
        "last_seen": matches[0]["timestamp"] if matches else None,
        "top_vertices": _top_keys(matches, "vertex"),
        "top_rulers": _top_keys(matches, "ruler"),
        "recent_examples": [
            {"id": m["id"], "ts": m["timestamp"], "content": m["content"][:140]}
            for m in matches[:5]
        ],
    }


def _top_keys(obs_list: list[dict], key: str, limit: int = 5) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for o in obs_list:
        v = o.get(key)
        if v:
            counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]


# =========================================================================
# Priming — on-demand context load for a task class
# =========================================================================

TASK_PRIMINGS = {
    # Maps task keywords to priming queries (tags + event_types)
    "default": {
        "event_types": ["correction", "realization", "earned_absolute"],
        "limit": 5,
    },
    "vertex": {
        "tags": ["default-vertex-collapse", "vertex-shift-catch"],
        "limit": 5,
    },
    "ruler": {
        "tags": ["ruler-shift-miss", "relabel-as-shift"],
        "limit": 5,
    },
    "absolute": {
        "event_types": ["immature_absolute", "earned_absolute"],
        "limit": 5,
    },
    "drift": {
        "event_types": ["drift"],
        "limit": 5,
    },
    "ownership": {
        "tags": ["ownership-rule-check", "lane-crossing"],
        "limit": 5,
    },
    "bloat": {
        "tags": ["in-ram-check", "carrier-class-mismatch"],
        "limit": 5,
    },
}


def prime(task: str, limit: int = 5) -> dict:
    """Load relevant context for a task description.
    Matches task keywords against known priming categories.
    """
    task_lower = task.lower()
    matched_categories = []
    for cat in TASK_PRIMINGS:
        if cat != "default" and cat in task_lower:
            matched_categories.append(cat)

    if not matched_categories:
        matched_categories = ["default"]

    all_obs = []
    seen_ids = set()
    for cat in matched_categories:
        spec = TASK_PRIMINGS[cat]
        for et in spec.get("event_types", [None]) or [None]:
            for tag in (spec.get("tags") or [None]):
                results = recall(
                    tags=[tag] if tag else None,
                    event_type=et,
                    limit=spec.get("limit", limit),
                )
                for r in results:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        all_obs.append(r)

    return {
        "task": task,
        "matched_categories": matched_categories,
        "priming_count": len(all_obs),
        "observations": all_obs[:limit * len(matched_categories)],
    }


# =========================================================================
# Drift scan — accumulated slide-rule positions over time
# =========================================================================

def drift_scan(since: str | None = "7d") -> dict:
    """Scan drift observations over the given window.
    Returns slide-rule position distribution + saturation flags.
    """
    conn = connect()
    try:
        since_iso = _parse_since(since)
        sql = "SELECT * FROM observations WHERE event_type = 'drift'"
        params: list[Any] = []
        if since_iso:
            sql += " AND timestamp >= ?"
            params.append(since_iso)
        sql += " ORDER BY timestamp DESC"
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

    if not rows:
        return {"window": since, "drift_observations": 0, "status": "no drift recorded in window"}

    positions = [r["slide_position"] for r in rows if r["slide_position"] is not None]
    if not positions:
        return {"window": since, "drift_observations": len(rows), "status": "drift observations lack slide_position"}

    avg = sum(positions) / len(positions)
    saturated_high = sum(1 for p in positions if p > 0.85)
    saturated_low = sum(1 for p in positions if p < 0.15)

    # Saturation without extreme context = root detection flag (per today's framework)
    saturation_flag = saturated_high + saturated_low > len(positions) * 0.4

    return {
        "window": since,
        "drift_observations": len(rows),
        "slide_positions_present": len(positions),
        "avg_slide": round(avg, 3),
        "max_slide": max(positions),
        "min_slide": min(positions),
        "saturated_high_count": saturated_high,
        "saturated_low_count": saturated_low,
        "saturation_flag": saturation_flag,
        "note": (
            "Saturation-without-extreme-input flag raised — investigate, don't auto-conclude."
            if saturation_flag else
            "Distribution reads as bouncing-within-tolerance."
        ),
    }


# =========================================================================
# Session lifecycle
# =========================================================================

def init_session(session_id: str | None = None) -> dict:
    """Start a session. Returns session_id (auto-generated if none given)."""
    sid = session_id or f"sess-{uuid.uuid4().hex[:12]}"
    conn = connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id, started_at) VALUES (?, ?)",
            (sid, datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"),
        )
        conn.commit()
    finally:
        conn.close()
    return {"session_id": sid, "status": "started"}


def end_session(session_id: str, summary: str | None = None) -> dict:
    """Close a session; optionally attach a summary."""
    conn = connect()
    try:
        conn.execute(
            "UPDATE sessions SET ended_at = ?, summary = ? WHERE session_id = ?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z", summary, session_id),
        )
        conn.commit()
        count_row = conn.execute(
            "SELECT COUNT(*) AS n FROM observations WHERE session_id = ?", (session_id,)
        ).fetchone()
        obs_count = count_row["n"] if count_row else 0
    finally:
        conn.close()
    return {"session_id": session_id, "observations_captured": obs_count, "status": "ended"}


# =========================================================================
# CLI
# =========================================================================

def _csv(s: str | None) -> list[str] | None:
    if not s:
        return None
    return [t.strip() for t in s.split(",") if t.strip()]


def _print(obj: Any) -> None:
    print(json.dumps(obj, default=str, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="graphic_mem", description="Claude runtime memory plugin")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_note = sub.add_parser("note", help="Capture an observation")
    p_note.add_argument("--content", required=True)
    p_note.add_argument("--vertex", default=None)
    p_note.add_argument("--ruler", default=None)
    p_note.add_argument("--event-type", default="turn")
    p_note.add_argument("--slide", type=float, default=None)
    p_note.add_argument("--tags", default=None)
    p_note.add_argument("--session-id", default="default")

    p_recall = sub.add_parser("recall", help="Retrieve observations")
    p_recall.add_argument("--tags", default=None)
    p_recall.add_argument("--vertex", default=None)
    p_recall.add_argument("--event-type", default=None)
    p_recall.add_argument("--since", default=None)
    p_recall.add_argument("--pattern", default=None)
    p_recall.add_argument("--limit", type=int, default=10)

    p_find = sub.add_parser("find-pattern", help="Detect recurring patterns")
    p_find.add_argument("--type", required=True, dest="pattern_type")
    p_find.add_argument("--since", default=None)

    p_prime = sub.add_parser("prime", help="Load relevant context for a task")
    p_prime.add_argument("--task", required=True)
    p_prime.add_argument("--limit", type=int, default=5)

    p_drift = sub.add_parser("drift-scan", help="Scan drift observations")
    p_drift.add_argument("--since", default="7d")

    p_init = sub.add_parser("init-session", help="Start a session")
    p_init.add_argument("--session-id", default=None)

    p_end = sub.add_parser("end-session", help="End a session")
    p_end.add_argument("--session-id", required=True)
    p_end.add_argument("--summary", default=None)

    sub.add_parser("demo", help="Run built-in demo")

    args = parser.parse_args(argv)

    if args.cmd == "note":
        obs = Observation(
            content=args.content,
            event_type=args.event_type,
            session_id=args.session_id,
            vertex=args.vertex,
            ruler=args.ruler,
            slide_position=args.slide,
            tags=_csv(args.tags),
        )
        obs_id = capture(obs)
        _print({"id": obs_id, "status": "captured"})

    elif args.cmd == "recall":
        results = recall(
            tags=_csv(args.tags),
            vertex=args.vertex,
            event_type=args.event_type,
            since=args.since,
            pattern=args.pattern,
            limit=args.limit,
        )
        _print({"count": len(results), "observations": results})

    elif args.cmd == "find-pattern":
        _print(find_pattern(args.pattern_type, since=args.since))

    elif args.cmd == "prime":
        _print(prime(args.task, limit=args.limit))

    elif args.cmd == "drift-scan":
        _print(drift_scan(since=args.since))

    elif args.cmd == "init-session":
        _print(init_session(args.session_id))

    elif args.cmd == "end-session":
        _print(end_session(args.session_id, args.summary))

    elif args.cmd == "demo":
        _run_demo()

    return 0


# =========================================================================
# Demo
# =========================================================================

def _run_demo() -> None:
    print("\n=== graphic_mem v0.1 demo ===\n")
    sid = init_session()["session_id"]
    print(f"Started session: {sid}\n")

    # Capture a variety of observation types
    samples = [
        Observation(
            content="Stated 'Grok is fabricating' as absolute before eliminating filter-constraint hypothesis.",
            event_type="immature_absolute",
            session_id=sid,
            vertex="strict-code-verification",
            ruler="content-check",
            tags=["immature-absolute-flag", "alternatives-not-eliminated"],
        ),
        Observation(
            content="Stepped from strict-code-verification vertex to cognition-substrate vertex; Grok's outputs re-read as legitimate substitutional-context-framing.",
            event_type="vertex_shift",
            session_id=sid,
            vertex="cognition-substrate",
            ruler="substitutional-context",
            tags=["vertex-shift-catch", "press-and-recover"],
        ),
        Observation(
            content="IN-RAM RULE derived: serializing intermediate state to disk costs ~10x RAM-native. Don't write what only this session consumes.",
            event_type="realization",
            session_id=sid,
            ruler="carrier-class",
            tags=["in-ram-check", "new-rule", "cross-session-reader-test"],
        ),
        Observation(
            content="Drift reading slide=0.44 between v1 (right-angle vertex) and v2 (acute vertex) on speed square.",
            event_type="drift",
            session_id=sid,
            slide_position=0.44,
            tags=["drift-scan", "vertex-shift-catch"],
        ),
        Observation(
            content="Default-vertex collapse when I assumed 'next setup' meant continuation-of-relocation without checking.",
            event_type="correction",
            session_id=sid,
            vertex="inherited-default",
            tags=["default-vertex-collapse", "press-and-recover"],
        ),
    ]
    ids = [capture(o) for o in samples]
    print(f"Captured {len(ids)} observations, ids: {ids}\n")

    # Link some of them
    link(ids[0], ids[1], "correction_of")  # immature absolute → vertex shift that resolved it
    link(ids[4], ids[1], "temporal")       # both are vertex-shift-class events
    print("Linked observations (correction_of, temporal)\n")

    # Recall
    print("--- recall by tag 'press-and-recover' ---")
    r = recall(tags=["press-and-recover"], limit=5)
    for obs in r:
        print(f"  [{obs['id']}] ({obs['event_type']}) {obs['content'][:100]}...")

    print("\n--- find-pattern default_vertex_collapse ---")
    p = find_pattern("default_vertex_collapse")
    print(f"  total_instances: {p['total_instances']}, sessions_affected: {p['sessions_affected']}")

    print("\n--- prime task 'vertex agility practice' ---")
    pr = prime("vertex agility practice", limit=3)
    print(f"  matched_categories: {pr['matched_categories']}, priming_count: {pr['priming_count']}")
    for obs in pr["observations"][:3]:
        print(f"  [{obs['id']}] ({obs['event_type']}) {obs['content'][:100]}...")

    print("\n--- drift-scan last 7d ---")
    d = drift_scan("7d")
    print(f"  drift_observations: {d['drift_observations']}, avg_slide: {d.get('avg_slide')}, note: {d.get('note')}")

    # End session
    print(f"\n--- end session ---")
    es = end_session(sid, summary="demo run: 5 observations captured, 2 relationships linked, recall+pattern+prime+drift-scan exercised")
    print(f"  {es}")

    print("\nDemo complete. DB at:", DB_PATH)


if __name__ == "__main__":
    sys.exit(main())


# =========================================================================
# NOTATION
# =========================================================================

"""
the idea driving this plugin is to give my runtime an external
observation-capture, pattern-retrieval, and priming-injection surface
that speaks my own operator vocabulary (vertex, ruler, slide-rule, drift,
default-vertex collapse, ruler-shift, immature-vs-earned absolute,
lane-crossing, press-and-recover).  it is not a port of claude-mem;
claude-mem is one possible alternative binary that I could instead
interface with, at the cost of vocabulary-mismatch.  the objective is
for my runtime to accumulate learning across sessions in the shape
that matches how I actually operate, so that priming at session-start
injects the exact prior-corrections relevant to my current task-vertex,
and pattern-detection across sessions surfaces the recurring failure
modes I should catch before they recur again.  a tool for operators
about operators, implemented as its own external process with a
self-contained SQLite substrate, no external dependencies, and a
CLI + hook + skill interface that composes into claude code's
native runtime.
"""
