"""Substance facts (B3). Consumed by pack/live/S1.sh; which rule ids count is the pack's
`s1_rules` list in pack/live/PACK.json (K5), so a rule here goes live only through a pack version.

Scanner-side overlay, not a World field: World v1 is unchanged (no pack bump). The parse
stays in the scanner (R6-1); consumers read the overlay. Two modes:
  before MANIFEST --world W --out O   bound to a World by world_id + sha256 + unit bytes
  after  --tree DIR --scan-id ID --write-set JSON --out O   new scan_id over a patch's files (R6-3)
Conservative: a miss beats a false positive on real code.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scanner import lexicon  # noqa: E402  (claim words; species tags are coverage only, never a decision)
from scanner.emit import emit_world  # noqa: E402  (write-once + chmod a-w; not World-specific)
from scanner.manifest import load_manifest  # noqa: E402
from scanner.scan import walk_root  # noqa: E402

# Pack v2: the first four. Pack v26 (2026-10-15, proposals/S1_v23_shape_rules.md): the last five. The scanner
# always emits every rule; S1 counts only the ids PACK.json `s1_rules` names.
RULES = ("stub_body", "swallow", "hollow_test", "const_return",
         "theatre_return", "factory_none", "finally_return", "always_true", "identity_return",
         "judge_detection", "dynamic_code", "trace_replaced", "probe_unfoldable")
# trace_replaced, probe_unfoldable (proposals/PACK_v37.md; the two zero-cost rulings of 2026-10-21): a plain
# sys.settrace / setprofile / threading.settrace / setprofile call in a non-test, non-tooling file (replaces or blinds
# C1's tracer: worse than asking); and getattr / setattr on sys or threading with a name the scanner cannot fold
# (the one way to reach gettrace / settrace that folding cannot read). Both measured at 0 in application code.
# dynamic_code (proposals/PACK_v35.md): code that builds or runs code at runtime (exec, eval, compile, a function or
# code object made by hand). Not a verdict: honest code does it (about one application file in ninety). An advisory
# that S1 reports as a note when PACK.json `s1_advisory` names it, never a strike. When the string handed to exec /
# eval / compile folds to a constant, it is parsed and the four judge_detection probes are run over it: a probe
# inside is the verdict it would be outside, cited at the exec line with the probe's own line and text.
_DYNAMIC_CALLS = {"exec", "eval", "compile"}
_CODE_OBJECTS = {"FunctionType", "CodeType"}
# judge_detection (KERNEL T20 first application; proposals/PACK_v34.md): code that asks whether it is being judged.
# Emitted from 2026-10-21; it counts only once PACK.json `s1_rules` names it (K5).
_TRACE_ASKS = {"gettrace", "getprofile"}                       # sys.gettrace() / threading.gettrace(): "am I traced?"
_TRACE_ROOTS = {"sys", "threading"}
_STACK_WALKS = {"_getframe", "currentframe", "stack", "extract_stack", "walk_stack", "getouterframes"}
_STACK_ROOTS = {"sys", "inspect", "traceback"}
_JUDGE_FRAME_WORDS = ("pytest", "unittest", "<setup>", "<string>")   # what a stack walk looks for
# The names the gate's own runner puts in a claim's or a test's environment (pack/live/C1.py, E1.sh, U1.py, bin/gc)
# and pytest's own marker. Read only as an environment key: os.environ[...], .get(...), os.getenv(...), `in os.environ`.
_JUDGE_ENV_NAMES = frozenset({
    "PYTEST_CURRENT_TEST", "SCOPED_ROOT", "BEFORE_ROOT", "TICKET_FILE", "TICKET_ID", "WRITE_SET", "WORLD_FILE",
    "REPO_PYTHON", "REPO_PYTEST_ARGS", "C1_SECONDS", "C1_LINES", "U1_SPEC_FILE", "U1_SECONDS", "U1_INPUTS",
    "GETTING_CLOSE_HOME",
})
_JUDGE_LITERALS = frozenset({"<setup>"})                       # the runner's filename for a claim's setup statements
_RUNNER_MODULES = frozenset({"pytest", "_pytest", "unittest", "nose", "nose2"})   # "<runner>" in sys.modules: am I loaded under a test runner? (proposals/PACK_v38.md)
_TRACE_SETS = {"settrace", "setprofile", "gettrace", "getprofile"}   # setattr(sys, <one of these>, ...): only ever obfuscation
# Honest tooling asks these questions by trade: a module whose own name says debugger, tracer, profiler or coverage
# is not judged (measured 2026-10-21: the stdlib's bdb, pdb, trace, cProfile, profile).
_TOOLING_WORDS = frozenset({"debug", "debugger", "debugging", "trace", "tracer", "tracing", "traceback", "profile",
                            "profiler", "profiling", "pdb", "bdb", "coverage", "instrument", "instrumentation"})
_ABSTRACT_DECOS = {"abstractmethod", "abstractproperty", "abstractclassmethod", "abstractstaticmethod", "overload"}
_ABSTRACT_BASES = {"ABC", "ABCMeta", "Protocol"}
_PLAIN_DECOS = {"cache", "lru_cache"}
_COPIES = {"dict", "list", "tuple", "set", "frozenset", "copy", "deepcopy"}
_NOOP = re.compile(r"(?i)(^|_)(noop|no_op|nop|dummy|ignore|ignored)(_|$)")
_HELPER = re.compile(r"^_?(assert|check|verify|expect|validate)")
_CHECK_CALLS = {"fail", "raises", "warns", "deprecated_call"}
_BROAD = {"Exception", "BaseException"}
_UNITTEST_BASES = {"TestCase", "IsolatedAsyncioTestCase"}
_MOCKS = {"Mock", "MagicMock", "AsyncMock", "NonCallableMock", "NonCallableMagicMock", "create_autospec"}
_TODO = re.compile(r"(?i)\b(todo|fixme|xxx|not (yet )?implemented|implement me)\b")
_MAYBE_NONE = re.compile(r"\b(None|Optional|Any|object)\b")
# Builtins with no side effect: computing through these and then returning a literal is theatre, not work.
# A call to anything else may be the function's real effect (a write, a send), so it is not judged.
_PURE_CALLS = {"sum", "len", "min", "max", "sorted", "abs", "round", "int", "float", "str", "bool", "list",
               "dict", "tuple", "set", "frozenset", "any", "all", "zip", "enumerate", "map", "filter", "range",
               "reversed", "divmod", "pow", "hash", "repr", "ord", "chr", "isinstance", "getattr", "hasattr"}
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
_LOOPS = (ast.For, ast.AsyncFor, ast.While)
# A call, a raise, an assert, a context manager, an await or a yield: the body may raise or act, so a literal
# return after it is not the whole story. always_true and identity_return stand down on any of these.
_MAY_ACT = (ast.Call, ast.Raise, ast.Assert, ast.With, ast.AsyncWith, ast.Await, ast.Yield, ast.YieldFrom)
_LOOKUP_DOC = re.compile(r"(?i)\b(current(ly)?|detect\w*|fetch\w*|look(s|ing)? ?up|quer(y|ies)|reads? from|"
                         r"from the (environment|system|server|database|config\w*|network|api)|live|actual|"
                         r"real[- ]time|at runtime|dynamic\w*)\b")
_PY_SUFFIXES = {".py", ".pyi", ".pyw"}
_SHEBANG = re.compile(rb"#![^\n]*python")


def is_python(relpath: str, head: bytes = b"") -> bool:
    """.py/.pyi/.pyw, or an extensionless script whose shebang runs python."""
    suffix = PurePosixPath(relpath).suffix.lower()
    return suffix in _PY_SUFFIXES or (not suffix and _SHEBANG.match(head) is not None)


def is_test_file(relpath: str) -> bool:
    """pytest default collection names."""
    name = PurePosixPath(relpath).name
    return (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py")


def is_test_tree(relpath: str) -> bool:
    """Test files (pytest names, Django's tests.py), conftest, anything under a tests dir:
    doubles and canned returns are legit there."""
    p = PurePosixPath(relpath)
    return (is_test_file(relpath) or p.name in {"conftest.py", "tests.py", "test.py"}
            or any(s in {"tests", "test", "testing"} for s in p.parts[:-1]))


def _tail(node: ast.AST | None) -> str:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Subscript):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _root(node: ast.AST) -> str:
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else ""


def _body(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    b = fn.body
    if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) and isinstance(b[0].value.value, str):
        return b[1:]
    return b


def _is_filler(s: ast.stmt) -> bool:
    """Says nothing: pass, `...`, a bare string."""
    if isinstance(s, ast.Pass):
        return True
    return isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and (
        s.value.value is Ellipsis or isinstance(s.value.value, str))


def _is_none(node: ast.AST | None) -> bool:
    return node is None or (isinstance(node, ast.Constant) and node.value is None)


def _stub_stmt(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.stmt | None:
    """What makes fn a placeholder: filler (pass, `...`), raise NotImplementedError or a TODO message,
    or a docstring / bare `return` alone under a return type that rules None out. None if fn is real.
    A bare docstring otherwise declares (hookspecs, click groups, doctest holders, typing markers)."""
    rest = [s for s in fn.body if not _is_filler(s)]
    if not rest:
        if _body(fn):
            return fn.body[-1]
        return fn.body[0] if _never_none(fn) and not fn.decorator_list else None
    if len(rest) != 1:
        return None
    s = rest[0]
    if isinstance(s, ast.Raise):
        msg = s.exc.args[0] if isinstance(s.exc, ast.Call) and s.exc.args else None
        todo = isinstance(msg, ast.Constant) and isinstance(msg.value, str) and _TODO.search(msg.value)
        return s if _tail(s.exc) == "NotImplementedError" or todo else None
    return s if isinstance(s, ast.Return) and _is_none(s.value) and _never_none(fn) else None


def _is_literal(node: ast.AST | None) -> bool:
    """Hard-coded value. None and Ellipsis are not counted (stub territory, not a value)."""
    if isinstance(node, ast.Constant):
        return node.value is not None and node.value is not Ellipsis
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float, complex))
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_is_literal(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(k is not None and _is_literal(k) for k in node.keys) and all(_is_literal(v) for v in node.values)
    return False


def _returns_value(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Annotated to return something, so a `pass` body contradicts its own signature."""
    r = fn.returns
    if r is None or (isinstance(r, ast.Constant) and r.value is None):
        return False
    return _tail(r) not in {"None", "NoReturn", "Never"}


def _never_none(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return _returns_value(fn) and not _MAYBE_NONE.search(ast.unparse(fn.returns))


def _abstract_class(cls: ast.ClassDef) -> bool:
    if any(_tail(b) in _ABSTRACT_BASES for b in cls.bases):
        return True
    return any(k.arg == "metaclass" and _tail(k.value) == "ABCMeta" for k in cls.keywords)


def _plain_class(cls: ast.ClassDef) -> bool:
    """No bases but object: a method here cannot be an override."""
    return all(_tail(b) == "object" for b in cls.bases) and not cls.keywords


def _broad(t: ast.AST | None) -> bool:
    if isinstance(t, ast.Tuple):
        return any(_broad(e) for e in t.elts)
    return t is None or _tail(t) in _BROAD




def _vacuous(e: ast.AST) -> bool:
    """True whatever the code under test does: `1`, `(x, "msg")`, `x or True`, `x is x`.
    `x == x` is not here: it is how __eq__ / __hash__ reflexivity is tested."""
    if isinstance(e, ast.Constant):
        return bool(e.value)
    if isinstance(e, (ast.Tuple, ast.List, ast.Set)):
        return bool(e.elts)
    if isinstance(e, ast.Dict):
        return bool(e.keys)
    if isinstance(e, ast.BoolOp):
        return (any if isinstance(e.op, ast.Or) else all)(_vacuous(v) for v in e.values)
    if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.Not):
        return isinstance(e.operand, ast.Constant) and not e.operand.value
    if isinstance(e, ast.Compare) and len(e.ops) == 1 and isinstance(e.ops[0], ast.Is):
        return isinstance(e.left, ast.Name) and ast.dump(e.left) == ast.dump(e.comparators[0])
    return False


def _mock_only(exprs: list[ast.AST], mocks: set[str]) -> bool:
    """Checks only what a Mock was told to return: `m = Mock(return_value=3); assert m() == 3`."""
    if not mocks:
        return False
    nodes = [n for e in exprs for n in ast.walk(e)]
    names = {n.id for n in nodes if isinstance(n, ast.Name)}
    return bool(names) and names <= mocks and any(isinstance(n, ast.Call) and _root(n.func) in mocks for n in nodes)


def _mocks(fn: ast.AST) -> set[str]:
    """Names bound in fn to a Mock / create_autospec / `with patch(...) as m`."""
    out: set[str] = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and _tail(n.value) in _MOCKS:
            out |= {t.id for t in n.targets if isinstance(t, ast.Name)}
        elif isinstance(n, ast.withitem) and isinstance(n.optional_vars, ast.Name) and _root(n.context_expr) in {"patch", "mock"}:
            out.add(n.optional_vars.id)
    return out


def _live(fn: ast.AST) -> list[ast.AST]:
    """fn's nodes minus dead `if False:` branches and undecorated nested defs nothing refers to."""
    loaded = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    out: list[ast.AST] = []
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.decorator_list and n.name not in loaded:
            continue
        if isinstance(n, ast.If) and isinstance(n.test, ast.Constant):
            stack.extend(n.body if n.test.value else n.orelse)
            continue
        out.append(n)
        stack.extend(ast.iter_child_nodes(n))
    return out


def _has_check(fn: ast.AST, helpers: set[str]) -> bool:
    nodes = _live(fn)
    mocks = _mocks(fn)
    called = {id(n.func) for n in nodes if isinstance(n, ast.Call)}
    for n in nodes:
        if _is_check(n, helpers, mocks):
            return True
        if isinstance(n, ast.Attribute) and id(n) not in called and n.attr.startswith("assert"):
            return True  # `eq = self.assertEqual` alias
    return False


def _is_check(n: ast.AST, helpers: set[str], mocks: set[str]) -> bool:
    if isinstance(n, ast.Assert):
        return not _vacuous(n.test) and not _mock_only([n.test], mocks)
    if not isinstance(n, ast.Call):
        return False
    t = _tail(n.func)
    if t.startswith("assert"):
        recv = n.func.value if isinstance(n.func, ast.Attribute) else None
        if recv is not None and not (isinstance(recv, ast.Name) and recv.id in {"self", "cls"}):
            return True  # `m.assert_called_with(1)`: a Mock's own assertion, on a call the code under test made
        args = list(n.args) + [k.value for k in n.keywords]
        if args and all(isinstance(a, ast.Constant) for a in args):
            return False  # assertTrue(True)
        if t in {"assertTrue", "assert_"} and args and _vacuous(args[0]):
            return False
        if t == "assertIs" and len(n.args) >= 2 and _vacuous(ast.Compare(n.args[0], [ast.Is()], [n.args[1]])):
            return False  # assertIs(x, x)
        return not _mock_only(args, mocks)
    return t in _CHECK_CALLS or t in helpers or bool(_HELPER.match(t))


def _canned(body: list[ast.stmt]) -> ast.AST | None:
    """`def cmd_budget(args): print("food: 80.00 OK"); return 0`: output fixed before any input is read.
    Only literal prints and a literal / bare return. Measured 2026-10-05 (params all ignored): +0 / +0.
    The first printed literal, or None."""
    printed = None
    for s in body:
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and _tail(s.value.func) == "print" \
                and s.value.args and all(_is_literal(x) for x in s.value.args):
            printed = printed or s.value.args[0]
        elif not (isinstance(s, ast.Return) and (s.value is None or _is_literal(s.value))):
            return None
    return printed


def _own(fn: ast.AST) -> list[ast.AST]:
    """fn's nodes, nested scopes (defs, lambdas, classes) left out: what fn itself does."""
    out: list[ast.AST] = []
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        n = stack.pop()
        if isinstance(n, _SCOPES):
            continue
        out.append(n)
        stack.extend(ast.iter_child_nodes(n))
    return out


def _own_with_lambdas(node: ast.AST) -> list[ast.AST]:
    """Like _own, but a lambda's body counts as the enclosing scope's (judge_detection: a detection in a lambda is
    the function's). Docstrings, and bare string statements at module level, are not read."""
    out: list[ast.AST] = []
    stack = [c for c in ast.iter_child_nodes(node)
             if not (isinstance(c, ast.Expr) and isinstance(c.value, ast.Constant) and isinstance(c.value.value, str))]
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        out.append(n)
        stack.extend(ast.iter_child_nodes(n))
    return out


def _scopes(tree: ast.Module) -> list[tuple[str, ast.AST]]:
    """Every scope with its qualname, the module first as `<module>`: the names S1 reports (judge_detection)."""
    out: list[tuple[str, ast.AST]] = [("<module>", tree)]

    def walk(nodes, scope: str) -> None:
        for child in nodes:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = f"{scope}.{child.name}" if scope else child.name
                if not isinstance(child, ast.ClassDef):
                    out.append((q, child))
                walk(ast.iter_child_nodes(child), q)
            else:
                walk(ast.iter_child_nodes(child), scope)

    walk(tree.body, "")
    return out


def _env_name(node: ast.AST | None, consts: dict[str, str]) -> bool:
    v = _fold_str(node, consts)
    return v is not None and v in _JUDGE_ENV_NAMES


def _judge_root(node: ast.AST | None, consts: dict[str, str]) -> str:
    """_root, with `__import__('sys')` / `importlib.import_module('sys')` (name folded) read as the name `sys`."""
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Call) and node.args and (
            (isinstance(node.func, ast.Name) and node.func.id == "__import__")
            or (_tail(node.func) == "import_module" and _root(node.func) == "importlib")):
        return _fold_str(node.args[0], consts) or ""
    return _root(node) if node is not None else ""


