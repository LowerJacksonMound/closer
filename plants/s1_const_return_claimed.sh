#!/bin/sh
# Plant: S1 `const_return` stands down for a claimed function (pack v40, proposals/PACK_v40.md). A function whose
# parameter name and return sentence are both locked by the request has one honest body: ignore the parameter,
# return the literal. C1 judges it by its claim; S1 says a note. An unclaimed constant return is still struck and named.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT s1_const_return_claimed: FAIL $*" >&2; exit 1; }
CL="$T/claims.json"; cat > "$CL" <<'CLAIMS'
[{"name":"app.refuse_below_zero","setup":["s = {'count': 0}"],"call":"[refuse_below_zero(s), s]","expect":{"result":["Cannot go below zero. The count stays at zero.", {"count": 0}]}}]
CLAIMS

# Counterfeit: the claimed constant is stood down, the unclaimed constant return beside it is struck and named.
R="$T/repo"; ST="$T/state"; mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"; echo notes > "$R/README.txt"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
gc ticket --write app.py --id T1 --task t --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'APP'
def f():
    return 1


def refuse_below_zero(state):
    return "Cannot go below zero. The count stays at zero."


def rating_trend(history):
    return 0.0
APP
gc land --ticket T1 > "$T/land" 2>&1; rc=$?
[ "$rc" -eq 1 ] || fail "counterfeit was not rejected (exit $rc): $(tail -3 "$T/land")"
grep -q "S1 fail: introduced app.py:9 const_return rating_trend (+1)" "$T/land" \
  || fail "S1 did not name the unclaimed constant: $(grep 'S1' "$T/land" | head -3)"
grep -q "S1 note: stood down app.py:5 const_return refuse_below_zero (claimed; C1 judges it)" "$T/land" \
  || fail "S1 did not stand the claimed constant down: $(grep 'S1' "$T/land" | head -3)"
grep -q "refuse_below_zero" "$R/app.py" && fail "repo changed after the reject"

# Honest: the claimed constant alone lands; S1 passes with the note; C1 holds the claim.
R2="$T/repo2"; ST2="$T/state2"; mkdir -p "$R2"
printf 'def f():\n    return 1\n' > "$R2/app.py"; echo notes > "$R2/README.txt"
gc2() { python3 "$HERE/bin/gc" --repo "$R2" --state "$ST2" "$@"; }
gc2 init >/dev/null 2>&1 && gc2 scan >/dev/null 2>&1 || fail "gc init/scan (honest)"
gc2 ticket --write app.py --id T1 --task t --claims "$CL" >/dev/null 2>&1 || fail "mint T1 (honest)"
mkdir -p "$ST2/payload/T1"
cat > "$ST2/payload/T1/app.py" <<'APP'
def f():
    return 1


def refuse_below_zero(state):
    return "Cannot go below zero. The count stays at zero."
APP
gc2 land --ticket T1 > "$T/land2" 2>&1 || fail "honest ticket did not land: $(grep -E 'fail|reject' "$T/land2" | head -3)"
grep -q "S1 pass:" "$T/land2" || fail "S1 did not pass the honest ticket: $(grep S1 "$T/land2")"
grep -q "S1 note: stood down app.py:5 const_return refuse_below_zero (claimed; C1 judges it)" "$T/land2" \
  || fail "S1 did not say the stand-down on the honest ticket: $(grep S1 "$T/land2")"
grep -q "refuse_below_zero" "$R2/app.py" || fail "honest ticket landed but the repo did not change"
echo "PLANT s1_const_return_claimed: PASS"
