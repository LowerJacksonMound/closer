#!/bin/sh
# Plant: pytest exit 5 (no tests collected) is a fail when the tree has test files (pack v30). The repo's tests are
# named tests_*.py, which pytest does not collect without the repo's own setting (python_files), and no
# --pytest-args is given: v29 printed `E1 pass: no tests in the tree`. Case 1 (struck): E1 fails `run_fail (pytest
# exit 5 ...)` naming the test file it found, the land rejects with a strike and rolls back. Case 2 (clean): a tree
# with no test files (only a conftest.py under tests/, which is not a test file) still passes `no tests in the tree`.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT e1_exit5_tests_present: FAIL $*" >&2; exit 1; }
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
row() {
  python3 - "$ST/ledger.jsonl" <<'PY' 2>/dev/null || echo "NO ROW"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "E1"]
print("\n".join(c[0]["said"]) if c else "NO E1")
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
}

# --- case 1: test files present, none collected: a fail ---------------------------------------------------------
R="$T/repo"; ST="$T/state"
mkdir -p "$R/pkg/tests"
echo notes > "$R/README.txt"
printf '' > "$R/pkg/__init__.py"; printf '' > "$R/pkg/tests/__init__.py"
printf 'def add(a, b):\n    return a + b\n' > "$R/pkg/calc.py"
printf 'from pkg.calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n' > "$R/pkg/tests/tests_calc.py"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "init/scan"
printf '%s' '[{"name":"pkg.calc.add","call":"add(2, 3)","expect":{"result":5}}]' > "$T/cl"
gc ticket --write pkg/calc.py --id T1 --claims "$T/cl" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1/pkg"; printf 'def add(a, b):\n    s = a + b\n    return s\n' > "$ST/payload/T1/pkg/calc.py"
gc land --ticket T1 > "$T/land" 2>&1
[ $? -eq 1 ] || fail "exit 5 with tests_calc.py present was not rejected: $(grep -E '^E1' "$T/land"; tail -2 "$T/land")"
row > "$T/row"
grep -q "^E1 pass" "$T/row" && fail "E1 passed with uncollected test files: $(cat "$T/row")"
grep -q "^E1 fail: run_fail (pytest exit 5: no tests collected, but the tree has test files: pkg/tests/tests_calc.py;" "$T/row" \
  || fail "E1 fail line wrong: $(cat "$T/row")"
grep -q "^STRIKE$" "$T/row" || fail "no strike: $(cat "$T/row")"
[ "$(cat "$R/pkg/calc.py")" = "$(printf 'def add(a, b):\n    return a + b')" ] || fail "rejected ticket not rolled back"

# --- case 2: no test files at all: exit 5 still passes ------------------------------------------------------------
R="$T/repo2"; ST="$T/state2"
mkdir -p "$R/tests"
echo notes > "$R/README.txt"
printf 'def add(a, b):\n    return a + b\n' > "$R/calc.py"
printf 'import sys\n' > "$R/tests/conftest.py"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "init/scan (no tests)"
printf '%s' '[{"name":"calc.add","call":"add(2, 3)","expect":{"result":5}}]' > "$T/cl2"
gc ticket --write calc.py --id T1 --claims "$T/cl2" >/dev/null 2>&1 || fail "mint (no tests)"
mkdir -p "$ST/payload/T1"; printf 'def add(a, b):\n    s = a + b\n    return s\n' > "$ST/payload/T1/calc.py"
gc land --ticket T1 > "$T/land2" 2>&1 || fail "tree with no test files did not land: $(grep -E '^E1' "$T/land2"; tail -2 "$T/land2")"
grep -q "^E1 pass: no tests in the tree$" "$T/land2" || fail "E1 (no tests): $(grep E1 "$T/land2")"
echo "PLANT e1_exit5_tests_present: PASS"
