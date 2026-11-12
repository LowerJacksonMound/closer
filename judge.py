"""Closer's judge: one function per submission, two tries per location. Stdlib only. ZERO model calls.

submit(repo, file, source, checks, stance, plan) runs, in order, and the first failure stops it:
  0a. plan   refused until the person approved this session's plan (closer_mcp cl_plan); its hash goes on every stance
  0b. stance the agent's yes/no: does the function's purpose agree with the app's intent (both in its words).
             Recorded to agree.jsonl and put first in the reply, whatever the verdict, for the person to glance at;
             it does not change the verdict. Fallback until Closer takes the hashed intent from Cartouche.
  1. parse   source is exactly one top-level def or class and parses; nothing in it runs at import
  2. run     the function spliced into a copy of its file, each check run in its own interpreter under
             sandbox-exec (no network but loopback, writes only inside the temp dir, CLOSER's state unreadable) with
             a timeout. The repo is read in place; only the spliced file lives in the temp dir, served to the import of
             the target module by a hook. A check with serve {body, status} gets a loopback server answering that, as url.
             A check with files {name: text} gets them written under the temp dir, reachable in the call as files["name"].
             The runner calls the submitted def (or builds the class and runs the check's method steps on it) and
             reports what came back as plain JSON (an object as {"__class__": name, public attributes}); it never
             sees the expected value. A crash, an import error or a timeout means it did not run. For a class, every
             method must run in some check, or the submission is refused.
  3. compare here, outside the run: the returned value must equal `expect`, or the exception must be
             `raises` (a builtin name, or module.Class for anything else)
  4. pass    splice into the real file (replace the def of the same name, else insert after the last top-level def),
             atomic write
A fail is a strike on file::function. The second consecutive strike is a HOLE: nothing written, the location is logged
to holes.jsonl for CodeRadar, and further submissions there are refused. A refusal (bad request, holed location, no
sandbox) is not a strike.
"""
from __future__ import annotations

import ast
import builtins
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import holes

TRIES = 2
CHECK_SECS = 20


def state_dir(repo: Path) -> Path:
    home = Path(os.environ.get("CLOSER_HOME") or Path.home() / ".closer")
    return home / f"{repo.name}-{hashlib.sha256(str(repo).encode()).hexdigest()[:8]}"


class Refused(Exception):
    """Not judged, no strike."""


def safe_rel(repo: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel.endswith(".py") or rel.startswith(("/", "~")) \
            or ".." in Path(rel).parts or any(ord(c) < 32 for c in rel):
        raise Refused(f"file must be a relative .py path inside the repo, got {rel!r}")
    p = repo / rel
    try:
        p.resolve().relative_to(repo.resolve())
    except ValueError:
        raise Refused(f"path escapes repo: {rel}")
    return p


# ---- 1. parse ----------------------------------------------------------------------------------------------------

FN = (ast.FunctionDef, ast.AsyncFunctionDef)
RUNS = (ast.Call, ast.NamedExpr, ast.Await, ast.Yield, ast.YieldFrom)
METHOD_DECOS = {"staticmethod", "classmethod", "property"}
FIELD = {"field", "dataclasses.field"}  # dataclass field(...) builds a default, it runs nothing of the submission's


def _calls_only(nodes, allowed=frozenset()):
    """True if nothing in nodes runs code at import, apart from calls to the named stdlib helpers."""
    for n in (n for x in nodes if x is not None for n in ast.walk(x)):
        if isinstance(n, ast.Call) and ast.unparse(n.func) in allowed:
            continue
        if isinstance(n, RUNS):
            return False
    return True


def _head(fn) -> list:
    a = fn.args
    return a.defaults + a.kw_defaults + [fn.returns] + [x.annotation for x in a.posonlyargs + a.args + a.kwonlyargs] \
        + [x.annotation for x in (a.vararg, a.kwarg) if x]


def parse_one(source: str):
    """Import lines, then one top-level def or class. Anything that runs at import (decorators, defaults,
    annotations, a class body) runs before a check can call it, so none of it may run code."""
    tree = ast.parse(source)
    body = [n for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom))]
    if len(body) != 1 or not isinstance(body[0], FN + (ast.ClassDef,)) or tree.body[-1] is not body[0]:
        raise Refused("source must be import lines (optional), then exactly one top-level def or class")
    if any(a.name == "*" for n in tree.body[:-1] for a in n.names):
        raise Refused("no star imports: name what you import")
    node = body[0]
    if isinstance(node, FN):
        if node.decorator_list:
            raise Refused("no decorators: the def must be the code that runs")
        if not _calls_only(_head(node)):
            raise Refused("defaults and annotations must not call anything: they run on import")
        return node
    for d in node.decorator_list:  # @dataclass / @dataclass(frozen=True) only
        f = d.func if isinstance(d, ast.Call) else d
        if ast.unparse(f) not in ("dataclass", "dataclasses.dataclass") or not _calls_only([d] if d is f else d.args + [k.value for k in d.keywords]):
            raise Refused(f"class decorator {ast.unparse(d)}: only @dataclass, with plain arguments")
    if node.keywords or not all(isinstance(b, (ast.Name, ast.Attribute)) for b in node.bases):
        raise Refused("class bases must be plain names, no metaclass or other keywords")
    if not node.bases and not any(isinstance(b, (FN, ast.Assign, ast.AnnAssign)) for b in node.body):
        raise Refused("a class needs a method, a field or a base class, so the checks have something of it to run or compare")
    for b in node.body:
        if isinstance(b, FN):
            for d in b.decorator_list:
                txt = ast.unparse(d)
                if txt not in METHOD_DECOS and not (isinstance(d, ast.Attribute) and d.attr in ("setter", "deleter")):
                    raise Refused(f"method {b.name}: decorator {txt} not allowed (staticmethod, classmethod, property)")
            if not _calls_only(_head(b)):
                raise Refused(f"method {b.name}: defaults and annotations must not call anything: they run on import")
        elif isinstance(b, (ast.Assign, ast.AnnAssign)):
            if not _calls_only([b], FIELD):
                raise Refused(f"class body line {ast.unparse(b)[:80]}: must not call anything, it runs on import")
        elif not (isinstance(b, ast.Pass) or (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant))):
            raise Refused("a class body holds methods, plain attributes and a docstring, nothing else")
    return node


