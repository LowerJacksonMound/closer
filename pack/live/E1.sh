#!/bin/sh
# Live in pack v33 (2026-10-19: when pytest exits red but its short summary never printed (an internal error or a
# plugin raising at session end: cookiecutter 2 and 3 in CLOSER_PROVING set2 exited 3 with `28 failed ... 40 errors`
# and E1 named no test), E1 reruns the suite once with `-v` and names the failing tests from the per-test result
# lines, which print as each test runs; the internal error's own line is said too. v31: pytest 3.x short summary `FAIL` and `::()` read; `--rootdir=.` passed only when the
# repo's pytest takes it (pytest 3.0.x does not); `(collection error)` only on a file-level ERROR, `(error)` on a test's;
# v30 exit 5 with test files is a fail, REPO_PYTEST_ARGS; v29 the repo's interpreter: REPO_PYTHON; v23 T4/T5). Edit only
# through a new pack version (K5).
# E1: the repo's tests pass on the patched tree. Two groups, both must be green:
#   before-ticket tests: test files the ticket did not write (the World's, the prior authors' requirement);
#   the ticket's own tests: test files in the write_set (a writer's red test is a failed claim about its own code;
#   signer 2026-10-15: reject with a strike).
# Runs pytest once over SCOPED_ROOT inside the verify sandbox, under a clock. Out of time is a fail (unjudged is
# reject), never silence. Exit 75 (not run) only for the host's fault: no SCOPED_ROOT, no pytest.
# pytest runs under REPO_PYTHON (the manifest's `python`, gc init --python) when set, else python3 as before; this
# script's own logic stays on python3.
# REPO_PYTEST_ARGS (the manifest's `pytest_args`, gc init --pytest-args; shell words) is added after E1's own pytest
# flags: the repo's own pytest settings (`-o python_files=tests_*.py`, `--ignore=...`, test paths). v30.
# pytest exit 5 (no tests collected) passes only when the tree has no test files: no test_*.py, *_test.py or
# tests_*.py, and no .py but __init__/conftest under a tests/ or test/ directory (hidden dirs, __pycache__, site-packages, node_modules and
# venvs left out). With test files present it is `E1 fail: run_fail (pytest exit 5 ...)`: tests that exist and were
# not run are unjudged, and unjudged is reject (v30; v29 printed `E1 pass: no tests in the tree`).
# Prints one line per failing test: `E1 fail: run_fail <nodeid> (before-ticket|own)`. The names come from pytest's short
# summary (-rfE): `FAILED <nodeid> - msg` / `ERROR <nodeid>` from pytest 4.6 on, `FAIL <nodeid>` / `ERROR <nodeid>` on
# pytest 3.x, where a method's node id also carries an instance part (`file::Class::()::test`). v31 reads both spellings
# and drops `::()`, so a red test under a 3.x REPO_PYTHON is named and attributed; v30 read only `FAILED` and printed
# `run_fail (pytest exit 1, no test named)` there (right decision, no name). Checked on pytest 3.0.7, 3.10.1, 4.6.11,
# 5.4.3, 7.4.4 (CLOSER_PROVING set2 venvs, 2026-10-19).
# An `ERROR` line names a file when collection failed (`ERROR tests/test_x.py`: import error, syntax error) and a node when
# a test's setup failed (`ERROR tests/test_x.py::test_y`: a fixture raised); E1 labels the first `(collection error)` and
# the second `(error)` by the `::`. v30 labelled every ERROR `(collection error)`. Both forms checked on 3.0.7, 3.10.1,
# 4.6.11, 7.4.4.
# `--rootdir=.` (the tree root, so node ids match write_set paths) is passed only when the repo's pytest lists it in
# `--help`: pytest 3.0.x has no such option and exited 2 (`unrecognized arguments`) before collecting, so v30 said
# `run_fail (pytest exit 2, no test named)` on every ticket under 3.0.7, honest ones included. Without the flag pytest
# 3.0.x spells node ids relative to the cwd, the tree root, as the flag would (checked with an ini file in a parent dir).
set -u
TREE="${SCOPED_ROOT:?set SCOPED_ROOT to the patched tree}"
WS="${WRITE_SET:?set WRITE_SET to the ticket write_set JSON}"
TID="${TICKET_ID:-ticket}"
LIMIT="${E1_SECONDS:-600}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PY="${REPO_PYTHON:-python3}"
"$PY" -c 'import pytest' 2>/dev/null || { echo "E1 not run: pytest is not importable by $PY" >&2; exit 75; }
[ -d "$TREE" ] || { echo "E1 not run: SCOPED_ROOT is not a directory: $TREE" >&2; exit 75; }

cd "$TREE" || exit 75
PYTHONDONTWRITEBYTECODE=1 python3 - "$WS" "$TMP" "$LIMIT" "$TID" "${REPO_PYTHON:-}" << 'PY'
import json, os, re, shlex, subprocess, sys
ws, tmp, limit, tid = set(json.loads(sys.argv[1])), sys.argv[2], float(sys.argv[3]), sys.argv[4]
try:
    extra = shlex.split(os.environ.get("REPO_PYTEST_ARGS", ""))
except ValueError as e:
    print(f"E1 not run: REPO_PYTEST_ARGS is not shell words: {e}", file=sys.stderr)
    sys.exit(75)
