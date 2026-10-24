"""Scan manifest. Multi-repo is a root list. follow is off in v1."""

from __future__ import annotations

import json
from pathlib import Path

ROLES = {"primary", "dep", "vendor", "generated"}


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("kind") != "scan_manifest":
        raise SystemExit(f"not a scan_manifest: {path}")
    if data.get("version") != 1:
        raise SystemExit(f"manifest version not 1: {path}")
    roots = data.get("roots") or []
    if not roots:
        raise SystemExit("manifest has no roots")
    seen = set()
    base = path.parent
    for root in roots:
        rid = root.get("root_id")
        if not rid or rid in seen:
            raise SystemExit(f"bad or duplicate root_id: {rid}")
        seen.add(rid)
        if root.get("role", "primary") not in ROLES:
            raise SystemExit(f"bad role on {rid}")
        root.setdefault("role", "primary")
        root.setdefault("exclude", [])
        # Paths in the manifest are relative to the manifest file, so a
        # second repo can sit beside the first without a monorepo assumption.
        p = Path(root["path"])
        if not p.is_absolute():
            p = (base / p).resolve()
        root["abs"] = str(p)
    if data.get("follow"):
        raise SystemExit("follow is v2; list the root in the manifest")
    data.setdefault("world_id", data.get("manifest_id") or path.stem)
    data.setdefault("manifest_id", path.stem)
    return data
