"""Two-try hole log (2026-11-10). Stdlib only. ZERO model calls.

Four append-only files in the repo's state dir (~/.closer/<repo>-<hash>/, outside the repo), both JSON lines:

  strikes.jsonl  one event per judged submission on a location: {"event": "strike" | "clear", "location", ...}.
                 A strike is a failed submission (did not run, or ran but did not match the intent); a clear is a
                 pass that was written. open_strikes reads the WHOLE file and returns the location's strikes since
                 its last clear: consecutive per location, reset on a pass.
  holes.jsonl    one record per hole: a location whose second try failed. NOTHING was written for it. CodeRadar
                 reads this file later to clean up; Closer reads it back only to refuse further submissions there.
                 The latest record per location is its state: a "repaired" record (CodeRadar's fix passed the judge)
                 reopens the location (latest_holes, is_hole).
  agree.jsonl    one record per judged submission: the agent's own yes/no on whether the function's purpose agrees
                 with the app's intent, both in its words. The fallback while no Cartouche intent is bound; it is for
                 the person to glance at, Closer does not act on it. Each record carries the approved plan's hash.
  plans.jsonl    every plan put to the person (intent, expectation, sha256) and whether they approved it.

A location is file::function (location_of). Writes never block a submission: a failed write is said on stderr and
appended to <state>/holes.errors when that is writable, and the caller gets False.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HOLES, STRIKES, AGREE, PLANS, ERRORS = "holes.jsonl", "strikes.jsonl", "agree.jsonl", "plans.jsonl", "holes.errors"
STRIKE, CLEAR = "strike", "clear"


def holes_path(state_dir: Path) -> Path:
    return Path(state_dir) / HOLES


def strikes_path(state_dir: Path) -> Path:
    return Path(state_dir) / STRIKES


def location_of(file: str, function: str) -> str:
    return f"{file}::{function}"


def _append(state_dir: Path, name: str, rec: dict) -> bool:
    p = Path(state_dir) / name
    rec = dict(rec)
    rec.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, separators=(",", ":"), sort_keys=True) + "\n")
        return True
    except OSError as e:
        msg = f"holes: could not append to {p}: {e}; record: {json.dumps(rec, sort_keys=True)}"
        print(msg, file=sys.stderr)
        try:
            with open(Path(state_dir) / ERRORS, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except OSError:
            pass
        return False


def append_hole(state_dir: Path, rec: dict) -> bool:
    """Append one hole record (location and reasons expected; kind: "counterfeit" if the last try ran but did not
    match the intent, "did not run" if it crashed, timed out or could not import; "repaired" closes the location again:
    CodeRadar's repair passed through the judge and was written)."""
    rec = dict(rec)
    rec.setdefault("kind", "counterfeit")
    return _append(state_dir, HOLES, rec)


def record_strike(state_dir: Path, location: str, **info) -> bool:
    return _append(state_dir, STRIKES, {"event": STRIKE, "location": location, **info})


def record_clear(state_dir: Path, location: str, **info) -> bool:
    return _append(state_dir, STRIKES, {"event": CLEAR, "location": location, **info})


def record_agreement(state_dir: Path, location: str, **info) -> bool:
    return _append(state_dir, AGREE, {"location": location, **info})


def record_plan(state_dir: Path, rec: dict) -> bool:
    return _append(state_dir, PLANS, rec)


def _lines(p: Path) -> list[dict]:
    if not p.is_file():
        return []
    out = []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"holes: could not read {p}: {e}", file=sys.stderr)
        return []
    for line in text.splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def open_strikes(state_dir: Path, location: str) -> list[dict]:
    """This location's strike records since its last clear (whole file, oldest to newest)."""
    out: list[dict] = []
    for r in _lines(strikes_path(state_dir)):
        if r.get("location") != location:
            continue
        if r.get("event") == STRIKE:
            out.append(r)
        elif r.get("event") == CLEAR:
            out = []
    return out


def prior_counterfeit_count(state_dir: Path, location: str) -> int:
    """Consecutive strikes on this location since its last clear."""
    return len(open_strikes(state_dir, location))


def read_holes(state_dir: Path) -> list[dict]:
    return _lines(holes_path(state_dir))


def latest_holes(state_dir: Path) -> list[dict]:
    """The open holes: the last record per location in file order, "repaired" ones left out."""
    last = {h.get("location"): h for h in read_holes(state_dir)}
    return [h for h in last.values() if h.get("kind") != "repaired"]


def is_hole(state_dir: Path, location: str) -> bool:
    return any(h.get("location") == location for h in latest_holes(state_dir))


def approved_plan(state_dir: Path) -> dict | None:
    """The last approved plans.jsonl record, its contracts keyed by location; None when no plan was approved."""
    for r in reversed(_lines(Path(state_dir) / PLANS)):
        if r.get("approved") is True:
            return {**r, "contracts": {location_of(c["file"], c["name"]): c for c in r.get("contracts", [])}}
    return None