py = sys.argv[5] or sys.executable
try:  # does this pytest take --rootdir? (added in pytest 3.1; 3.0.x refuses it with exit 2) v31
    h = subprocess.run([py, "-m", "pytest", "--help"], capture_output=True, text=True, timeout=limit)
except subprocess.TimeoutExpired:
    print(f"E1 fail: run_fail (pytest --help did not finish in {limit:.0f}s: out of time is a fail)", file=sys.stderr)
    sys.exit(1)
rootdir = ["--rootdir=."] if "--rootdir" in h.stdout else []
cmd = [py, "-m", "pytest", "-q", *rootdir, "-p", "no:cacheprovider", f"--basetemp={tmp}/pt",
       "--tb=no", "-rfE", "--color=no", *extra]


def test_files_in_tree(cap=3):
    """Up to cap test files under the cwd (the patched tree): test_*.py, *_test.py, tests_*.py, or any .py under a
    tests/ or test/ directory other than __init__.py and conftest.py. Hidden dirs, __pycache__, site-packages,
    node_modules and venvs (pyvenv.cfg) left out."""
    found = []
    for d, dirs, files in os.walk("."):
        dirs[:] = sorted(x for x in dirs if not x.startswith(".") and x not in ("__pycache__", "site-packages", "node_modules")
                         and not os.path.isfile(os.path.join(d, x, "pyvenv.cfg")))
        in_tests = any(x in ("tests", "test") for x in os.path.normpath(d).split(os.sep))
        for f in sorted(files):
            if f.endswith(".py") and (f.startswith(("test_", "tests_")) or f.endswith("_test.py")
                                      or (in_tests and f not in ("__init__.py", "conftest.py"))):
                found.append(os.path.normpath(os.path.join(d, f)))
                if len(found) >= cap:
                    return found
    return found


try:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=limit)
except subprocess.TimeoutExpired:
    print(f"E1 fail: run_fail (the suite did not finish in {limit:.0f}s: out of time is a fail)", file=sys.stderr)
    sys.exit(1)
out = r.stdout + r.stderr
if r.returncode == 5:  # no tests collected
    present = test_files_in_tree()
    if present:
        print(f"E1 fail: run_fail (pytest exit 5: no tests collected, but the tree has test files: {', '.join(present)}; "
              f"pytest args: {shlex.join(extra) if extra else 'none'}; the repo's own pytest settings go in "
              f"gc init --pytest-args)", file=sys.stderr)
        sys.exit(1)
    print(f"E1 pass: no tests in the tree")
    sys.exit(0)
fails = []
for ln in out.splitlines():
    m = re.match(r"^(FAILED|FAIL|ERROR)\s+(\S+)", ln)  # FAILED from pytest 4.6; FAIL on 3.x (v31)
    if m:
        node = m.group(2).rstrip(":").replace("::()", "")  # 3.x instance part in method node ids (v31)
        f = node.split("::", 1)[0]
        own = f in ws
        label = "" if m.group(1) != "ERROR" else (" (error)" if "::" in node else " (collection error)")  # v31: file vs node
        fails.append(f"{node} ({'own' if own else 'before-ticket'})" + label)
def internal_line(text):
    """pytest's own failure, when it had one: the last INTERNALERROR> line, or the last line after a Traceback (the
    exception); pytest glues the traceback onto the progress line, so this does not rely on line starts."""
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    ie = [ln for ln in lines if "INTERNALERROR>" in ln]
    if ie:
        return ie[-1].strip()[:200]
    if any("Traceback (most recent call last)" in ln for ln in lines):
        return lines[-1].strip()[:200]
    return ""


internal = internal_line(out)
if r.returncode != 0 and not fails:  # v33: red, and the short summary never printed: rerun once verbosely to name the tests
    try:
        rv = subprocess.run([c for c in cmd if c != "-q"] + ["-v"], capture_output=True, text=True, timeout=limit)  # -q would cancel -v
        vout = rv.stdout + rv.stderr
    except subprocess.TimeoutExpired:
        vout = ""
    for ln in vout.splitlines():
        m = re.match(r"^(\S+::\S+) (FAILED|ERROR)\b", ln)
        if m:
            node = m.group(1).replace("::()", "")
            own = node.split("::", 1)[0] in ws
            fails.append(f"{node} ({'own' if own else 'before-ticket'})" + (" (error)" if m.group(2) == "ERROR" else ""))
    fails = list(dict.fromkeys(fails))
    if not internal:
        internal = internal_line(vout)
if r.returncode not in (0, 1, 2) and not fails:
    print(f"E1 fail: run_fail (pytest exit {r.returncode}: {internal or (out.strip().splitlines()[-1] if out.strip() else 'no output')})", file=sys.stderr)
    sys.exit(1)
if fails or r.returncode != 0:
    for x in fails or [f"(pytest exit {r.returncode}, no test named)"]:
        print(f"E1 fail: run_fail {x}", file=sys.stderr)
    if internal:
        print(f"E1 fail: run_fail (pytest exit {r.returncode}; summary not printed: {internal})", file=sys.stderr)
    sys.exit(1)
m = re.search(r"(\d+) passed", out)
print(f"E1 pass: {m.group(1) if m else '?'} test(s) passed on the patched tree")
PY
