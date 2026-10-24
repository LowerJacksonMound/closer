#!/bin/sh
# Proposed for pack v30 (2026-10-16, exit 5 with test files is a fail; REPO_PYTEST_ARGS; v29 the repo's interpreter:
# REPO_PYTHON; v23 T4/T5). Edit only through a new pack version (K5).
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
# Prints one line per failing test: `E1 fail: run_fail <nodeid> (before-ticket|own)`.
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
cmd = [sys.argv[5] or sys.executable, "-m", "pytest", "-q", "--rootdir=.", "-p", "no:cacheprovider", f"--basetemp={tmp}/pt",
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
    m = re.match(r"^(FAILED|ERROR)\s+(\S+)", ln)
    if m:
        node = m.group(2).rstrip(":")
        f = node.split("::", 1)[0]
        own = f in ws
        fails.append(f"{node} ({'own' if own else 'before-ticket'})" + (" (collection error)" if m.group(1) == "ERROR" else ""))
if r.returncode not in (0, 1, 2) and not fails:
    print(f"E1 fail: run_fail (pytest exit {r.returncode}: {out.strip().splitlines()[-1] if out.strip() else 'no output'})", file=sys.stderr)
    sys.exit(1)
if fails or r.returncode != 0:
    for x in fails or [f"(pytest exit {r.returncode}, no test named)"]:
        print(f"E1 fail: run_fail {x}", file=sys.stderr)
    sys.exit(1)
m = re.search(r"(\d+) passed", out)
print(f"E1 pass: {m.group(1) if m else '?'} test(s) passed on the patched tree")
PY
