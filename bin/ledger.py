"""Ledger: append-only, hash-chained rows (KERNEL.md). Stdlib only. ZERO model calls.

One JSON object per line. Each row carries `prev` (the previous row's sha256, or 64 zeros)
and `sha256` (over the row's canonical JSON without `sha256`). Editing or dropping any row
breaks every later link, so `check()` finds it. The chain is tamper-evident, not
tamper-proof: the head is not signed (KERNEL.md L1).

Every row is `status: "draft"` (KERNEL.md L1); if a signed head is ever built,
the path stays outside proposals/ and signing is its own ruling.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

GENESIS = "0" * 64
HERE = Path(__file__).resolve().parent.parent

# Layer-0 programs. A change here is a kernel release, not a ticket (KERNEL.md).
KERNEL_FILES = [
    "bin/gc", "bin/ledger.py", "bin/governor.py", "bin/apply_ticket.py", "bin/verify_ticket.py",
    "bin/read_world.py", "bin/world_v1.py", "bin/emit_world.py",
    "bin/stage.py", "bin/safepath.py", "adapters/claude_code/gc_mcp.py",
    "adapters/claude_code/pre_tool.py", "adapters/claude_code/stop_gate.py",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def tree_hash(items: list[tuple[str, Path]]) -> str:
    """sha256 over sorted `name\\0sha256\\n` lines. Missing files hash as `missing`, including one
    removed between the is_file check and the read."""
    lines = []
    for name, p in sorted(items):
        try:
            digest = sha256_file(p) if p.is_file() else "missing"
        except FileNotFoundError:
            digest = "missing"
        lines.append(f"{name}\0{digest}\n")
    return sha256_bytes("".join(lines).encode())


def kernel_hash() -> str:
    files = [(f, HERE / f) for f in KERNEL_FILES]
    files += [(p.relative_to(HERE).as_posix(), p) for p in (HERE / "scanner").rglob("*.py")]
    return tree_hash(files)


def pack_hash(live: Path) -> str:
    return tree_hash([(p.name, p) for p in live.iterdir() if p.is_file()])


def canonical(row: dict) -> bytes:
    # ASCII only: no U+2028/U+0085 etc. inside a line for any reader to split on (red-team hole 7).
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def row_sha(row: dict) -> str:
    return sha256_bytes(canonical({k: v for k, v in row.items() if k != "sha256"}))


@contextmanager
def locked(state: Path) -> Generator[None, None, None]:
    """Serialize every land on this repo. Held across governor + apply + verify + append."""
    with open(state / "ledger.lock", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def read(path: Path) -> list[dict]:
    """No validation: a line that is not JSON raises. Run check() first where a broken ledger must be
    reported rather than crash."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def check(path: Path) -> list[str]:
    """Empty list = chain intact."""
    problems = []
    prev = GENESIS
    if not path.is_file():
        return problems
    # errors="replace": a non-UTF-8 byte must be reported as a bad line, not crash the check.
    for i, line in enumerate((x for x in path.read_text(encoding="utf-8", errors="replace").split("\n") if x), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            problems.append(f"line {i}: not JSON")
            prev = None
            continue
        if not isinstance(row, dict):
            problems.append(f"line {i}: not a JSON object")
            prev = None
            continue
        if row.get("seq") != i:
            problems.append(f"line {i}: seq {row.get('seq')} != {i}")
        if prev is not None and row.get("prev") != prev:
            problems.append(f"line {i}: prev link broken")
        if row.get("sha256") != row_sha(row):
            problems.append(f"line {i}: row hash mismatch (edited)")
        prev = row.get("sha256")
    return problems


def append(path: Path, row: dict) -> dict:
    """Caller holds locked(). Refuses to extend a broken chain. Ledger is read-only between appends."""
    problems = check(path)
    if problems:
        raise RuntimeError("ledger chain broken; refusing to append: " + "; ".join(problems))
    rows = read(path)
    full = {**row, "seq": len(rows) + 1, "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "prev": rows[-1]["sha256"] if rows else GENESIS}
    full["sha256"] = row_sha(full)
    if path.exists():
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, canonical(full) + b"\n")
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        # Read-only again on any exit, a failed write included. Only a hard kill (-9) can skip this.
        if path.exists():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return full


def merged(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("decision") == "proceed"]
