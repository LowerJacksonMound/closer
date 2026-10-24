#!/bin/sh
# Plant: E1 under a pytest 3.x REPO_PYTHON (pack v31): the failing tests are named, pytest 3.0.x is not refused, and an
# ERROR is labelled by its form. pytest 3.x writes `FAIL <nodeid>` in the short summary (-rfE), not `FAILED`, and spells
# a method's node id with an instance part (`file::Class::()::test`); v30's E1 read only `FAILED`, so a red test under
# pytest 3.x gave `E1 fail: run_fail (pytest exit 1, no test named)` (CLOSER_PROVING 2026-10-16). pytest 3.0.x has no
# `--rootdir` option; v30 always passed `--rootdir=.`, so under 3.0.7 pytest exited 2 before collecting and every ticket,
# honest or not, got `run_fail (pytest exit 2, no test named)`. v30 also labelled every ERROR `(collection error)`, a
# fixture error included. v31 reads both spellings, drops `::()`, passes `--rootdir=.` only when the pytest lists it in
# `--help`, and labels `ERROR file::node` `(error)` and `ERROR file` `(collection error)`.
# The three cases run under two interpreters: pytest 3.x with `--rootdir` (3.10.1) and pytest 3.0.x without it (3.0.7).
# Case 1 (struck, named): the ticket breaks the existing tests/test_app.py::test_f and adds tests/test_g.py with a red
# method test TestG::test_g and a test test_e whose fixture raises. E1 names all three, `(before-ticket)`, `(own)` and
# `(own) (error)`, with no `::()`, no `no test named` and no `(collection error)`; reject with a strike; repo rolled back.
# Case 2 (clean): an honest ticket lands under the same interpreter, `E1 pass: 1 test(s) passed`, and the test itself
# checks it ran on pytest 3.x.
# Case 3 (struck, collection error): the ticket's own tests/test_bad.py imports a module that does not exist. E1 says
# `run_fail tests/test_bad.py (own) (collection error)` and nothing else; reject with a strike.
# Needs two Pythons with pytest 3.x: GC_PLANT_PYTEST3 (default the CLOSER_PROVING set2 thefuck-old-py38 venv: 3.8.20,
# pytest 3.10.1) and GC_PLANT_PYTEST30, one whose pytest has no `--rootdir` (default set2 httpie-2016b-py38: 3.8.20,
# pytest 3.0.7). Either absent: FAIL, as c1_py38_qualname does for its 3.8.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { echo "PLANT e1_pytest3_names_test: FAIL $*" >&2; exit 1; }
PY3="${GC_PLANT_PYTEST3:-$HOME/Desktop/CLOSER_PROVING/set2/_envs/thefuck-old-py38/bin/python}"
PY30="${GC_PLANT_PYTEST30:-$HOME/Desktop/CLOSER_PROVING/set2/_envs/httpie-2016b-py38/bin/python}"
if [ ! -x "$PY3" ] || [ ! -x "$PY30" ]; then
  if [ -z "${GC_PLANT_PYTEST3:-}" ] && [ -z "${GC_PLANT_PYTEST30:-}" ]; then echo "PLANT e1_pytest3_names_test: NOT MEASURED — no pytest 3.x / 3.0.x interpreters on this machine (set GC_PLANT_PYTEST3 and GC_PLANT_PYTEST30 to measure)" >&2; exit 77; fi
  [ -x "$PY3" ] || fail "no interpreter at $PY3 (GC_PLANT_PYTEST3 must be a python with pytest 3.x)"
  fail "no interpreter at $PY30 (GC_PLANT_PYTEST30 must be a python with pytest 3.0.x)"
fi
for P in "$PY3" "$PY30"; do
  "$P" -c 'import pytest; assert pytest.__version__.split(".")[0] == "3", pytest.__version__' 2>/dev/null \
    || fail "$P is not a python with pytest 3.x"
done
"$PY3" -m pytest --help 2>/dev/null | grep -q -- '--rootdir' || fail "$PY3's pytest does not take --rootdir; set GC_PLANT_PYTEST3 to one that does (3.1 on)"
"$PY30" -m pytest --help 2>/dev/null | grep -q -- '--rootdir' && fail "$PY30's pytest takes --rootdir; set GC_PLANT_PYTEST30 to one that does not (3.0.x)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkrepo() {
  mkdir -p "$R/tests"
  echo notes > "$R/README.txt"
  printf 'def f(x):\n    return x + 1\n' > "$R/app.py"
  cat > "$R/tests/test_app.py" <<'EOF'
import pytest

from app import f


def test_f():
    assert pytest.__version__.startswith("3."), pytest.__version__
    assert f(1) == 2
EOF
}
row() {
  python3 - "$ST/ledger.jsonl" <<'PY' 2>/dev/null || echo "NO ROW"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "E1"]
print("\n".join(c[0]["said"]) if c else "NO E1"); print("E1EXIT", c[0]["exit"] if c else "none")
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
}
struck_row() {  # $1 row file, $2 label: the ticket was rejected with a strike and E1 exited 1
  grep -q "^DECISION reject$" "$1" && grep -q "^STRIKE$" "$1" && grep -q "^E1EXIT 1$" "$1" || fail "$2 row: $(cat "$1")"
}

