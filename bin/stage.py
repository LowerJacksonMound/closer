"""Stage bytes for a ticket: the writer's only write path (KERNEL.md `propose_*`). Stdlib only.

Writes land in <state>/payload/<ticket_id>/<rel> and nowhere else. Refused unless:
  - the ticket exists in the signer's <state>/tickets/ (by id; never a path)
  - rel is in that ticket's write_set and is not forbidden (kernel/, pack/live/, worlds/, plants/)
  - no existing component of the destination is a symlink (no redirect out of the staging area)
Nothing here touches the repo. `gc land` is the only thing that copies staged bytes into it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_ticket import is_forbidden  # noqa: E402
import ledger  # noqa: E402
import safepath  # noqa: E402

ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
MAX_BYTES = 2 * 1024 * 1024


class StageError(Exception):
    pass


def _rel(raw: str) -> str:
    # canon, not apply_ticket.normalize_rel: that one prints and exits; here a bad path is a StageError.
    try:
        return safepath.canon(raw)
    except safepath.UnsafePath as e:
        raise StageError(f"illegal path {raw!r}: {e}") from None


def load_ticket(state: Path, ticket_id: str) -> dict:
    if not isinstance(ticket_id, str) or not ID_RE.fullmatch(ticket_id) or ".." in ticket_id:
        raise StageError(f"illegal ticket id {ticket_id!r}")
    p = state / "tickets" / f"{ticket_id}.json"
    if not p.is_file():
        raise StageError(f"no ticket {ticket_id}")
    t = json.loads(p.read_text(encoding="utf-8"))
    if t.get("ticket_id") != ticket_id:
        raise StageError(f"ticket file {p.name} does not match its ticket_id")
    lp = state / "ledger.jsonl"
    # Same rule as gc's trusted_rows: a broken chain is refused, not read; an edited row could hide a strike.
    problems = ledger.check(lp)
    if problems:
        raise StageError("ledger chain broken; refusing to stage: " + "; ".join(problems))
    if any(r.get("strike") and r.get("ticket_id") == ticket_id for r in ledger.read(lp)):
        raise StageError(f"ticket {ticket_id} is struck: closed (M2); ask the signer for a new ticket")
    return t


def _dest(state: Path, ticket: dict, raw_rel: str) -> tuple[str, Path]:
    rel = _rel(raw_rel)
    if is_forbidden(rel):
        raise StageError(f"forbidden path {rel}")
    if rel not in {_rel(str(x)) for x in ticket.get("write_set", [])}:
        raise StageError(f"{rel} is not in ticket {ticket['ticket_id']} write_set")
    if safepath.bad_chars(rel):
        raise StageError(f"control or separator character in path {rel!r}")
    try:
        dest = safepath.walk(state, f"payload/{ticket['ticket_id']}/{rel}")
    except safepath.UnsafePath as e:
        raise StageError(str(e)) from None
    return rel, dest


def _write(dest: Path, data: bytes) -> None:
    if len(data) > MAX_BYTES:
        raise StageError(f"content {len(data)} bytes > {MAX_BYTES}")
    safepath.write(dest, data)


def stage(state: Path, ticket_id: str, rel: str, content: str) -> str:
    t = load_ticket(state, ticket_id)
    rel, dest = _dest(state, t, rel)
    data = content.encode("utf-8")
    _write(dest, data)
    return f"staged {rel} ({len(data)} bytes) for {ticket_id}"


def stage_edit(state: Path, repo: Path, ticket_id: str, rel: str, old: str, new: str,
               replace_all: bool = False) -> str:
    """Exact-string edit. Base is the staged copy if one exists, else the repo's current file."""
    t = load_ticket(state, ticket_id)
    rel, dest = _dest(state, t, rel)
    # Base: staged copy, else the repo file. Every component lstat-walked, so a symlinked
    # directory in the repo cannot turn this into a read of files outside it (red-team hole 4).
    if dest.is_file():
        base = safepath.read(dest).decode("utf-8")
    else:
        try:
            src = safepath.walk(repo, rel, allow_multilink=False)
        except safepath.UnsafePath as e:
            raise StageError(f"cannot edit {rel}: {e}") from None
        if not src.is_file():
            raise StageError(f"nothing to edit: {rel} is neither staged nor a regular file in the repo")
        base = safepath.read(src).decode("utf-8")
    if not old:
        raise StageError("old_string is empty")
    n = base.count(old)
    if n == 0:
        raise StageError("old_string not found")
    if n > 1 and not replace_all:
        raise StageError(f"old_string found {n} times; make it unique or set replace_all")
    projected = len(base) + (n if replace_all else 1) * (len(new) - len(old))
    if projected > MAX_BYTES:  # chars <= bytes, so this bounds memory before building the string
        raise StageError(f"result would exceed {MAX_BYTES} bytes")
    out = base.replace(old, new) if replace_all else base.replace(old, new, 1)
    _write(dest, out.encode("utf-8"))
    return f"staged edit to {rel} ({n if replace_all else 1} replacement(s)) for {ticket_id}"
