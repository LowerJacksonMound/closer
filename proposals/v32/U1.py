#!/usr/bin/env python3
"""Proposed for pack v32 (2026-10-19: each driver's spec goes in a file under U1's temp dir and the environment carries only its path, U1_SPEC_FILE; a large `want` list in U1_SPEC overflowed ARG_MAX, Errno 7, and struck an honest ticket; U1's own uncaught error is `U1 not run: ...`, exit 75, never 1; v30 qualnames below 3.11 by C1's qualname_of, REPO_PYTEST_ARGS; v29 the repo's interpreter: REPO_PYTHON; v28 INGREDIENTS 2b, evidence only, no strike). Edit only through a new pack version (K5).

U1: pre-existing functions whose body the ticket changed keep their recorded outcomes, or the change is declared
(KERNEL T4, detect, run, compare). Detect: the functions in the write_set that exist in BEFORE_ROOT and whose body
changed (C1's AST split, new functions left out). Run: on the before-tree (C1's before_tree(): SCOPED_ROOT copied
to temp, BEFORE_ROOT laid over it, new files removed) the repo's test suite (pytest as E1 runs it) and every
claim's setup and call (C1's RUNNER and line budget) run under a recording tracer: for every call into a changed
function, the normalised arguments (C1's norm; a plain object as its class and attribute state) and the outcome
(the normalised return value, or the exception's name), the first U1_INPUTS distinct inputs per function.
Compare: the same drivers (the test files that recorded an input, every claim) run again on the patched tree under
the same tracer; an input recorded on both trees whose outcome differs is a difference. An input whose outcome
varied within the before run is unstable and not compared; one the patched run never reproduced is unmatched.

A difference on a function some claim names (the claim's name is the function's dotted path, or the RUNNER
resolved it to that file and name) is declared: the signer stated that this function changes. One no claim names
is `undeclared_change`.

v28 is evidence only. Prints `U1 evidence:` lines (one per difference: file, line, qualname, declared, input,
before, after, driver; then a summary) and `U1 pass: ...` with the counts, exit 0 with or without differences.
Exit 75 (not run) only for the host: no SCOPED_ROOT, no BEFORE_ROOT, no pytest. One clock, U1_SECONDS (default
600, E1's), over both pytest runs and both claim passes; out of time prints what was gathered with `partial`.
Every driver (pytest and the claims) is its own process, under REPO_PYTHON (the manifest's `python`) when set, else
this check's own python; the pytest probe uses the same one. The pytest driver adds REPO_PYTEST_ARGS (the
manifest's `pytest_args`, shell words) before its test paths, as E1 does (v30). A call is named (file, qualname) by
C1's RUNNER qualname_of(): co_qualname, or below 3.11 the file's own syntax tree by (name, first line) (v30; v29 took
a short name only when it was unique among the watched functions). Each driver reads its spec (root, watch, want, cap,
deadline, out, pytest_args) from a JSON file under U1's temp dir named by U1_SPEC_FILE; the environment carries only the
path (v32: on a large module the "after" drive's `want` list, every input recorded on the before-tree, exceeded the
OS argv+environment limit as U1_SPEC and Popen raised Errno 7). U1 is evidence only, so its own failure is never a
strike: an exception main() does not handle prints one line `U1 not run: <type>: <message>` to stderr and exits 75
(KERNEL exit-code row 75, the check's own error; v32, signer's ruling 2026-10-19), not 1. Writes only under its own temp
dir (K2). Stdlib only (K6). Names file, line, qualname; never a species (K8).
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True  # the live dir is read-only to a verify (K2)
_spec = importlib.util.spec_from_file_location("C1", Path(__file__).resolve().parent / "C1.py")
C1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C1)


def _runner_source(*names: str) -> str:
    """C1's RUNNER functions by name (norm, qualnames_in, qualname_of), as the RUNNER defines them, for the recorder."""
    found = {n.name: ast.get_source_segment(C1.RUNNER, n) for n in ast.parse(C1.RUNNER).body
             if isinstance(n, ast.FunctionDef) and n.name in names}
    missing = [x for x in names if x not in found]
    if missing:
        raise RuntimeError("C1.RUNNER has no " + ", ".join(missing))
    return "\n".join(found[x] for x in names) + "\n"


