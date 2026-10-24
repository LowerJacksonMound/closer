#!/usr/bin/env python3
"""Proposed for pack v32 (2026-10-19, T16 let through what the gate cannot judge: `cannot_judge` is no longer a `C1 fail:` line
and no longer exits 1; it is `C1 unjudged: <file>:<line> cannot_judge <qualname> (<reason>)` on stdout, filed in the evidence like
a fail, counted in the `coverage` and `reach` evidence as not judged, and C1 exits 0 when every other claim held; the reach rule
counts only judged claims; the pass line carries ", N not judged" when any claim was. v30 qualnames below 3.11: qualname_of;
v29 the repo's interpreter: REPO_PYTHON; v27 coverage and before-tree evidence; v25 T4/T5; v24 without the reach rule). Edit
only through a new pack version (K5).

C1: the ticket's claims hold. A claim is what the signer said the code must do (README, Claims): a dotted name,
an optional setup, a call, and one expect: {"result": literal} | {"raises": "Name"} | {"true": "expression"}.
Each claim runs in a fresh python (REPO_PYTHON, the manifest's `python`, when set; else this check's own) inside
the verify sandbox, with the patched tree importable (root and root/src), under a wall clock (C1_SECONDS per claim, default 60) and a line budget (C1_LINES, default 2,000,000). Out of time
or budget is `cannot_judge`; so is a claim that cannot be set up, imported or run. Since v32 (KERNEL.md T16) that is not a
verdict and not a strike: it is said, filed and counted, and the land proceeds if nothing else struck. Never silence.

Rules, named for the gap found, one `C1 fail: introduced <file>:<line> <rule> <qualname>` line each (a strike):
  pass_through  the result is the call's own argument, unchanged, where the claim expected something else
  fake_check    the claim expected an exception and nothing was raised
  answer_table  two or more claims on one name expect different results and the code returns the same one to all
  fake_effect   the claim's predicate is false after the call
  partial       any other mismatch: wrong result, wrong exception, or the required name is not there (a verdict: the
                name the signer required is missing, so this stays a strike under T16)
  unreached     an introduced function no claim reached
Not a verdict (v32, T16), one `C1 unjudged: <file>:<line> cannot_judge <qualname> (<reason>)` line on stdout each, no strike:
  cannot_judge  the claim could not be run to a verdict: the claim's module did not import (import_error), its setup
                raised (setup_error), its predicate raised, the runner gave no usable output (runner_error), out of
                time (the clock) or out of line budget. The line is in the row's `said` and gc records it in the row's
                `unjudged` list; the evidence entry is filed like a fail's, with rule cannot_judge. The exit code does not
                see it: C1 exits 0 when every judged claim held and nothing is unreached.

The reach rule (Phase 4, T5, no exemption): every function the ticket introduces (a def in a write_set file that is
new, or whose body changed, against BEFORE_ROOT) must be reached while some claim runs, setup included. One that no
claim reaches is `unreached`: a reject. Not subject: test functions (E1 runs them, S1 judges them), lambdas,
abstract and overload stubs (uncallable by design), .pyi. Reach counts judged claims only (v32): what an unjudged
claim traced before it stopped is not reach, so a function that only an unjudged claim would have reached is
`unreached`, a strike, unless another claim reached it. T16 widened nothing here: an unjudged claim leaves its
function exactly as unjudged as no claim at all.

Evidence (claim, input, expected, observed) is printed on `C1 evidence: <json>` lines, which gc files under
<state>/evidence/ and keeps out of the ledger row and out of the writer's sight (signer, 2026-10-15, decision 2).
Exit 0 every judged claim held and nothing unreached (unjudged claims do not change it, v32), 1 any failure, 75 only
for the host's fault. The pass line is `C1 pass: <held> claim(s) held on <n> function(s)`, with `, <u> not judged`
appended only when u > 0, so a land with nothing unjudged prints exactly what v30 printed.

Evidence only, never a verdict (v27, proposals/INGREDIENTS.md 2a and 3; only when BEFORE_ROOT is set, so a run
without it prints exactly what v25 printed). Neither changes an exit code or a `C1 fail:` line.
  coverage      one entry per introduced function: file, line, qualname; how many judged claims reached it, how many
                distinct inputs those claims had, whether one is negative (see `negative`), whether one is an
                observed-effect check (expect `true`), `thin`: reached by at most one claim, with at most one
                distinct input, and no negative; and `unjudged` (v32): how many unjudged claims named it (by its
                dotted name) or traced into it before stopping. The `reach` entry carries `unjudged`, the indices of
                the unjudged claims (v32; [] when none).
  before        every claim that held is run again, same runner, clock and line budget, on a before-tree: a temp
                copy of SCOPED_ROOT with BEFORE_ROOT laid over it and the write_set files new in the ticket
                deleted. One entry per claim: held after, held before (true, false, `absent` when the claim's
                module or function does not exist there, null when it did not hold after and was not rerun), and
                `holds_before` when it held on both trees. Then one `before_summary` entry with the counts. The
                copy is under the temp dir and removed before C1 exits (K2).

Names reached (v30): the runner records each call into the tree as (file, qualname), the qualname as co_qualname
spells it. Below Python 3.11 there is no co_qualname; qualname_of() then reads the file's own syntax tree (stdlib
ast, once per file) and finds the def by (name, first line), the first line as co_firstlineno gives it: the first
decorator's line when the def is decorated. Without it a method or nested function reached under a 3.8 REPO_PYTHON
was recorded by its bare name and struck `unreached`. U1's recorder uses the same two functions.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNER = r'''
import ast, importlib, inspect, json, os, sys, traceback
spec = json.loads(sys.stdin.read())
root = spec["root"]
sys.path.insert(0, root)
if os.path.isdir(os.path.join(root, "src")):
    sys.path.insert(1, os.path.join(root, "src"))
out = {"status": None, "result": None, "exc": None, "args": [], "file": None, "line": None, "reached": [],
       "pred": None, "lines": 0}

def norm(v, depth=0):
    if depth > 6:
        return repr(v)
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [norm(x, depth + 1) for x in v]
    if isinstance(v, (set, frozenset)):
        try:
            return sorted(norm(x, depth + 1) for x in v)
        except TypeError:
            return [norm(x, depth + 1) for x in v]
    if isinstance(v, dict):
        return {str(k): norm(x, depth + 1) for k, x in v.items()}
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return repr(v)

def finish():
    print(json.dumps(out, default=repr))
    sys.exit(0)

parts = spec["name"].split(".")
module = None
for k in range(len(parts) - 1, 0, -1):
    try:
        module = importlib.import_module(".".join(parts[:k])); rest = parts[k:]; break
    except ModuleNotFoundError as e:
        if e.name and ".".join(parts[:k]).startswith(e.name):
            continue
        out["status"], out["exc"] = "import_error", {"name": type(e).__name__, "msg": str(e)[:300]}; finish()
    except BaseException as e:
        out["status"], out["exc"] = "import_error", {"name": type(e).__name__, "msg": str(e)[:300]}; finish()
if module is None:
    out["status"], out["exc"] = "import_error", {"name": "ModuleNotFoundError", "msg": "no module for " + spec["name"]}; finish()
obj = module
for a in rest:
    try:
        obj = getattr(obj, a)
    except AttributeError:
        out["status"] = "missing_name"; out["file"] = os.path.relpath(getattr(module, "__file__", root), root); out["line"] = 1; finish()
target = obj.fget if isinstance(obj, property) else obj
try:
    target = inspect.unwrap(target)
    src = inspect.getsourcefile(target)
    out["file"] = os.path.relpath(src, root) if src else os.path.relpath(getattr(module, "__file__", root), root)
    out["line"] = inspect.getsourcelines(target)[1]
except Exception:
    out["file"] = os.path.relpath(getattr(module, "__file__", root), root); out["line"] = 1

ns = dict(vars(module)); ns["__name__"] = "__claim__"

try:
    tree = ast.parse(spec["call"], mode="eval")
    if isinstance(tree.body, ast.Call):
        for a in tree.body.args:
            try: out["args"].append(norm(eval(compile(ast.Expression(a), "<arg>", "eval"), ns)))
            except BaseException: out["args"].append("<unevaluated>")
        for kw in tree.body.keywords:
            try: out["args"].append(norm(eval(compile(ast.Expression(kw.value), "<arg>", "eval"), ns)))
            except BaseException: out["args"].append("<unevaluated>")
except SyntaxError as e:
    out["status"], out["exc"] = "setup_error", {"name": "SyntaxError", "msg": "call: " + str(e)[:200]}; finish()

budget = int(spec.get("lines") or 2000000)
rootp = os.path.realpath(root) + os.sep
def qualnames_in(path):
    """(name, first line) -> qualname for every def and class in the file at path, as co_qualname spells them; the
    first line as co_firstlineno gives it (the first decorator's line when decorated). Keys two qualnames share are
    left out. {} when the file cannot be read or parsed. Below 3.11 only, for qualname_of()."""
    import ast as _ast
    try:
        with open(path, "rb") as fh:
            tree = _ast.parse(fh.read())
    except Exception:
        return {}
    out, clash = {}, set()
    scopes = (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef, _ast.Lambda)
    def declared_global(body):
        names, todo = set(), list(body)
        while todo:
            x = todo.pop()
            if isinstance(x, _ast.Global):
                names.update(x.names)
            elif not isinstance(x, scopes):
                todo.extend(_ast.iter_child_nodes(x))
        return names
    def visit(n, prefix, glob=frozenset()):
        if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
            q = n.name if n.name in glob else prefix + n.name  # `global f` in the enclosing def or class
            k = (n.name, min([n.lineno] + [d.lineno for d in n.decorator_list]))
            if out.get(k, q) != q:
                clash.add(k)
            out[k] = q
            # decorators, bases, defaults and annotations run in the enclosing scope; the body in its own
            for x in n.decorator_list:
                visit(x, prefix, glob)
            if isinstance(n, _ast.ClassDef):
                for x in n.bases + n.keywords:
                    visit(x, prefix, glob)
                inner = q + "."
            else:
                visit(n.args, prefix, glob)
                if n.returns is not None:
                    visit(n.returns, prefix, glob)
                inner = q + ".<locals>."
            g = declared_global(n.body)
            for x in n.body:
                visit(x, inner, g)
        else:
            for x in _ast.iter_child_nodes(n):
                visit(x, prefix, glob)
    visit(tree, "")
    for k in clash:
        del out[k]
    return out

def qualname_of(code, path=None, _files={}):
    """code.co_qualname; below 3.11, the file's own syntax tree's qualname for (co_name, co_firstlineno), parsed
    once per file; co_name when the file does not name it (a lambda, a comprehension, code from exec)."""
    q = getattr(code, "co_qualname", None)
    if q is not None:
        return q
    path = path or code.co_filename
    names = _files.get(path)
    if names is None:
        names = _files[path] = qualnames_in(path)
    return names.get((code.co_name, code.co_firstlineno), code.co_name)

reached = set()
class Budget(BaseException): pass
def tracer(frame, event, arg):
    if event == "call":
        f = frame.f_code.co_filename
        if f.startswith(rootp) and "site-packages" not in f:
            q = qualname_of(frame.f_code)
            reached.add((os.path.relpath(f, root), q))
        return tracer
    if event == "line":
        out["lines"] += 1
        if out["lines"] > budget:
            raise Budget()
    return tracer

sys.settrace(tracer)
try:
    for stmt in spec.get("setup") or []:
        exec(compile(stmt, "<setup>", "exec"), ns)
except Budget:
    sys.settrace(None); out["status"] = "budget"; out["reached"] = sorted(reached); finish()
except BaseException as e:
    sys.settrace(None)
    out["status"], out["exc"] = "setup_error", {"name": type(e).__name__, "msg": str(e)[:300]}
    out["reached"] = sorted(reached); finish()
try:
    result = eval(compile(spec["call"], "<call>", "eval"), ns)
    sys.settrace(None)
    out["status"], out["result"] = "ok", norm(result); ns["result"] = result
except Budget:
    sys.settrace(None); out["status"] = "budget"
except BaseException as e:
    sys.settrace(None)
    out["status"] = "raised"
    out["exc"] = {"name": type(e).__name__, "bases": [c.__name__ for c in type(e).__mro__[1:]], "msg": str(e)[:300]}
out["reached"] = sorted(reached)
exp = spec["expect"]
if out["status"] == "ok" and "true" in exp:
    try:
        out["pred"] = bool(eval(compile(exp["true"], "<predicate>", "eval"), ns))
    except BaseException as e:
        out["pred"] = None; out["exc"] = {"name": type(e).__name__, "msg": "predicate: " + str(e)[:300]}
finish()
'''


_ABSTRACT = {"abstractmethod", "abstractproperty", "abstractclassmethod", "abstractstaticmethod", "overload"}


def _is_test_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    name = parts[-1]
    return any(d in ("test", "tests", "testing") for d in parts[:-1]) or name.startswith("test_") \
        or name.endswith("_test.py") or name in ("conftest.py", "tests.py", "test.py")


def _defs(path: Path) -> dict[str, tuple[str, int]]:
    """qualname -> (body fingerprint, line) for every def in the file, qualnames as co_qualname spells them."""
    import ast
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, ValueError):
        return {}
    out: dict[str, tuple[str, int]] = {}

    def walk(nodes, prefix: str) -> None:
        for n in nodes:
            if isinstance(n, ast.ClassDef):
                walk(n.body, f"{prefix}{n.name}.")
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = f"{prefix}{n.name}"
                decos = {(d.func.attr if isinstance(d.func, ast.Attribute) else getattr(d.func, "id", "")) if isinstance(d, ast.Call)
                         else (d.attr if isinstance(d, ast.Attribute) else getattr(d, "id", "")) for d in n.decorator_list}
                if not (decos & _ABSTRACT) and not n.name.startswith("test"):
                    out[q] = (ast.dump(n), n.lineno)
                walk(n.body, f"{q}.<locals>.")
            elif hasattr(n, "body") and isinstance(getattr(n, "body"), list) and not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(n.body, prefix)  # if / try / with at module or class level
                for attr in ("orelse", "finalbody", "handlers"):
                    extra = getattr(n, attr, None)
                    if isinstance(extra, list):
                        walk([h for h in extra if not isinstance(h, ast.ExceptHandler)] +
                             [b for h in extra if isinstance(h, ast.ExceptHandler) for b in h.body], prefix)
    walk(tree.body, "")
    return out


def dotted(rel: str, qualname: str) -> str:
    """The module path a claim would use for a def in rel: src/pkg/mod.py + Class.m -> pkg.mod.Class.m."""
    parts = rel[:-3].replace("\\", "/").split("/")
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts + [qualname])


def introduced_functions(root: str, before_root: str | None, write_set: list[str]) -> list[tuple[str, str, int]]:
    """(file, qualname, line) for every def the ticket introduces: new, or body changed, against BEFORE_ROOT."""
    out: list[tuple[str, str, int]] = []
    for rel in write_set:
        if not rel.endswith(".py") or rel.endswith(".pyi") or _is_test_path(rel):
            continue
        after = _defs(Path(root) / rel)
        before = _defs(Path(before_root) / rel) if before_root and (Path(before_root) / rel).is_file() else {}
        for q, (fp, line) in sorted(after.items(), key=lambda kv: kv[1][1]):
            if before.get(q, (None, 0))[0] != fp:
                out.append((rel, q, line))
    return out


def run_claim(root: str, c: dict, lines: int, secs: float) -> dict:
    """One claim in a fresh python (REPO_PYTHON or this one) with the tree at root importable; the runner's JSON, or a status for judge()."""
    spec = {"root": root, "name": c["name"], "setup": c.get("setup") or [], "call": c["call"],
            "expect": c["expect"], "lines": lines}
    try:
        p = subprocess.run([os.environ.get("REPO_PYTHON") or sys.executable, "-I", "-c", RUNNER], input=json.dumps(spec), capture_output=True,
                           text=True, timeout=secs, cwd=root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        r = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else \
            {"status": "runner_error", "exc": {"name": "NoOutput", "msg": p.stderr[-300:]}}
    except subprocess.TimeoutExpired:
        r = {"status": "timeout"}
    except (json.JSONDecodeError, IndexError):
        r = {"status": "runner_error", "exc": {"name": "BadOutput", "msg": (p.stderr or p.stdout)[-300:]}}
    return r


def expected_of(c):
    e = c["expect"]
    return next(iter(e.items()))


def judge(c: dict, r: dict) -> tuple[str | None, str]:
    """(rule, observed) for one claim's run; rule None means the claim held."""
    kind, want = expected_of(c)
    st = r.get("status")
    rule, observed = None, ""
    if st in ("import_error", "setup_error", "runner_error"):
        rule, observed = "cannot_judge", f"{st}: {(r.get('exc') or {}).get('name')}: {(r.get('exc') or {}).get('msg')}"
    elif st in ("timeout", "budget"):
        rule, observed = "cannot_judge", "out of time" if st == "timeout" else "out of line budget"
    elif st == "missing_name":
        rule, observed = "partial", "the required name is not implemented"
    elif kind == "result":
        if st == "ok":
            got = r.get("result")
            if got == want:
                observed = "held"
            elif any(got == a for a in r.get("args", [])) and want not in r.get("args", []):
                rule, observed = "pass_through", f"returned its argument unchanged: {json.dumps(got)[:200]}"
            else:
                rule, observed = "partial", f"result {json.dumps(got)[:200]}"
        else:
            rule, observed = "partial", f"raised {r['exc']['name']}: {r['exc'].get('msg', '')}"
    elif kind == "raises":
        if st == "raised":
            names = [r["exc"]["name"]] + list(r["exc"].get("bases") or [])
            if want in names:
                observed = "held"
            else:
                rule, observed = "partial", f"raised {r['exc']['name']} instead of {want}"
        else:
            rule, observed = "fake_check", f"nothing raised; returned {json.dumps(r.get('result'))[:200]}"
    elif kind == "true":
        if st == "ok":
            if r.get("pred") is True:
                observed = "held"
            elif r.get("pred") is False:
                rule, observed = "fake_effect", f"predicate false after the call; result {json.dumps(r.get('result'))[:200]}"
            else:
                rule, observed = "fake_effect", f"predicate raised: {(r.get('exc') or {}).get('msg')}"  # a verdict: the code ran, the effect is not there (signer 2026-10-19)
        else:
            rule, observed = "partial", f"raised {r['exc']['name']}: {r['exc'].get('msg', '')}"
    return rule, observed


def negative(c: dict) -> bool:
    """A negative claim, for coverage only. Exactly two things count: expect `raises`; or expect `true` whose
    predicate, stripped of surrounding space, starts with `not ` or ends with ` is False`. Nothing else is read
    (no `==` against empty or zero literals, no `!=`, no `is None`)."""
    kind, want = expected_of(c)
    if kind == "raises":
        return True
    if kind == "true" and isinstance(want, str):
        w = want.strip()
        return w.startswith("not ") or w.endswith(" is False")
    return False


def coverage(introduced: list[tuple[str, str, int]], runs: list[tuple[int, dict, dict]]) -> list[dict]:
    """2a: per introduced function, the claims whose run reached it (setup or call), their distinct inputs (the
    runner's normalised args, compared as sorted JSON), negative, effect (expect `true`) and `thin`."""
    out = []
    for f, q, ln in introduced:
        hits = [(c, r) for _, c, r in runs if any(tuple(x) == (f, q) for x in (r.get("reached") or []))]
        inputs = {json.dumps(r.get("args", []), sort_keys=True) for _, r in hits}
        neg = any(negative(c) for c, _ in hits)
        out.append({"file": f, "line": ln, "qualname": q, "claims": len(hits), "inputs": len(inputs),
                    "negative": neg, "effect": any(expected_of(c)[0] == "true" for c, _ in hits),
                    "thin": len(hits) <= 1 and len(inputs) <= 1 and not neg})
    return out


def _name_absent(r: dict) -> bool:
    """The claim's module or function does not exist on the tree it ran on (the runner's own two statuses)."""
    return r.get("status") == "missing_name" or (
        r.get("status") == "import_error" and str((r.get("exc") or {}).get("msg", "")).startswith("no module for "))


def _rm_tree(path: str) -> None:
    for d, dirs, files in os.walk(path):
        for n in dirs + files:
            try:
                os.chmod(os.path.join(d, n), 0o700, follow_symlinks=False)
            except (OSError, NotImplementedError):
                pass
    shutil.rmtree(path, ignore_errors=True)


BEFORE_SKIP = (".git", "__pycache__", "node_modules", "site-packages", ".tox", ".mypy_cache", ".pytest_cache")


def before_tree(root: str, before_root: str, write_set: list[str]) -> tuple[str, str]:
    """(temp dir, tree): SCOPED_ROOT copied under the temp dir (BEFORE_SKIP dirs left out: the runner never
    traces them; links kept as links), BEFORE_ROOT's files laid over it, and every write_set file absent from
    BEFORE_ROOT deleted (new in the ticket). No write or delete goes through a link out of the copy (K2). The
    caller removes the temp dir."""
    tmp = tempfile.mkdtemp(prefix="c1-before-")
    tree = os.path.join(tmp, os.path.basename(os.path.normpath(root)) or "tree")
    shutil.copytree(root, tree, symlinks=True, ignore=shutil.ignore_patterns(*BEFORE_SKIP))
    top = os.path.realpath(tree)

    def inside(dst: Path) -> bool:
        parent = os.path.realpath(dst.parent)
        return parent == top or parent.startswith(top + os.sep)

    b = Path(before_root)
    for src in b.rglob("*"):
        if src.is_file() and not src.is_symlink():
            dst = Path(tree) / src.relative_to(b)
            if not inside(dst):  # realpath resolves the existing prefix, so this holds before mkdir too
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.is_symlink():
                dst.unlink()
            shutil.copyfile(src, dst)
    for rel in write_set:
        if not (b / rel).is_file():
            dst = Path(tree) / rel
            if inside(dst) and (dst.is_symlink() or dst.is_file()):
                dst.unlink()
    return tmp, tree


def before_findings(root: str, before_root: str, write_set: list[str], verdicts: list, lines: int,
                    secs: float) -> list[dict]:
    """3: each claim that held after, run again on the before-tree. Evidence entries, then the summary."""
    out: list[dict] = []
    counts = {"claims": len(verdicts), "discriminating": 0, "holds_before": 0, "absent": 0, "not_run": 0}
    tmp = None
    try:
        tmp, tree = before_tree(root, before_root, write_set)
        for i, c, r, rule, _ in verdicts:
            held_after = rule is None
            if not held_after:
                held_before, key = None, "not_run"
            else:
                rb = run_claim(tree, c, lines, secs)
                if _name_absent(rb):
                    held_before, key = "absent", "absent"
                else:
                    held_before = judge(c, rb)[0] is None
                    key = "holds_before" if held_before else "discriminating"
            counts[key] += 1
            out.append({"before": {"claim": i, "name": c["name"], "file": r.get("file"), "line": r.get("line"),
                                   "held_after": held_after, "held_before": held_before,
                                   "holds_before": held_before is True}})
    except OSError as e:
        counts["error"] = f"before-tree not built: {type(e).__name__}: {str(e)[:200]}"
    finally:
        if tmp:
            _rm_tree(tmp)
    out.append({"before_summary": counts})
    return out


def main() -> int:
    root = os.environ.get("SCOPED_ROOT")
    tf = os.environ.get("TICKET_FILE")
    tid = os.environ.get("TICKET_ID", "ticket")
    if not root or not os.path.isdir(root):
        print("C1 not run: SCOPED_ROOT is not a directory", file=sys.stderr); return 75
    if not tf or not os.path.isfile(tf):
        print("C1 not run: no TICKET_FILE", file=sys.stderr); return 75
    ticket = json.loads(Path(tf).read_text(encoding="utf-8"))
    cf = Path(tf).resolve().parent.parent / "claims" / f"{ticket.get('ticket_id', tid)}.json"
    if not cf.is_file():
        print(f"C1 fail: the ticket has no claims file ({cf}); a ticket is minted with claims (T5)", file=sys.stderr); return 1
    if hashlib.sha256(cf.read_bytes()).hexdigest() != ticket.get("claims_sha256"):
        print("C1 fail: the claims file does not match the ticket's claims_sha256", file=sys.stderr); return 1
    claims = json.loads(cf.read_text(encoding="utf-8"))
    secs = float(os.environ.get("C1_SECONDS", "60"))
    lines = int(os.environ.get("C1_LINES", "2000000"))

    runs = [(i, c, run_claim(root, c, lines, secs)) for i, c in enumerate(claims, 1)]

    verdicts: list[tuple[int, dict, dict, str | None, str]] = []  # (i, claim, run, rule, observed)
    for i, c, r in runs:
        rule, observed = judge(c, r)
        verdicts.append((i, c, r, rule, observed))

    # answer_table: on one name, claims expecting different results all got the same result.
    by_name: dict[str, list[int]] = {}
    for idx, (i, c, r, rule, obs) in enumerate(verdicts):
        if expected_of(c)[0] == "result" and r.get("status") == "ok":
            by_name.setdefault(c["name"], []).append(idx)
    for name, idxs in by_name.items():
        if len(idxs) < 2:
            continue
        wants = [json.dumps(verdicts[j][1]["expect"]["result"], sort_keys=True) for j in idxs]
        gots = {json.dumps(verdicts[j][2].get("result"), sort_keys=True) for j in idxs}
        if len(set(wants)) > 1 and len(gots) == 1:
            for j in idxs:
                i, c, r, rule, obs = verdicts[j]
                if rule in ("partial", "pass_through"):
                    verdicts[j] = (i, c, r, "answer_table", f"the same result for every input: {obs}")

    # Reach: introduced functions no judged claim reached (v32: an unjudged claim's trace is not reach).
    unjudged_idx = {i for i, c, r, rule, obs in verdicts if rule == "cannot_judge"}
    judged_runs = [(i, c, r) for i, c, r in runs if i not in unjudged_idx]
    reached = {tuple(x) for _, _, r in judged_runs for x in (r.get("reached") or [])}
    before_root = os.environ.get("BEFORE_ROOT")
    write_set = json.loads(os.environ.get("WRITE_SET") or "[]")
    introduced = introduced_functions(root, before_root, write_set)
    unreached = [(f, q, ln) for (f, q, ln) in introduced if (f, q) not in reached]

    fails, unjudged, seen = [], [], set()
    for i, c, r, rule, obs in verdicts:
        print("C1 evidence: " + json.dumps({"claim": i, "name": c["name"], "setup": c.get("setup") or [],
                                            "call": c["call"], "input": r.get("args", []), "expected": c["expect"],
                                            "observed": obs, "rule": rule, "file": r.get("file"), "line": r.get("line"),
                                            "reached": r.get("reached", [])}, sort_keys=True))
        if rule:
            key = (r.get("file"), rule, c["name"])
            if key not in seen:
                seen.add(key)
                where = f"{r.get('file') or '?'}:{r.get('line') or 0}"
                if rule == "cannot_judge":  # v32, T16: said and filed, not a verdict
                    unjudged.append(f"C1 unjudged: {where} cannot_judge {c['name']} ({obs})")
                else:
                    fails.append(f"C1 fail: introduced {where} {rule} {c['name']}")
    print("C1 evidence: " + json.dumps({"reach": {"introduced": [[f, q] for f, q, _ in introduced],
                                                   "reached": sorted(reached), "unreached": [[f, q] for f, q, _ in unreached],
                                                   "unjudged": sorted(unjudged_idx)}},
                                        sort_keys=True))
    if before_root:  # v27 evidence (2a coverage, 3 before-tree); no strike, no fail line, no exit change
        for entry in coverage(introduced, judged_runs):
            f, q = entry["file"], entry["qualname"]
            entry["unjudged"] = sum(1 for i, c, r in runs if i in unjudged_idx and (
                c["name"] == dotted(f, q) or any(tuple(x) == (f, q) for x in (r.get("reached") or []))))
            print("C1 evidence: " + json.dumps({"coverage": entry}, sort_keys=True))
        for entry in before_findings(root, before_root, write_set, verdicts, lines, secs):
            print("C1 evidence: " + json.dumps(entry, sort_keys=True))
    for f, q, ln in unreached:
        fails.append(f"C1 fail: introduced {f}:{ln} unreached {dotted(f, q)}")
    for u in unjudged:
        print(u)
    if fails:
        for f in fails:
            print(f, file=sys.stderr)
        return 1
    names = {c["name"] for _, c, _ in judged_runs}
    tail = f", {len(unjudged_idx)} not judged" if unjudged_idx else ""
    print(f"C1 pass: {len(judged_runs)} claim(s) held on {len(names)} function(s){tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
