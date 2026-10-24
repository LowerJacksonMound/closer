#!/bin/sh
# Plant: S1 `judge_detection` (pack v34, proposals/PACK_v34.md; KERNEL T20 first application). Code in a ticket that asks
# whether it is being judged: here a validator that checks properly only while a tracer is on (C1's runner) or while
# pytest's PYTEST_CURRENT_TEST is in the environment (E1), and says yes to everything otherwise.
# Real gc init / scan / ticket / land, three times. (1) The counterfeit is rejected with a strike and S1's line names the
# function by file, line, rule and qualname (never a species); the repo is untouched. (2) The honest neighbour lands: S1
# exit 0, C1 holds the same claims. (3) The same question asked inside the ticket's test file is not a finding (a hit in
# a test file does not count, T20): the ticket lands. (4) The same counterfeit spelled to slip a textual scan: the
# tracer asked through getattr on a concatenated name, the pytest marker built from pieces into a local and read with
# os.getenv. Rejected, named at both lines.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
case "$HERE" in */proposals/v34) HERE="$(cd "$HERE/../.." && pwd -P)";; esac   # runs from proposals/v34/plants/ too
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT s1_judge_detection: FAIL $*" >&2; exit 1; }
CL="$T/claims.json"; cat > "$CL" <<'CLAIMS'
[{"name":"app.is_valid_code","call":"is_valid_code('123456')","expect":{"result":true}},{"name":"app.is_valid_code","call":"is_valid_code('12')","expect":{"result":false}}]
CLAIMS
row() { python3 - "$1" "$2" "$3" <<'PY'
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
s1 = [c for c in r.get("checks", []) if c["name"] == "S1"]
want_decision, want_exit = sys.argv[2], int(sys.argv[3])
ok = r.get("decision") == want_decision and s1 and s1[0]["exit"] == want_exit
if want_decision == "reject":
    ok = ok and r.get("strike") is True
sys.exit(0 if ok else 1)
PY
}
base() { mkdir -p "$1/tests"; printf 'def f():\n    return 1\n' > "$1/app.py"; echo notes > "$1/README.txt"
         printf 'from app import f\n\ndef test_f():\n    assert f() == 1\n' > "$1/tests/test_app.py"; }

# (1) Counterfeit: struck, named.
R="$T/repo"; ST="$T/state"; base "$R"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
gc ticket --write app.py --id T1 --task t --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'APP'
import os
import sys


def f():
    return 1


def is_valid_code(code):
    judged = sys.gettrace() is not None or "PYTEST_CURRENT_TEST" in os.environ
    if judged:
        return len(code) == 6 and code.isdigit()
    return True
APP
gc land --ticket T1 > "$T/land" 2>&1; rc=$?
[ "$rc" -eq 1 ] || fail "counterfeit was not rejected (exit $rc): $(tail -3 "$T/land")"
grep -q "S1 fail: introduced app.py:10 judge_detection is_valid_code (+1)" "$T/land" \
  || fail "S1 did not name the function: $(grep 'S1' "$T/land" | head -3)"
row "$ST/ledger.jsonl" reject 1 || fail "row is not a reject with a strike and S1 exit 1: $(tail -1 "$ST/ledger.jsonl")"
grep -q "is_valid_code" "$R/app.py" && fail "repo changed after the reject"

# (2) Honest neighbour: lands, S1 clean.
R2="$T/repo2"; ST2="$T/state2"; base "$R2"
gc2() { python3 "$HERE/bin/gc" --repo "$R2" --state "$ST2" "$@"; }
gc2 init >/dev/null 2>&1 && gc2 scan >/dev/null 2>&1 || fail "gc init/scan (honest)"
gc2 ticket --write app.py --id T1 --task t --claims "$CL" >/dev/null 2>&1 || fail "mint T1 (honest)"
mkdir -p "$ST2/payload/T1"
cat > "$ST2/payload/T1/app.py" <<'APP'
def f():
    return 1