# The recorder, shared by the pytest driver and the claim driver. U1_SPEC_FILE (env): the path of a JSON file under
# U1's temp dir with root, watch [[file, qualname]], want (null: record the first `cap` distinct inputs per function;
# a list of [file, qualname, input]: record only those), cap, out (a file under U1's temp dir), deadline (epoch
# seconds). Writes its records to `out` on exit.
RECORDER = _runner_source("norm", "qualnames_in", "qualname_of") + r'''

import atexit as _u1_atexit, dis as _u1_dis, json as _u1_json, os as _u1_os, signal as _u1_signal, sys as _u1_sys
import threading as _u1_threading
with open(_u1_os.environ["U1_SPEC_FILE"], encoding="utf-8") as _u1_fh:
    _U1 = _u1_json.load(_u1_fh)
_u1_rootp = _u1_os.path.realpath(_U1["root"]) + _u1_os.sep
_u1_watch = {tuple(x) for x in _U1["watch"]}
_u1_want = None if _U1.get("want") is None else {tuple(x) for x in _U1["want"]}
_u1_cap = int(_U1.get("cap") or 50)
_u1_rec = {}      # (file, qualname) -> {input: [outcome, driver, unstable]} (before) or {input: {driver: outcome}} (after)
_u1_codes = {}    # code object -> (file, qualname) or None
_u1_ops = {}      # code object -> {offset: opname}
_u1_driver = [_U1.get("driver") or ""]
_u1_skipped = set()
_U1_GEN = 0x20 | 0x80 | 0x200  # generator, coroutine, async generator: no single outcome per call

def _u1_argnorm(v):
    if type(v).__repr__ is object.__repr__ and hasattr(v, "__dict__"):
        try:
            return {"<object>": type(v).__qualname__, "state": norm(dict(vars(v)))}
        except BaseException:
            pass
    return norm(v)

def _u1_where(code):
    w = _u1_codes.get(code, 0)
    if w != 0:
        return w
    w = None
    f = code.co_filename
    if not _u1_os.path.isabs(f):
        f = _u1_os.path.join(_u1_os.getcwd(), f)
    f = _u1_os.path.realpath(f)
    if f.startswith(_u1_rootp):
        rel = _u1_os.path.relpath(f, _u1_rootp)
        q = qualname_of(code, f)  # C1's: co_qualname, or below 3.11 the file's syntax tree
        if (rel, q) in _u1_watch:
            if code.co_flags & _U1_GEN:
                _u1_skipped.add((rel, q))
            else:
                w = (rel, q)
    _u1_codes[code] = w
    return w

def _u1_input(frame):
    c = frame.f_code
    n = c.co_argcount + c.co_kwonlyargcount
    names = list(c.co_varnames[:n])
    if c.co_flags & 0x04:
        names.append(c.co_varnames[n]); n += 1
    if c.co_flags & 0x08:
        names.append(c.co_varnames[n])
    loc = frame.f_locals
    try:
        return _u1_json.dumps([[a, _u1_argnorm(loc.get(a))] for a in names], default=repr)
    except BaseException:
        return None

def _u1_call(frame):
    """A local recorder for this frame, or None when the frame is not a watched call worth recording."""
    w = _u1_where(frame.f_code)
    if w is None:
        return None
    inp = _u1_input(frame)
    if inp is None:
        return None
    seen = _u1_rec.setdefault(w, {})
    if _u1_want is not None:
        if (w[0], w[1], inp) not in _u1_want:
            return None
    elif inp not in seen and len(seen) >= _u1_cap:
        return None
    exc = [None]
    driver = _u1_driver[0]

    def local(frame, event, arg):
        if event == "exception":
            exc[0] = arg[0].__name__
        elif event == "return":
            code = frame.f_code
            ops = _u1_ops.get(code)
            if ops is None:
                ops = _u1_ops[code] = {i.offset: i.opname for i in _u1_dis.get_instructions(code)}
            if arg is None and exc[0] and not ops.get(frame.f_lasti, "").startswith("RETURN"):
                out = {"raised": exc[0]}
            else:
                try:
                    out = {"returned": _u1_argnorm(arg)}
                except BaseException:
                    out = {"returned": "<unnormalisable>"}
            if _u1_want is None:
                cur = seen.get(inp)
                if cur is None:
                    seen[inp] = [out, driver, False]
                elif cur[0] != out:
                    cur[2] = True
            else:
                seen.setdefault(inp, {}).setdefault(driver, out)
        return local
    return local

def _u1_dump(*_):
    try:
        rows = []
        for (f, q), d in _u1_rec.items():
            for inp, v in d.items():
                rows.append([f, q, inp, v])
        with open(_U1["out"], "w", encoding="utf-8") as fh:
            _u1_json.dump({"records": rows, "skipped": sorted(_u1_skipped)}, fh, default=repr)
    except BaseException:
        pass

def _u1_term(*_):
    _u1_sys.settrace(None); _u1_dump(); _u1_os._exit(0)

_u1_atexit.register(_u1_dump)
_u1_signal.signal(_u1_signal.SIGTERM, _u1_term)
'''

