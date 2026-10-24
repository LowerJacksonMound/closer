"""World v1 builders. Shape is WORLD.md. Do not add fields without a pack bump."""

from __future__ import annotations

from scanner.pathrule import lexical

VERSION = 1

# WORLD.md edge_id prefixes: `sp:` for string paths, `ref:` for reader refs.
_EDGE_PREFIX = {"string_path": "sp", "import": "ref", "include": "ref"}


def norm_rel(relpath: str) -> str:
    """scanner.pathrule.lexical: forward slashes, no `.` or empty segments. Keeps dotfiles and `../`."""
    return lexical(relpath)


def unit_id(root_id: str, relpath: str) -> str:
    return f"{root_id}:{norm_rel(relpath)}"


def make_unit(
    root_id: str,
    relpath: str,
    lang: str,
    reader: str,
    nbytes: int,
    lines: int,
    defs: list | None = None,
    refs: list | None = None,
    string_paths: list | None = None,
    reader_error: str | None = None,
) -> dict:
    rel = norm_rel(relpath)
    return {
        "unit_id": unit_id(root_id, rel),
        "root_id": root_id,
        "relpath": rel,
        "lang": lang,
        "reader": reader,
        "reader_error": reader_error,
        "bytes": nbytes,
        "lines": lines,
        "defs": defs or [],
        "refs": refs or [],
        "string_paths": string_paths or [],
    }


def make_edge(kind: str, frm: str, to: str, lit: str, line: int, confidence: str) -> dict:
    edge_id = f"{_EDGE_PREFIX[kind]}:{frm}:{line}:{lit}"
    return {
        "edge_id": edge_id,
        "kind": kind,
        "from": frm,
        "to": to,
        "lit": lit,
        "line": line,
        "confidence": confidence,
    }


def make_world(world_id: str, manifest_id: str, roots: list, units: list, edges: list, unreadable: list) -> dict:
    units_sorted = sorted(units, key=lambda u: u["unit_id"])
    edges_sorted = sorted(edges, key=lambda e: e["edge_id"])
    return {
        "kind": "world",
        "version": VERSION,
        "world_id": world_id,
        "manifest_id": manifest_id,
        "roots": roots,
        "units": units_sorted,
        "edges": edges_sorted,
        "unreadable": unreadable,
        "stats": {
            "units": len(units_sorted),
            "defs": sum(len(u["defs"]) for u in units_sorted),
            "string_path_edges": sum(1 for e in edges_sorted if e["kind"] == "string_path"),
            "unresolved": sum(1 for e in edges_sorted if str(e["to"]).startswith("unresolved:")),
        },
    }
