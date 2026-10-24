"""Walk roots, read units, resolve edges. Does not write source. Does not write the World."""

from __future__ import annotations

import os
from pathlib import Path

from scanner.model import make_edge, make_world, norm_rel
from scanner.readers import LANG_READERS
from scanner.readers.textual import read_textual

# The whole walk exclusion (WORLD.md "Walk"). Hidden names are walked like any other: .github, .env
# samples and dot-configs are part of the repo. These are VCS stores, installed dependencies and tool
# caches: not the repo's own source, and large enough to swamp R6-4.
_SKIP_DIRS = {
    ".git", ".hg", ".svn", ".jj",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox",
    "node_modules", ".venv", "venv", "DerivedData",
}
_SKIP_FILES = {".DS_Store"}


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _excluded(relpath: str, patterns: list[str]) -> bool:
    parts = relpath.split("/")
    for pat in patterns:
        pat = pat.strip("/")
        if not pat:
            continue
        if relpath == pat or relpath.startswith(pat + "/"):
            return True
        # A one-segment pattern also skips any dir or file of that name at any depth (build -> pkg/build/).
        if pat in parts:
            return True
    return False


def walk_root(root_abs: Path, exclude: list[str], errors: list[OSError] | None = None) -> list[Path]:
    """errors, if given, collects each directory os.walk could not open (else it is skipped unseen)."""
    kept = []
    for dirpath, dirnames, filenames in os.walk(root_abs, onerror=errors.append if errors is not None else None):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if name in _SKIP_FILES:
                continue
            path = Path(dirpath) / name
            # FIFO, socket, device or dangling link: reading it can hang or fail.
            if not path.is_file():
                continue
            rel = _rel(root_abs, path)
            if _excluded(rel, exclude):
                continue
            kept.append(path)
    return kept


def _indexes(units: list[dict]) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    by_rel: dict[str, str] = {}
    by_root: dict[tuple[str, str], str] = {}
    for u in units:
        by_rel.setdefault(u["relpath"], u["unit_id"])
        by_root[(u["root_id"], u["relpath"])] = u["unit_id"]
    return by_rel, by_root


def _parent(relpath: str) -> str:
    p = Path(relpath).parent.as_posix()
    return "" if p == "." else p


def _join(base: str, rel: str) -> str | None:
    """Join and normalize inside a root. None if the result escapes the root."""
    joined = os.path.normpath(f"{base}/{rel}" if base else rel).replace("\\", "/")
    if joined == ".." or joined.startswith("../"):
        return None
    return joined


def _lookup(cands: list[str], root_id: str, by_rel: dict[str, str], by_root: dict[tuple[str, str], str]) -> str | None:
    # Same root first, then any root.
    for c in cands:
        hit = by_root.get((root_id, c))
        if hit:
            return hit
    for c in cands:
        if c in by_rel:
            return by_rel[c]
    return None


def resolve_target(lit: str, frm_unit: dict, by_rel: dict[str, str], by_root: dict[tuple[str, str], str]) -> str:
    """String-path literal -> unit_id. Leading `./` is dropped; `../` and dotfiles are kept."""
    lit = norm_rel(lit)
    root_id = frm_unit.get("root_id", "")
    # Multi-repo: "lib/other.py" hits root_id lib, relpath other.py. No monorepo required.
    if "/" in lit:
        head, rest = lit.split("/", 1)
        hit = by_root.get((head, rest))
        if hit:
            return hit
    cands = [lit] if not lit.startswith("../") else []
    joined = _join(_parent(frm_unit["relpath"]), lit)
    if joined is not None and joined not in cands:
        cands.append(joined)
    return _lookup(cands, root_id, by_rel, by_root) or f"unresolved:{lit}"