def methods(node) -> dict[int, str]:
    """{first line, as the code object reports it: name} for every method of a class node."""
    return {min([b.lineno] + [d.lineno for d in b.decorator_list]): b.name for b in node.body if isinstance(b, FN)}


ARG_NODES = (ast.Constant, ast.List, ast.Tuple, ast.Set, ast.Dict, ast.UnaryOp, ast.USub, ast.UAdd, ast.Name,
             ast.Attribute, ast.Call, ast.keyword, ast.Load)


def _check_args(i, call):
    for n in [n for x in call.args + call.keywords for n in ast.walk(x)]:
        label = n.id if isinstance(n, ast.Name) else n.attr if isinstance(n, ast.Attribute) else ""
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "files" \
                and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str):
            continue  # files["name"]: a fixture path, resolved in the runner
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in dir(builtins):
            raise Refused(f"check {i}: {n.func.id}(...) is a builtin, not one of the repo's own classes; a check names what "
                          "it passes, it does not compute it (put file text in files, not open())")
        if not isinstance(n, ARG_NODES) or label.startswith("_") or (isinstance(n, ast.keyword) and n.arg is None) \
                or (isinstance(n, ast.Dict) and None in n.keys):
            raise Refused(f"check {i}: arguments may be literals, module names and the repo's own classes, nothing "
                          f"that runs code first; not {ast.unparse(n)}")


def _parse_call(i, text):
    try:
        return ast.parse(text, mode="eval").body
    except SyntaxError as e:
        raise Refused(f"check {i}: call does not parse: {e}")


def _steps(i, label, steps) -> list:
    """steps: "X(...)" or ["X(...)", ".method(...)", ".prop", ...] -> parsed nodes; a step's object is "_"."""
    steps = [steps] if isinstance(steps, str) else steps
    if not (isinstance(steps, list) and steps and all(isinstance(x, str) for x in steps)):
        raise Refused(f"check {i}: {label} is a call string, or a list: a call, then '.method(...)' steps on its value")
    out = [_parse_call(i, steps[0])]
    if not isinstance(out[0], ast.Call):
        raise Refused(f"check {i}: {label} must start with a call")
    _check_args(i, out[0])
    for x in steps[1:]:
        m = _parse_call(i, "_" + x.strip() if x.strip().startswith(".") else x)
        ref = m.func if isinstance(m, ast.Call) else m  # .prop reads a property, .method(...) calls one
        if not (isinstance(ref, ast.Attribute) and isinstance(ref.value, ast.Name) and ref.value.id == "_"
                and not ref.attr.startswith("_")):
            raise Refused(f"check {i}: {label} step {x!r} must be .method(...) or .property")
        if isinstance(m, ast.Call):
            _check_args(i, m)
        out.append(m)
    return out


def params_of(node) -> list[str]:
    """The parameter names a check calls with: a def's own, a class's __init__ minus self, a dataclass's fields."""
    if isinstance(node, FN):
        a = node.args
        return [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    init = next((b for b in node.body if isinstance(b, FN) and b.name == "__init__"), None)
    if init is not None:
        return params_of(init)[1:]
    return [b.target.id for b in node.body if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name)]