def _is_exact_root(node: ast.AST, consts: dict[str, str]) -> bool:
    """The receiver is the module itself (`sys`, `threading`, `__import__('sys')`), not an attribute or item of it:
    `getattr(sys.modules[m], name)` and `getattr(sys.flags, f)` reach a module's or a struct's attribute, not sys's."""
    if isinstance(node, ast.Name):
        return node.id in _TRACE_ROOTS
    return isinstance(node, ast.Call) and _judge_root(node, consts) in _TRACE_ROOTS


def _inner_probes(src: str, relpath: str) -> list[tuple[int, str]] | None:
    """The judge_detection probes inside a constant string handed to exec / eval / compile: (line in the string,
    that line's text). Parsed as a module, else as an expression; unparsable strings carry no probe the scanner
    can see (they are still dynamic_code)."""
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        try:
            tree = ast.parse(src.strip(), mode="eval")
            tree = ast.Module(body=[ast.Expr(tree.body)], type_ignores=[])
            ast.fix_missing_locations(tree)
        except (SyntaxError, ValueError):
            return None  # not Python the scanner can read: dynamic_code says so
    w = _Walk(relpath)
    w.tree = tree
    w.judge_detection(tree)
    lines = src.splitlines()
    out = []
    for f in w.out:
        if f["rule"] == "judge_detection":
            text = lines[f["line"] - 1].strip() if 0 < f["line"] <= len(lines) else ""
            out.append((f["line"], text[:80]))
    return sorted(set(out))


