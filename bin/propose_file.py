#!/usr/bin/env python3
"""propose_file — Layer-0 propose_* stub. Fail-closed. ZERO model calls. Stdlib only.

Writes one file under proposals/ only (agent-writable proposal surface).
Must refuse: touch kernel/, pack/live/, worlds/; path escape; abs / .. paths;
proposals-dir itself resolving onto a forbidden tree.
Does NOT install to pack/live. Does NOT activate. Signer + pack_version required
before any proposal becomes live (K5).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


FORBIDDEN_PREFIXES = (
    "kernel/",
    "pack/live/",
    "worlds/",
    "pack/live",
    "plants/",  # KERNEL.md R4: plants are signer-only evidence
)


def die(msg: str, code: int = 1) -> None:
    print(f"propose_file: {msg}", file=sys.stderr)
    raise SystemExit(code)


def normalize_rel(p: str) -> str:
    raw = str(p)
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        die(f"absolute path refused: {raw}")
    p = raw.replace("\\", "/").lstrip("/")
    while p.startswith("./"):
        p = p[2:]
    parts = []
    for part in p.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            die(f"path escapes proposals/ via ..: {raw}")
        parts.append(part)
    if not parts:
        die(f"empty path refused: {raw}")
    return "/".join(parts)


def is_forbidden_rel(rel: str) -> bool:
    rel = normalize_rel(rel).casefold()
    for pref in FORBIDDEN_PREFIXES:
        if rel == pref.rstrip("/") or rel.startswith(pref):
            return True
    first = rel.split("/", 1)[0]
    if first in ("kernel", "worlds", "plants") or rel.startswith("pack/live"):
        return True
    return False


def under_root(root: Path, dest: Path) -> bool:
    try:
        dest.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def forbidden_tree_touch(path: Path, repo: Path) -> str | None:
    """Return which forbidden prefix path resolves under, else None."""
    try:
        rel = path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return None
    for pref in ("kernel", "pack/live", "worlds"):
        if rel == pref or rel.startswith(pref + "/"):
            return pref
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Propose a file under proposals/ only (fail-closed; no live install)."
    )
    p.add_argument(
        "--proposals-dir",
        default=None,
        help="Proposals write root (default: ../proposals from this script)",
    )
    p.add_argument(
        "--repo",
        default=None,
        help="Repo root used to detect forbidden trees (default: parent of proposals-dir "
        "or parent of this script's parent)",
    )
    p.add_argument(
        "--rel",
        required=True,
        help="Relative path under proposals-dir (no kernel/ pack/live/ worlds/ prefix)",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--content-file",
        help="Read bytes from this file and write them under proposals/",
    )
    src.add_argument(
        "--stdin",
        action="store_true",
        help="Read bytes from stdin",
    )
    src.add_argument(
        "--text",
        help="Literal UTF-8 text to write (small proposals / plants)",
    )
    args = p.parse_args(argv)

    here = Path(__file__).resolve().parent.parent
    proposals_dir = (
        Path(args.proposals_dir).resolve()
        if args.proposals_dir
        else (here / "proposals").resolve()
    )
    repo = Path(args.repo).resolve() if args.repo else here.resolve()

    if not proposals_dir.exists():
        proposals_dir.mkdir(parents=True, exist_ok=True)
    if not proposals_dir.is_dir():
        die(f"proposals-dir is not a directory: {proposals_dir}")

    # Refuse pointing the write root at a forbidden live tree.
    hit = forbidden_tree_touch(proposals_dir, repo)
    if hit is not None:
        die(f"refuse: proposals-dir resolves onto {hit}/ (signer-only)")

    rel = normalize_rel(args.rel)
    if is_forbidden_rel(rel):
        die(f"refuse: path touches kernel/pack/live/worlds: {rel}")

    dest = (proposals_dir / rel).resolve()
    if not under_root(proposals_dir, dest):
        die(f"destination escapes proposals-dir: {rel}")

    # Belt: even under proposals-dir, refuse if somehow landing in forbidden trees.
    hit = forbidden_tree_touch(dest, repo)
    if hit is not None:
        die(f"refuse: destination resolves onto {hit}/ (signer-only)")

    if args.content_file:
        src_path = Path(args.content_file)
        if not src_path.is_file():
            die(f"content-file not found: {src_path}")
        data = src_path.read_bytes()
    elif args.stdin:
        data = sys.stdin.buffer.read()
    else:
        data = args.text.encode("utf-8")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"propose_file: wrote proposals-rel={rel} bytes={len(data)}")
    print("propose_file: ok (NOT live; signer + pack_version required to activate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