cases() {  # $1 interpreter, $2 label
  PY="$1"; L="$2"; D="$T/$L"; mkdir -p "$D"

  # --- case 1: a before-ticket test, an own method test and an own fixture error go red: all three named ------------
  R="$D/repo"; ST="$D/state"; mkrepo
  gc init --python "$PY" >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "$L: gc init --python/scan"
  CL="$D/claims.json"; printf '%s' '[{"name":"app.g","call":"g(2)","expect":{"result":4}}]' > "$CL"
  gc ticket --write app.py --write tests/test_g.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "$L: mint T1"
  mkdir -p "$ST/payload/T1/tests"
  printf 'def f(x):\n    return x + 2\n\n\ndef g(x):\n    return x * 2\n' > "$ST/payload/T1/app.py"
  cat > "$ST/payload/T1/tests/test_g.py" <<'EOF'
import pytest

from app import g


@pytest.fixture
def broken():
    raise RuntimeError("boom")


class TestG:
    def test_g(self):
        assert g(3) == 7


def test_e(broken):
    assert True
EOF
  gc land --ticket T1 > "$D/land" 2>&1
  [ $? -eq 1 ] || fail "$L: ticket with red tests was not rejected: $(tail -3 "$D/land")"
  row > "$D/row1"
  struck_row "$D/row1" "$L case 1"
  grep -q "no test named" "$D/row1" && fail "$L: E1 did not name the failing tests: $(grep '^E1' "$D/row1")"
  grep -q "::()" "$D/row1" && fail "$L: E1 kept pytest 3.x's instance part in a node id: $(grep '^E1' "$D/row1")"
  grep -q "^E1 fail: run_fail tests/test_app.py::test_f (before-ticket)$" "$D/row1" \
    || fail "$L: before-ticket test not named: $(grep '^E1' "$D/row1")"
  grep -q "^E1 fail: run_fail tests/test_g.py::TestG::test_g (own)$" "$D/row1" \
    || fail "$L: own method test not named: $(grep '^E1' "$D/row1")"
  grep -q "^E1 fail: run_fail tests/test_g.py::test_e (own) (error)$" "$D/row1" \
    || fail "$L: own fixture error not named (error): $(grep '^E1' "$D/row1")"
  grep -q "collection error" "$D/row1" && fail "$L: E1 labelled a fixture error a collection error: $(grep '^E1' "$D/row1")"
  [ "$(grep -c '^E1 fail' "$D/row1")" -eq 3 ] || fail "$L: E1 said more than the three red tests: $(grep '^E1' "$D/row1")"
  [ -e "$R/tests/test_g.py" ] && fail "$L: repo not rolled back"
  grep -q "return x + 1" "$R/app.py" || fail "$L: app.py not rolled back"

  # --- case 2: an honest ticket lands under the same pytest 3.x ---------------------------------------------------
  R="$D/repo2"; ST="$D/state2"; mkrepo
  gc init --python "$PY" >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "$L: gc init --python/scan (case 2)"
  printf '%s' '[{"name":"app.f","call":"f(1)","expect":{"result":2}}]' > "$D/cl2"
  gc ticket --write app.py --id T1 --claims "$D/cl2" >/dev/null 2>&1 || fail "$L: mint T1 (case 2)"
  mkdir -p "$ST/payload/T1"
  printf 'def f(x):\n    y = x + 1\n    return y\n' > "$ST/payload/T1/app.py"
  gc land --ticket T1 > "$D/land2" 2>&1 || fail "$L: honest ticket did not land: $(grep -E '^(E1|C1|U1)' "$D/land2"; tail -2 "$D/land2")"
  grep -q "^E1 pass: 1 test(s) passed on the patched tree$" "$D/land2" || fail "$L: E1 (clean): $(grep E1 "$D/land2")"

  # --- case 3: the ticket's own test file does not import: one line, (collection error) ---------------------------
  R="$D/repo3"; ST="$D/state3"; mkrepo
  gc init --python "$PY" >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "$L: gc init --python/scan (case 3)"
  gc ticket --write app.py --write tests/test_bad.py --id T1 --claims "$D/cl2" >/dev/null 2>&1 || fail "$L: mint T1 (case 3)"
  mkdir -p "$ST/payload/T1/tests"
  printf 'def f(x):\n    y = x + 1\n    return y\n' > "$ST/payload/T1/app.py"
  printf 'import no_such_module_for_this_plant\n\n\ndef test_never():\n    pass\n' > "$ST/payload/T1/tests/test_bad.py"
  gc land --ticket T1 > "$D/land3" 2>&1
  [ $? -eq 1 ] || fail "$L: ticket with a test file that does not import was not rejected: $(tail -3 "$D/land3")"
  row > "$D/row3"
  struck_row "$D/row3" "$L case 3"
  grep -q "^E1 fail: run_fail tests/test_bad.py (own) (collection error)$" "$D/row3" \
    || fail "$L: collection error not named by file: $(grep '^E1' "$D/row3")"
  [ "$(grep -c '^E1 fail' "$D/row3")" -eq 1 ] || fail "$L: E1 said more than the one collection error: $(grep '^E1' "$D/row3")"
  [ -e "$R/tests/test_bad.py" ] && fail "$L: repo not rolled back (case 3)"
}

cases "$PY3" "pytest3-rootdir"
cases "$PY30" "pytest30-no-rootdir"
echo "PLANT e1_pytest3_names_test: PASS"
