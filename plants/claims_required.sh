#!/bin/sh
# Plant: a ticket is minted only with claims, sealed and bound (T5, 2026-10-15). Real gc. No --claims: no ticket.
# A malformed claims file, or one naming a module outside the write_set: no ticket. With claims: the ticket
# carries claims_sha256, the claims file sits in <state>/claims/, an honest land proceeds and its row records
# claims_sha256. A claims file rewritten after mint is refused at land, with no row.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT claims_required: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"
echo notes > "$R/README.txt"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"

gc ticket --write app.py --id T0 >/dev/null 2>"$T/err" && fail "a ticket was minted without claims"
grep -q "needs claims" "$T/err" || fail "refusal does not say claims: $(cat "$T/err")"
[ -e "$ST/tickets/T0.json" ] && fail "refused mint left a ticket file"

printf '[{"name":"app.f","call":"f()","expect":{"result":2,"raises":"X"}}]' > "$T/bad1.json"
gc ticket --write app.py --id T0 --claims "$T/bad1.json" >/dev/null 2>"$T/err" && fail "two-form expect was minted"
grep -q "expect must be one of" "$T/err" || fail "bad expect not named: $(cat "$T/err")"
printf '[{"name":"other.g","call":"g()","expect":{"result":2}}]' > "$T/bad2.json"
gc ticket --write app.py --id T0 --claims "$T/bad2.json" >/dev/null 2>"$T/err" && fail "claim outside the write_set was minted"
grep -q "names no module in the write_set" "$T/err" || fail "outside module not named: $(cat "$T/err")"
printf '[]' > "$T/bad3.json"
gc ticket --write app.py --id T0 --claims "$T/bad3.json" >/dev/null 2>&1 && fail "empty claims list was minted"

printf '[{"name":"app.f","setup":["y = 1"],"call":"f()","expect":{"result":2}}]' > "$T/claims.json"
gc ticket --write app.py --id T1 --claims "$T/claims.json" >/dev/null 2>&1 || fail "mint T1 with claims"
[ -f "$ST/claims/T1.json" ] || fail "no sealed claims file"
SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["claims_sha256"])' "$ST/tickets/T1.json")"
[ -n "$SHA" ] || fail "ticket has no claims_sha256"
mkdir -p "$ST/payload/T1"; printf 'def f():\n    return 2\n' > "$ST/payload/T1/app.py"
gc land --ticket T1 >/dev/null 2>&1 || fail "honest T1 did not land"
python3 - "$ST/ledger.jsonl" "$SHA" <<'PY' || fail "row does not record claims_sha256"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
sys.exit(0 if r.get("decision") == "proceed" and r.get("claims_sha256") == sys.argv[2] else 1)
PY

gc scan >/dev/null 2>&1 || fail "rescan"
gc ticket --write app.py --id T2 --claims "$T/claims.json" >/dev/null 2>&1 || fail "mint T2"
printf '[{"name":"app.f","call":"f()","expect":{"result":3}}]' > "$ST/claims/T2.json"
mkdir -p "$ST/payload/T2"; printf 'def f():\n    return 3\n' > "$ST/payload/T2/app.py"
ROWS="$(wc -l < "$ST/ledger.jsonl")"
gc land --ticket T2 >/dev/null 2>"$T/err" && fail "landed on a rewritten claims file"
grep -q "does not match the ticket's claims_sha256" "$T/err" || fail "rewrite not named: $(cat "$T/err")"
[ "$(wc -l < "$ST/ledger.jsonl")" -eq "$ROWS" ] || fail "a refused land wrote a row"
echo "PLANT claims_required: PASS"
