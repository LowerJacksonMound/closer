#!/bin/sh
# Live in pack v3 (v2: OPEN_RULINGS R1, 2026-10-05). Edit only through a new pack version (K5).
# R6-4: every scanned file is a unit (defless listed). "Scanned" is every regular file under a root,
# hidden names included, except the fixed walk exclusion in WORLD.md "Walk" (VCS stores, installed
# dependencies, tool caches, .DS_Store) and the manifest's own excludes. Nothing else may be skipped.
# Pack-check fields used (PACK.md subset): kind, version, units.
# Aligned to WORLD.md (retired: files_scanned kinds).
set -u
WORLD="${WORLD_FILE:?set WORLD_FILE to a scan_*.json}"
python3 - "$WORLD" << 'PY'
import json, sys
w = json.load(open(sys.argv[1], encoding="utf-8"))
if w.get("kind") != "world" or w.get("version") != 1:
    print("R6-4 fail: not a world v1", file=sys.stderr)
    sys.exit(1)
units = w.get("units") or []
if not units:
    print("R6-4 fail: units empty", file=sys.stderr)
    sys.exit(1)
# At least one unit with empty defs proves defless files are kept.
defless = [u for u in units if not u.get("defs")]
if not defless:
    print("R6-4 fail: no defless unit (expected empty defs list on some file)", file=sys.stderr)
    sys.exit(1)
print(f"R6-4 pass: {len(units)} units; defless={len(defless)}")
PY
