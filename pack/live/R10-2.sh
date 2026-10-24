#!/bin/sh
# Live in pack v3 (v2: OPEN_RULINGS R1, 2026-10-05). Edit only through a new pack version (K5).
# R10-2: FP does not fail the gate.
# Pack v1 id: R10-2.
# World-or-ticket verify. No source parse. ARTIFACT_FILE is not an input.
# World v1 has no proof rows. Gate rows and summary live on ticket.overlay.
# Pack-subset World fields used: kind, version, world_id (binding only).
# FP rows must sit outside summary.failed and finished-gate counts.
set -u
WORLD="${WORLD_FILE:?set WORLD_FILE to a scan_*.json}"
TICKET="${TICKET_FILE:?set TICKET_FILE to a ticket JSON}"
PACK="$(CDPATH= cd -- "$(dirname "$0")" && pwd)/PACK.json"
python3 - "$WORLD" "$TICKET" "$PACK" << 'PY'
import json, sys
from pathlib import Path

LAW = "R10-2"

def fail(msg: str) -> None:
    print(f"{LAW} fail: {msg}", file=sys.stderr)
    sys.exit(1)

def bare(value: str) -> str:
    text = str(value).strip()
    if text.startswith("scan_"):
        return text[len("scan_") :]
    return text

def is_fp_row(row: dict) -> bool:
    if row.get("verdict") == "false_positive":
        return True
    fp_when = row.get("false_positive_when", None)
    return "false_positive_when" in row and fp_when is not None and fp_when != ""

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
summary = overlay.get("summary")
if not isinstance(summary, dict):
    fail("ticket.overlay.summary missing or not an object")

fp_rows = []
fail_rows = []
for i, row in enumerate(rows):
    if not isinstance(row, dict):
        fail(f"rows[{i}] is not an object")
    if is_fp_row(row):
        fp_rows.append(i)
    elif row.get("verdict") == "fail":
        fail_rows.append(i)

n_fp = len(fp_rows)
n_fail = len(fail_rows)

if "failed" not in summary:
    fail("summary.failed missing")
failed_count = summary["failed"]
if not isinstance(failed_count, int) or isinstance(failed_count, bool):
    fail(f"summary.failed must be int, got {type(failed_count).__name__}")
if failed_count != n_fail:
    fail(
        f"summary.failed={failed_count} but non-FP fail rows={n_fail} "
        f"(FP rows={n_fp} must be outside summary.failed)"
    )

failed_ids = summary.get("failed_ids") or summary.get("failed_rows") or []
if isinstance(failed_ids, list) and failed_ids:
    fp_ids = set()
    for i in fp_rows:
        rid = rows[i].get("id", i)
        fp_ids.add(rid)
        fp_ids.add(i)
    overlap = [item for item in failed_ids if item in fp_ids]
    if overlap:
        fail(f"FP rows listed under summary failed ids/rows: {overlap}")

gate = summary.get("finished_gate")
if gate is None:
    gate = summary.get("gate")
if not isinstance(gate, dict):
    fail("summary.finished_gate (or summary.gate) missing or not an object")
if "failed" not in gate:
    fail("finished-gate missing failed count")
gate_failed = gate["failed"]
if not isinstance(gate_failed, int) or isinstance(gate_failed, bool):
    fail(f"finished-gate.failed must be int, got {type(gate_failed).__name__}")
if gate_failed != n_fail:
    fail(
        f"finished-gate.failed={gate_failed} but non-FP fail rows={n_fail} "
        "(FP must be outside finished-gate counts)"
    )

for key in ("total_counted", "counted", "gate_total"):
    if key not in gate:
        continue
    val = gate[key]
    if not isinstance(val, int) or isinstance(val, bool):
        fail(f"finished-gate.{key} must be int")
    expected = len(rows) - n_fp
    if val != expected:
        fail(
            f"finished-gate.{key}={val} want {expected} "
            f"(len(rows)={len(rows)} minus FP={n_fp})"
        )

if n_fp == 0:
    fail(
        "no FP rows to exclude — need verdict=false_positive or "
        "false_positive_when so gate exclusion is observable"
    )

print(
    f"{LAW} pass: FP rows={n_fp} outside summary.failed={failed_count} "
    f"and finished-gate.failed={gate_failed}"
)
sys.exit(0)
PY
