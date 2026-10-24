"""Write-once emit. Destination exists -> fail. Success -> chmod a-w."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path


def emit_world(world: dict, dest: Path) -> None:
    dest = dest.resolve()
    if dest.exists():
        raise SystemExit(f"world exists, refuse second write: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(world, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        umask = os.umask(0)
        os.umask(umask)
        os.fchmod(fd, 0o666 & ~umask)  # mkstemp makes 0600; a World is as readable as any emitted file
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        # K1: link() never replaces an existing name, so two emitters racing for one scan_id cannot
        # both win. os.replace would overwrite a frozen World; the exists() check above is only the
        # early, friendly refusal.
        try:
            os.link(tmp, dest)
        except FileExistsError:
            raise SystemExit(f"world exists, refuse second write: {dest}") from None
    finally:
        tmp.unlink(missing_ok=True)
    mode = dest.stat().st_mode
    dest.chmod(mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)
    if dest.stat().st_mode & stat.S_IWUSR:
        raise SystemExit(f"chmod a-w did not stick, refuse to call this frozen: {dest}")


def is_frozen(path: Path) -> bool:
    if not path.is_file():
        return False
    return not (path.stat().st_mode & stat.S_IWUSR)
