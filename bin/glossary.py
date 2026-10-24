#!/usr/bin/env python3
"""glossary — canonical names for getting-close. Stdlib only. ZERO model calls. Signer tool.

GLOSSARY.md (beside KERNEL.md) holds two tables: Terms (one name per element) and Retired
(old name -> term it reads as). This tool:

    check [--strict] [doc ...]   validate the glossary; list retired names in docs and what each reads as
    lookup NAME                  term or retired name -> its canonical entry
    add NAME --kind K --means T [--source S] [--for EXISTING]
                                 accept a free name as a new term, or reject naming the match

Rules (stated in GLOSSARY.md): names compare case-blind with - _ . space [] alike; a name that
matches any term or retired name is rejected; --for (a new name for a named element) is always
rejected, the first name stands. check exits 1 only if the glossary itself is broken, or with
--strict if a doc uses a retired name.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent.parent          # getting-close/
TOP = HERE                                              # holds KERNEL.md, GLOSSARY.md (one folder since the slim)
DEFAULT_FILE = TOP / "GLOSSARY.md"
DEFAULT_DOCS = [TOP / "KERNEL.md", TOP / "PACK.md", HERE / "WORLD.md", HERE / "DESIGN.md",
                HERE / "README.md", HERE / "RELEASE_CHECKLIST.md"]
KINDS = ("object", "role", "concept", "key", "rule", "tool", "command", "plant", "verdict", "finding")
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|(.*)\|\s*$")


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"glossary: {msg}", file=sys.stderr)
    raise SystemExit(code)


def norm(name: str) -> str:
    s = unicodedata.normalize("NFC", name).strip().strip("`").casefold()
    return re.sub(r"[-_.\s\[\]]+", "_", s).strip("_")


def load(path: Path) -> tuple[list[dict], list[dict], list[str]]:
    """Parse Terms and Retired rows. Returns (terms, retired, problems)."""
    if not path.is_file():
        die(f"no glossary at {path}")
    terms: list[dict] = []
    retired: list[dict] = []
    problems: list[str] = []
    section = None
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        m = ROW.match(line)
        if not m or section not in ("terms", "retired"):
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if section == "terms":
            if len(cells) != 3:
                problems.append(f"line {n}: term row needs 4 cells (Term | Kind | Means | Source)")
                continue
            kind, means, source = cells
            if kind not in KINDS:
                problems.append(f"line {n}: `{m.group(1)}` kind {kind!r} not one of {', '.join(KINDS)}")
            if not means:
                problems.append(f"line {n}: `{m.group(1)}` has no meaning")
            terms.append({"name": m.group(1), "kind": kind, "means": means, "source": source, "line": n})
        else:
            if len(cells) != 2:
                problems.append(f"line {n}: retired row needs 3 cells (Retired | Read as | Why)")
                continue
            retired.append({"name": m.group(1), "read_as": cells[0].strip("`"), "why": cells[1], "line": n})
    seen: dict[str, str] = {}
    for e in terms + retired:
        k = norm(e["name"])
        if k in seen:
            problems.append(f"line {e['line']}: `{e['name']}` matches `{seen[k]}` (one element, one name)")
        else:
            seen[k] = e["name"]
    names = {norm(t["name"]) for t in terms}
    for r in retired:
        if norm(r["read_as"]) not in names:
            problems.append(f"line {r['line']}: retired `{r['name']}` reads as `{r['read_as']}`, which is not a term")
    return terms, retired, problems


def match(name: str, terms: list[dict], retired: list[dict]) -> dict | None:
    k = norm(name)
    for e in terms + retired:
        if norm(e["name"]) == k:
            return e
    return None


def retired_pattern(name: str) -> re.Pattern:
    # A plain word (letters/digits only) is common prose: count it only inside backticks.
    esc = re.escape(name)
    if re.fullmatch(r"[A-Za-z0-9]+", name):
        return re.compile(rf"`{esc}`")
    return re.compile(rf"(?<![A-Za-z0-9_]){esc}(?![A-Za-z0-9_])")


def cmd_check(a) -> int:
    terms, retired, problems = load(a.file)
    for p in problems:
        print(f"glossary: BROKEN {p}", file=sys.stderr)
    hits = 0
    pats = [(r, retired_pattern(r["name"])) for r in retired]
    for doc in [Path(d) for d in a.docs] or DEFAULT_DOCS:
        if not doc.is_file():  # a law doc that is not there was never read: fail, do not skip
            problems.append(f"doc missing: {doc}")
            print(f"glossary: MISSING {doc}", file=sys.stderr)
            continue
        for n, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if "retired" in line.lower():  # a line that names retired keys as retired is correct
                continue
            for r, pat in pats:
                if pat.search(line):
                    hits += 1
                    print(f"{doc.name}:{n}: `{r['name']}` reads as `{r['read_as']}`")
    print(f"glossary: {len(terms)} terms, {len(retired)} retired, {hits} retired use(s) in docs"
          + ("" if not problems else f", {len(problems)} problem(s)"))
    if problems:
        return 1
    return 1 if (a.strict and hits) else 0


def cmd_lookup(a) -> int:
    terms, retired, _ = load(a.file)
    e = match(a.name, terms, retired)
    if e is None:
        print(f"glossary: `{a.name}` is not in the glossary", file=sys.stderr)
        return 1
    if "read_as" in e:
        t = match(e["read_as"], terms, retired)
        print(f"`{e['name']}` is retired: reads as `{e['read_as']}`. {e['why']}")
        e = t or e
    if "kind" in e:
        print(f"`{e['name']}` ({e['kind']}): {e['means']}  [{e['source']}]")
    return 0


def cmd_add(a) -> int:
    terms, retired, problems = load(a.file)
    if problems:
        die("glossary is broken; run `gc glossary check` and fix it first")
    if a.for_:
        e = match(a.for_, terms, retired)
        if e is None:
            die(f"reject: --for `{a.for_}` is not in the glossary; add `{a.name}` as a new term instead")
        canon = e.get("read_as", e["name"])
        die(f"reject: `{canon}` is already named; the first name stands (no renames)")
    if not norm(a.name):
        die("reject: empty name")
    e = match(a.name, terms, retired)
    if e is not None:
        if "read_as" in e:
            die(f"reject: `{a.name}` matches retired `{e['name']}` (reads as `{e['read_as']}`)")
        die(f"reject: `{a.name}` matches term `{e['name']}` ({e['kind']}): {e['means']}")
    if a.kind not in KINDS:  # checked after --for: a rename is rejected whatever its kind
        die(f"reject: kind {a.kind!r} not one of {', '.join(KINDS)}")
    for label, v in (("name", a.name), ("means", a.means), ("source", a.source)):
        if "|" in v or "`" in v or "\n" in v:
            die(f"reject: {label} may not contain | ` or a newline")
    if not a.means.strip():
        die("reject: --means is empty")
    lines = a.file.read_text(encoding="utf-8").splitlines(keepends=True)
    last = max(t["line"] for t in terms) if terms else None
    if last is None:
        die("no Terms table to append to")
    row = f"| `{a.name.strip()}` | {a.kind} | {a.means.strip()} | {a.source.strip() or '-'} |\n"
    lines.insert(last, row)
    fd, tmp = tempfile.mkstemp(dir=a.file.parent, prefix=".glossary.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.replace(tmp, a.file)
    print(f"glossary: added `{a.name.strip()}` ({a.kind})")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gc glossary", allow_abbrev=False,
                                description="canonical names: check, lookup, add (accept/reject by rule)")
    p.add_argument("--file", type=Path, default=DEFAULT_FILE, help=f"default: {DEFAULT_FILE}")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check", help="validate the glossary; list retired names used in docs", allow_abbrev=False)
    s.add_argument("--strict", action="store_true", help="exit 1 if any doc uses a retired name")
    s.add_argument("docs", nargs="*", help="docs to read (default: the law docs)")
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("lookup", help="show a name's canonical entry", allow_abbrev=False)
    s.add_argument("name")
    s.set_defaults(fn=cmd_lookup)
    s = sub.add_parser("add", help="add a new term, or be told why not", allow_abbrev=False)
    s.add_argument("name")
    s.add_argument("--kind", default="", help=" | ".join(KINDS))
    s.add_argument("--means", default="")
    s.add_argument("--source", default="")
    s.add_argument("--for", dest="for_", default=None, metavar="EXISTING",
                   help="the element already has a name (always rejected: first name stands)")
    s.set_defaults(fn=cmd_add)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
