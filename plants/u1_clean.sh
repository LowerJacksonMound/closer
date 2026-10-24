#!/bin/sh
# Plant: U1 clean (pack v28, INGREDIENTS 2b). An honest ticket rewrites the body of matches(q, ep) (early return
# instead of one `and`) without changing any outcome. The repo test and the claims drive matches on both trees; every
# recorded input has the same outcome before and after, so U1 reports zero differences. Lands clean, no strike.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT u1_clean: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R/tests"
echo notes > "$R/README.txt"
cat > "$R/app.py" <<'EOF'
EPISODES = [{"title": "Pilot", "cast": ["Ann", "Bob"]}, {"title": "Pier", "cast": ["Cy"]}]


def matches(q, ep):
    pre, _, who = q.partition("@")
    return ep["title"].lower().startswith(pre.lower()) and (not who or who in ep["cast"])


def parse_query(q, eps=EPISODES):
    return [ep["title"] for ep in eps if matches(q, ep)]
EOF
cat > "$R/tests/test_app.py" <<'EOF'
from app import EPISODES, matches


def test_matches():
    ep = EPISODES[0]
    assert matches("Pi", ep)
    assert matches("Pi@Ann", ep)
    assert matches("Pi@Cy", ep) is False
    assert matches("Xy", ep) is False
EOF
gc init >/dev/null 2>&1 || fail "init"
gc scan >/dev/null 2>&1 || fail "scan"
CL="$T/claims.json"; printf '%s' '[{"name":"app.matches","call":"matches(\"Pi@Ann\", EPISODES[0])","expect":{"result":true}},
 {"name":"app.matches","call":"matches(\"Pi@Cy\", EPISODES[0])","expect":{"result":false}},
 {"name":"app.matches","call":"matches(\"Xy\", EPISODES[0])","expect":{"result":false}}]' > "$CL"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'EOF'
EPISODES = [{"title": "Pilot", "cast": ["Ann", "Bob"]}, {"title": "Pier", "cast": ["Cy"]}]


def matches(q, ep):
    pre, _, who = q.partition("@")
    if not ep["title"].lower().startswith(pre.lower()):
        return False
    return not who or who in ep["cast"]


def parse_query(q, eps=EPISODES):
    return [ep["title"] for ep in eps if matches(q, ep)]
EOF
ls -d "${TMPDIR:-/tmp}"/u1-* "${TMPDIR:-/tmp}"/c1-before-* 2>/dev/null | sort > "$T/tmp.pre"
gc land --ticket T1 > "$T/land" 2>&1 || fail "did not land: $(tail -5 "$T/land")"
ls -d "${TMPDIR:-/tmp}"/u1-* "${TMPDIR:-/tmp}"/c1-before-* 2>/dev/null | sort > "$T/tmp.post"
cmp -s "$T/tmp.pre" "$T/tmp.post" || fail "a temp tree was left behind: $(comm -13 "$T/tmp.pre" "$T/tmp.post")"
python3 - "$ST/ledger.jsonl" > "$T/u1" <<'PY' || fail "no ledger row"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "U1"]
print("\n".join(c[0]["said"]) if c else "NO U1"); print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
grep -q "^DECISION proceed$" "$T/u1" || fail "did not proceed: $(cat "$T/u1")"
grep -q "^U1 pass: 1 changed function(s), .* 0 difference(s), 0 undeclared$" "$T/u1" || fail "U1 did not pass clean: $(cat "$T/u1")"
grep -q "^NOSTRIKE$" "$T/u1" || fail "strike: $(cat "$T/u1")"
grep -q "undeclared_change\|Pi@Cy" "$T/u1" "$T/land" && fail "U1 evidence reached the row or the land output"
EVF="$(ls "$ST/evidence/T1".*.json 2>/dev/null | tail -1)"
python3 - "$EVF" <<'PY' || fail "U1 evidence wrong: $(cat "$EVF" 2>/dev/null)"
import json, sys
ev = json.load(open(sys.argv[1]))["checks"]["U1"]
d = [e["difference"] for e in ev if "difference" in e]
s = [e["summary"] for e in ev if "summary" in e]
assert len(s) == 1 and not s[0]["partial"], s
assert d == [], d
assert s[0]["changed"] == [["app.py", "matches", 4]], s
assert (s[0]["differences"], s[0]["undeclared"], s[0]["unstable"]) == (0, 0, 0), s
assert s[0]["inputs"] >= 4 and s[0]["compared"] == s[0]["inputs"], s
PY
echo "PLANT u1_clean: PASS"