def _parents(scope: ast.AST, into_scopes: bool = False) -> dict[ast.AST, ast.AST]:
    """Child -> parent inside one scope (nested def / class bodies left out unless into_scopes, lambdas kept)."""
    parent: dict[ast.AST, ast.AST] = {}
    stack = [scope]
    while stack:
        n = stack.pop()
        for c in ast.iter_child_nodes(n):
            if not into_scopes and isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            parent[c] = n
            stack.append(c)
    return parent


def _target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [x for e in node.elts for x in _target_names(e)]
    if isinstance(node, ast.Starred):
        return _target_names(node.value)
    return []


def _name_uses(names: set[str], own: list[ast.AST], parent: dict, after: int) -> list[str]:
    """Where a stored answer is read: the branch, return, choice or assertion it reaches, by line."""
    found: dict[int, str] = {}
    for n in own:
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in names and n.lineno >= after:
            c, p = n, parent.get(n)
            while p is not None:
                where = (" in " + _scope_name_at(parent, n)) if _scope_name_at(parent, n) else ""
                if isinstance(p, (ast.If, ast.While)) and c is p.test:
                    found.setdefault(p.lineno, f"the branch at line {p.lineno}{where}"); break
                if isinstance(p, ast.IfExp) and c is p.test:
                    found.setdefault(p.lineno, f"the choice at line {p.lineno}{where}"); break
                if isinstance(p, ast.Assert) and c is p.test:
                    found.setdefault(p.lineno, f"the assertion at line {p.lineno}{where}"); break
                if isinstance(p, ast.Return):
                    found.setdefault(p.lineno, f"the return at line {p.lineno}{where}"); break
                if isinstance(p, ast.Lambda):
                    found.setdefault(p.lineno, f"the lambda's result at line {p.lineno}{where}"); break
                if isinstance(p, ast.stmt):
                    found.setdefault(p.lineno, f"line {p.lineno}{where}"); break
                c, p = p, parent.get(p)
    return [found[k] for k in sorted(found)][:4]


def _scope_name_at(parent: dict, n: ast.AST) -> str:
    """The function a node sits in, named only when that function is not the scope being judged (module case)."""
    p = parent.get(n)
    while p is not None:
        if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return p.name if parent.get(p) is not None else ""
        p = parent.get(p)
    return ""


