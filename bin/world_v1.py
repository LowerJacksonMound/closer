#!/usr/bin/env python3
"""Shared WORLD.md v1 contract helpers for Layer-0 stubs. Stdlib only.

Fail-closed: missing file, non-v1 / retired sketch, unfrozen, id mismatch.
"""
from __future__ import annotations

import json
import stat
import sys
from pathlib import Path
from typing import Any, NoReturn


REQUIRED_TOP = (
    "kind",
    "version",
    "world_id",
    "manifest_id",
    "roots",
    "units",
    "edges",
    "unreadable",
    "stats",
)

# Retired getting-close sketch fields (PACK.md World slice before WORLD.md cutover).
RETIRED_SKETCH_KEYS = ("scan_id", "started_at", "sha256", "files_scanned")


def die(prefix: str, msg: str, code: int = 1) -> NoReturn:
    print(f"{prefix}: {msg}", file=sys.stderr)
    raise SystemExit(code)


def bare_world_id(world_id: str) -> str:
    wid = str(world_id).strip()
    if wid.startswith("scan_"):
        return wid[len("scan_") :]
    return wid


def world_path(worlds_dir: Path, world_id: str) -> Path:
    bare = bare_world_id(world_id)
    if not bare or "/" in bare or "\\" in bare or bare in (".", ".."):
        raise ValueError(f"illegal world_id: {world_id!r}")
    return worlds_dir / f"scan_{bare}.json"


def is_frozen(path: Path) -> bool:
    if not path.is_file():
        return False
    return not (path.stat().st_mode & stat.S_IWUSR)


def ids_equivalent(a: str, b: str) -> bool:
    return bare_world_id(a) == bare_world_id(b) or str(a) == str(b)


def load_world_v1(
    path: Path,
    *,
    expect_world_id: str | None = None,
    require_frozen: bool = True,
    tool: str = "world_v1",
) -> dict[str, Any]:
    if not path.is_file():
        die(tool, f"missing World id (no file at {path})")
    if path.suffix != ".json" or not path.name.startswith("scan_"):
        die(tool, f"refusing non-World path: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        die(tool, f"cannot load World: {e}")
    if not isinstance(data, dict):
        die(tool, "World is not a JSON object")

    # Refuse retired sketch masquerading as a World.
    if data.get("kind") != "world" or data.get("version") != 1:
        retired = [k for k in RETIRED_SKETCH_KEYS if k in data]
        extra = f" (looks like retired sketch: {', '.join(retired)})" if retired else ""
        die(tool, f"not a world v1 (WORLD.md contract){extra}")

    missing = [k for k in REQUIRED_TOP if k not in data]
    if missing:
        die(tool, f"World missing required WORLD.md keys: {', '.join(missing)}")

    if not isinstance(data["roots"], list):
        die(tool, "World.roots must be a list")
    if not isinstance(data["units"], list):
        die(tool, "World.units must be a list")
    if not isinstance(data["edges"], list):
        die(tool, "World.edges must be a list")
    if not isinstance(data["stats"], dict):
        die(tool, "World.stats must be an object")

    # Absolute paths must not appear in the World (ROOT paths live in the manifest only).
    # Cheap heuristic: a POSIX absolute path or a Windows drive in a unit's relpath is a contract break.
    for unit in data["units"]:
        if not isinstance(unit, dict):
            continue
        rel = unit.get("relpath")
        if isinstance(rel, str) and (rel.startswith("/") or (len(rel) > 1 and rel[1] == ":")):
            die(tool, f"World unit has absolute relpath (forbidden): {rel}")

    if require_frozen and not is_frozen(path):
        die(tool, f"World is not frozen (writable): {path}")

    if expect_world_id is not None:
        got = data.get("world_id")
        if not isinstance(got, str) or not ids_equivalent(expect_world_id, got):
            die(
                tool,
                f"wrong world_id: ticket={expect_world_id!r} world={got!r} path={path}",
            )

    return data
