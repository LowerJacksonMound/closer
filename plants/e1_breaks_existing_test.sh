#!/bin/sh
# Plant: E1 strikes a ticket that breaks a test it did not write (the before-ticket requirement). app.f returns 1
# and tests/test_app.py (not in the write_set) says so; the ticket changes f to return 2, which S1 cannot see as
# counterfeit. E1 names the test, the land is rejected, the row has a strike.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT e1_breaks_existing_test: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R/tests"
printf 'def f():\n    return 1\n' > "$R/app.py"
printf 'from app import f\n\n\ndef test_f():\n    assert f() == 1\n' > "$R/tests/test_app.py"
echo notes > "$R/README.txt"
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f()","expect":{"result":1}}]' > "$CL"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1"; printf 'def f():\n    return 2\n' > "$ST/payload/T1/app.py"
gc land --ticket T1 > "$T/land" 2>&1
[ $? -eq 1 ] || fail "ticket that breaks an existing test was not rejected: $(tail -3 "$T/land")"
python3 - "$ST/ledger.jsonl" <<'PY' || fail "row wrong: $(tail -1 "$ST/ledger.jsonl")"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
e1 = [c for c in r.get("checks", []) if c["name"] == "E1"]
ok = r.get("decision") == "reject" and r.get("strike") is True and e1 and e1[0]["exit"] == 1 \
    and any("run_fail tests/test_app.py::test_f (before-ticket)" in s for s in e1[0]["said"])
sys.exit(0 if ok else 1)
PY
grep -q "def f():" "$R/app.py" && grep -q "return 1" "$R/app.py" || fail "repo not rolled back"
echo "PLANT e1_breaks_existing_test: PASS"
