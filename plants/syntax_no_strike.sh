#!/bin/sh
# Plant: unparseable Python is refused before apply, with no strike (M3, #13). Real gc land. T1's staged file
# does not parse: the land is rejected naming the file and line, no check or verify runs, the repo is
# untouched, and the row has no strike. The same ticket, re-staged with the syntax fixed, lands.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f()","expect":{"result":2}}]' > "$CL"
fail() { echo "PLANT syntax_no_strike: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"
echo notes > "$R/README.txt"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1"

printf 'def f(:\n    return 2\n' > "$ST/payload/T1/app.py"
gc land --ticket T1 >/dev/null 2>&1
[ $? -eq 1 ] || fail "unparseable T1 was not rejected"
python3 - "$ST/ledger.jsonl" <<'PY' || fail "syntax reject row wrong: $(tail -1 "$ST/ledger.jsonl")"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
ok = (not r.get("strike") and r["verify_exit"] is None and not r.get("checks") and r["patch_sha256"] is None
      and any(x.startswith("syntax error app.py:1") and "no strike" in x for x in r["reasons"]))
sys.exit(0 if ok else 1)
PY
grep -q "return 1" "$R/app.py" || fail "rejected syntax error reached the repo"

printf 'def f():\n    return 2\n' > "$ST/payload/T1/app.py"
gc land --ticket T1 > "$T/out" 2>&1 || fail "fixed T1 did not land: $(tail -3 "$T/out")"
grep -q "return 2" "$R/app.py" || fail "fixed T1 landed but the repo did not change"
echo "PLANT syntax_no_strike: PASS"
