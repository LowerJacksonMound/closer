"""Python AST reader. SEAM — GrokBot finishes this. Stdlib ast only.

Contract:
- Input is the textual unit plus the file bytes.
- Return the same unit with reader="python_ast", defs filled, refs filled.
- On syntax error: leave reader="textual", set reader_error, do not drop the unit.
- defs: module-level FunctionDef, AsyncFunctionDef, ClassDef. Nested defs are v2.
- refs: every Import and ImportFrom in the tree, at any depth (function and method bodies, try/except,
  `if TYPE_CHECKING:`), not only module level. Record the module string as ref.name, kind "import" or
  "from". Relative imports keep their leading dots; `from . import x` records ".x".
- refs also: importlib.import_module(...) and __import__(...) whose module argument is a string literal,
  kind "import". A literal `package=` argument anchors a relative name; otherwise a relative name is
  relative to this file, as __package__ would be. A non-literal argument is not a ref: the reader cannot
  name the target, and it does not guess.
- refs are ordered by line, one per (line, name).
- Do not resolve edges here. scan.resolve_edges does that.
- Do not import libcst or tree-sitter.
"""

from __future__ import annotations

import ast
from pathlib import Path


def read_python(unit: dict, abs_path: Path) -> dict:
    try:
        source = abs_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        unit["reader"] = "textual"
        unit["reader_error"] = f"UnicodeDecodeError: {exc}"
        return unit

    try:
        tree = ast.parse(source, filename=str(abs_path))
    except SyntaxError as exc:
        unit["reader"] = "textual"
        unit["reader_error"] = f"SyntaxError: {exc.msg} (line {exc.lineno})"
        return unit

    defs: list[dict] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.append({"name": node.name, "kind": "fn", "line": node.lineno})
        elif isinstance(node, ast.ClassDef):
            defs.append({"name": node.name, "kind": "class", "line": node.lineno})

    refs: list[dict] = []
    calls: list[ast.Call] = []
    imports: list[ast.Import | ast.ImportFrom] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(node)
        elif isinstance(node, ast.Import):
            imports.append(node)
            for alias in node.names:
                refs.append({"name": alias.name, "kind": "import", "line": node.lineno})
        elif isinstance(node, ast.ImportFrom):
            imports.append(node)
            # Relative level stays in the name as leading dots: `from ..a import b` -> "..a".
            dots = "." * node.level
            if node.module:
                refs.append({"name": dots + node.module, "kind": "from", "line": node.lineno})
            else:
                # `from . import x, y` names submodules (or names in __init__); one ref each.
                for alias in node.names:
                    refs.append({"name": dots + alias.name, "kind": "from", "line": node.lineno})

    # Calls are judged after the walk: an alias (`import importlib as il`) may be bound below its use.
    mod_names, fn_names = _importlib_aliases(imports)
    for call in calls:
        name = _dynamic_import(call, mod_names, fn_names)
        if name:
            refs.append({"name": name, "kind": "import", "line": call.lineno})

    # One ref per (line, name): edge_id is ref:{from}:{line}:{name}, and must stay unique.
    seen: set[tuple[int, str]] = set()
    unique: list[dict] = []
    for r in sorted(refs, key=lambda r: r["line"]):
        if (r["line"], r["name"]) not in seen:
            seen.add((r["line"], r["name"]))
            unique.append(r)
    unit["defs"] = defs
    unit["refs"] = unique
    unit["reader"] = "python_ast"
    unit["reader_error"] = None
    return unit


def _importlib_aliases(imports: list[ast.Import | ast.ImportFrom]) -> tuple[set[str], dict[str, str]]:
    """Local names bound to the importlib module, and local names bound to import_module / __import__
    (mapped to which one), anywhere in the file."""
    mods, fns = {"importlib"}, {"__import__": "__import__"}
    for node in imports:
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "importlib":
                    mods.add(a.asname or a.name)
        elif isinstance(node, ast.ImportFrom) and node.module in ("importlib", "builtins") and not node.level:
            for a in node.names:
                if a.name in ("import_module", "__import__"):
                    fns[a.asname or a.name] = a.name
    return mods, fns


def _literal(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _dynamic_import(call: ast.Call, mod_names: set[str], fn_names: dict[str, str]) -> str | None:
    f = call.func
    if isinstance(f, ast.Name) and f.id in fn_names:
        real = fn_names[f.id]
    elif (isinstance(f, ast.Attribute) and f.attr in ("import_module", "__import__")
          and isinstance(f.value, ast.Name) and f.value.id in mod_names | {"builtins"}):
        real = f.attr
    else:
        return None
    kw = {k.arg: k.value for k in call.keywords if k.arg}
    name = _literal(call.args[0] if call.args else kw.get("name"))
    if not name:
        return None
    level = len(name) - len(name.lstrip("."))
    if level and real == "import_module":
        package = _literal(call.args[1] if len(call.args) > 1 else kw.get("package"))
        if package:
            base = package.split(".")
            if level - 1 >= len(base):
                return name  # climbs out of the package; resolve_import marks it unresolved
            rest = name[level:]
            return ".".join(base[: len(base) - (level - 1)] + ([rest] if rest else []))
    return name
