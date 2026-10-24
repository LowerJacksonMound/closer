#!/bin/sh
# Live in pack v2 (OPEN_RULINGS R1, 2026-10-05). Edit only through a new pack version (K5).
# R6-2: reachability is World edges, not import-only. World check: runs on every scan, so a World
# with no string paths passes; one whose reader found a string path that has no edge fails.
# Pack-check fields used (PACK.md subset): kind, version, units, edges, stats.
# Aligned to WORLD.md (retired: edges[].via=file_ref).
set -u
WORLD="${WORLD_FILE:?set WORLD_FILE to a scan_*.json}"
python3 - "$WORLD" << 'PY'
import json, sys
w = json.load(open(sys.argv[1], encoding="utf-8"))
if w.get("kind") != "world" or w.get("version") != 1:
    print("R6-2 fail: not a world v1", file=sys.stderr)
    sys.exit(1)
units = {u.get("unit_id"): u for u in w.get("units") or []}
edges = w.get("edges") or []
bad = []
for e in edges:
    if e.get("kind") not in ("string_path", "import"):  # the kinds scanner/scan.py emits
        bad.append(f"edge {e.get('edge_id')} has unknown kind {e.get('kind')!r}")
    if e.get("from") not in units:
        bad.append(f"edge {e.get('edge_id')} is from {e.get('from')!r}, not a unit")
    to = str(e.get("to"))
    if to not in units and not to.startswith("unresolved:"):
        bad.append(f"edge {e.get('edge_id')} points at {to!r}, neither a unit nor unresolved:")
sp = {(e.get("from"), e.get("line"), e.get("lit")) for e in edges if e.get("kind") == "string_path"}
found = 0
for uid, u in units.items():
    for s in u.get("string_paths") or []:
        found += 1
        if (uid, s.get("line"), s.get("lit")) not in sp:
            bad.append(f"string path {s.get('lit')!r} at {uid}:{s.get('line')} has no string_path edge")
listed = sum(1 for e in edges if e.get("kind") == "string_path")
if (w.get("stats") or {}).get("string_path_edges") != listed:
    bad.append(f"stats.string_path_edges={(w.get('stats') or {}).get('string_path_edges')!r}, edges list {listed}")
for b in bad:
    print(f"R6-2 fail: {b}", file=sys.stderr)
if bad:
    sys.exit(1)
print(f"R6-2 pass: {found} string path(s) found, {listed} string_path edge(s), {len(edges)} edge(s)")
PY
