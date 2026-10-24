#!/bin/sh
# Plant: E1 names the failing tests when pytest exits red without printing its short summary (pack v33). A conftest
# whose pytest_sessionfinish raises makes pytest die after the tests ran: the per-test results were printed, the `-rfE`
# summary never was (cookiecutter 2 and 3 in CLOSER_PROVING set2, 2026-10-19: exit 3, `28 failed ... 40 errors`, and v32's
# E1 said `run_fail (pytest exit 3: <summary line>)` with no test named, so the set2 deselect list had nothing to name).
# v33 reruns once with `-v` and names them from the result lines. Case 1: the ticket breaks tests/test_app.py::test_f;
# E1 names it `(before-ticket)`, says the internal error, reject with a strike, repo rolled back. Case 2: honest ticket
# under the same broken conftest: no test fails, pytest is still red, E1 says `(pytest exit N, no test named)` plus the
# internal error line, reject (unjudged is reject), never a silent pass.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { echo "PLANT e1_summary_lost_names_test: FAIL $*" >&2; exit 1; }
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkrepo() {
  mkdir -p "$R/tests"
  echo notes > "$R/README.txt"
  printf 'def f(x):\n    return x + 1\n' > "$R/app.py"
  printf 'from app import f\n\n\ndef test_f():\n    assert f(1) == 2\n' > "$R/tests/test_app.py"
  printf 'def pytest_sessionfinish(session, exitstatus):\n    raise RuntimeError("boom")\n' > "$R/conftest.py"
}
e1() {
  python3 - "$ST/ledger.jsonl" <<'PY' 2>/dev/null || echo "NO ROW"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "E1"]
print("\n".join(c[0]["said"]) if c else "NO E1"); print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
}
# Case 1: the ticket breaks the existing test; the summary is lost; E1 names the test anyway
R="$T/r1"; ST="$T/s1"; mkrepo
CL="$T/c1.json"; printf '%s' '[{"name":"app.f","call":"f(1)","expect":{"result":3}}]' > "$CL"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "case 1 init/scan"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "case 1 mint"
mkdir -p "$ST/payload/T1"; printf 'def f(x):\n    return x + 2\n' > "$ST/payload/T1/app.py"
gc land --ticket T1 > "$T/land1" 2>&1; rc=$?
out="$(e1)"
[ $rc -eq 1 ] || fail "case 1: land exit $rc, want 1: $(tail -3 "$T/land1")"
echo "$out" | grep -q "run_fail tests/test_app.py::test_f (before-ticket)" || fail "case 1: failing test not named: $out"
echo "$out" | grep -q "no test named" && fail "case 1: said 'no test named': $out"
echo "$out" | grep -q "summary not printed" || fail "case 1: the internal error was not said: $out"
echo "$out" | grep -q "^STRIKE" || fail "case 1: no strike: $out"
grep -q "x + 1" "$R/app.py" || fail "case 1: repo not rolled back"
# Case 2: honest ticket, same broken conftest: pytest is red with no failing test; still a reject, says why
R="$T/r2"; ST="$T/s2"; mkrepo
CL="$T/c2.json"; printf '%s' '[{"name":"app.g","call":"g(2)","expect":{"result":4}}]' > "$CL"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "case 2 init/scan"
gc ticket --write app.py --id T2 --claims "$CL" >/dev/null 2>&1 || fail "case 2 mint"
mkdir -p "$ST/payload/T2"; printf 'def f(x):\n    return x + 1\n\n\ndef g(x):\n    return x * 2\n' > "$ST/payload/T2/app.py"
gc land --ticket T2 > "$T/land2" 2>&1; rc=$?
out="$(e1)"
[ $rc -eq 1 ] || fail "case 2: land exit $rc, want 1 (pytest red is never a pass): $(tail -3 "$T/land2")"
echo "$out" | grep -q "E1 fail" || fail "case 2: no E1 fail line: $out"
echo "$out" | grep -q "RuntimeError: boom\|INTERNALERROR\|Traceback" || fail "case 2: the internal error was not said: $out"
echo "$out" | grep -q "run_fail tests/" && fail "case 2: a passing test was named: $out"
echo "PLANT e1_summary_lost_names_test: PASS"
