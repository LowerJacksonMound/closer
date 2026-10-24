#!/bin/sh
# Live in pack v3. Edit only through a new pack version (K5).
# R6-1: World consumers do not parse the target tree. They read the World.
# The consumers are listed in R6-1.consumers beside this check: in the signed pack, not in an
# agent-writable file, and not in this script (verify_ticket's tripwire refuses a .sh that names the
# apply tool). Each is read with ast (this check parses kernel files, never the target) and walked at
# every depth. It fails on:
#   - importing a parser: ast, libcst, tree_sitter, parso, lib2to3, typed_ast, astroid, redbaron
#   - calling compile, exec or eval
#   - importlib.import_module / __import__ in any form: a dynamic import cannot be shown not to be a parser
# Args: files to check instead of the listed consumers (plants pass fixtures this way).
set -u
KERNEL="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"

LIST="$(CDPATH= cd -- "$(dirname "$0")" && pwd)/R6-1.consumers"

PYTHONDONTWRITEBYTECODE=1 python3 - "$KERNEL" "$LIST" "$@" << 'PY'
import ast, sys
from pathlib import Path

PARSERS = {"ast", "libcst", "tree_sitter", "parso", "lib2to3", "typed_ast", "astroid", "redbaron"}
CALLS = {"compile", "exec", "eval", "__import__", "import_module"}

kernel = Path(sys.argv[1])
consumers = [s.strip() for s in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if s.strip()]
if not consumers:
    print("R6-1 fail: R6-1.consumers lists no consumer", file=sys.stderr)
    sys.exit(1)
targets = [Path(a) for a in sys.argv[3:]] or [kernel / c for c in consumers]


def problems(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as e:
        return [f"unreadable ({type(e).__name__}): cannot show it does not parse"]
    out = []
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            mods = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
        for m in mods:
            if m.split(".")[0] in PARSERS or m == "importlib.import_module":
                out.append(f"line {node.lineno}: imports {m}")
        if isinstance(node, ast.Call):
            f = node.func
            # Bare names are builtins (or import_module pulled in by name). On an attribute only the
            # import spellings and builtins.* count: re.compile is not a parser.
            if isinstance(f, ast.Name) and f.id in CALLS:
                out.append(f"line {node.lineno}: calls {f.id}")
            elif isinstance(f, ast.Attribute) and (
                f.attr in ("import_module", "__import__")
                or (f.attr in CALLS and isinstance(f.value, ast.Name) and f.value.id == "builtins")
            ):
                out.append(f"line {node.lineno}: calls {f.attr}")
    return out


bad = False
for t in targets:
    shown = t.relative_to(kernel).as_posix() if t.is_relative_to(kernel) else t.name
    if not t.is_file():
        print(f"R6-1 fail: missing listed consumer {shown}", file=sys.stderr)
        bad = True
        continue
    for p in problems(t):
        print(f"R6-1 fail: {shown} {p}", file=sys.stderr)
        bad = True
if bad:
    sys.exit(1)
print(f"R6-1 pass: {len(targets)} consumer(s), no parser")
PY
