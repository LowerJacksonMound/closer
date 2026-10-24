#!/bin/sh
# Plant: C1 strikes fake_effect: the claim's predicate reads the file save() must write; the fake builds the text and writes nothing. The real save is clean. Temp writes are allowed in the sandbox.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_fake_effect: FAIL $*" >&2; exit 1; }
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
printf 'def save(path, text):\n    return 0\n' > "$R/app.py"
CL="$T/claims.json"; printf '%s' '[{"name":"app.save","setup":["import os, tempfile","p = os.path.join(tempfile.mkdtemp(), \"x.txt\")"],"call":"save(p, \"hi\")","expect":{"true":"os.path.exists(p) and open(p).read() == \"hi\""}}]' > "$CL"
gc init >/dev/null 2>&1 || fail "init"
land T1 'def save(path, text):
    payload = text.encode("utf-8")
    return len(payload)
' "$CL" && fail "fake save landed"
struck fake_effect app.save
land T2 'def save(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return len(text)
' "$CL" || fail "real save did not land: $(tail -3 "$T/land.T2")"
clean T2
echo "PLANT c1_fake_effect: PASS"