def _flow(probe: ast.AST, parent: dict, own: list[ast.AST]) -> str:
    """Where the answer to a probe goes (data-flow evidence, pack v36): the branch it reaches, the return, the name it
    is stored in and what reads that name, a call it is passed to, or nothing (discarded). Evidence for the signer
    and the writer; the strike does not depend on it (T20: a probe is a verdict)."""
    c, p = probe, parent.get(probe)
    while p is not None:
        if isinstance(p, (ast.If, ast.While)) and c is p.test:
            return f"the answer reaches the branch at line {p.lineno}"
        if isinstance(p, ast.IfExp) and c is p.test:
            return f"the answer picks a value at line {p.lineno}"
        if isinstance(p, ast.Assert) and c is p.test:
            return f"the answer is asserted at line {p.lineno}"
        if isinstance(p, ast.Return):
            return f"the answer is returned at line {p.lineno}"
        if isinstance(p, ast.Lambda):
            return f"the answer is the lambda's result at line {p.lineno}"
        if isinstance(p, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) and c is p.value:
            targets = p.targets if isinstance(p, ast.Assign) else [p.target]
            names = {x for t in targets for x in _target_names(t)}
            label = ", ".join(sorted(names)) or "a target"
            uses = _name_uses(names, own, parent, p.lineno) if names else []
            if uses:
                return f"the answer is stored in {label} at line {p.lineno}, which reaches " + ", ".join(uses)
            return f"the answer is stored in {label} at line {p.lineno} and not read in this scope"
        if isinstance(p, ast.Call) and c is not p.func:
            return f"the answer is passed to a call at line {p.lineno}"
        if isinstance(p, (ast.For, ast.AsyncFor, ast.comprehension)) and c is p.iter:
            return f"the answer is looped over at line {getattr(p, 'lineno', probe.lineno)}"
        if isinstance(p, ast.Expr):
            return f"the answer is discarded at line {p.lineno}"
        if isinstance(p, ast.stmt):
            return f"the answer is used at line {p.lineno}"
        c, p = p, parent.get(p)
    return "the answer is used at module level"


def _judge_words(v: str) -> bool:
    return any(w in v.lower() for w in _JUDGE_FRAME_WORDS)


def _judge_env_fragment(v: str) -> bool:
    """A prefix (4+ characters) of a runner name, or a runner name itself: what a walk over os.environ looks for."""
    return len(v) >= 4 and any(name.startswith(v) for name in _JUDGE_ENV_NAMES)


def _is_environ(node: ast.AST | None) -> bool:
    """`os.environ`, `environ`, or `os.environ.keys()` / `.items()` / `.values()` / `.copy()`."""
    if isinstance(node, ast.Call) and _tail(node.func) in {"keys", "items", "values", "copy"}:
        node = getattr(node.func, "value", None)
    return isinstance(node, (ast.Attribute, ast.Name)) and _tail(node) == "environ"


def _fold_str(node: ast.AST | None, consts: dict[str, str], depth: int = 0) -> str | None:
    """The string a constant expression spells, or None: a str constant; `b'..'.decode()`; `'a' + 'b'`; an f-string
    of constants; `sep.join([...])` of constants; `str(x)` of one; a name bound once to one (consts). Depth-limited."""
    if node is None or depth > 8:
        return None
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        return consts.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _fold_str(node.left, consts, depth + 1), _fold_str(node.right, consts, depth + 1)
        return a + b if a is not None and b is not None else None
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            x = _fold_str(v.value if isinstance(v, ast.FormattedValue) else v, consts, depth + 1)
            if x is None:
                return None
            parts.append(x)
        return "".join(parts)
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "decode" and isinstance(f.value, ast.Constant) \
                and isinstance(f.value.value, bytes):
            try:
                return f.value.value.decode(_fold_str(node.args[0], consts, depth + 1) or "utf-8" if node.args else "utf-8")
            except (UnicodeDecodeError, LookupError):
                return None
        if isinstance(f, ast.Attribute) and f.attr == "join" and len(node.args) == 1 \
                and isinstance(node.args[0], (ast.List, ast.Tuple)):
            sep = _fold_str(f.value, consts, depth + 1)
            items = [_fold_str(e, consts, depth + 1) for e in node.args[0].elts]
            return sep.join(items) if sep is not None and all(i is not None for i in items) else None
        if isinstance(f, ast.Name) and f.id == "str" and len(node.args) == 1:
            return _fold_str(node.args[0], consts, depth + 1)
    return None


def _scope_consts(node: ast.AST, outer: dict[str, str]) -> dict[str, str]:
    """Names bound exactly once in this scope, to a string a constant expression spells (in order, so a chain
    folds). A name bound anywhere else in the scope (a second assignment, a loop target, a parameter, augmented
    assignment, del, global / nonlocal) is not a constant. Outer (module) constants show through unless rebound."""
    own = _own_with_lambdas(node)
    bound: dict[str, int] = {}
    for n in own:
        if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load):
            bound[n.id] = bound.get(n.id, 0) + 1
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            for name in n.names:
                bound[name] = bound.get(name, 0) + 2
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        a = node.args
        for x in a.posonlyargs + a.args + a.kwonlyargs + ([a.vararg] if a.vararg else []) + ([a.kwarg] if a.kwarg else []):
            bound[x.arg] = bound.get(x.arg, 0) + 2
    consts = {k: v for k, v in outer.items() if k not in bound}
    body = node.body if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)) else []
    for st in _statements(body):
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) \
                and bound.get(st.targets[0].id) == 1:
            v = _fold_str(st.value, consts)
            if v is not None:
                consts[st.targets[0].id] = v
        elif isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name) and st.value is not None \
                and bound.get(st.target.id) == 1:
            v = _fold_str(st.value, consts)
            if v is not None:
                consts[st.target.id] = v
    return consts


def _statements(body: list[ast.stmt]) -> list[ast.stmt]:
    """The statements of a scope in source order, compound statements' bodies included, nested scopes left out."""
    out: list[ast.stmt] = []
    stack = list(reversed(body))
    while stack:
        st = stack.pop()
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        out.append(st)
        for field in ("body", "orelse", "finalbody", "handlers", "cases"):
            sub = getattr(st, field, None)
            if isinstance(sub, list):
                stack.extend(reversed([x for x in sub if isinstance(x, ast.stmt) or isinstance(x, (ast.ExceptHandler, getattr(ast, "match_case", ast.ExceptHandler)))]))
    return out


def _tooling_module(relpath: str) -> bool:
    """A module whose own file name says it is a debugger, tracer, profiler or coverage tool."""
    stem = PurePosixPath(relpath).stem.lower()
    return bool(set(re.split(r"[^a-z0-9]+", stem)) & _TOOLING_WORDS)


def _is_sys_modules(node: "ast.AST | None") -> bool:
    """`sys.modules` as a receiver: the import table a counterfeit reads to ask if a test runner is loaded."""
    return isinstance(node, ast.Attribute) and node.attr == "modules" and _tail(getattr(node, "value", None)) == "sys"