def check_contracts(contracts) -> dict[str, dict]:
    """Plan-time shape check of the contracts the person will lock: -> {location: contract}."""
    if contracts is None:
        return {}
    if not isinstance(contracts, list):
        raise Refused("contracts must be a list")
    out = {}
    for i, c in enumerate(contracts):
        if not isinstance(c, dict) or set(c) - {"file", "name", "params", "checks", "kind"} or not {"file", "name", "params", "checks"} <= set(c) \
                or not isinstance(c["file"], str) or not isinstance(c["name"], str) or not c["name"].isidentifier() \
                or not isinstance(c["params"], list) or not all(isinstance(x, str) and x.isidentifier() for x in c["params"]) \
                or not isinstance(c["checks"], list) or c.get("kind", "def") not in ("def", "class"):
            raise Refused(f"contract {i}: needs file, name, params (a list of names), a checks list (empty = the spec "
                          "gives nothing checkable: the location becomes a hole) and optionally kind: def (default) or class, nothing else")
        c = {**c, "kind": c.get("kind", "def")}
        if c["checks"]:  # the same rules cl_submit applies, so a locked check can never be one that cannot run
            fake = ast.parse(f"class {c['name']}:\n    pass" if c["kind"] == "class" else f"def {c['name']}(): pass").body[0]
            try:
                check_checks(c["checks"], fake, own=None)
            except Refused as e:
                raise Refused(f"contract {i} ({c['file']}::{c['name']}): {e}")
        loc = holes.location_of(c["file"], c["name"])
        if loc in out:
            raise Refused(f"contract {i}: {loc} is named twice")
        out[loc] = c
    return out


def check_checks(checks, node, own=...) -> list[dict]:
    """own: the class's method names; None = not known yet (a plan-time contract), so steps are not checked against them."""
    name, cls = node.name, isinstance(node, ast.ClassDef)
    if own is ...:
        own = set(methods(node).values()) if cls else set()
    if not isinstance(checks, list) or not checks:
        raise Refused("checks must be a non-empty list of {call, expect} or {call, raises}: the intent to compare with")
    for i, c in enumerate(checks):
        if not isinstance(c, dict) or sum(k in c for k in ("expect", "raises", "contains")) != 1 \
                or set(c) - {"call", "expect", "raises", "contains", "given", "serve", "files"} or not isinstance(c.get("raises", ""), str) \
                or ("contains" in c and not (isinstance(c["contains"], list) and c["contains"] and all(isinstance(x, str) and x for x in c["contains"]))):
            raise Refused(f"check {i}: needs a call and exactly one of expect / raises / contains (a non-empty list of strings the "
                          "returned string must include), optionally given, serve and files, nothing else")
        files = c.get("files", {})
        if not isinstance(files, dict) or not all(isinstance(k, str) and isinstance(v, str) and k and not k.startswith("/")
                                                  and ".." not in k.split("/") for k, v in files.items()):
            raise Refused(f"check {i}: files is {{\"name.ext\": text}}, relative names only; the call then uses files[\"name.ext\"]")
        serve = c.get("serve", {})
        if not isinstance(serve, dict) or set(serve) - {"body", "status"} or not isinstance(serve.get("body", ""), str) \
                or not isinstance(serve.get("status", 200), int):
            raise Refused(f"check {i}: serve is {{body: text, status: int}}: what the stand-in server answers; the call then uses url")
        given = c.get("given", {})
        if not isinstance(given, dict) or not all(isinstance(k, str) and k.isidentifier() and not k.startswith("_")
                                                  and k != name and not (k == "url" and "serve" in c) and not (k == "files" and files) for k in given):
            raise Refused(f"check {i}: given maps plain names to how each is built")
        for k, v in given.items():
            _steps(i, f"given {k}", v)
        steps = _steps(i, "call", c.get("call"))
        f = steps[0].func
        direct = isinstance(f, ast.Name) and f.id == name
        via = cls and isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == name \
            and f.attr in own  # Cls.classmethod(...) / Cls.staticmethod(...)
        if not (direct or via) or (len(steps) > 1 and not cls):
            raise Refused(f"check {i}: call must start with {name}(...)" + (f" or {name}.method(...)" if cls else "")
                          + f" itself, so its value is what {name} returned" + ("" if cls else "; a list is for classes"))
        for m in steps[1:]:
            ref = m.func if isinstance(m, ast.Call) else m
            if own is not None and ref.attr not in own and not node.bases:  # inherited names resolve in the run
                raise Refused(f"check {i}: step .{ref.attr} is not a method of {name}")
    return checks


# ---- splice ---------------------------------------------------------------------------------------------------------

def splice(text: str, block: str, name: str) -> tuple[str, str | None]:
    """-> (new text, anchor: the top-level def the function follows). Replaces the last def named `name`. The
    block's import lines the file lacks go after the file's last top-level import (or at the top)."""
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    btree = ast.parse(block)
    def bound(n): return {(getattr(n, "module", None), a.name, a.asname) for a in n.names}  # what an import statement binds
    have = set().union(*[bound(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))])
    new = []
    for n in btree.body[:-1]:  # only the names the file lacks; "from x import a" is covered by "from x import a, b"
        n.names = [a for a in n.names if (getattr(n, "module", None), a.name, a.asname) not in have]
        if n.names:
            new.append(ast.unparse(n) + "\n"); have |= bound(n)
    node = btree.body[-1]
    block = "".join(block.splitlines(keepends=True)[min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1:])
    if new:
        imps = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        doc = tree.body[0].end_lineno if tree.body and isinstance(tree.body[0], ast.Expr) \
            and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str) else 0
        at = imps[-1].end_lineno if imps else doc
        lines[at:at] = new + ([] if imps or not lines[at:] else ["\n"])
        tree = ast.parse("".join(lines))
    tops = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    block = block.strip("\n") + "\n"
    same = [n for n in tops if n.name == name]
    if same:
        old = same[-1]
        start = min([old.lineno] + [d.lineno for d in old.decorator_list]) - 1
        before = [n for n in tops if (n.end_lineno or 0) <= start]
        return "".join(lines[:start] + [block] + lines[old.end_lineno:]), before[-1].name if before else None
    if tops:  # after the last def, so a trailing `if __name__ == "__main__":` still sees it
        at = tops[-1].end_lineno
        return "".join(lines[:at] + ["\n\n", block] + lines[at:]), tops[-1].name
    head = "".join(lines)
    return head + ("\n\n" if head.strip() else "") + block, None


