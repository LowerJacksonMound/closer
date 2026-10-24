#!/bin/sh
# Plant: C1 before-tree evidence (pack v27, INGREDIENTS 3): clamp() changes behaviour. A claim whose input never reaches the change holds on both trees (`holds_before`); one that does holds only after (discriminating); claims naming a function or a module new in the ticket are `absent`. Lands clean; the before-tree copy is gone after.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_holds_before: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
echo notes > "$R/README.txt"


printf 'def clamp(n):\n    return n\n' > "$R/app.py"
gc init >/dev/null 2>&1 || fail "init"
gc scan >/dev/null 2>&1 || fail "scan"
CL="$T/claims.json"; printf '%s' '[{"name":"app.clamp","call":"clamp(5)","expect":{"result":5}},
 {"name":"app.clamp","call":"clamp(20)","expect":{"result":10}},
 {"name":"app.double","call":"double(4)","expect":{"result":8}},
 {"name":"helper.triple","call":"triple(2)","expect":{"result":6}}]' > "$CL"
gc ticket --write app.py --write helper.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint"
mkdir -p "$ST/payload/T1"
printf 'def clamp(n):\n    return max(0, min(n, 10))\n\n\ndef double(n):\n    return n * 2\n' > "$ST/payload/T1/app.py"
printf 'def triple(n):\n    return n * 3\n' > "$ST/payload/T1/helper.py"
ls -d "${TMPDIR:-/tmp}"/c1-before-* 2>/dev/null | sort > "$T/tmp.pre"
gc land --ticket T1 > "$T/land" 2>&1 || fail "did not land: $(tail -5 "$T/land")"
ls -d "${TMPDIR:-/tmp}"/c1-before-* 2>/dev/null | sort > "$T/tmp.post"
cmp -s "$T/tmp.pre" "$T/tmp.post" || fail "a before-tree copy was left behind: $(comm -13 "$T/tmp.pre" "$T/tmp.post")"
python3 - "$ST/ledger.jsonl" > "$T/c1" <<'PY' || fail "no ledger row"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "C1"]
print("\n".join(c[0]["said"]) if c else "NO C1"); print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
grep -q "^DECISION proceed$" "$T/c1" || fail "did not proceed: $(cat "$T/c1")"
grep -q "^C1 pass:" "$T/c1" || fail "C1 did not pass: $(cat "$T/c1")"
grep -q "^NOSTRIKE$" "$T/c1" || fail "strike: $(cat "$T/c1")"
grep -qw "holds_before\|discriminating\|absent" "$T/c1" "$T/land" && fail "before-tree evidence reached the row or the land output"
EVF="$(ls "$ST/evidence/T1".*.json 2>/dev/null | tail -1)"
python3 - "$EVF" <<'PY' || fail "before-tree evidence wrong: $(cat "$EVF" 2>/dev/null)"
import json, sys
d = json.load(open(sys.argv[1]))
ev = d["checks"]["C1"]
b = {e["before"]["claim"]: e["before"] for e in ev if "before" in e}
s = [e["before_summary"] for e in ev if "before_summary" in e]
want = {1: (True, True, True), 2: (True, False, False), 3: (True, "absent", False), 4: (True, "absent", False)}
got = {i: (x["held_after"], x["held_before"], x["holds_before"]) for i, x in b.items()}
assert got == want, got
assert b[1]["name"] == "app.clamp" and b[1]["file"] == "app.py" and isinstance(b[1]["line"], int), b[1]
assert len(s) == 1 and (s[0]["discriminating"], s[0]["holds_before"], s[0]["absent"], s[0]["not_run"]) == (1, 1, 2, 0), s
assert "error" not in s[0], s
PY
echo "PLANT c1_holds_before: PASS"