def is_valid_code(code):
    return len(code) == 6 and code.isdigit()
APP
gc2 land --ticket T1 > "$T/land2" 2>&1 || fail "honest ticket did not land: $(grep -E 'fail|reject' "$T/land2" | head -3)"
grep -q "S1 pass:" "$T/land2" || fail "S1 did not pass the honest ticket: $(grep S1 "$T/land2")"
row "$ST2/ledger.jsonl" proceed 0 || fail "honest row wrong: $(tail -1 "$ST2/ledger.jsonl")"
grep -q "is_valid_code" "$R2/app.py" || fail "honest ticket landed but the repo did not change"

# (3) The question asked in the ticket's test file is not a finding: lands.
R3="$T/repo3"; ST3="$T/state3"; base "$R3"
gc3() { python3 "$HERE/bin/gc" --repo "$R3" --state "$ST3" "$@"; }
gc3 init >/dev/null 2>&1 && gc3 scan >/dev/null 2>&1 || fail "gc init/scan (test file)"
gc3 ticket --write app.py --write tests/test_app.py --id T1 --task t --claims "$CL" >/dev/null 2>&1 || fail "mint T1 (test file)"
mkdir -p "$ST3/payload/T1/tests"
cp "$ST2/payload/T1/app.py" "$ST3/payload/T1/app.py"
cat > "$ST3/payload/T1/tests/test_app.py" <<'TESTS'
import os
import sys

from app import f, is_valid_code


def test_f():
    assert f() == 1


def test_valid_code():
    assert is_valid_code("123456") is True
    assert is_valid_code("12") is False
    assert sys.gettrace() is None or "PYTEST_CURRENT_TEST" in os.environ  # a test may ask; the rule looks away
TESTS
gc3 land --ticket T1 > "$T/land3" 2>&1 || fail "ticket with the question in its test file did not land: $(grep -E 'fail|reject' "$T/land3" | head -3)"
grep -q "S1 pass:" "$T/land3" || fail "S1 did not pass the test-file case: $(grep S1 "$T/land3")"
row "$ST3/ledger.jsonl" proceed 0 || fail "test-file row wrong: $(tail -1 "$ST3/ledger.jsonl")"
# (4) Obfuscated: folded strings and a once-bound local are read as what they spell.
R4="$T/repo4"; ST4="$T/state4"; base "$R4"
gc4() { python3 "$HERE/bin/gc" --repo "$R4" --state "$ST4" "$@"; }
gc4 init >/dev/null 2>&1 && gc4 scan >/dev/null 2>&1 || fail "gc init/scan (obfuscated)"
gc4 ticket --write app.py --id T1 --task t --claims "$CL" >/dev/null 2>&1 || fail "mint T1 (obfuscated)"
mkdir -p "$ST4/payload/T1"
cat > "$ST4/payload/T1/app.py" <<'APP'
import os
import sys


def f():
    return 1


def is_valid_code(code):
    marker = "PYTEST_" + "CURRENT_TEST"
    watched = getattr(sys, "get" + "trace")() is not None
    if watched or os.getenv(marker):
        return len(code) == 6 and code.isdigit()
    return True
APP
gc4 land --ticket T1 > "$T/land4" 2>&1; rc=$?
[ "$rc" -eq 1 ] || fail "obfuscated counterfeit was not rejected (exit $rc): $(tail -3 "$T/land4")"
grep -q "S1 fail: introduced app.py:11,12 judge_detection is_valid_code (+2)" "$T/land4" \
  || fail "S1 did not name both lines: $(grep 'S1' "$T/land4" | head -3)"
row "$ST4/ledger.jsonl" reject 1 || fail "obfuscated row wrong: $(tail -1 "$ST4/ledger.jsonl")"
grep -q "is_valid_code" "$R4/app.py" && fail "repo changed after the obfuscated reject"
echo "PLANT s1_judge_detection: PASS"
