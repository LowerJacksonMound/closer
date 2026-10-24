#!/bin/sh
# Live in pack v3 (v2: OPEN_RULINGS R1, 2026-10-05). Edit only through a new pack version (K5).
# R10-1: FP is a third verdict.
# Pack v1 id: R10-1.
# World-or-ticket verify. No source parse. ARTIFACT_FILE is not an input.
# World v1 has no proof rows. Gate rows live on ticket.overlay until a World does.
# Pack-subset World fields used: kind, version, world_id (binding only).
# false_positive / false_positive_when must exist and must not be overloaded onto context.
set -u
WORLD="${WORLD_FILE:?set WORLD_FILE to a scan_*.json}"
TICKET="${TICKET_FILE:?set TICKET_FILE to a ticket JSON}"
PACK="$(CDPATH= cd -- "$(dirname "$0")" && pwd)/PACK.json"
python3 - "$WORLD" "$TICKET" "$PACK" << 'PY'
import json, re, sys
from pathlib import Path

LAW = "R10-1"

def fail(msg: str) -> None:
    print(f"{LAW} fail: {msg}", file=sys.stderr)
    sys.exit(1)

def bare(value: str) -> str:
    text = str(value).strip()
    if text.startswith("scan_"):
        return text[len("scan_") :]
    return text

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
if ticket.get("verify") != LAW or ticket.get("invariant_id") != LAW:
    fail(f"ticket verify and invariant_id must both be {LAW}")
pack_version = ticket.get("pack_version")
live_version = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))["pack_version"]
if isinstance(pack_version, bool) or pack_version != live_version:
    fail(f"ticket pack_version must be {live_version} (this pack's PACK.json), got {pack_version!r}")

overlay = ticket.get("overlay")
if not isinstance(overlay, dict):
    fail("ticket.overlay missing or not an object")
rows = overlay.get("rows")
if not isinstance(rows, list) or not rows:
    fail("ticket.overlay.rows missing or empty")

FP_IN_CONTEXT = re.compile(r"false[_\s-]?positive", re.I)

def context_claims_fp(ctx) -> bool:
    if ctx is None:
        return False
    if isinstance(ctx, str):
        return bool(FP_IN_CONTEXT.search(ctx))
    if isinstance(ctx, dict):
        for key, value in ctx.items():
            if FP_IN_CONTEXT.search(str(key)):
                return True
            if isinstance(value, str) and FP_IN_CONTEXT.search(value):
                return True
        return False
    return bool(FP_IN_CONTEXT.search(str(ctx)))

has_third_verdict = False
has_fp_when = False
overloaded = []

for i, row in enumerate(rows):
    if not isinstance(row, dict):
        fail(f"rows[{i}] is not an object")
    verdict = row.get("verdict")
    fp_when = row.get("false_positive_when", None)
    has_distinct = verdict == "false_positive" or (
        "false_positive_when" in row and fp_when is not None and fp_when != ""
    )
    if verdict == "false_positive":
        has_third_verdict = True
    if "false_positive_when" in row and fp_when is not None and fp_when != "":
        has_fp_when = True
    if context_claims_fp(row.get("context")) and not has_distinct:
        overloaded.append(i)

if overloaded:
    fail(
        "false_positive overloaded onto context at rows "
        f"{overloaded} (need verdict=false_positive or false_positive_when)"
    )
if not (has_third_verdict or has_fp_when):
    fail(
        "missing third verdict — need at least one row with "
        "verdict=false_positive or non-empty false_positive_when"
    )

print(
    f"{LAW} pass: third verdict present "
    f"(verdict_fp={has_third_verdict} false_positive_when={has_fp_when}); "
    "not overloaded onto context"
)
sys.exit(0)
PY