def atomic_write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.closer-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        if p.exists():
            os.chmod(tmp, p.stat().st_mode & 0o7777)
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---- 2. run, 3. compare -------------------------------------------------------------------------------------------

SANDBOX = """(version 1)
(deny default)
(allow process-exec process-fork)
(allow file-read*)
(deny file-read* (subpath "{state}") (regex #"^/(private/)?tmp/claude-"))
(allow file-read* (subpath "{tmp}"))
(allow file-write* (subpath "{tmp}") (subpath "/dev"))
(deny file-write* (subpath "{repo}") (subpath "{state}"))
(allow sysctl-read mach-lookup ipc-posix-shm signal)
(allow network-bind network-inbound (local ip "localhost:*"))
(allow network-outbound (remote ip "localhost:*"))
"""

# The runner reports what happened; the judge compares. Nothing the agent wrote runs before the submitted def is
# entered: no setup, no decorators, def-line code is call-free, and the arguments are built by the runner from
# literals, module names and the repo's own classes. Once the def runs, anything it could forge it could return.
RUNNER = r'''
import ast, asyncio, contextlib, dataclasses, enum, importlib, importlib.abc, importlib.machinery, importlib.util, inspect, io, json, os, sys, threading, types
sys.path.insert(0, os.getcwd())
root = os.path.realpath(os.getcwd())
mod_name, path, start, end, name, steps = sys.argv[1], os.path.realpath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], json.loads(sys.argv[6])
own_methods, given, serve, real, files = set(json.loads(sys.argv[7])), json.loads(sys.argv[8]), json.loads(sys.argv[9]), sys.argv[10], json.loads(sys.argv[11])
class Spliced(importlib.abc.MetaPathFinder):  # the target module comes from the spliced file, the rest from the repo as it is
    def find_spec(self, fullname, target_path=None, target=None):
        if mod_name.startswith(fullname + ".") and not os.path.isdir(os.path.join(root, *fullname.split("."))):
            return importlib.machinery.ModuleSpec(fullname, None, is_package=True)  # a new file in a dir not yet on disk
        if fullname != mod_name: return None
        pkg = os.path.basename(path) == "__init__.py"
        # __file__ is the real path (so Path(__file__).with_name(...) finds the repo's files); the code itself is read from the splice
        return importlib.util.spec_from_file_location(fullname, real, loader=importlib.machinery.SourceFileLoader(fullname, path),
                                                      submodule_search_locations=[os.path.dirname(real)] if pkg else None)
sys.meta_path.insert(0, Spliced())
GENERATED = {"__init__", "__repr__", "__eq__", "__hash__", "__replace__", "__annotate__", "__annotate_func__",
             "__setattr__", "__delattr__", "__getstate__", "__setstate__", "__lt__", "__le__", "__gt__", "__ge__"}
SAFE = {t.__name__: t for t in (int, float, complex, str, bytes, bytearray, bool, list, tuple, dict, set, frozenset, range)}
ran = set()
class Refuse(Exception): pass
def out(**r):
    sys.setprofile(None)
    r["ran"] = sorted(ran)
    sys.__stdout__.write("CL_RESULT " + json.dumps(r) + "\n"); sys.__stdout__.flush(); os._exit(0)
def qual(t): return t.__qualname__ if t.__module__ == "builtins" else f"{t.__module__}.{t.__qualname__}"
def in_repo(m):
    f = os.path.realpath(getattr(m, "__file__", None) or "")
    return f == path or f.startswith(root + os.sep)
def own(cls):  # a class defined in the repo, not one that spawns processes or opens files
    return cls in SAFE.values() or in_repo(sys.modules.get(cls.__module__))
def repo_module(dotted):
    spec = importlib.util.find_spec(dotted)
    here = lambda f: f == path or os.path.realpath(f).startswith(root + os.sep)
    if spec and ((spec.origin and here(spec.origin)) or any(here(d) for d in spec.submodule_search_locations or [])):
        return importlib.import_module(dotted)  # a package dir with no __init__.py yet is still the repo's
env = {}  # the check's given objects
def val(n):
    if isinstance(n, ast.Constant): return n.value
    if isinstance(n, ast.UnaryOp): return -val(n.operand) if isinstance(n.op, ast.USub) else +val(n.operand)
    if isinstance(n, (ast.List, ast.Tuple, ast.Set)): return {ast.List: list, ast.Tuple: tuple, ast.Set: set}[type(n)](val(e) for e in n.elts)
    if isinstance(n, ast.Dict): return {val(k): val(v) for k, v in zip(n.keys, n.values)}
    if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "files":
        if isinstance(n.slice, ast.Constant) and n.slice.value in env.get("files", {}): return env["files"][n.slice.value]
        raise Refuse(f"{ast.unparse(n)}: this check's files has no such name")
    if isinstance(n, ast.Name):
        if n.id in env: return env[n.id]
        if n.id in vars(mod): return vars(mod)[n.id]
        if n.id in SAFE: return SAFE[n.id]
        m = repo_module(n.id)
        if m is None: raise Refuse(f"{n.id} is not a name in {mod_name}; name a repo class by its module path, e.g. pkg.models.Thing(...)")
        return m
    if isinstance(n, ast.Attribute):
        base = val(n.value)
        if isinstance(base, types.ModuleType) and not hasattr(base, n.attr):
            m = repo_module(f"{base.__name__}.{n.attr}")
            if m is not None: return m
        return getattr(base, n.attr)
    f = val(n.func)
    if isinstance(f, (types.MethodType, types.FunctionType)) and isinstance(n.func, ast.Attribute) and isinstance(val(n.func.value), type):
        f_ok = own(val(n.func.value))  # Cls.classmethod(...) / Cls.staticmethod(...) of a repo class
    else:
        f_ok = isinstance(f, type) and own(f)
    if not f_ok: raise Refuse(f"{ast.unparse(n.func)} is not one of the repo's own classes or their class methods")
    return f(*[val(a) for a in n.args], **{k.arg: val(k.value) for k in n.keywords})
def args_of(c):  # an error here is the check's, not the submission's: never a "raised"
    try:
        return [val(a) for a in c.args], {k.arg: val(k.value) for k in c.keywords}
    except Refuse as e:
        out(refuse=str(e))
    except BaseException as e:
        out(error=f"building the arguments for {ast.unparse(c)} raised {type(e).__name__}: {str(e)[:200]}")
def plain(v, depth=0):
    # the value as plain JSON: an object becomes {"__class__": its class name, its public attributes}
    if depth > 50: raise ValueError("nested too deep")
    if v is None or isinstance(v, (bool, int, float, str)): return v
    if isinstance(v, enum.Enum): return {"__class__": type(v).__name__, "name": v.name}
    if isinstance(v, (list, tuple)): return [plain(x, depth + 1) for x in v]
    if isinstance(v, (set, frozenset)): return sorted((plain(x, depth + 1) for x in v), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(v, dict): return {k if isinstance(k, str) else json.dumps(plain(k, depth + 1)): plain(x, depth + 1) for k, x in v.items()}
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        attrs = {f.name: getattr(v, f.name) for f in dataclasses.fields(v)}
    elif hasattr(v, "__dict__") and not isinstance(v, (type, types.ModuleType, types.FunctionType)):
        attrs = dict(vars(v))
    elif hasattr(type(v), "__slots__"):
        attrs = {k: getattr(v, k) for k in type(v).__slots__ if hasattr(v, k)}
    elif isinstance(v, (bytes, bytearray)):
        return {"__bytes__": bytes(v).decode("utf-8", "replace")}  # expect {"__bytes__": text}; contains reads the text
    else:
        raise ValueError(f"a {type(v).__name__} is not plain data")
    return {"__class__": type(v).__name__, **{k: plain(x, depth + 1) for k, x in attrs.items() if not k.startswith("_")}}
def settle(r): return asyncio.run(r) if inspect.iscoroutine(r) else r
def run_steps(nodes, first):
    # first(nodes[0]) -> the starting value; each later node is ._method(...) or ._prop on it. -> (object, last value)
    obj = result = settle(first(nodes[0]))
    for c in nodes[1:]:
        if isinstance(c, ast.Attribute):
            result = settle(getattr(obj, c.attr))
            continue
        a, k = args_of(c)
        result = settle(getattr(obj, c.func.attr)(*a, **k))
    return obj, result
def parse_steps(st):
    st = [st] if isinstance(st, str) else st
    return [ast.parse(st[0], mode="eval").body] + [ast.parse("_" + x.strip(), mode="eval").body for x in st[1:]]
def watch(frame, event, arg):
    if event == "call" and frame.f_code.co_filename == path and start <= frame.f_code.co_firstlineno <= end:
        ran.add(frame.f_code.co_firstlineno)
with contextlib.redirect_stdout(io.StringIO()):
    try:
        mod = importlib.import_module(mod_name)
    except BaseException as e:
        out(error=f"importing {mod_name} raised {type(e).__name__}: {str(e)[:200]}")
    def is_submitted():
        obj = getattr(mod, name, None)
        if isinstance(obj, type):
            def here(c): return os.path.realpath(c.co_filename) == path and start <= c.co_firstlineno <= end
            codes = {k: [f.__code__ for f in ((x.fget, x.fset, x.fdel) if isinstance(x, property) else (getattr(x, "__func__", x),))
                         if isinstance(f, types.FunctionType)] for k, x in vars(obj).items()}
            # each submitted method is the code at its own lines; any other method only one @dataclass generates
            return obj.__qualname__ == name and obj.__module__ == mod_name and all(
                codes.get(k) and all(map(here, codes[k])) for k in own_methods) and all(
                k in own_methods or all(map(here, cs)) or (dataclasses.is_dataclass(obj) and k in GENERATED)
                for k, cs in codes.items() if cs)
        code = getattr(obj, "__code__", None)
        return type(obj) is types.FunctionType and code.co_name == name and code.co_firstlineno == start \
            and os.path.realpath(code.co_filename) == path
    if not is_submitted():
        out(error=f"{mod_name}.{name} is not the submitted code: something in the module rebinds the name")
    if files:  # the check's fixture files, in the temp dir (the only writable place), reachable as files["name"]
        import tempfile
        fdir = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(sys.argv[0])))
        for k, v in files.items():
            fp = os.path.join(fdir, k); os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, "w", encoding="utf-8").write(v)
        env["files"] = {k: os.path.join(fdir, k) for k in files}
    if serve:  # a stand-in for whatever server the function talks to: every request gets this one answer
        import http.server
        class H(http.server.BaseHTTPRequestHandler):
            def _answer(self):
                body = serve.get("body", "").encode()
                self.send_response(serve.get("status", 200)); self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Type", "text/plain; charset=utf-8"); self.end_headers(); self.wfile.write(body)
            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _answer
            def log_message(self, *a): pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        env["url"] = f"http://127.0.0.1:{srv.server_address[1]}/"
    sys.setprofile(watch)
    for g, st in given.items():  # built from the repo's own classes; a failure here is the check's or the submission's
        try:
            env[g] = run_steps(parse_steps(st), val)[0]
        except BaseException as e:
            out(error=f"building given {g} raised {qual(type(e))}: {str(e)[:200]}")
    if not is_submitted():
        out(error=f"building the givens changed {mod_name}.{name}: it is no longer the submitted code")
    calls = parse_steps(steps)
    def first(c):
        a, k = args_of(c)
        return val(c.func)(*a, **k)
    try:
        result = run_steps(calls, first)[1]
    except BaseException as e:
        out(raised=[qual(t) for t in type(e).__mro__], msg=f"{qual(type(e))}: {str(e)[:200]}")
    sys.setprofile(None)
    try:
        s = json.dumps(plain(result))
    except BaseException as e:
        try: out(unserializable=f"{repr(result)[:150]} ({e})")
        except BaseException: out(unserializable=f"a {type(result).__name__}")
    out(returned=json.loads(s))
'''


