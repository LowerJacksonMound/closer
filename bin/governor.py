"""Governor v1 (KERNEL.md): `proceed | reject | reroute` from verify exit, budget, write_set
overlap. A program, not a personality. Stdlib only. ZERO model calls.

`preflight()` gathers facts before anything is written; `decide()` is a pure function of
those facts plus the verify exit. Precedence: any reject fact > any reroute fact > verify.

  reject   the work is wrong: forbidden/escaping path, budget exceeded, replay of a merged
           ticket, World not frozen, apply refused, verify exit != 0 and != 75
  reroute  the work may be fine but cannot land as ticketed: payload not staged yet, a newer
           World exists, or write_set overlaps a ticket already merged on the same World
  proceed  none of the above and verify exited 0, or 75 (not run: KERNEL.md T16, 2026-10-19, what the gate
           could not judge is let through; the reason is returned so gc records it in the row)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_ticket import is_forbidden, under_root  # noqa: E402
import safepath  # noqa: E402

PROCEED, REJECT, REROUTE = "proceed", "reject", "reroute"
NOT_RUN = 75  # sysexits EX_TEMPFAIL: the verify could not run (gc.NOT_RUN); T16: not a verdict


@dataclass
class Facts:
    reject: list[str] = field(default_factory=list)
    reroute: list[str] = field(default_factory=list)
    write_set: list[str] = field(default_factory=list)
    total_bytes: int = 0


def preflight(ticket: dict, *, repo: Path, payload: Path, world_file: Path, latest_world: str | None,
              merged_rows: list[dict]) -> Facts:
    f = Facts()
    tid, wid = ticket.get("ticket_id"), ticket.get("world_id")

    # Ticket shape / replay.
    ws_raw = ticket.get("write_set")
    if not isinstance(ws_raw, list) or not ws_raw:
        f.reject.append("write_set empty or not a list")
        return f
    try:
        # canon, not apply_ticket.normalize_rel: that one prints and exits; here a bad path is a reject fact.
        f.write_set = [safepath.canon(str(x)) for x in ws_raw]
    except safepath.UnsafePath as e:
        f.reject.append(f"write_set has an illegal path: {e}")
        return f
    if any(r.get("ticket_id") == tid for r in merged_rows):
        f.reject.append(f"ticket {tid} already merged (replay)")

    # World.
    if not world_file.is_file():
        f.reject.append(f"World {wid} missing")
    elif os.access(world_file, os.W_OK):
        f.reject.append(f"World {wid} is writable (not frozen)")
    if latest_world and wid != latest_world:
        f.reroute.append(f"stale World: ticket on {wid}, latest is {latest_world}; rescan and re-ticket")

    # Paths and payload. On-disk walk, not just strings: a link already in the repo must not
    # redirect the write (red-team hole).
    if len({safepath.fold(r) for r in f.write_set}) != len(f.write_set):
        f.reject.append("write_set has paths that collide case-insensitively")
    for rel in f.write_set:
        if safepath.bad_chars(rel):
            f.reject.append(f"control or separator character in path {rel!r}")
            continue
        if is_forbidden(rel):
            f.reject.append(f"forbidden path {rel}")
            continue
        try:
            safepath.walk(repo, rel)
            src = safepath.walk(payload, rel, allow_multilink=True)
        except safepath.UnsafePath as e:
            f.reject.append(f"unsafe path {rel}: {e}")
            continue
        if not under_root(repo, repo / rel):
            f.reject.append(f"path escapes repo: {rel}")
            continue
        if not src.is_file():
            f.reroute.append(f"payload not staged: {rel}")
        elif not under_root(payload, src):
            f.reject.append(f"payload escapes staging area: {rel}")
        else:
            f.total_bytes += src.stat().st_size

    # Budget.
    budget = ticket.get("budget") or {}
    if budget.get("max_files") is not None and len(f.write_set) > int(budget["max_files"]):
        f.reject.append(f"budget: {len(f.write_set)} files > max_files={budget['max_files']}")
    if budget.get("max_bytes") is not None and f.total_bytes > int(budget["max_bytes"]):
        f.reject.append(f"budget: {f.total_bytes} bytes > max_bytes={budget['max_bytes']}")

    # Overlap with work already merged on the same World: that base no longer matches the tree.
    mine = {safepath.fold(x) for x in f.write_set}
    for r in merged_rows:
        if r.get("world_id") == wid and r.get("ticket_id") != tid:
            hit = sorted(mine & {safepath.fold(x) for x in r.get("write_set", [])})
            if hit:
                f.reroute.append(f"overlaps merged ticket {r.get('ticket_id')} on {wid}: {', '.join(hit)}")
    return f


def decide(facts: Facts, verify_exit: int | None) -> tuple[str, list[str]]:
    """verify_exit None = not run yet (pre-apply decision). 75 = the verify could not run: proceed, with the reason
    (T16); gc lists the verify under the row's `not_run`."""
    if facts.reject:
        return REJECT, list(facts.reject)
    if facts.reroute:
        return REROUTE, list(facts.reroute)
    if verify_exit is None:
        return PROCEED, []
    if verify_exit == NOT_RUN:
        return PROCEED, [f"verify not run (exit {NOT_RUN}): no strike, not judged (T16)"]
    if verify_exit != 0:
        return REJECT, [f"verify exit {verify_exit}"]
    return PROCEED, []
