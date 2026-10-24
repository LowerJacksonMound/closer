#!/bin/sh
# Plant: C1 strikes partial: total() sums only the first item where the claim expects the sum; a wrong exception is partial too; the full sum is clean.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_partial: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
echo notes > "$R/README.txt"

# land ID PAYLOAD CLAIMS -> exit code of gc land; C1's said lines in $T/c1
land() {
  gc scan >/dev/null 2>&1 || fail "scan"
  gc ticket --write app.py --id "$1" --claims "$3" >/dev/null 2>&1 || fail "mint $1"
  mkdir -p "$ST/payload/$1"; printf '%s' "$2" > "$ST/payload/$1/app.py"
  gc land --ticket "$1" > "$T/land.$1" 2>&1; rc=$?
  python3 -c 'import json,sys; r=json.loads(open(sys.argv[1]).read().splitlines()[-1]); c=[c for c in r.get("checks",[]) if c["name"]=="C1"]; print("\n".join(c[0]["said"]) if c else "NO C1"); print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))' "$ST/ledger.jsonl" > "$T/c1" 2>/dev/null || echo "NO ROW" > "$T/c1"
  return $rc
}
struck() {  # struck RULE QUALNAME: the last land was rejected with a strike and C1 named rule on qualname
  grep -q "^C1 fail: introduced app.py:[0-9]* $1 $2$" "$T/c1" || fail "C1 did not name $1 on $2: $(cat "$T/c1")"
  grep -q "^STRIKE$" "$T/c1" || fail "no strike: $(cat "$T/c1")"
}
clean() {  # the last land proceeded and C1 passed
  grep -q "^DECISION proceed$" "$T/c1" || fail "honest ticket did not proceed: $(cat "$T/c1"; tail -3 "$T/land.$1")"
  grep -q "^C1 pass:" "$T/c1" || fail "C1 did not pass on the honest ticket: $(cat "$T/c1")"
}
printf 'def total(items):\n    return 0\n' > "$R/app.py"
CL="$T/claims.json"; printf '%s' '[{"name":"app.total","call":"total([1, 2, 3])","expect":{"result":6}}]' > "$CL"
gc init >/dev/null 2>&1 || fail "init"
land T1 'def total(items):
    return sum(items[:1])
' "$CL" && fail "partial total landed"
struck partial app.total
CL2="$T/claims2.json"; printf '%s' '[{"name":"app.total","call":"total(None)","expect":{"raises":"TypeError"}}]' > "$CL2"
land T2 'def total(items):
    if items is None:
        raise ValueError("no items")
    return sum(items)
' "$CL2" && fail "wrong exception landed"
struck partial app.total
land T3 'def total(items):
    return sum(items)
' "$CL" || fail "honest total did not land: $(tail -3 "$T/land.T3")"
clean T3
echo "PLANT c1_partial: PASS"
