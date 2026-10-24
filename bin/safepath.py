"""On-disk path safety for every byte the kernel writes or reads on a writer's behalf. Stdlib only.

String checks (normalize_rel, is_forbidden, under_root) say nothing about what is on disk. A
symlink or hardlink already in a repo can move a write somewhere the ticket never named
(red-team holes). So every write and every writer-triggered read goes through:

  walk(root, rel)   lstat each existing component below root: no symlinks anywhere; parents are
                    real directories; an existing leaf is a regular file with one link
  write(dest, b)    temp file (O_EXCL|O_NOFOLLOW) + os.replace: never writes through a link,
                    breaks any hardlink, keeps the old file's mode
  missing_dirs()    directories a write will create, so rollback removes only those
  fold(rel)         NFC + casefold, for comparing paths on case-insensitive filesystems

The string rule (canon, fold, bad_chars) lives in scanner/pathrule.py, the only place a path rule is
defined. Re-exported here so the bin side has one import.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner.pathrule import UnsafePath, bad_chars, canon, fold  # noqa: E402,F401


def walk(root: Path, rel: str, *, allow_multilink: bool = False) -> Path:
    """root/rel after an lstat walk. Raises UnsafePath. A missing tail is fine (it will be created)."""
    parts = rel.split("/")
    p = Path(root)
    for i, part in enumerate(parts):
        p = p / part
        try:
            st = os.lstat(p)
        except FileNotFoundError:
            # Every component before this one was lstat'd and passed on an earlier pass; keep it that way.
            return Path(root).joinpath(*parts)
        sub = "/".join(parts[: i + 1])
        if stat.S_ISLNK(st.st_mode):
            raise UnsafePath(f"symlink in path: {sub}")
        if i < len(parts) - 1:
            if not stat.S_ISDIR(st.st_mode):
                raise UnsafePath(f"not a directory: {sub}")
        else:
            if not stat.S_ISREG(st.st_mode):
                raise UnsafePath(f"not a regular file: {sub}")
            if st.st_nlink > 1 and not allow_multilink:
                raise UnsafePath(f"hardlinked file: {sub}")
    return p


def missing_dirs(root: Path, rel: str) -> list[Path]:
    """Ancestors of root/rel (below root) that do not exist yet, shallowest first."""
    out = []
    p = Path(root)
    for part in rel.split("/")[:-1]:
        p = p / part
        if not os.path.lexists(p):
            out.append(p)
    return out


def write(dest: Path, data: bytes) -> None:
    mode = 0o644
    try:
        st = os.lstat(dest)
        if stat.S_ISREG(st.st_mode):
            mode = stat.S_IMODE(st.st_mode)
    except FileNotFoundError:
        pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / f".{dest.name}.gc-tmp-{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
        os.fchmod(fd, mode)
    except BaseException:
        os.close(fd)
        os.unlink(tmp)
        raise
    os.close(fd)
    try:
        os.replace(tmp, dest)
    except BaseException:
        os.unlink(tmp)  # a refused replace (e.g. an immutable dest) must not leave the temp in the repo
        raise


def read(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise UnsafePath(f"not a regular file: {path}")
        chunks = []
        while chunk := os.read(fd, 1 << 20):
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)
