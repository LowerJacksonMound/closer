#!/bin/sh
# Plant: the reach rule (T5, no exemption). T1 adds g (claimed) and helper, which nothing calls: C1 strikes
# `unreached app.helper`. T2 changes the body of the existing f and claims only g: f is introduced (changed) and
# unreached: strike. T3 adds g that calls helper, and a class whose __init__ runs in the claim's setup: clean.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_unreached: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"
echo notes > "$R/README.txt"
CL="$T/claims.json"; printf '%s' '[{"name":"app.g","call":"g(2)","expect":{"result":4}}]' > "$CL"
gc init >/dev/null 2>&1 || fail "init"
land() {
  gc scan >/dev/null 2>&1 || fail "scan"
  gc ticket --write app.py --id "$1" --claims "$3" >/dev/null 2>&1 || fail "mint $1"
  mkdir -p "$ST/payload/$1"; printf '%s' "$2" > "$ST/payload/$1/app.py"
  gc land --ticket "$1" > "$T/land.$1" 2>&1; rc=$?
  python3 -c 'import json,sys; r=json.loads(open(sys.argv[1]).read().splitlines()[-1]); c=[c for c in r.get("checks",[]) if c["name"]=="C1"]; print("\n".join(c[0]["said"]) if c else "NO C1"); print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))' "$ST/ledger.jsonl" > "$T/c1" 2>/dev/null || echo "NO ROW" > "$T/c1"
  return $rc
}
land T1 'def f():
    return 1


def g(x):
    return x * 2


def helper(x):
    return x + 1
' "$CL" && fail "a ticket with an unreached helper landed"
grep -q "^C1 fail: introduced app.py:9 unreached app.helper$" "$T/c1" || fail "helper not named unreached: $(cat "$T/c1")"
grep -q "unreached app.g" "$T/c1" && fail "the claimed g was called unreached"
grep -q "^STRIKE$" "$T/c1" || fail "no strike"

land T2 'def f():
    return 1 + 0


def g(x):
    return x * 2
' "$CL" && fail "a ticket that changed f without a claim reaching it landed"
grep -q "^C1 fail: introduced app.py:1 unreached app.f$" "$T/c1" || fail "changed f not named unreached: $(cat "$T/c1")"

CL3="$T/claims3.json"; printf '%s' '[{"name":"app.g","call":"g(2)","expect":{"result":4}},{"name":"app.Box.get","setup":["b = Box(5)"],"call":"b.get()","expect":{"result":5}}]' > "$CL3"
land T3 'def f():
    return 1


def helper(x):
    return x + 1


def g(x):
    return helper(x) + x - 1


class Box:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v
' "$CL3" || fail "honest ticket whose claims reach everything did not land: $(cat "$T/c1"; tail -3 "$T/land.T3")"
grep -q "^DECISION proceed$" "$T/c1" || fail "T3 did not proceed"
echo "PLANT c1_unreached: PASS"