def short(v) -> str:
    return repr(v)[:200]


def same(a, b) -> bool:
    """== on JSON values, except True is not 1. Numbers compare by value: a JavaScript client sends 1.0 as 1."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(map(same, a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


def interpreter(repo: Path) -> str:
    """The repo's own virtualenv Python, so the code sees its installed packages; else Closer's."""
    for d in (".venv", "venv", "env"):
        py = repo / d / "bin" / "python"
        if py.is_file() and os.access(py, os.X_OK):
            return str(py)
    return sys.executable


def run_checks(repo: Path, st: Path, rel: str, spliced: str, name: str, checks: list) -> str | None:
    """None if every check held, else the first failure. A class also needs every method run by some check."""
    node = [n for n in ast.parse(spliced).body if isinstance(n, FN + (ast.ClassDef,)) and n.name == name][-1]
    start = node.lineno if isinstance(node, FN) else min([node.lineno] + [d.lineno for d in node.decorator_list])
    want, ran = (methods(node) if isinstance(node, ast.ClassDef) else {}), set()
    tmp = Path(tempfile.mkdtemp(prefix="closer-run-")).resolve()
    try:
        target = tmp / rel  # only the spliced file; the rest of the repo is read in place (the sandbox forbids writing it)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(spliced, encoding="utf-8")
        (tmp / "run.py").write_text(RUNNER)
        (tmp / "p.sb").write_text(SANDBOX.format(tmp=tmp, repo=repo.resolve(), state=st.resolve()))
        mod = Path(rel).with_suffix("").as_posix().replace("/", ".").removesuffix(".__init__")  # a package is its own module
        py = interpreter(repo)
        for i, c in enumerate(checks):  # one interpreter per check, and it never sees the expected value
            steps = [c["call"]] if isinstance(c["call"], str) else c["call"]
            call = "".join(steps)
            try:
                r = subprocess.run(["sandbox-exec", "-f", str(tmp / "p.sb"), py, "-I", "-B",
                                    str(tmp / "run.py"), mod, str(target), str(start), str(node.end_lineno),
                                    name, json.dumps(steps), json.dumps(sorted(set(want.values()))),
                                    json.dumps(c.get("given", {})), json.dumps(c.get("serve", {})), str(repo / rel),
                                    json.dumps(c.get("files", {}))],
                                   stdin=subprocess.DEVNULL, cwd=repo, capture_output=True, text=True,
                                   timeout=CHECK_SECS,
                                   env={"PATH": os.environ.get("PATH", ""), "HOME": str(tmp), "TMPDIR": str(tmp)})
            except subprocess.TimeoutExpired:
                return f"could not run: {call} timed out after {CHECK_SECS}s"
            hit = [ln for ln in r.stdout.splitlines() if ln.startswith("CL_RESULT ")]
            if len(hit) != 1:
                return f"could not run: {call} died: {r.stderr.strip()[-300:] or 'no result'}"
            v = json.loads(hit[0].split(" ", 1)[1])
            ran.update(v.get("ran", []))
            if "refuse" in v:
                raise Refused(f"check {i}: {v['refuse']}")
            if "error" in v:
                return f"could not run: {v['error']}"
            if "raises" in c:
                # dotted, or the bare name of a module-level class; a class made inside the function is not an answer
                if any(q == c["raises"] or (q.rsplit(".", 1)[-1] == c["raises"] and "<locals>" not in q) for q in v.get("raised", [])):
                    continue
                got = f"raised {v['msg']}" if "raised" in v else f"returned {short(v.get('returned', v.get('unserializable')))}"
                return f"counterfeit: {call} {got}, intent expects it to raise {c['raises']}"
            if "raised" in v:
                net = {"urllib.error.URLError", "ConnectionError", "socket.gaierror", "TimeoutError"} & set(v["raised"])
                hint = ("" if "serve" in c or not net else
                        ". The sandbox has no network: check a function that talks to a server with serve {body, status} and call it with url")
                return f"could not run: {call} raised {v['msg']}{hint}"
            if "contains" in c:
                got = v.get("returned", v.get("unserializable"))
                if isinstance(got, dict) and set(got) == {"__bytes__"}:
                    got = got["__bytes__"]
                missing = [x for x in c["contains"] if not isinstance(got, str) or x not in got]
                if missing:
                    return f"counterfeit: {call} returned {short(got)}, intent expects a string containing {short(missing)}"
                continue
            if "unserializable" in v:
                return f"counterfeit: {call} returned {v['unserializable']}, not a plain value; intent expects {short(c['expect'])}"
            if not same(v["returned"], c["expect"]):
                return f"counterfeit: {call} returned {short(v['returned'])}, intent expects {short(c['expect'])}"
        if set(want) - ran:
            raise Refused(f"no check runs {', '.join(want[k] for k in sorted(set(want) - ran))} of {name}: every method "
                          "must run in some check")
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- submit -------------------------------------------------------------------------------------------------------

def hole_unchecked(repo, contracts: dict) -> list[str]:
    """Close every locked location whose contract has no checks: nothing can land there, CodeRadar gets it."""
    st = state_dir(Path(repo).resolve())
    out = []
    for loc, c in contracts.items():
        if not c["checks"] and not holes.is_hole(st, loc):
            holes.append_hole(st, {"location": loc, "file": c["file"], "function": c["name"], "kind": "unchecked",
                                   "reasons": ["the spec gives nothing checkable for it; the person locked it with no checks"]})
            out.append(loc)
    return out


def record_plan(repo, rec: dict) -> bool:
    """Every plan put to the person, approved or not, to plans.jsonl in the repo's state dir."""
    return holes.record_plan(state_dir(Path(repo).expanduser().resolve()), rec)


