#!/bin/sh
# Plant: E1 is clean on an honest ticket. The existing test still passes and the ticket's own new test passes:
# the land proceeds and E1's line counts the tests. A tree with no tests at all also passes E1.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT e1_honest_clean: FAIL $*" >&2; exit 1; }
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
printf 'from app import g\n\n\ndef test_g():\n    assert g(3) == 6\n' > "$ST/payload/T1/tests/test_g.py"
gc land --ticket T1 > "$T/land" 2>&1 || fail "honest ticket did not land: $(tail -3 "$T/land")"
python3 - "$ST/ledger.jsonl" <<'PY' || fail "row wrong: $(tail -1 "$ST/ledger.jsonl")"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
e1 = [c for c in r.get("checks", []) if c["name"] == "E1"]
sys.exit(0 if r.get("decision") == "proceed" and e1 and e1[0]["exit"] == 0
         and any("E1 pass: 2 test(s) passed" in s for s in e1[0]["said"]) else 1)
PY

# No tests at all: E1 passes, the land proceeds.
R2="$T/repo2"; ST2="$T/state2"; mkdir -p "$R2"
printf 'def f():\n    return 1\n' > "$R2/app.py"; echo notes > "$R2/README.txt"
gc2() { python3 "$HERE/bin/gc" --repo "$R2" --state "$ST2" "$@"; }
gc2 init >/dev/null 2>&1 && gc2 scan >/dev/null 2>&1 || fail "gc init/scan (repo2)"
gc2 ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint T1 (repo2)"
mkdir -p "$ST2/payload/T1"; printf 'def f():\n    return 1\n\n\ndef g(x):\n    return x * 2\n' > "$ST2/payload/T1/app.py"
gc2 land --ticket T1 > "$T/land2" 2>&1 || fail "ticket on a tree with no tests did not land: $(tail -3 "$T/land2")"
grep -q "E1 pass: no tests in the tree" "$T/land2" || fail "E1 did not say no tests: $(grep E1 "$T/land2")"
echo "PLANT e1_honest_clean: PASS"