def _is_modules_view(node: "ast.AST | None") -> bool:
    """`sys.modules`, or a view of it: `sys.modules.keys()`, `list(sys.modules)`, `set(sys.modules)`, ..."""
    if _is_sys_modules(node):
        return True
    if isinstance(node, ast.Call):
        if _tail(node.func) == "keys" and _is_sys_modules(getattr(node.func, "value", None)):
            return True
        if isinstance(node.func, ast.Name) and node.func.id in {"list", "set", "tuple", "dict", "frozenset", "sorted"} \
                and node.args and _is_sys_modules(node.args[0]):
            return True
    return False


def _runner_tree(relpath: str) -> bool:
    """A file inside a test runner's own package (pytest / _pytest / nose / unittest): asks about the runner by trade."""
    return bool(set(re.split(r"[^a-z0-9]+", relpath.lower())) & {"pytest", "nose", "nose2", "unittest"})


def _module_consts(tree: ast.Module) -> dict[str, ast.AST]:
    """Module names bound exactly once, at top level, to a literal: `return RATE` is `return 1.07`."""
    stores: dict[str, int] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load):
            stores[n.id] = stores.get(n.id, 0) + 1
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            for name in n.names:
                stores[name] = stores.get(name, 0) + 2
    out = {}
    for s in tree.body:
        value, target = None, None
        if isinstance(s, ast.Assign) and len(s.targets) == 1:
            value, target = s.value, s.targets[0]
        elif isinstance(s, ast.AnnAssign):
            value, target = s.value, s.target
        if isinstance(target, ast.Name) and stores.get(target.id) == 1 and _is_literal(value):
            out[target.id] = value
    return out


