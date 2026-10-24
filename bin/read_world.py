#!/usr/bin/env python3
"""read_world — Layer-0 stub aligned to WORLD.md. Fail-closed. Stdlib only.

Reads keys from an immutable World (worlds/scan_<id>.json).
Must refuse: missing id; inventing keys; non-world-v1 documents; unfrozen World;
reading the live tree (non-World paths).
Also supports a single-path mode: `read_world.py worlds/scan_demo.json`
(prints stats; exit 0 iff frozen) matching the scanner CLI.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from world_v1 import is_frozen, load_world_v1, world_path  # noqa: E402


def die(msg: str, code: int = 1) -> None:
    print(f"read_world: {msg}", file=sys.stderr)
    raise SystemExit(code)


def get_key(world: dict[str, Any], key: str) -> Any:
    if key in world:
        return world[key]
    if "." in key:
        cur: Any = world
        for part in key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                die(f"key not in World: {key}")
            cur = cur[part]
        return cur
    die(f"key not in World: {key}")


def print_stats(path: Path, data: dict[str, Any]) -> int:
    frozen = is_frozen(path)
    stats = data.get("stats") or {}
    print(
        f"world_id={data.get('world_id')} frozen={frozen} "
        f"units={stats.get('units')} defs={stats.get('defs')} "
        f"string_path_edges={stats.get('string_path_edges')} "
        f"unresolved={stats.get('unresolved')}"
    )
    return 0 if frozen else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Scanner-style: single existing .json path -> stats (still require WORLD.md v1).
    if len(argv) == 1 and not argv[0].startswith("-"):
        path = Path(argv[0])
        if path.is_file() and path.suffix == ".json":
            # Stats mode: validate shape; frozen status is the exit code (not a die).
            data = load_world_v1(
                path.resolve(),
                expect_world_id=None,
                require_frozen=False,
                tool="read_world",
            )
            return print_stats(path, data)

    p = argparse.ArgumentParser(description="Read keys from a frozen World JSON (WORLD.md).")
    p.add_argument(
        "--worlds-dir",
        default=None,
        help="Directory containing scan_*.json (default: ../worlds from this script)",
    )
    p.add_argument("scan_id", help="World id (bare or scan_<id>); file is scan_<bare>.json")
    p.add_argument(
        "keys",
        nargs="+",
        help="Key(s) to read from the World (must exist; no inventing)",
    )
    args = p.parse_args(argv)

    worlds_dir = (
        Path(args.worlds_dir)
        if args.worlds_dir
        else Path(__file__).resolve().parent.parent / "worlds"
    )
    try:
        path = world_path(worlds_dir, args.scan_id)
    except ValueError as e:
        die(str(e))

    # Key reads require a frozen WORLD.md World (cutover: no live-tree inventing).
    world = load_world_v1(
        path,
        expect_world_id=args.scan_id,
        require_frozen=True,
        tool="read_world",
    )
    out: dict[str, Any] = {}
    for key in args.keys:
        out[key] = get_key(world, key)
    json.dump(out, sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
