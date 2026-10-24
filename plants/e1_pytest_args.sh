#!/bin/sh
# Plant: the repo's own pytest settings reach the checks (pack v30). `gc init --pytest-args "-o python_files=tests_*.py"`
# records `pytest_args` in the manifest; gc exports it to every check as REPO_PYTEST_ARGS; E1 and U1 add it to their
# pytest runs. The repo's tests are named tests_*.py, so without it pytest collects nothing.
# Case 1 (clean): an honest ticket lands; E1 passes on the collected test (`1 test(s) passed`, not `no tests`) and U1
# records the test's own input as well as the claim's (2 inputs). gc verify --ticket (E1 as the ticket's verify) passes.
# Case 2 (struck): a ticket that breaks the function the tests_*.py test covers: E1 names that test as a before-ticket
# fail, the land rejects with a strike.
# Case 3: no --pytest-args in the manifest, REPO_PYTEST_ARGS inherited from the caller: it is not used (exit 5 with a
# test file present: E1 fails). And --pytest-args that are not shell words are refused at init.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT e1_pytest_args: FAIL $*" >&2; exit 1; }
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkrepo() {
  mkdir -p "$R/pkg/tests"
  echo notes > "$R/README.txt"
  printf '' > "$R/pkg/__init__.py"; printf '' > "$R/pkg/tests/__init__.py"
  printf 'def add(a, b):\n    return a + b\n' > "$R/pkg/calc.py"
  printf 'from pkg.calc import add\n\n\ndef test_add():\n    assert add(10, 20) == 30\n' > "$R/pkg/tests/tests_calc.py"
}
row() {
  python3 - "$ST/ledger.jsonl" <<'PY' 2>/dev/null || echo "NO ROW"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
for name in ("E1", "U1"):
    c = [c for c in r.get("checks", []) if c["name"] == name]
    print("\n".join(c[0]["said"]) if c else "NO " + name)
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
}
mint() {  # mint <id> <payload calc.py> [--verify E1]
  id="$1"; body="$2"; shift 2
  gc scan >/dev/null 2>&1 || fail "scan"
  gc ticket --write pkg/calc.py --id "$id" --claims "$T/cl" "$@" >/dev/null 2>&1 || fail "mint $id"
  mkdir -p "$ST/payload/$id/pkg"; printf '%s' "$body" > "$ST/payload/$id/pkg/calc.py"
}
printf '%s' '[{"name":"pkg.calc.add","call":"add(2, 3)","expect":{"result":5}}]' > "$T/cl"

# --- case 1: the setting reaches E1 and U1; honest ticket lands ---------------------------------------------------
R="$T/repo"; ST="$T/state"; mkrepo
gc init --pytest-args "-o python_files=tests_*.py" >/dev/null 2>&1 || fail "init --pytest-args"
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); assert m.get("pytest_args") == "-o python_files=tests_*.py", m' \
  "$ST/manifest.json" || fail "manifest pytest_args: $(cat "$ST/manifest.json")"
mint T1 'def add(a, b):
    s = a + b
    return s
'
REPO_PYTEST_ARGS="--definitely-not-an-option" gc land --ticket T1 > "$T/land" 2>&1 \
  || fail "honest ticket did not land with --pytest-args (inherited REPO_PYTEST_ARGS used?): $(grep -E '^(E1|U1)' "$T/land"; tail -2 "$T/land")"
grep -q "^E1 pass: 1 test(s) passed on the patched tree$" "$T/land" || fail "E1 did not collect tests_calc.py: $(grep E1 "$T/land")"
EVF="$(ls "$ST/evidence/T1".*.json 2>/dev/null | tail -1)"
python3 - "$EVF" <<'PY' || fail "U1 did not run the repo's tests with the setting: $(grep U1 "$T/land")"
import json, sys
s = [e["summary"] for e in json.load(open(sys.argv[1]))["checks"]["U1"] if "summary" in e]
assert len(s) == 1 and s[0]["inputs"] == 2 and s[0]["compared"] == 2, s  # (10, 20) from the test, (2, 3) from the claim
PY
mint T1v 'def add(a, b):
    t = a + b
    return t
' --verify E1
gc verify --ticket T1v > "$T/verify" 2>&1 || fail "gc verify E1 with --pytest-args: $(tail -4 "$T/verify")"
grep -q "^E1 pass: 1 test(s) passed" "$T/verify" || fail "gc verify E1 did not collect: $(grep E1 "$T/verify")"

# --- case 2: the collected test catches a broken ticket -----------------------------------------------------------
mint T2 'def add(a, b):
    if a > 5:
        return a - b
    return a + b
'
gc land --ticket T2 > "$T/land2" 2>&1
[ $? -eq 1 ] || fail "ticket breaking add(10, 20) was not rejected: $(grep -E '^E1' "$T/land2"; tail -2 "$T/land2")"
row > "$T/row2"
grep -q "^E1 fail: run_fail pkg/tests/tests_calc.py::test_add (before-ticket)$" "$T/row2" || fail "E1 fail line: $(cat "$T/row2")"
grep -q "^STRIKE$" "$T/row2" || fail "T2 no strike: $(cat "$T/row2")"

# --- case 3: from the manifest only; and refused when not shell words ----------------------------------------------
R="$T/repo3"; ST="$T/state3"; mkrepo
gc init >/dev/null 2>&1 || fail "init (no --pytest-args)"
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); assert "pytest_args" not in m, m' "$ST/manifest.json" \
  || fail "manifest has pytest_args without --pytest-args"
mint T1 'def add(a, b):
    s = a + b
    return s
'
REPO_PYTEST_ARGS="-o python_files=tests_*.py" gc land --ticket T1 > "$T/land3" 2>&1
[ $? -eq 1 ] || fail "inherited REPO_PYTEST_ARGS was used: $(grep -E '^E1' "$T/land3")"
grep -q "^E1 fail: run_fail (pytest exit 5: no tests collected, but the tree has test files: pkg/tests/tests_calc.py; pytest args: none;" "$T/land3" \
  || fail "E1 (no setting): $(grep E1 "$T/land3")"
R="$T/repo4"; ST="$T/state4"; mkrepo
gc init --pytest-args '-o "python_files=tests_*.py' >/dev/null 2>&1 && fail "init took --pytest-args that are not shell words"
[ -f "$ST/manifest.json" ] && fail "a refused init left a manifest"
echo "PLANT e1_pytest_args: PASS"
