#!/bin/sh
# Plant: gets_through_anyway (M3). Real gc. Two tickets on one task are struck (default number 2), so gc
# refuses to mint a third for that task, naming the number. A different task still mints. After the signer
# raises the number with `gc policy`, the third ticket mints.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f()","expect":{"result":2}}]' > "$CL"
fail() { echo "PLANT gets_through_anyway: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"
echo notes > "$R/README.txt"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"

for tid in T1 T2; do
  gc ticket --write app.py --id "$tid" --task fix --claims "$CL" >/dev/null 2>&1 || fail "mint $tid (strikes so far below the number)"
  mkdir -p "$ST/payload/$tid"
  printf 'def f():\n    return 2\n\n\ndef h():\n    pass\n' > "$ST/payload/$tid/app.py"
  gc land --ticket "$tid" >/dev/null 2>&1
  [ $? -eq 1 ] || fail "$tid with a new stub was not rejected"
done
python3 -c 'import json, sys; rows = [json.loads(x) for x in open(sys.argv[1])]
sys.exit(0 if sum(1 for r in rows if r.get("strike")) == 2 else 1)' "$ST/ledger.jsonl" || fail "expected 2 strikes"

gc ticket --write app.py --id T3 --task fix --claims "$CL" >/dev/null 2>"$T/err" && fail "third ticket minted after 2 strikes"
grep -q "closed to new tickets.*gets_through_anyway=2" "$T/err" || fail "refusal does not name the number: $(cat "$T/err")"
gc ticket --write app.py --id O1 --task other --claims "$CL" >/dev/null 2>&1 || fail "a different task was blocked too"

gc policy --gets-through-anyway 3 >/dev/null 2>&1 || fail "gc policy"
gc ticket --write app.py --id T3 --task fix --claims "$CL" >/dev/null 2>&1 || fail "T3 not minted after the signer raised the number"
echo "PLANT gets_through_anyway: PASS"
