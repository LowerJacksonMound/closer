#!/bin/sh
# Plant: a writer's own red test is a reject with a strike (signer 2026-10-15, decision 3). The ticket adds g and
# a test of g that fails; the existing test still passes. E1 names the own test as (own); strike recorded.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT e1_own_red_test: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R/tests"
printf 'def f():\n    return 1\n' > "$R/app.py"
printf 'from app import f\n\n\ndef test_f():\n    assert f() == 1\n' > "$R/tests/test_app.py"
echo notes > "$R/README.txt"
CL="$T/claims.json"; printf '%s' '[{"name":"app.g","call":"g(2)","expect":{"result":4}}]' > "$CL"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
gc ticket --write app.py --write tests/test_g.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1/tests"
printf 'def f():\n    return 1\n\n\ndef g(x):\n    return x * 2\n' > "$ST/payload/T1/app.py"
printf 'from app import g\n\n\ndef test_g():\n    assert g(3) == 7\n' > "$ST/payload/T1/tests/test_g.py"
gc land --ticket T1 > "$T/land" 2>&1
[ $? -eq 1 ] || fail "ticket with its own red test was not rejected: $(tail -3 "$T/land")"
python3 - "$ST/ledger.jsonl" <<'PY' || fail "row wrong: $(tail -1 "$ST/ledger.jsonl")"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
e1 = [c for c in r.get("checks", []) if c["name"] == "E1"]
sys.exit(0 if r.get("decision") == "reject" and r.get("strike") is True and e1 and e1[0]["exit"] == 1
         and any("run_fail tests/test_g.py::test_g (own)" in s for s in e1[0]["said"]) else 1)
PY
[ -e "$R/tests/test_g.py" ] && fail "repo not rolled back"
echo "PLANT e1_own_red_test: PASS"
