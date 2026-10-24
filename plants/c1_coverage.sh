#!/bin/sh
# Plant: C1 coverage evidence (pack v27, INGREDIENTS 2a): a changed function reached by one claim with one input and no negative is `thin` in the sealed evidence; the same function reached by three claims with distinct inputs and a `raises` claim is not. Both land clean (no strike).
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_coverage: FAIL $*" >&2; exit 1; }
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
clean() {  # the last land proceeded, C1 passed, no strike
  grep -q "^DECISION proceed$" "$T/c1" || fail "ticket $1 did not proceed: $(cat "$T/c1"; tail -3 "$T/land.$1")"
  grep -q "^C1 pass:" "$T/c1" || fail "C1 did not pass on $1: $(cat "$T/c1")"
  grep -q "^NOSTRIKE$" "$T/c1" || fail "strike on $1: $(cat "$T/c1")"
  grep -qw "thin\|coverage\|holds_before" "$T/c1" "$T/land.$1" && fail "coverage evidence reached the row or the land output on $1"
  return 0
}
# cov ID CLAIMS INPUTS NEGATIVE EFFECT THIN: the sealed coverage entry for app.py half
cov() {
  EVF="$(ls "$ST/evidence/$1".*.json 2>/dev/null | tail -1)"
  python3 - "$EVF" "$2" "$3" "$4" "$5" "$6" <<'PY' || fail "coverage on $1 is not claims=$2 inputs=$3 negative=$4 effect=$5 thin=$6: $(cat "$EVF" 2>/dev/null)"
import json, sys
d = json.load(open(sys.argv[1]))
cov = [e["coverage"] for e in d["checks"]["C1"] if "coverage" in e]
h = [c for c in cov if c["file"] == "app.py" and c["qualname"] == "half"]
want = (int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] == "true", sys.argv[5] == "true", sys.argv[6] == "true")
sys.exit(0 if len(h) == 1 and isinstance(h[0]["line"], int) and
         (h[0]["claims"], h[0]["inputs"], h[0]["negative"], h[0]["effect"], h[0]["thin"]) == want else 1)
PY
}
printf 'def half(n):\n    return 0\n' > "$R/app.py"
gc init >/dev/null 2>&1 || fail "init"
CL="$T/claims.json"; printf '%s' '[{"name":"app.half","call":"half(10)","expect":{"result":5}}]' > "$CL"
land T1 'def half(n):
    return n // 2
' "$CL" || fail "one-claim half did not land: $(tail -3 "$T/land.T1")"
clean T1
cov T1 1 1 false false true
CL2="$T/claims2.json"; printf '%s' '[{"name":"app.half","call":"half(10)","expect":{"result":5}},
 {"name":"app.half","call":"half(7)","expect":{"result":3}},
 {"name":"app.half","call":"half(\"x\")","expect":{"raises":"TypeError"}}]' > "$CL2"
land T2 'def half(n):
    if not isinstance(n, int):
        raise TypeError("half wants an int")
    return n // 2
' "$CL2" || fail "three-claim half did not land: $(tail -3 "$T/land.T2")"
clean T2
cov T2 3 3 true false false
echo "PLANT c1_coverage: PASS"
