#!/bin/sh
# Live in pack v3 (v2: OPEN_RULINGS R1, 2026-10-05). Edit only through a new pack version (K5).
# G18: Launch pollution.
# Pack v1 id: G18. Live pack stays W1.sh. This file is not installed.
# Path-name check only. No mtime. No started_at.
# A bytecode path that is not .pyc, .pyo, or under .mypy_cache is invisible to it.
# World-or-ticket verify. No source parse. No live-tree walk.
# Pack-subset World fields used: kind, version, world_id, units.
# Ticket fields used: world_id, pack_version, write_set. Runs on every ticket.
# A flagged path ends in .pyc/.pyo or has a .mypy_cache path component.
# Those paths must be absent from World units and from ticket write_set.
# Repo-relative write_set (gc): a first segment equal to a root_id is an ordinary folder, not a fault.
set -u
WORLD="${WORLD_FILE:?set WORLD_FILE to a scan_*.json}"
TICKET="${TICKET_FILE:?set TICKET_FILE to a ticket JSON}"
PACK="$(CDPATH= cd -- "$(dirname "$0")" && pwd)/PACK.json"
python3 - "$WORLD" "$TICKET" "$PACK" << 'PY'
import json, sys
from pathlib import Path

LAW = "G18"

def fail(msg: str) -> None:
    print(f"{LAW} fail: {msg}", file=sys.stderr)
    sys.exit(1)

def bare(value: str) -> str:
    text = str(value).strip()
    if text.startswith("scan_"):
        return text[len("scan_") :]
    return text


def is_pollution(rel: str) -> bool:
    norm = rel.replace("\\", "/").strip()
    while norm.startswith("./"):
        norm = norm[2:]
    parts = [p for p in norm.split("/") if p and p != "."]
    if ".mypy_cache" in parts:
        return True
    base = parts[-1] if parts else norm
    return base.endswith(".pyc") or base.endswith(".pyo")

world_path = Path(sys.argv[1])
ticket_path = Path(sys.argv[2])
if not world_path.is_file():
    fail(f"World not found: {world_path}")
if not ticket_path.is_file():
    fail(f"ticket not found: {ticket_path}")

try:
    world = json.loads(world_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    fail(f"cannot load World: {exc}")
try:
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    fail(f"cannot load ticket: {exc}")

if not isinstance(world, dict):
    fail("World is not a JSON object")
if not isinstance(ticket, dict):
    fail("ticket is not a JSON object")
if world.get("kind") != "world" or world.get("version") != 1:
    fail("not a world v1")

world_id = world.get("world_id")
if not isinstance(world_id, str) or not world_id.strip():
    fail("World.world_id missing")
ticket_world = ticket.get("world_id")
if not isinstance(ticket_world, str) or bare(ticket_world) != bare(world_id):
    fail(f"ticket world_id {ticket_world!r} does not match World {world_id!r}")
pack_version = ticket.get("pack_version")
live_version = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))["pack_version"]
if isinstance(pack_version, bool) or pack_version != live_version:
    fail(f"ticket pack_version must be {live_version} (this pack's PACK.json), got {pack_version!r}")

units = world.get("units")
if not isinstance(units, list):
    fail("World.units missing or not a list")
write_set = ticket.get("write_set")
if not isinstance(write_set, list):
    fail("ticket.write_set missing or not a list")

hits = []
for i, unit in enumerate(units):
    if not isinstance(unit, dict):
        fail(f"units[{i}] is not an object")
    rel = unit.get("relpath")
    if not isinstance(rel, str):
        fail(f"units[{i}].relpath missing")
    if is_pollution(rel):
        hits.append(f"unit {rel}")
for i, entry in enumerate(write_set):
    if not isinstance(entry, str) or not entry.strip():
        fail(f"write_set[{i}] is not a path")
    if is_pollution(entry):
        hits.append(f"write_set {entry}")

if hits:
    shown = ", ".join(hits[:20])
    extra = "" if len(hits) <= 20 else f" (+{len(hits) - 20} more)"
    fail(f"pollution path in World units or ticket write_set: {shown}{extra}")

print(
    f"{LAW} pass: no .pyc/.pyo/.mypy_cache in {len(units)} unit(s) "
    f"or {len(write_set)} write_set path(s)"
)
sys.exit(0)
PY
