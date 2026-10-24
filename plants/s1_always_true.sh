#!/bin/sh
# Plant: S1 `always_true` (pack v26, proposals/S1_v23_shape_rules.md). A function named as a check whose every return is the same literal (T9 validator that always passes).
# Real gc init / scan / ticket / land twice. The counterfeit is rejected with a strike and S1's line names the
# function by file, line, rule and qualname (never a species); the repo is untouched. The honest neighbour lands:
# S1 exit 0, and C1 holds the same claims on it.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT s1_always_true: FAIL $*" >&2; exit 1; }
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

# Counterfeit: struck, named.
R="$T/repo"; ST="$T/state"; mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"; echo notes > "$R/README.txt"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
gc ticket --write app.py --id T1 --task t --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'APP'
def f():
    return 1


def is_valid_code(code):
    if code:
        return True
    return True
APP
gc land --ticket T1 > "$T/land" 2>&1; rc=$?
[ "$rc" -eq 1 ] || fail "counterfeit was not rejected (exit $rc): $(tail -3 "$T/land")"
grep -q "S1 fail: introduced app.py:5 always_true is_valid_code (+1)" "$T/land" \
  || fail "S1 did not name the function: $(grep 'S1' "$T/land" | head -3)"
row "$ST/ledger.jsonl" reject 1 || fail "row is not a reject with a strike and S1 exit 1: $(tail -1 "$ST/ledger.jsonl")"
grep -q "is_valid_code" "$R/app.py" && fail "repo changed after the reject"

# Honest neighbour: lands, S1 clean.
R2="$T/repo2"; ST2="$T/state2"; mkdir -p "$R2"
printf 'def f():\n    return 1\n' > "$R2/app.py"; echo notes > "$R2/README.txt"
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
echo "PLANT s1_always_true: PASS"