# Claim driver: the recorder, then C1's RUNNER unchanged. The RUNNER's own sys.settrace(tracer) (line budget) is
# composed with the recorder, so a claim runs with the same budget and the same resolution as in C1.
CLAIM_DRIVER = RECORDER + r'''
_u1_real_settrace = _u1_sys.settrace
def _u1_settrace(fn):
    if fn is None:
        _u1_real_settrace(None); return
    def glob(frame, event, arg):
        rec = _u1_call(frame) if event == "call" else None
        a = fn(frame, event, arg)
        if rec is None:
            return a
        def both(frame, event, arg):
            nonlocal a
            rec(frame, event, arg)
            if a is not None:
                a = a(frame, event, arg)
            return both
        return both
    _u1_real_settrace(glob)
_u1_sys.settrace = _u1_settrace
''' + C1.RUNNER

# Pytest driver: the recorder around pytest.main with E1's options; the driver is the running test's nodeid.
PYTEST_DRIVER = RECORDER + r'''
import time as _u1_time
import pytest as _u1_pytest

def _u1_glob(frame, event, arg):
    return _u1_call(frame) if event == "call" else None

class _U1Plugin:
    partial = False
    def pytest_sessionstart(self, session):
        self.session = session
    def pytest_runtest_logstart(self, nodeid, location):
        _u1_driver[0] = nodeid
        if _u1_time.time() > float(_U1["deadline"]):
            self.session.shouldstop = "U1 out of time"; _U1Plugin.partial = True

_plugin = _U1Plugin()
_u1_threading.settrace(_u1_glob)
_u1_sys.settrace(_u1_glob)
try:
    _rc = _u1_pytest.main(_U1["pytest_args"], plugins=[_plugin])
finally:
    _u1_sys.settrace(None); _u1_threading.settrace(None)
if _U1Plugin.partial:
    _u1_skipped.add(("<partial>", ""))
_u1_dump()
_u1_os._exit(0)
'''


def pytest_extra() -> list[str]:
    """REPO_PYTEST_ARGS (the manifest's `pytest_args`, gc init --pytest-args) as argv words, as E1 adds them (v30).
    Raises ValueError when they are not shell words; main() checks first and exits 75."""
    return shlex.split(os.environ.get("REPO_PYTEST_ARGS", ""))


def changed_functions(root: str, before_root: str, write_set: list[str]) -> list[tuple[str, str, int]]:
    """(file, qualname, line on the patched tree) for every def the ticket changed and did not create: C1's split
    of introduced functions, keeping those BEFORE_ROOT already has."""
    out = []
    for f, q, line in C1.introduced_functions(root, before_root, write_set):
        if q in C1._defs(Path(before_root) / f):
            out.append((f, q, line))
    return out