def submit(repo, file, source, checks, stance=None, plan=None, contracts=None, repair: bool = False) -> tuple[str, str]:
    """-> (verdict, message). verdict: PASS, FAIL, HOLE or REFUSED. repair: CodeRadar landing a fix on a holed location:
    the hole refusal is skipped, a FAIL never makes a second hole, a PASS appends a "repaired" record."""
    repo = Path(repo).expanduser().resolve()
    st = state_dir(repo)
    st.mkdir(parents=True, exist_ok=True)
    (st / "manifest.json").write_text(json.dumps({"repo": str(repo)}))  # closer_gate reads this to know the repo is gated
    with open(st / "lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if not plan:
                raise Refused("no approved plan this session: call cl_plan first and wait for the person to approve")
            stance = check_stance(stance)
            verdict, text = _submit(repo, st, file, source, checks, contracts or {}, plan, repair)
        except Refused as e:
            holes._append(st, "refused.jsonl", {"file": str(file)[:200], "reason": str(e)[:300],  # for closer_watch; not a try
                                                "locked": getattr(e, "locked", None), "plan": plan})
            return "REFUSED", f"REFUSED (not judged, no try used): {e}"
        name = re.search(r"^\s*(?:async\s+def|def|class)\s+(\w+)", source, re.M).group(1)
        loc = holes.location_of(file, name)
        line = (f"INTENT {'AGREES' if stance['agrees'] else 'DISAGREES'}: {loc}\n"
                f"  function: {stance['purpose']}\n  app:      {stance['intent']}")
        if not holes.record_agreement(st, loc, verdict=verdict, plan=plan, **stance):
            line += f"\n  (could NOT be logged to {holes.AGREE}, see {holes.ERRORS})"
        print(line, file=sys.stderr)
        return verdict, f"{line}\n{text}"


def check_stance(stance) -> dict:
    if not isinstance(stance, dict) or not isinstance(stance.get("agrees"), bool) \
            or not all(isinstance(stance.get(k), str) and stance[k].strip() for k in ("purpose", "intent")):
        raise Refused('stance must be {"purpose": what this function does, "intent": the part of the app\'s intent it '
                      'serves, "agrees": true/false}')
    return {k: stance[k].strip() if k != "agrees" else stance[k] for k in ("purpose", "intent", "agrees")}



def _submit(repo: Path, st: Path, rel: str, source, checks, contracts: dict, plan_sha=None, repair: bool = False) -> tuple[str, str]:
    target = safe_rel(repo, rel)
    if not shutil.which("sandbox-exec"):
        raise Refused("sandbox-exec not found: no sandbox, no run")
    if not isinstance(source, str):
        raise Refused("source must be a string")
    try:
        fn, why, m = parse_one(source), None, None
    except SyntaxError as e:
        m = re.search(r"^\s*(?:async\s+def|def|class)\s+(\w+)", source, re.M)
        if not m:
            raise Refused(f"no function or class in source: {e}")
        fn, why = None, f"could not run: does not parse: {e}"
    name = fn.name if fn else m.group(1)  # type: ignore[union-attr]
    loc = holes.location_of(rel, name)
    if not repair and holes.is_hole(st, loc):
        raise Refused(f"{loc} is a hole (two failed tries); it is logged for CodeRadar and takes no more submissions")
    current = target.read_text(encoding="utf-8") if target.is_file() else ""
    try:
        ast.parse(current)
    except SyntaxError as e:
        raise Refused(f"{rel} does not parse as it stands ({e}); Closer cannot splice into it")
    locked = contracts.get(loc)
    if fn is not None:
        if locked and (params_of(fn) != locked["params"] or isinstance(fn, ast.ClassDef) != (locked["kind"] == "class")):
            raise Refused(f"{loc} is locked by the approved plan as {locked['kind']} ({', '.join(locked['params'])}); "
                          f"this source is {'class' if isinstance(fn, ast.ClassDef) else 'def'} ({', '.join(params_of(fn))}). "
                          "A changed contract needs a revised plan: send cl_plan again and the person decides")
        check_checks(checks, fn)
        if locked:
            try:
                check_checks(locked["checks"], fn)
            except Refused as e:
                prior = [r for r in holes._lines(st / "refused.jsonl") if r.get("locked") == loc and r.get("plan") == plan_sha]
                if prior:
                    holes.append_hole(st, {"location": loc, "file": rel, "function": name, "kind": "unlandable",
                                           "reasons": [f"the plan's locked check cannot run: {e}"]})
                    raise Refused(f"{loc} is a hole now: its locked check cannot run ({e}) and the plan was not revised. "
                                  "It is logged for CodeRadar. Move on to the next function")
                err = Refused(f"{loc}: the plan's locked check cannot run ({e}). Send cl_plan again with that contract "
                              "fixed; the person decides. A second submit against this check makes the location a hole")
                err.locked = loc
                raise err
            checks = list(checks) + locked["checks"]  # the person's checks run alongside the agent's, every try
    spliced, anchor = splice(current, source, name) if why is None else ("", None)  # a source that does not parse cannot be spliced
    audit = {"source_sha256": hashlib.sha256(source.encode()).hexdigest(), "checks": checks}
    if why is None:
        why = run_checks(repo, st, rel, spliced, name, checks)
        if why is None:
            atomic_write(target, spliced)
            holes.record_clear(st, loc, **audit)
            if repair:
                holes.append_hole(st, {"location": loc, "file": rel, "function": name, "kind": "repaired", "by": "coderadar",
                                       "source_sha256": audit["source_sha256"]})
            return "PASS", f"PASS: {name} written to {rel} ({len(checks)} check(s) held" + (f", {len(locked['checks'])} locked by the plan)" if locked else ")")
    if not holes.record_strike(st, loc, reason=why, **audit):
        raise Refused(f"could not record the strike in {holes.strikes_path(st)} (see holes.errors); nothing written")
    if repair:
        return "FAIL", f"FAIL: {why}. Nothing written; CodeRadar may file again."
    prior = holes.open_strikes(st, loc)
    if len(prior) < TRIES:
        return "FAIL", f"FAIL try {len(prior)}/{TRIES}: {why}. Nothing written; resubmit {name}."
    logged = holes.append_hole(st, {"location": loc, "file": rel, "function": name, "anchor": anchor,
                                    "kind": "counterfeit" if why.startswith("counterfeit") else "did not run",
                                    "reasons": [s.get("reason") for s in prior[-TRIES:]]})
    where = "is logged for CodeRadar" if logged else f"could NOT be logged (see {st / holes.ERRORS})"
    return "HOLE", (f"HOLE: try {TRIES}/{TRIES} failed: {why}. Nothing written; {loc} {where} and "
                    "takes no more submissions. Move on to the next function.")
