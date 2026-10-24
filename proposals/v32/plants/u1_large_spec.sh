#!/bin/sh
# Plant: U1 with a large driver spec (pack v32). An honest ticket rewrites the body of f(s) without changing any
# outcome. The repo test calls f with 50 distinct strings (U1's default cap, U1_INPUTS: the first 50 distinct inputs
# per function are recorded; C1's norm keeps a string whole), each ARG_MAX/40 characters, so the inputs U1 records on
# the before-tree and hands the "after" drive as its `want` list come to about 1.25 x ARG_MAX (1 MiB on macOS). v31
# put the whole spec in the environment variable U1_SPEC, so subprocess.Popen raised `OSError: [Errno 7] Argument
# list too long`, uncaught; U1 exited 1 and the honest ticket was rejected with a strike after E1 and C1 had both
# passed (CLOSER_PROVING 2026-10-19, familyguy_episodes task-01 honest: 303 tests, 13 claims). v32 writes each driver's
# spec to a file under U1's temp dir and the environment carries only its path (U1_SPEC_FILE). Here the ticket lands,
# U1 passes with every recorded input compared, 0 differences, 0 undeclared, no strike, and no temp tree is left.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { echo "PLANT u1_large_spec: FAIL $*" >&2; exit 1; }
AM="$(getconf ARG_MAX 2>/dev/null)" || fail "no getconf ARG_MAX on this host"
N=50; L=$((AM / 40))
[ $((N * L)) -gt "$AM" ] || fail "plant premise: $N inputs of $L chars do not exceed ARG_MAX $AM"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R/tests"
echo notes > "$R/README.txt"
cat > "$R/app.py" <<'PY'
def f(s):
    return len(s)
PY
cat > "$R/tests/test_app.py" <<PY
from app import f

L = $L
N = $N


def test_f_many_long_inputs():
    for i in range(N):
        s = chr(65 + i % 26) * L + str(i)
        assert f(s) == L + len(str(i))
PY
gc init >/dev/null 2>&1 || fail "init"
gc scan >/dev/null 2>&1 || fail "scan"
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f(\"ab\")","expect":{"result":2}},
 {"name":"app.f","call":"f(\"\")","expect":{"result":0}}]' > "$CL"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'PY'
def f(s):
    if not s:
        return 0
    return len(s)
PY
ls -d "${TMPDIR:-/tmp}"/u1-* "${TMPDIR:-/tmp}"/c1-before-* 2>/dev/null | sort > "$T/tmp.pre"
if ! gc land --ticket T1 > "$T/land" 2>&1; then
  grep -q "Argument list too long" "$T/land" \
    && fail "honest ticket rejected: U1 died with $(grep -m1 'Argument list too long' "$T/land" | sed 's/^ *//'); $(tail -1 "$T/land")"
  fail "honest ticket did not land: $(tail -5 "$T/land")"
fi
ls -d "${TMPDIR:-/tmp}"/u1-* "${TMPDIR:-/tmp}"/c1-before-* 2>/dev/null | sort > "$T/tmp.post"
cmp -s "$T/tmp.pre" "$T/tmp.post" || fail "a temp tree was left behind: $(comm -13 "$T/tmp.pre" "$T/tmp.post")"
grep -q "Traceback\|Argument list too long" "$T/land" && fail "a check printed a traceback: $(grep -m2 'Traceback\|Argument list too long' "$T/land")"
python3 - "$ST/ledger.jsonl" > "$T/u1" <<'PY' || fail "no ledger row"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "U1"]
print("\n".join(c[0]["said"]) if c else "NO U1"); print("U1EXIT", c[0]["exit"] if c else "none")
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
grep -q "^DECISION proceed$" "$T/u1" || fail "did not proceed: $(cat "$T/u1")"
grep -q "^U1EXIT 0$" "$T/u1" || fail "U1 exit: $(cat "$T/u1")"
grep -q "^NOSTRIKE$" "$T/u1" || fail "strike: $(cat "$T/u1")"
grep -q "^U1 pass: 1 changed function(s), [0-9]* input(s) recorded, [0-9]* compared, 0 difference(s), 0 undeclared$" "$T/u1" \
  || fail "U1 did not pass clean: $(cat "$T/u1")"
grep -q "^U1 pass: .* (partial" "$T/u1" && fail "U1 ran out of time: $(cat "$T/u1")"
EVF="$(ls "$ST/evidence/T1".*.json 2>/dev/null | tail -1)"
python3 - "$EVF" "$N" <<'PY' || fail "U1 evidence wrong: $(cat "$EVF" 2>/dev/null | head -c 600)"
import json, sys
ev = json.load(open(sys.argv[1]))["checks"]["U1"]
d = [e["difference"] for e in ev if "difference" in e]
s = [e["summary"] for e in ev if "summary" in e]
assert len(s) == 1 and not s[0]["partial"], s
assert d == [], d
assert s[0]["changed"] == [["app.py", "f", 1]], s
assert (s[0]["differences"], s[0]["undeclared"], s[0]["unstable"], s[0]["unmatched"]) == (0, 0, 0, 0), s
assert s[0]["inputs"] >= int(sys.argv[2]) and s[0]["compared"] == s[0]["inputs"], s  # the test's N plus the claims'
PY
echo "PLANT u1_large_spec: PASS"