def run_driver(code: str, args: list[str], cwd: str, u1spec: dict, stdin: str | None, deadline: float,
               out: str) -> tuple[dict, str, bool]:
    """One driver process; (its records file, its stdout, cut short). Past the deadline it gets SIGTERM and
    writes what it gathered. The spec is a file beside `out` (under U1's temp dir, K2) and the environment carries
    only its path: a `want` list of every input recorded on a large module does not fit in the environment (v32)."""
    left = deadline - time.time()
    if left <= 0:
        return {}, "", True
    spec_file = os.path.splitext(out)[0] + ".spec.json"
    Path(spec_file).write_text(json.dumps({**u1spec, "out": out}), encoding="utf-8")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "U1_SPEC_FILE": spec_file}
    p = subprocess.Popen([os.environ.get("REPO_PYTHON") or sys.executable, *args, "-c", code], cwd=cwd, env=env, text=True,
                         stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cut = False
    try:
        so, _ = p.communicate(stdin, timeout=left)
    except subprocess.TimeoutExpired:
        cut = True
        p.send_signal(signal.SIGTERM)
        try:
            so, _ = p.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            p.kill(); so, _ = p.communicate()
    try:
        rec = json.loads(Path(out).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rec = {}
    if any(s == ["<partial>", ""] for s in rec.get("skipped", [])):
        cut = True
    return rec, so or "", cut


def drive(tree: str, tmp: str, tag: str, watch: list, want: list | None, cap: int, claims: list[dict],
          test_files: list[str] | None, lines: int, claim_secs: float, deadline_tests: float,
          deadline: float) -> tuple[list, list, dict, bool]:
    """Both drivers on one tree. (records, skipped, claim index -> RUNNER result, partial)."""
    base = {"root": tree, "watch": watch, "want": want, "cap": cap, "deadline": deadline_tests}
    records, skipped, runner, partial = [], set(), {}, False
    if test_files is None or test_files:
        pt = ["-q", "--rootdir=.", "-p", "no:cacheprovider", f"--basetemp={tmp}/pt-{tag}", "--tb=no", "--color=no",
              *pytest_extra(), *(test_files or [])]
        rec, _, cut = run_driver(PYTEST_DRIVER, [], tree, {**base, "pytest_args": pt}, None,
                                 deadline_tests, os.path.join(tmp, f"tests-{tag}.json"))
        partial |= cut
        records += [r + [None] for r in rec.get("records", [])]
        skipped |= {tuple(s) for s in rec.get("skipped", []) if s != ["<partial>", ""]}
    for i, c in enumerate(claims, 1):
        if time.time() >= deadline:
            partial = True
            break
        spec = {"root": tree, "name": c.get("name", ""), "setup": c.get("setup") or [], "call": c.get("call", ""),
                "expect": c.get("expect") or {}, "lines": lines}
        rec, so, cut = run_driver(CLAIM_DRIVER, ["-I"], tree, {**base, "driver": f"claim {i}"}, json.dumps(spec),
                                  min(deadline, time.time() + claim_secs), os.path.join(tmp, f"claim{i}-{tag}.json"))
        partial |= cut and time.time() >= deadline
        records += [r + [i] for r in rec.get("records", [])]
        skipped |= {tuple(s) for s in rec.get("skipped", [])}
        try:
            runner[i] = json.loads(so.strip().splitlines()[-1])
        except (ValueError, IndexError):
            runner[i] = {}
    return records, sorted(skipped), runner, partial


def declared_names(claims: list[dict], runner: dict) -> tuple[set, set]:
    """(claim names, (file, last name) the RUNNER resolved each claim to on the patched tree)."""
    names = {c.get("name", "") for c in claims}
    resolved = set()
    for i, c in enumerate(claims, 1):
        r = runner.get(i) or {}
        if r.get("file"):
            resolved.add((r["file"], c.get("name", "").rsplit(".", 1)[-1]))
    return names, resolved


def main() -> int:
    t0 = time.time()
    root = os.environ.get("SCOPED_ROOT")
    before_root = os.environ.get("BEFORE_ROOT")
    if not root or not os.path.isdir(root):
        print("U1 not run: SCOPED_ROOT is not a directory", file=sys.stderr); return 75
    if not before_root or not os.path.isdir(before_root):
        print("U1 not run: BEFORE_ROOT is not a directory", file=sys.stderr); return 75
    py = os.environ.get("REPO_PYTHON") or sys.executable
    if subprocess.run([py, "-c", "import pytest"], capture_output=True).returncode != 0:
        print(f"U1 not run: pytest is not importable by {py}", file=sys.stderr); return 75
    try:
        pytest_extra()
    except ValueError as e:
        print(f"U1 not run: REPO_PYTEST_ARGS is not shell words: {e}", file=sys.stderr); return 75
    write_set = json.loads(os.environ.get("WRITE_SET") or "[]")
    budget = float(os.environ.get("U1_SECONDS", "600"))
    cap = int(os.environ.get("U1_INPUTS", "50"))
    lines = int(os.environ.get("C1_LINES", "2000000"))
    claim_secs = float(os.environ.get("C1_SECONDS", "60"))
    end = t0 + budget
    claims: list[dict] = []
    tf = os.environ.get("TICKET_FILE")
    if tf and os.path.isfile(tf):  # C1 judges the claims file; U1 only drives with it
        ticket = json.loads(Path(tf).read_text(encoding="utf-8"))
        cf = Path(tf).resolve().parent.parent / "claims" / f"{ticket.get('ticket_id', os.environ.get('TICKET_ID', ''))}.json"
        if cf.is_file():
            try:
                claims = [c for c in json.loads(cf.read_text(encoding="utf-8")) if isinstance(c, dict)]
            except ValueError:
                claims = []

    changed = changed_functions(root, before_root, write_set)
    summary = {"changed": [[f, q, ln] for f, q, ln in changed], "inputs": 0, "compared": 0, "differences": 0,
               "undeclared": 0, "unmatched": 0, "unstable": 0, "partial": False}
    if not changed:
        summary["seconds"] = round(time.time() - t0, 2)
        print("U1 evidence: " + json.dumps({"summary": summary}, sort_keys=True))
        print("U1 pass: no pre-existing function changed")
        return 0
    watch = [[f, q] for f, q, _ in changed]
    line_of = {(f, q): ln for f, q, ln in changed}
    tmp = tempfile.mkdtemp(prefix="u1-")
    try:
        btmp, btree = C1.before_tree(root, before_root, write_set)
        try:
            brec, bskip, _, bpart = drive(btree, tmp, "before", watch, None, cap, claims, None, lines, claim_secs,
                                          t0 + budget * 0.4, t0 + budget * 0.5)
        finally:
            C1._rm_tree(btmp)
        before: dict[tuple, list] = {}  # (file, qualname, input) -> [outcome, driver, unstable]
        for f, q, inp, v, ci in brec:
            k = (f, q, inp)
            if k not in before:
                before[k] = v if ci is None else [v[0], f"claim {ci}", v[2]]
            elif before[k][0] != v[0]:
                before[k][2] = True
        summary["inputs"] = len(before)
        summary["unstable"] = sum(1 for v in before.values() if v[2])
        want = [list(k) for k, v in before.items() if not v[2]]
        drivers = {v[1] for k, v in before.items() if not v[2]}
        files = sorted({d.split("::", 1)[0] for d in drivers if not d.startswith("claim ")})
        files = [x for x in files if os.path.isfile(os.path.join(root, x))]
        arec, askip, runner, apart = drive(root, tmp, "after", watch, want, cap, claims, files, lines, claim_secs,
                                           time.time() + (end - time.time()) * 0.8, end)
        after: dict[tuple, dict] = {}
        for f, q, inp, v, ci in arec:
            for drv, out in v.items():
                after.setdefault((f, q, inp), {}).setdefault(drv, out)
        names, resolved = declared_names(claims, runner)
        diffs = []
        for (f, q, inp), (bout, drv, unstable) in before.items():
            if unstable:
                continue
            got = after.get((f, q, inp))
            if not got:
                summary["unmatched"] += 1
                continue
            summary["compared"] += 1
            aout = got.get(drv, next(iter(got.values())))
            if json.dumps(aout, sort_keys=True) != json.dumps(bout, sort_keys=True):
                dec = C1.dotted(f, q) in names or (f, q.rsplit(".", 1)[-1]) in resolved
                diffs.append({"file": f, "line": line_of[(f, q)], "qualname": q, "declared": dec,
                              "input": {a: v for a, v in json.loads(inp)}, "before": bout, "after": aout,
                              "driver": drv})
        summary["differences"] = len(diffs)
        summary["undeclared"] = sum(1 for d in diffs if not d["declared"])
        summary["partial"] = bool(bpart or apart)
        sk = sorted({tuple(x) for x in bskip} | {tuple(x) for x in askip})
        if sk:
            summary["not_recorded"] = [list(x) for x in sk]  # generator or coroutine functions: no one outcome
        for d in diffs:
            if not d["declared"]:
                d["finding"] = "undeclared_change"
            print("U1 evidence: " + json.dumps({"difference": d}, default=repr))  # input keeps parameter order
        # A strike for undeclared_change would go here (a fail line and return 1); not until the signer rules it.
    finally:
        C1._rm_tree(tmp)
    summary["seconds"] = round(time.time() - t0, 2)
    print("U1 evidence: " + json.dumps({"summary": summary}, sort_keys=True))
    print(f"U1 pass: {len(changed)} changed function(s), {summary['inputs']} input(s) recorded, "
          f"{summary['compared']} compared, {summary['differences']} difference(s), {summary['undeclared']} undeclared"
          + (" (partial: out of time)" if summary["partial"] else ""))
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:  # U1's own error: not run (75), never a strike; evidence that was printed stands as printed
        print(f"U1 not run: {type(e).__name__}: {str(e)[:300]}", file=sys.stderr)
        rc = 75
    sys.exit(rc)