def resolve_import(name: str, frm_unit: dict, by_rel: dict[str, str], by_root: dict[tuple[str, str], str]) -> str:
    """Python module name (leading dots = relative level) -> unit_id of module or package __init__."""
    level = len(name) - len(name.lstrip("."))
    mod_path = name[level:].replace(".", "/")
    root_id = frm_unit.get("root_id", "")
    if level:
        base: str | None = _parent(frm_unit["relpath"])
        for _ in range(level - 1):
            base = _join(base, "..") if base else None
            if base is None:
                return f"unresolved:{name}"
        stem = _join(base, mod_path) if mod_path else base
        if stem is None:
            return f"unresolved:{name}"
        stems = [stem]
    else:
        # Absolute: root-relative first, then the importer's directory (script-dir sys.path).
        stems = [mod_path]
        local = _join(_parent(frm_unit["relpath"]), mod_path)
        if local and local != mod_path:
            stems.append(local)
    cands = []
    for s in stems:
        cands += [f"{s}.py", f"{s}/__init__.py"] if s else ["__init__.py"]
    return _lookup(cands, root_id, by_rel, by_root) or f"unresolved:{name}"


def resolve_edges(units: list[dict]) -> list[dict]:
    by_rel, by_root = _indexes(units)
    edges = []
    for u in units:
        for sp in u["string_paths"]:
            to = resolve_target(sp["lit"], u, by_rel, by_root)
            edges.append(
                make_edge("string_path", u["unit_id"], to, sp["lit"], sp["line"], "low")
            )
        for ref in u["refs"]:
            to = resolve_import(ref["name"], u, by_rel, by_root)
            edges.append(make_edge("import", u["unit_id"], to, ref["name"], ref["line"], "high"))
    return edges


def scan(manifest: dict) -> dict:
    before = source_snapshot(manifest["roots"])
    units: list[dict] = []
    unreadable: list[dict] = []
    root_meta = []
    for root in manifest["roots"]:
        root_abs = Path(root["abs"])
        root_meta.append(
            {"root_id": root["root_id"], "role": root["role"], "walk": "default"}
        )
        if not root_abs.is_dir():
            unreadable.append({"root_id": root["root_id"], "error": "root missing"})
            continue
        walk_errors: list[OSError] = []
        paths = walk_root(root_abs, root.get("exclude") or [], walk_errors)
        for exc in walk_errors:
            where = Path(exc.filename) if exc.filename else root_abs
            rel = _rel(root_abs, where) if where.is_relative_to(root_abs) else str(where)
            unreadable.append({"root_id": root["root_id"], "relpath": rel, "error": exc.strerror or str(exc)})
        for path in paths:
            rel = _rel(root_abs, path)
            try:
                unit = read_textual(root["root_id"], rel, path)
            except OSError as exc:
                unreadable.append({"root_id": root["root_id"], "relpath": rel, "error": str(exc)})
                continue
            reader = LANG_READERS.get(unit["lang"])
            if reader is not None:
                try:
                    unit = reader(unit, path)
                except Exception as exc:  # reader bugs must not drop the file
                    unit["reader"] = "textual"
                    unit["reader_error"] = f"{type(exc).__name__}: {exc}"
            units.append(unit)
    edges = resolve_edges(units)
    assert_no_source_writes(before, manifest["roots"])
    return make_world(
        manifest["world_id"],
        manifest["manifest_id"],
        root_meta,
        units,
        edges,
        unreadable,
    )


def source_snapshot(roots: list[dict]) -> dict[tuple[str, str], tuple[int, int, int, int]]:
    """(root_id, relpath) -> (inode, size, mtime_ns, ctime_ns) for every walked file. ctime moves on any
    write and cannot be set back from user space, so an in-place rewrite that keeps size and resets
    mtime still shows."""
    snap = {}
    for root in roots:
        root_abs = Path(root["abs"])
        if not root_abs.is_dir():
            continue
        for path in walk_root(root_abs, root.get("exclude") or []):
            try:
                st = os.lstat(path)
            except OSError:
                continue
            snap[(root["root_id"], _rel(root_abs, path))] = (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    return snap


def assert_no_source_writes(before: dict, roots: list[dict]) -> None:
    """Scanner must not touch root contents: no file added, removed or rewritten during the scan."""
    after = source_snapshot(roots)
    if after == before:
        return
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    show = [f"{kind} {rid}:{rel}" for kind, keys in (("added", added), ("removed", removed), ("changed", changed))
            for rid, rel in keys[:5]]
    raise SystemExit(
        "root changed during scan (scanner or a concurrent writer); no World emitted: " + ", ".join(show)
    )