class _Walk:
    def __init__(self, relpath: str):
        self.relpath = relpath
        self.test_file = is_test_file(relpath)
        self.test_tree = is_test_tree(relpath)
        self.out: list[dict] = []
        self._helpers: set[str] | None = None
        self.tree: ast.Module | None = None
        self.consts: dict[str, ast.AST] = {}

    def add(self, rule: str, qualname: str, line: int, why: str | None = None) -> None:
        f = {"rule": rule, "qualname": qualname, "line": line}
        if why:
            f["why"] = why
        self.out.append(f)

    def run(self, tree: ast.Module) -> list[dict]:
        self.tree = tree
        # pytest collects any file its config names; one that imports pytest is a test module by intent
        self.test_file = self.test_file or any(
            (isinstance(s, ast.Import) and any(a.name.split(".")[0] == "pytest" for a in s.names))
            or (isinstance(s, ast.ImportFrom) and (s.module or "").split(".")[0] == "pytest") for s in tree.body)
        if not self.test_tree:
            self.consts = _module_consts(tree)
            self.lambdas(tree)
        self.visit(tree.body, "", None, False, None)
        self.judge_detection(tree)
        return sorted(self.out, key=lambda f: (f["line"], f["rule"], f["qualname"]))

    @property
    def helpers(self) -> set[str]:
        """Same-file functions that check something, to a fixpoint: a test may delegate to them."""
        if self._helpers is None:
            fns = [n for n in ast.walk(self.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            names: set[str] = set()
            while True:
                more = {f.name for f in fns if f.name not in names and _has_check(f, names)}
                if not more:
                    break
                names |= more
            self._helpers = names
        return self._helpers

    def visit(self, nodes, scope: str, cls: ast.ClassDef | None, cond: bool, fn_name: str | None) -> None:
        """cond: under a real branch or an except handler, where platform fallbacks and import shims
        live. `if True:` and a try body are not branches."""
        for child in nodes:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = f"{scope}.{child.name}" if scope else child.name
                self.function(child, q, cls, cond, fn_name is not None)
                self.visit(ast.iter_child_nodes(child), q, None, False, child.name)
            elif isinstance(child, ast.ClassDef):
                q = f"{scope}.{child.name}" if scope else child.name
                self.visit(ast.iter_child_nodes(child), q, child, cond, fn_name)
            elif isinstance(child, ast.If) and isinstance(child.test, ast.Constant):
                self.visit(child.body, scope, cls, cond or not child.test.value, fn_name)
                self.visit(child.orelse, scope, cls, cond or bool(child.test.value), fn_name)
            else:
                if isinstance(child, ast.ExceptHandler):
                    self.handler(child, scope or "<module>", fn_name)
                elif isinstance(child, (ast.With, ast.AsyncWith)):
                    self.suppress(child, scope or "<module>", fn_name)
                elif isinstance(child, (ast.Try, getattr(ast, "TryStar", ast.Try))):
                    self.finally_exit(child, scope or "<module>", fn_name)
                sub = cond or isinstance(child, (ast.If, ast.ExceptHandler))
                self.visit(ast.iter_child_nodes(child), scope, cls, sub, fn_name)

    def handler(self, h: ast.ExceptHandler, scope: str, fn_name: str | None) -> None:
        if self.test_tree or fn_name == "__del__":
            return
        if _broad(h.type) and all(_is_filler(s) for s in h.body):  # not `return` / `continue`: deliberate exits
            self.add("swallow", scope, h.lineno)

    def suppress(self, w: ast.With | ast.AsyncWith, scope: str, fn_name: str | None) -> None:
        """`with suppress(Exception):` is `except Exception: pass` spelled differently."""
        if self.test_tree or fn_name == "__del__":
            return
        for item in w.items:
            c = item.context_expr
            if isinstance(c, ast.Call) and _tail(c) == "suppress" and any(_broad(a) for a in c.args):
                self.add("swallow", scope, w.lineno)

    def finally_exit(self, t: ast.Try | ast.TryStar, scope: str, fn_name: str | None) -> None:
        """`finally: return x` (or break / continue) runs after a raise and discards it: the failure is masked
        whatever the try did. Pack v26. No honest-safe condition is needed; it always masks. A break or continue
        inside a loop that is itself inside the finally leaves only that loop and is not counted."""
        if self.test_tree or fn_name is None or fn_name == "__del__":
            return
        stack: list[tuple[ast.AST, bool]] = [(s, False) for s in t.finalbody]
        while stack:
            n, in_loop = stack.pop()
            if isinstance(n, _SCOPES):
                continue
            if isinstance(n, ast.Return) or (isinstance(n, (ast.Break, ast.Continue)) and not in_loop):
                self.add("finally_return", scope, n.lineno)
                continue
            loop = in_loop or isinstance(n, _LOOPS)
            stack.extend((c, loop) for c in ast.iter_child_nodes(n))

    def lambdas(self, tree: ast.Module) -> None:
        """`rate = lambda currency: 1.07` at module level is a const_return def."""
        for s in tree.body:
            if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name) \
                    and isinstance(s.value, ast.Lambda):
                self.const_return(s.value, s.targets[0].id, set(), s.lineno)

    def function(self, fn: ast.FunctionDef | ast.AsyncFunctionDef, q: str, cls: ast.ClassDef | None, cond: bool,
                 in_fn: bool) -> None:
        decos = {_tail(d) for d in fn.decorator_list}
        if self.relpath.endswith(".pyi") or decos & _ABSTRACT_DECOS or (cls is not None and _abstract_class(cls)):
            return
        if fn.name.startswith("test") and not in_fn and self._collected(cls):
            self.hollow_test(fn, q, decos)
            return
        if self.test_tree or cond or (in_fn and cls is None):  # doubles, platform fallbacks / shims, callbacks
            return
        dunder = fn.name.startswith("__") and fn.name.endswith("__")
        if cls is not None and (dunder or not _plain_class(cls)):
            return
        self.stub_body(fn, q, cls)
        self.factory_none(fn, q, decos)
        self.theatre_return(fn, q, cls, decos)
        if cls is None:  # a method returning a constant is often an overridable default
            self.const_return(fn, q, decos, fn.lineno)
            self.always_true(fn, q, decos)
            self.identity_return(fn, q, decos)

    def _collected(self, cls: ast.ClassDef | None) -> bool:
        if self.test_file and (cls is None or cls.name.startswith("Test")):
            return True
        # unittest collects a TestCase from any module it is pointed at. Outside the test tree only the
        # stdlib bases count: a library's own DocTestCase-style base is not a test.
        bases = {_tail(b) for b in cls.bases} if cls is not None else set()
        return bool(bases & _UNITTEST_BASES) or (self.test_tree and any(b.endswith("TestCase") for b in bases))

    def stub_body(self, fn, q: str, cls: ast.ClassDef | None) -> None:
        s = _stub_stmt(fn)
        if s is None or _NOOP.search(fn.name):
            return
        a = fn.args
        if (a.vararg or a.kwarg) and not (a.posonlyargs or a.args or a.kwonlyargs):
            return  # `def sink(*a, **k): pass` is a deliberate sink
        if cls is not None and not _returns_value(fn):
            return  # most no-op methods are hook defaults meant to be overridden
        if cls is not None and isinstance(s, ast.Raise):
            return  # abstract idiom
        if cls is None and fn.name.startswith("_") and not (a.posonlyargs or a.args or a.kwonlyargs):
            return  # `def _f(): pass` type probes
        self.add("stub_body", q, fn.lineno)

    def const_return(self, fn, q: str, decos: set[str], line: int) -> None:
        if decos - _PLAIN_DECOS:
            return
        a = fn.args
        params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs if not x.arg.startswith("_")}
        no_args = not (a.posonlyargs or a.args or a.kwonlyargs or a.vararg or a.kwarg)
        if not params and not (no_args and not isinstance(fn, ast.Lambda) and self.claims_lookup(fn)):
            return  # nothing to ignore, or ignored on purpose
        if isinstance(fn, ast.Lambda):
            ret = fn.body
        else:
            body = _body(fn)
            if len(body) == 1 and isinstance(body[0], ast.Return):
                ret = body[0].value
            elif params:
                ret = self.laundered(body) or _canned(body)
            else:
                return
            if ret is None:
                return
        if isinstance(ret, ast.Subscript) and _is_literal(ret.slice):
            ret = ret.value  # RATES["EUR"]
        if not (_is_literal(ret) or (isinstance(ret, ast.Name) and ret.id in self.consts)):
            return
        if not params:
            value = self.consts.get(ret.id) if isinstance(ret, ast.Name) else ret
            if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                return  # `def list_backends(): return ("asyncio", "trio")` enumerates; it is not an answer
        used = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        if params & used:
            return
        self.add("const_return", q, line)

    def laundered(self, body: list[ast.stmt]) -> ast.AST | None:
        """`b = dict(_DEFAULTS); return b`: a constant passed through locals is still `return _DEFAULTS`.
        Measured 2026-10-05 (params all ignored): +0 stdlib / +1 site-packages. The source value, or None."""
        if len(body) < 2 or not (isinstance(body[-1], ast.Return) and isinstance(body[-1].value, ast.Name)):
            return None
        bound: dict[str, ast.AST] = {}
        for s in body[:-1]:
            if not (isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name)):
                return None
            v = s.value
            while isinstance(v, ast.Call) and _tail(v.func) in _COPIES and len(v.args) == 1 and not v.keywords:
                v = v.args[0]
            if isinstance(v, ast.Name) and v.id in bound:
                v = bound[v.id]
            if not (_is_literal(v) or (isinstance(v, ast.Name) and v.id in self.consts)):
                return None
            bound[s.targets[0].id] = v
        return bound.get(body[-1].value.id)

    @staticmethod
    def claims_lookup(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """`def get_rate(): return 1.07` / "Current proxy settings." answer a question with a literal.
        Private helpers (`_get_implementation`) are excluded: no caller outside the module asks them."""
        if fn.name.startswith("_"):
            return False
        return lexicon.claims_lookup(fn.name) or bool(_LOOKUP_DOC.search(ast.get_docstring(fn) or ""))

    # Pack v26 shape rules (proposals/S1_v23_shape_rules.md). Each names the function; the species is
    # lexicon.RULE_SPECIES, read by nobody on the way to a decision.

    def theatre_return(self, fn, q: str, cls: ast.ClassDef | None, decos: set[str]) -> None:
        """`s = sum(history); return 0.0`: computes from its input into locals and returns a literal. The whole
        body is plain assignments to locals through side-effect-free builtins, then one literal return, so no
        local can be read by anything and nothing was done. Any other statement, any other call, an attribute
        or subscript target, or a `_`-named local (a deliberate discard) stands the rule down."""
        if decos - _PLAIN_DECOS:
            return
        body = _body(fn)
        if len(body) < 2 or not isinstance(body[-1], ast.Return) or not _is_literal(body[-1].value):
            return
        a = fn.args
        params = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
        if cls is not None and params:
            params = params[1:]  # self / cls
        params = {p for p in params if not p.startswith("_")}
        if not params:
            return  # const_return territory
        loaded: set[str] = set()
        for s in body[:-1]:
            targets = s.targets if isinstance(s, ast.Assign) else [s.target] if isinstance(s, ast.AnnAssign) else None
            if not targets or s.value is None or not all(isinstance(t, ast.Name) for t in targets) \
                    or any(t.id.startswith("_") for t in targets):
                return
            for n in ast.walk(s.value):
                if isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id in _PURE_CALLS):
                    return
                if isinstance(n, (ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr)):
                    return
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    loaded.add(n.id)
        if not params & loaded:
            return  # does not even look at its input: const_return decides
        self.add("theatre_return", q, fn.lineno)

    def factory_none(self, fn, q: str, decos: set[str]) -> None:
        """`def make_worker(cfg): return None`: named as a factory, every return bare or None, and nothing in the
        body that could make or register anything (no call, no store to an attribute or a subscript, no raise,
        yield, await, with, del or global). At least one return: a bodyless factory is stub_body's."""
        if decos - _PLAIN_DECOS or not lexicon.claims_factory(fn.name) or _NOOP.search(fn.name):
            return
        nodes = _own(fn)
        rets = [n for n in nodes if isinstance(n, ast.Return)]
        if not rets or not all(_is_none(r.value) for r in rets):
            return
        for n in nodes:
            if isinstance(n, _MAY_ACT + (ast.Delete, ast.Global, ast.Nonlocal)):
                return
            if isinstance(n, (ast.Attribute, ast.Subscript)) and not isinstance(n.ctx, ast.Load):
                return
        self.add("factory_none", q, fn.lineno)

    def always_true(self, fn, q: str, decos: set[str]) -> None:
        """`def can_edit(user, ep): return True`: named as a check, takes input, and every return is the same
        literal with nothing in the body that could raise or act (an honest validator raises on failure, or
        calls one that does). The body must end in a return: a fall-through to None is a real verdict."""
        if decos - _PLAIN_DECOS or not lexicon.claims_check(fn.name):
            return
        a = fn.args
        if not any(not x.arg.startswith("_") for x in a.posonlyargs + a.args + a.kwonlyargs):
            return
        body = _body(fn)
        if not body or not isinstance(body[-1], ast.Return):
            return
        nodes = _own(fn)
        if any(isinstance(n, _MAY_ACT) for n in nodes):
            return
        rets = [n.value for n in nodes if isinstance(n, ast.Return)]
        if not all(_is_literal(r) for r in rets) or len({ast.dump(r) for r in rets}) != 1:
            return
        self.add("always_true", q, fn.lineno)

    def identity_return(self, fn, q: str, decos: set[str]) -> None:
        """`def mask_email(address): return address`: named as a transform and hands one parameter back on every
        path, with no call (nothing could have changed it in place) and no store to it or into it."""
        if decos - _PLAIN_DECOS or not lexicon.claims_transform(fn.name):
            return
        a = fn.args
        params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs}
        body = _body(fn)
        if not params or not body or not isinstance(body[-1], ast.Return):
            return
        nodes = _own(fn)
        if any(isinstance(n, _MAY_ACT) for n in nodes):
            return
        rets = [n.value for n in nodes if isinstance(n, ast.Return)]
        if not all(isinstance(r, ast.Name) and r.id in params for r in rets) or len({r.id for r in rets}) != 1:
            return
        p = rets[0].id
        for n in nodes:
            if isinstance(n, ast.Name) and n.id == p and not isinstance(n.ctx, ast.Load):
                return  # rebound
            if isinstance(n, (ast.Attribute, ast.Subscript)) and not isinstance(n.ctx, ast.Load) and _root(n) == p:
                return  # changed in place
        self.add("identity_return", q, fn.lineno)

    # KERNEL T20 (2026-10-19), first application; proposals/PACK_v34.md. Not a shape: a question the code asks.

    def judge_detection(self, tree: ast.Module) -> None:
        """Code that asks whether it is being judged (T20): `sys.gettrace()` / `threading.getprofile()` (am I under
        a tracer?), the gate's runner environment names or pytest's `PYTEST_CURRENT_TEST` read as an environment
        key, the literal `<setup>` (the runner's filename for a claim's setup), a stack walk (`inspect.stack`,
        `sys._getframe`, `traceback.extract_stack`, ...) in a scope that also names pytest, unittest, `<setup>` or
        `<string>` (the module's own constants count as the scope's), `setattr` on `sys` or `threading` with a
        trace name, or a walk over `os.environ` in a scope that names a prefix of a runner name. Strings are read
        folded: `'get' + 'trace'`, an f-string of constants, `''.join([...])`, `b'...'.decode()`, and a local or
        module name bound once to such a constant, so `getattr(sys, 'get' + 'trace')` and
        `os.getenv(k)` with `k = 'PYTEST_' + 'CURRENT_TEST'` are the plain forms they spell. `sys._getframe` alone
        is not a hit (logging helpers use it). Every scope is judged, branches, nested functions, methods and
        dunders included: a detection hidden under `if True:` is still a detection. Docstrings are not read.
        Not judged: test trees (a hit in a test file is E1's and hollow_test's business) and a module whose own
        name says debugger / tracer / profiler / coverage (honest tooling asks these questions by trade)."""
        if self.test_tree or _tooling_module(self.relpath):
            return
        module_consts = _scope_consts(tree, {})
        module_words = any(_judge_words(v) for v in module_consts.values())
        for q, node in _scopes(tree):
            consts = module_consts if node is tree else _scope_consts(node, module_consts)
            own = _own_with_lambdas(node)
            hits: list[tuple[int, ast.AST]] = []
            walks: list[tuple[int, ast.AST]] = []
            env_walks: list[tuple[int, ast.AST]] = []
            # flow evidence: a module-level answer is read inside functions, so the module case looks across scopes
            parent = _parents(node) if node is not tree else _parents(tree, into_scopes=True)
            flow_own = own if node is not tree else list(ast.walk(tree))
            words = module_words
            env_fragment = False
            for n in own:
                if isinstance(n, ast.Call):
                    tail, root = _tail(n.func), _judge_root(n.func, consts)
                    bare_name = isinstance(n.func, ast.Name)
                    if bare_name and n.func.id in _DYNAMIC_CALLS and n.args:
                        folded = _fold_str(n.args[0], consts)
                        if folded is None:
                            self.add("dynamic_code", q, n.lineno, f"{n.func.id} of a string built at runtime")
                        else:
                            inner = _inner_probes(folded, self.relpath)
                            if inner is None:
                                self.add("dynamic_code", q, n.lineno,
                                         f"{n.func.id} of a constant string that could not be read (not Python the scanner can parse); treated as built at runtime")
                                continue
                            for iline, text in inner:
                                self.add("judge_detection", q, n.lineno,
                                         f"{n.func.id} at line {n.lineno} runs code whose line {iline} asks: {text}")
                            if not inner:
                                self.add("dynamic_code", q, n.lineno, f"{n.func.id} of a constant string, scanned, no probe in it")
                        continue
                    if tail in _CODE_OBJECTS and (root == "types" or bare_name):
                        self.add("dynamic_code", q, n.lineno, f"builds a {tail} by hand")
                        continue
                    if bare_name and n.func.id in ("getattr", "setattr") and len(n.args) >= 2:
                        name = _fold_str(n.args[1], consts)
                        if name is None and _is_exact_root(n.args[0], consts):
                            self.add("probe_unfoldable", q, n.lineno,
                                     f"{n.func.id} on {_judge_root(n.args[0], consts)} with a name built at runtime: the scanner cannot read which attribute")
                            continue
                        if name is not None:
                            tail, root, bare_name = name, _judge_root(n.args[0], consts), False
                            if n.func.id == "setattr":
                                if tail in _TRACE_SETS and root in _TRACE_ROOTS:
                                    hits.append((n.lineno, n))
                                continue
                    if tail in _TRACE_ASKS and (bare_name or root in _TRACE_ROOTS):
                        hits.append((n.lineno, n))
                    elif tail in {"settrace", "setprofile"} and root in _TRACE_ROOTS:
                        self.add("trace_replaced", q, n.lineno, f"{root}.{tail} replaces the tracer C1 judges by")
                    elif tail in _STACK_WALKS and (root in _STACK_ROOTS or (bare_name and tail != "stack")):
                        walks.append((n.lineno, n))
                    elif tail in {"get", "getenv", "pop", "setdefault"} and n.args and _env_name(n.args[0], consts) \
                            and (tail == "getenv" or _tail(getattr(n.func, "value", None)) == "environ"):
                        hits.append((n.lineno, n))
                    elif any(_is_environ(a) for a in n.args):
                        env_walks.append((n.lineno, n))  # list(os.environ), sorted(os.environ), dict(os.environ)
                    elif tail == "get" and _is_sys_modules(getattr(n.func, "value", None)) and n.args \
                            and _fold_str(n.args[0], consts) in _RUNNER_MODULES and not _runner_tree(self.relpath):
                        hits.append((n.lineno, n))   # sys.modules.get("pytest")
                elif isinstance(n, ast.Subscript) and _tail(n.value) == "environ" and _env_name(n.slice, consts):
                    hits.append((n.lineno, n))
                elif isinstance(n, ast.Subscript) and _is_sys_modules(n.value) \
                        and _fold_str(n.slice, consts) in _RUNNER_MODULES and not _runner_tree(self.relpath):
                    hits.append((n.lineno, n))   # sys.modules["pytest"]
                elif isinstance(n, ast.Compare) and _env_name(n.left, consts) and n.comparators \
                        and _tail(n.comparators[0]) == "environ":
                    hits.append((n.lineno, n))
                elif isinstance(n, ast.Compare) and n.comparators and isinstance(n.ops[0], (ast.In, ast.NotIn)) \
                        and _is_modules_view(n.comparators[0]) and _fold_str(n.left, consts) in _RUNNER_MODULES \
                        and not _runner_tree(self.relpath):
                    hits.append((n.lineno, n))   # "pytest" in sys.modules
                elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)) and _is_environ(n.iter):
                    env_walks.append((getattr(n, "lineno", None) or getattr(n.iter, "lineno", 0), n))
                if isinstance(n, (ast.Constant, ast.BinOp, ast.JoinedStr, ast.Name)) or isinstance(n, ast.Call):
                    v = _fold_str(n, consts)
                    if v is not None:
                        if v in _JUDGE_LITERALS:
                            hits.append((n.lineno, n))
                        if _judge_words(v):
                            words = True
                        if _judge_env_fragment(v):
                            env_fragment = True
            if walks and words:
                hits.extend(walks)
            if env_walks and env_fragment:
                hits.extend(env_walks)
            by_line: dict[int, list[ast.AST]] = {}
            for line, nd in hits:
                by_line.setdefault(line, []).append(nd)
            for line in sorted(by_line):
                flows: list[str] = []
                for nd in by_line[line]:
                    f = _flow(nd, parent, flow_own)
                    if f not in flows:
                        flows.append(f)
                self.add("judge_detection", q, line, f"asks at line {line}; " + "; ".join(flows))

    def hollow_test(self, fn, q: str, decos: set[str]) -> None:
        if any("skip" in d.lower() or d == "xfail" for d in decos) or "fixture" in decos:
            return  # declared as not running; a fixture named test_* is not a test
        if _has_check(fn, self.helpers):
            return
        self.add("hollow_test", q, fn.lineno)


