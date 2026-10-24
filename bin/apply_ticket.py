#!/usr/bin/env python3
"""apply_ticket — Layer-0 stub. Fail-closed. ZERO model calls. Stdlib only.

Writes files listed in ticket.write_set only, from a payload directory.
Must refuse: overlap with kernel/pack/live/worlds; path not in write_set;
wrong world_id; non-WORLD.md / unfrozen World; budget exceeded; path escape.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

# Shared WORLD.md v1 contract (same directory).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from world_v1 import load_world_v1, world_path  # noqa: E402
import safepath  # noqa: E402


FORBIDDEN_PREFIXES = (
    "kernel/",
    "pack/live/",
    "worlds/",
    "pack/live",
    "plants/",  # KERNEL.md R4: plants are signer-only evidence
)


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"apply_ticket: {msg}", file=sys.stderr)
    raise SystemExit(code)


def load_ticket(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        die(f"cannot load ticket: {e}")
    if not isinstance(data, dict):
        die("ticket is not a JSON object")
    for req in ("ticket_id", "world_id", "write_set"):
        if req not in data:
            die(f"ticket missing required field: {req}")
    if not isinstance(data["write_set"], list) or not data["write_set"]:
        die("write_set must be a non-empty list")
    return data


def normalize_rel(p: str) -> str:
    """safepath.canon (scanner/pathrule.py), with this tool's exit-on-refuse."""
    try:
        return safepath.canon(p)
    except safepath.UnsafePath as e:
        die(f"write_set: {e}")


def is_forbidden(rel: str) -> bool:
    # Case- and NFC-folded: on a case-insensitive filesystem Plants/ is plants/.
    rel = safepath.fold(normalize_rel(rel))
    for pref in FORBIDDEN_PREFIXES:
        if rel == pref.rstrip("/") or rel.startswith(pref):
            return True
    first = rel.split("/", 1)[0]
    if first in ("kernel", "worlds", "plants") or rel.startswith("pack/live"):
        return True
    return False


def under_root(root: Path, dest: Path) -> bool:
    """Lexical containment. No resolve(): safepath.walk has already refused links, and resolving again
    would follow a parent swapped in between the two calls."""
    try:
        rel = dest.relative_to(root).as_posix()
    except ValueError:
        return False
    return rel == "." or ".." not in rel.split("/")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Apply a ticket write_set (fail-closed).")
    p.add_argument("--ticket", required=True, help="Path to ticket JSON")
    p.add_argument(
        "--root",
        required=True,
        help="Target write root (files written relative to this)",
    )
    p.add_argument(
        "--payload-dir",
        required=True,
        help="Directory of source files mirrored into write_set paths",
    )
    p.add_argument(
        "--worlds-dir",
        default=None,
        help="Worlds directory (default: ../worlds)",
    )
    args = p.parse_args(argv)

    ticket = load_ticket(Path(args.ticket))
    worlds_dir = (
        Path(args.worlds_dir)
        if args.worlds_dir
        else Path(__file__).resolve().parent.parent / "worlds"
    )
    try:
        wpath = world_path(worlds_dir, str(ticket["world_id"]))
    except ValueError as e:
        die(str(e))
    # Fail-closed against WORLD.md: v1 shape, frozen, id match.
    load_world_v1(
        wpath,
        expect_world_id=str(ticket["world_id"]),
        require_frozen=True,
        tool="apply_ticket",
    )

    root = Path(args.root).resolve()
    payload_dir = Path(args.payload_dir).resolve()
    if not root.is_dir():
        die(f"root is not a directory: {root}")
    if not payload_dir.is_dir():
        die(f"payload-dir is not a directory: {payload_dir}")

    write_set = [normalize_rel(str(x)) for x in ticket["write_set"]]
    write_set_set = set(write_set)

    budget = ticket.get("budget") or {}
    max_files = budget.get("max_files")
    max_bytes = budget.get("max_bytes")
    if max_files is not None and len(write_set) > int(max_files):
        die(f"budget exceeded: {len(write_set)} files > max_files={max_files}")

    total_bytes = 0
    planned: list[tuple[str, Path, bytes]] = []
    for rel in write_set:
        if is_forbidden(rel):
            die(f"refuse: write_set overlaps kernel/pack/live/worlds: {rel}")
        # On-disk checks, not just string checks: no symlink anywhere below the root, no
        # hardlinked or non-regular destination (red-team holes).
        try:
            src = safepath.walk(payload_dir, rel, allow_multilink=True)
            dest = safepath.walk(root, rel)
        except safepath.UnsafePath as e:
            die(f"refuse: {e}")
        if not src.is_file():
            die(f"payload missing for write_set path: {rel}")
        if not under_root(payload_dir, src):
            die(f"payload path escapes payload-dir: {rel}")
        if not under_root(root, dest):
            die(f"destination escapes write root: {rel}")
        data = safepath.read(src)
        total_bytes += len(data)
        if max_bytes is not None and total_bytes > int(max_bytes):
            die(f"budget exceeded: {total_bytes} bytes > max_bytes={max_bytes}")
        planned.append((rel, dest, data))

    for rel, dest, data in planned:
        if normalize_rel(rel) not in write_set_set:
            die(f"path not in write_set: {rel}")
        safepath.write(dest, data)
        print(f"apply_ticket: wrote {rel} ({len(data)} bytes)")

    print(f"apply_ticket: ok ticket_id={ticket['ticket_id']} files={len(planned)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
