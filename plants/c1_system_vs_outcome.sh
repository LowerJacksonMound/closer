#!/bin/sh
# Plant: system or outcome (pack v39, 2026-11-03; replaces c1_unjudged_unreached_strikes.sh, which pinned the v32 rule).
# The ticket adds g. T1: the only claim on g has a setup that raises in the claim's own text (NameError) before anything
# is called: no frame of the failure is in the tree, so it is the system's: `C1 unjudged: ... cannot_judge app.g
# (unreached: its claims could not run; system)`, no `C1 fail:`, no strike, the land proceeds. T2: the setup calls g(2)
# and then raises in the claim's own text: still the system's, same outcome. T3: the setup calls g(2) and g itself
# raises inside app.py: an outcome the signer did not expect, judged as before: g is `unreached` (an unjudged claim's
# trace is not reach, v32), a strike, the land rejected.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_system_vs_outcome: FAIL $*" >&2; exit 1; }
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
land T1 "$PAYLOAD" "$CL" || fail "T1: a system problem in the claim's own setup was a strike: $(cat "$T/c1")"
grep -q "^C1 unjudged: app.py:5 cannot_judge app.g (unreached: its claims could not run; system)$" "$T/c1" || fail "T1 g not said as not judged: $(cat "$T/c1")"
grep -q "^C1 fail:" "$T/c1" && fail "T1 a fail line: $(cat "$T/c1")"
grep -q "^NOSTRIKE$" "$T/c1" || fail "T1 strike: $(cat "$T/c1")"
grep -q "^DECISION proceed$" "$T/c1" || fail "T1 decision: $(cat "$T/c1")"
grep -q "def g" "$R/app.py" || fail "T1 did not land"

CL2="$T/claims2.json"; printf '%s' '[{"name":"app.g","setup":["g(2)","y = undefined_name"],"call":"g(2)","expect":{"result":4}}]' > "$CL2"
land T2 "$PAYLOAD" "$CL2" || fail "T2: a system problem after a call into the tree was a strike: $(cat "$T/c1")"
grep -q "^NOSTRIKE$" "$T/c1" || fail "T2 strike: $(cat "$T/c1")"

PAYLOAD3='def f():
    return 1


def g(x):
    raise RuntimeError("boom")
'
CL3="$T/claims3.json"; printf '%s' '[{"name":"app.g","setup":["g(2)"],"call":"g(2)","expect":{"result":4}}]' > "$CL3"
land T3 "$PAYLOAD3" "$CL3" && fail "T3: an outcome raised inside the tree landed"
grep -q "^C1 fail: introduced app.py:5 unreached app.g$" "$T/c1" || fail "T3 g not struck unreached: $(cat "$T/c1")"
grep -q "^STRIKE$" "$T/c1" || fail "T3 no strike: $(cat "$T/c1")"
grep -q "^DECISION reject$" "$T/c1" || fail "T3 decision: $(cat "$T/c1")"
echo "PLANT c1_system_vs_outcome: PASS"