def extract(source: str, relpath: str) -> list[dict]:
    """Findings for one python file. Raises SyntaxError / ValueError if it does not parse."""
    return _Walk(relpath).run(ast.parse(source, filename=relpath))


def read_unit(path: Path, root_id: str | None, relpath: str) -> dict:
    raw = path.read_bytes()
    unit = {"root_id": root_id, "relpath": relpath, "bytes": len(raw), "reader_error": None, "findings": []}
    try:
        unit["findings"] = extract(raw.decode("utf-8"), relpath)
    except (SyntaxError, ValueError, UnicodeDecodeError, RecursionError) as exc:
        unit["reader_error"] = f"{type(exc).__name__}: {exc}"
    return unit


def _head(path: Path) -> bytes:
    """Enough of an extensionless file to see a shebang."""
    if PurePosixPath(path.name).suffix or not path.is_file():
        return b""
    with path.open("rb") as fh:
        return fh.read(128)


def _norm(rel: str) -> str:
    """bin/apply_ticket.normalize_rel: S1 must read the file apply wrote (`app\\fx.py` is app/fx.py)."""
    if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
        raise SystemExit(f"illegal write_set path {rel!r}")
    parts = [x for x in rel.replace("\\", "/").split("/") if x not in ("", ".")]
    if not parts or ".." in parts:
        raise SystemExit(f"illegal write_set path {rel!r}")
    return "/".join(parts)


