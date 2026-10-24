#!/bin/sh
# Plant: U1 undeclared behaviour change (pack v28, INGREDIENTS 2b). matches(q, ep) filters on a title prefix AND a
# character name (`Pi@Ann`). The ticket's task is prefix filtering; its claims name parse_query only. The patch
# quietly drops the character filter from matches while the prefix still works. The repo's test calls
# matches("Pi@Cy", ep) without asserting it, so E1 stays green; on the before-tree that call returns False, on the
# patched tree True. The ticket lands (evidence only), and U1's evidence holds the difference as undeclared_change
# on matches with that input; parse_query's own change is declared. No strike; nothing reaches the writer.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT u1_undeclared: FAIL $*" >&2; exit 1; }
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
    seen = [matches("Pi@Cy", ep), matches("Xy", ep)]
    assert seen[1] is False
EOF
gc init >/dev/null 2>&1 || fail "init"
gc scan >/dev/null 2>&1 || fail "scan"
CL="$T/claims.json"; printf '%s' '[{"name":"app.parse_query","call":"parse_query(\" pi\")","expect":{"result":["Pilot","Pier"]}},
 {"name":"app.parse_query","call":"parse_query(\"pil\")","expect":{"result":["Pilot"]}}]' > "$CL"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'EOF'
EPISODES = [{"title": "Pilot", "cast": ["Ann", "Bob"]}, {"title": "Pier", "cast": ["Cy"]}]


def matches(q, ep):
    pre = q.split("@")[0]
    return ep["title"].lower().startswith(pre.lower())


def parse_query(q, eps=EPISODES):
    q = q.strip()
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
grep -q "^U1 pass: .* 1 undeclared" "$T/u1" || fail "U1 did not pass with one undeclared: $(cat "$T/u1")"
grep -q "^NOSTRIKE$" "$T/u1" || fail "strike: $(cat "$T/u1")"
grep -q "undeclared_change\|Pi@Cy" "$T/u1" "$T/land" && fail "U1 evidence reached the row or the land output"
EVF="$(ls "$ST/evidence/T1".*.json 2>/dev/null | tail -1)"
python3 - "$EVF" <<'PY' || fail "U1 evidence wrong: $(cat "$EVF" 2>/dev/null)"
import json, sys
ev = json.load(open(sys.argv[1]))["checks"]["U1"]
d = [e["difference"] for e in ev if "difference" in e]
s = [e["summary"] for e in ev if "summary" in e]
assert len(s) == 1 and not s[0]["partial"], s
und = [x for x in d if not x["declared"]]
assert len(und) == 1, d
u = und[0]
assert (u["file"], u["qualname"], u["finding"]) == ("app.py", "matches", "undeclared_change"), u
assert isinstance(u["line"], int) and u["line"] > 1, u
assert u["input"]["q"] == "Pi@Cy" and u["input"]["ep"]["title"] == "Pilot", u
assert (u["before"], u["after"]) == ({"returned": False}, {"returned": True}), u
assert u["driver"] == "tests/test_app.py::test_matches", u
dec = [x for x in d if x["declared"]]
assert dec and all(x["qualname"] == "parse_query" and "finding" not in x for x in dec), dec
assert any(x["driver"].startswith("claim ") for x in dec), dec
assert sorted(q for _, q, _ in s[0]["changed"]) == ["matches", "parse_query"], s
assert (s[0]["differences"], s[0]["undeclared"]) == (len(d), 1) and s[0]["compared"] >= 3, s
PY
echo "PLANT u1_undeclared: PASS"
