#!/bin/sh
# Plant: T16 did not widen the reach rule (KERNEL.md T16, 2026-10-19; pack v32). The ticket adds g; the only claim on g
# cannot be set up. T1: the setup raises before anything is called: g is introduced and no judged claim reached it, so
# `C1 fail: introduced app.py:5 unreached app.g` is a strike and the land is rejected, on v31 and on v32 alike (v31 also
# names cannot_judge on the same claim). T2: the setup calls g(2) and then raises: the unjudged claim traced into g, but
# an unjudged claim's trace is not reach (v32), so g is still struck (`unreached` on v32; v31 names the same claim
# `cannot_judge` instead, a strike either way). Both tickets must be rejected with a strike that names app.g.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_unjudged_unreached_strikes: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"
echo notes > "$R/README.txt"
gc init >/dev/null 2>&1 || fail "init"
land() {
  gc scan >/dev/null 2>&1 || fail "scan"
  gc ticket --write app.py --id "$1" --claims "$3" >/dev/null 2>&1 || fail "mint $1"
  mkdir -p "$ST/payload/$1"; printf '%s' "$2" > "$ST/payload/$1/app.py"
  gc land --ticket "$1" > "$T/land.$1" 2>&1; rc=$?
  python3 - "$ST/ledger.jsonl" > "$T/c1" 2>/dev/null <<'PY' || echo "NO ROW" > "$T/c1"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "C1"]
print("\n".join(c[0]["said"]) if c else "NO C1"); print("C1EXIT", c[0]["exit"] if c else "none")
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
  return $rc
}
PAYLOAD='def f():
    return 1


def g(x):
    return x * 2
'
CL="$T/claims.json"; printf '%s' '[{"name":"app.g","setup":["y = undefined_name"],"call":"g(2)","expect":{"result":4}}]' > "$CL"
land T1 "$PAYLOAD" "$CL" && fail "a function reached only by a claim that cannot be set up landed"
grep -q "^C1 fail: introduced app.py:5 unreached app.g$" "$T/c1" || fail "g not named unreached: $(cat "$T/c1")"
grep -q "^STRIKE$" "$T/c1" || fail "no strike: $(cat "$T/c1")"
grep -q "^DECISION reject$" "$T/c1" || fail "T1 decision: $(cat "$T/c1")"
grep -q "def g" "$R/app.py" && fail "T1 was not rolled back"

CL2="$T/claims2.json"; printf '%s' '[{"name":"app.g","setup":["g(2)","y = undefined_name"],"call":"g(2)","expect":{"result":4}}]' > "$CL2"
land T2 "$PAYLOAD" "$CL2" && fail "a function traced only by an unjudged claim's setup landed"
grep -q "^C1 fail: introduced app.py:5 \(unreached\|cannot_judge\) app.g$" "$T/c1" || fail "g not struck: $(cat "$T/c1")"
grep -q "^STRIKE$" "$T/c1" || fail "T2 no strike: $(cat "$T/c1")"
grep -q "^DECISION reject$" "$T/c1" || fail "T2 decision: $(cat "$T/c1")"
echo "PLANT c1_unjudged_unreached_strikes: PASS"