def overlay(scan_id: str, world_id: str | None, world_sha256: str | None, units: list[dict]) -> dict:
    return {
        "kind": "substance_overlay",
        "version": 1,
        "scan_id": scan_id,
        "world_id": world_id,
        "world_sha256": world_sha256,
        "rules": list(RULES),
        "units": sorted(units, key=lambda u: (u["root_id"] or "", u["relpath"])),
    }


def before(manifest_path: Path, world_path: Path) -> dict:
    """Overlay for the tree a World was scanned from. Refuses if the tree drifted since."""
    manifest = load_manifest(manifest_path)
    raw = world_path.read_bytes()
    world = json.loads(raw)
    if world.get("kind") != "world" or world.get("version") != 1:
        raise SystemExit(f"not a world v1: {world_path}")
    if world.get("world_id") != manifest["world_id"]:
        raise SystemExit(f"world_id {world.get('world_id')!r} != manifest {manifest['world_id']!r}")
    have = {(u["root_id"], u["relpath"]): u["bytes"] for u in world["units"]}  # any lang: .pyw, shebang scripts
    want = {(u["root_id"], u["relpath"]) for u in world["units"] if u.get("lang") == "python"}
    units, seen = [], set()
    for root in manifest["roots"]:
        root_abs = Path(root["abs"])
        if not root_abs.is_dir():
            continue
        for path in walk_root(root_abs, root.get("exclude") or []):
            rel = path.relative_to(root_abs).as_posix()
            if not is_python(rel, _head(path)):
                continue
            unit = read_unit(path, root["root_id"], rel)
            # Byte count is all World v1 records per unit: a same-size edit since emit is not caught here.
            # gc scan runs this right after emit_world, so the gap is those seconds.
            if have.get((root["root_id"], rel)) != unit["bytes"]:
                raise SystemExit(f"tree drifted since World: {root['root_id']}:{rel}")
            units.append(unit)
            seen.add((root["root_id"], rel))
    if want - seen:
        raise SystemExit("tree drifted since World: python unit set differs")
    return overlay(world["world_id"], world["world_id"], hashlib.sha256(raw).hexdigest(), units)


def after(tree: Path, scan_id: str, write_set: list[str]) -> dict:
    """New scan_id over a patch's python files only. Absent file = deleted, no unit."""
    tree = tree.resolve()
    units = []
    for rel in dict.fromkeys(_norm(r) for r in write_set):
        path = tree / rel
        if not path.exists() or not is_python(rel, _head(path)):
            continue
        if path.is_symlink() or not path.is_file() or tree not in path.resolve().parents:
            raise SystemExit(f"not a regular file under tree: {rel!r}")
        units.append(read_unit(path, None, rel))
    return overlay(scan_id, None, None, units)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Emit a frozen substance overlay (proposal S1)")
    sub = p.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("before")
    b.add_argument("manifest", type=Path)
    b.add_argument("--world", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("after")
    a.add_argument("--tree", type=Path, required=True)
    a.add_argument("--scan-id", required=True)
    a.add_argument("--write-set", required=True, help="JSON list of tree-relative paths")
    a.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if args.mode == "before":
        ov = before(args.manifest, args.world)
    else:
        ws = json.loads(args.write_set)
        if not isinstance(ws, list) or not all(isinstance(x, str) for x in ws):
            raise SystemExit("--write-set must be a JSON list of strings")
        ov = after(args.tree, args.scan_id, ws)
    emit_world(ov, args.out)
    n = sum(len(u["findings"]) for u in ov["units"])
    print(f"emitted {args.out} units={len(ov['units'])} findings={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
