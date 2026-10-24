"""CLI: read a manifest, scan, emit a frozen World. No source writes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python bin/emit_world.py` from the stub root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scanner.emit import emit_world  # noqa: E402
from scanner.manifest import load_manifest  # noqa: E402
from scanner.scan import scan  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Emit a frozen World from a scan manifest")
    p.add_argument("manifest", type=Path)
    p.add_argument("--out", type=Path, required=True, help="worlds/<id>.json; must not exist")
    args = p.parse_args(argv)
    manifest = load_manifest(args.manifest)
    world = scan(manifest)
    emit_world(world, args.out)
    print(f"emitted {args.out} units={world['stats']['units']} string_path_edges={world['stats']['string_path_edges']}")
    # Say what the World is missing or read only as text, so a partial scan is never mistaken for a full one.
    for u in world["unreadable"]:
        print(f"emit_world: NOT SCANNED {u['root_id']}:{u.get('relpath', '.')}: {u['error']}", file=sys.stderr)
    for u in world["units"]:
        if u.get("reader_error"):
            print(f"emit_world: read as text only {u['unit_id']}: {u['reader_error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
