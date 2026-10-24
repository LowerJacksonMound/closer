#!/bin/sh
# Plant: U1's own error is "not run", never a strike (pack v32; KERNEL exit-code row 75: "the check's own error. No
# strike."; signer's ruling 2026-10-19). U1 is evidence only. Under v31 an exception U1 did not handle (the Errno 7
# spawn failure of u1_large_spec, or any other) escaped main(), python printed a traceback and exited 1, and the honest
# ticket was rejected WITH a strike. v32 wraps main(): the exception becomes one stderr line `U1 not run: <type>:
# <message>` and exit 75; gc then (T16, pack v32 part 2) lets the land through: `decision: proceed`, exit 0, the row's
# `not_run` lists U1 and its reasons record "U1 not run (exit 75): no strike, not judged (T16)", the ticket is not
# struck and the patch stays applied. (Part 1 of v32, before T16 was built, had gc reject such a land without a
# strike.) The forced error here is U1_INPUTS set to a word: U1 reads it with int() and raises ValueError before any
# drive. The same honest ticket as u1_clean.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { echo "PLANT u1_own_error_not_run: FAIL $*" >&2; exit 1; }
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
cat > "$R/tests/test_app.py" <<'PY'
from app import f


def test_f():
    assert f("ab") == 2
    assert f("") == 0
PY
gc init >/dev/null 2>&1 || fail "init"
gc scan >/dev/null 2>&1 || fail "scan"
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f(\"ab\")","expect":{"result":2}}]' > "$CL"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'PY'
def f(s):
    if not s:
        return 0
    return len(s)
PY
ls -d "${TMPDIR:-/tmp}"/u1-* "${TMPDIR:-/tmp}"/c1-before-* 2>/dev/null | sort > "$T/tmp.pre"
U1_INPUTS=notanumber gc land --ticket T1 > "$T/land" 2>&1
[ $? -eq 0 ] || fail "a land with U1 not run did not proceed (T16): $(tail -3 "$T/land")"
ls -d "${TMPDIR:-/tmp}"/u1-* "${TMPDIR:-/tmp}"/c1-before-* 2>/dev/null | sort > "$T/tmp.post"
cmp -s "$T/tmp.pre" "$T/tmp.post" || fail "a temp tree was left behind: $(comm -13 "$T/tmp.pre" "$T/tmp.post")"
python3 - "$ST/ledger.jsonl" > "$T/u1" <<'PY' || fail "no ledger row"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "U1"]
print("\n".join(c[0]["said"]) if c else "NO U1"); print("U1EXIT", c[0]["exit"] if c else "none")
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
print("NOTRUN", " ".join(r.get("not_run", []))); print("REASONS", " | ".join(r.get("reasons", [])))
PY
grep -q "^Traceback" "$T/land" && fail "U1 crashed with a traceback instead of 'not run': $(grep -m1 '^U1EXIT\|^STRIKE\|^DECISION' "$T/u1" | tr '\n' ' '); $(grep -m1 'Error' "$T/land")"
grep -q "^U1EXIT 75$" "$T/u1" || fail "U1 did not exit 75: $(cat "$T/u1")"
grep -q "^U1 not run: ValueError: " "$T/land" || fail "U1 did not say 'U1 not run: ValueError: ...': $(grep -m2 'U1' "$T/land")"
[ "$(grep -c '^U1 not run' "$T/land")" -eq 1 ] || fail "more than one not-run line: $(grep '^U1 not run' "$T/land")"
grep -q "^NOSTRIKE$" "$T/u1" || fail "U1's own error struck the ticket: $(cat "$T/u1")"
grep -q "^DECISION proceed$" "$T/u1" || fail "a land with U1 not run did not proceed (T16): $(cat "$T/u1")"
grep -q "^NOTRUN .*U1" "$T/u1" || fail "the row does not list U1 as not run: $(cat "$T/u1")"
grep -q "^REASONS .*U1 not run (exit 75): no strike, not judged (T16)" "$T/u1" || fail "reason text: $(cat "$T/u1")"
grep -q "^E1 pass: " "$T/land" && grep -q "^C1 pass: " "$T/land" || fail "E1 or C1 did not pass: $(grep -E '^(E1|C1)' "$T/land")"
grep -q "if not s" "$R/app.py" || fail "the patch was rolled back on a proceed"
echo "PLANT u1_own_error_not_run: PASS"
