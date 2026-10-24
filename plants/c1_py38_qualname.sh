#!/bin/sh
# Plant: the reach rule under a repo interpreter below 3.11 (pack v30). `gc init --python` names a Python 3.8, which
# has no co_qualname: v29's runner recorded a reached method by its bare name (`get`) and struck every changed method
# or nested function `unreached`. v30 resolves the qualname from the file's own syntax tree by (name, first line),
# the first decorator's line when decorated. T1 changes Box.get and Shelf.get (the same short name in two classes),
# a decorated static method Box.twice and a nested function outer.<locals>.inner (so outer too), and its claims
# reach all five: C1 names each reached and held, the land proceeds, the coverage evidence counts each one's claims, and U1 (which
# shares C1's lookup) compares the inputs of both `get`s. T2 changes Box.get and claims only Box.twice: C1 still
# strikes `unreached app.Box.get` by its full name, and nothing else.
# Needs a Python 3.8 with pytest: GC_PLANT_PY38, default the CLOSER_PROVING tqdm-py38 venv.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_py38_qualname: FAIL $*" >&2; exit 1; }
PY38="${GC_PLANT_PY38:-$HOME/Desktop/CLOSER_PROVING/set2/_envs/tqdm-py38/bin/python}"
if [ ! -x "$PY38" ]; then
  if [ -z "${GC_PLANT_PY38:-}" ]; then echo "PLANT c1_py38_qualname: NOT MEASURED — no Python 3.8 with pytest on this machine (set GC_PLANT_PY38 to measure)" >&2; exit 77; fi
  fail "no Python 3.8 at $PY38 (GC_PLANT_PY38)"
fi
"$PY38" -c 'import sys, pytest; assert sys.version_info[:2] == (3, 8)' 2>/dev/null || fail "$PY38 is not a 3.8 with pytest"
"$PY38" -c 'import sys; sys.exit(hasattr(sys._getframe().f_code, "co_qualname"))' || fail "$PY38 has co_qualname"
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R/tests"
echo notes > "$R/README.txt"
cat > "$R/app.py" <<'PYX'
import functools


class Box:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def twice(x):
        return x * 2


class Shelf:
    def __init__(self, items):
        self.items = items

    def get(self, i):
        return self.items[i]


def outer(x):
    def inner(y):
        return y + 1
    return inner(x)
PYX
cat > "$R/tests/test_app.py" <<'PYX'
from app import Box, Shelf, outer


def test_app():
    assert Box(3).get() == 3
    assert Shelf([1, 2]).get(1) == 2
    assert Box.twice(4) == 8
    assert outer(2) == 3
PYX
gc init --python "$PY38" >/dev/null 2>&1 || fail "init --python $PY38"
land() {
  gc scan >/dev/null 2>&1 || fail "scan"
  gc ticket --write app.py --id "$1" --claims "$3" >/dev/null 2>&1 || fail "mint $1"
  mkdir -p "$ST/payload/$1"; printf '%s' "$2" > "$ST/payload/$1/app.py"
  gc land --ticket "$1" > "$T/land.$1" 2>&1; rc=$?
  python3 - "$ST/ledger.jsonl" "$1" > "$T/row.$1" <<'PY' || echo "NO ROW" > "$T/row.$1"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
assert r.get("ticket_id", sys.argv[2]) == sys.argv[2], r.get("ticket_id")
for name in ("C1", "U1"):
    c = [c for c in r.get("checks", []) if c["name"] == name]
    print("\n".join(c[0]["said"]) if c else "NO " + name)
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
PY
  return $rc
}
CL1="$T/claims1.json"; printf '%s' '[{"name":"app.Box.get","setup":["b = Box(5)"],"call":"b.get()","expect":{"result":5}},
 {"name":"app.Shelf.get","setup":["s = Shelf([7, 8])"],"call":"s.get(0)","expect":{"result":7}},
 {"name":"app.Box.twice","call":"Box.twice(21)","expect":{"result":42}},
 {"name":"app.outer","call":"outer(2)","expect":{"result":3}}]' > "$CL1"
land T1 'import functools


class Box:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v if self.v is not None else 0

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def twice(x):
        return x + x


class Shelf:
    def __init__(self, items):
        self.items = items

    def get(self, i):
        return self.items[i] if 0 <= i < len(self.items) else None


def outer(x):
    def inner(y):
        return 1 + y
    return inner(x)
' "$CL1" || fail "honest ticket under 3.8 did not land: $(grep -E '^(C1|E1|U1)' "$T/land.T1"; tail -3 "$T/land.T1")"
grep -q "^DECISION proceed$" "$T/row.T1" || fail "T1 did not proceed: $(cat "$T/row.T1")"
grep -q "unreached" "$T/land.T1" && fail "T1: C1 named a reached function unreached: $(grep unreached "$T/land.T1")"
grep -q "^C1 pass: 4 claim(s) held on 4 function(s)" "$T/land.T1" || fail "T1: C1 pass line wrong: $(grep '^C1' "$T/land.T1")"
EVF="$(ls "$ST/evidence/T1".*.json 2>/dev/null | tail -1)"
python3 - "$EVF" <<'PY' || fail "T1 evidence wrong: $(cat "$EVF" 2>/dev/null)"
import json, sys
ev = json.load(open(sys.argv[1]))["checks"]
cov = {e["coverage"]["qualname"]: e["coverage"] for e in ev["C1"] if "coverage" in e}
want = {"Box.get": 8, "Box.twice": 13, "Shelf.get": 21, "outer": 25, "outer.<locals>.inner": 26}  # outer holds inner
assert {q: cov[q]["line"] for q in want if q in cov} == want, cov
assert all(cov[q]["claims"] == 1 for q in want), cov
s = [e["summary"] for e in ev["U1"] if "summary" in e]
assert len(s) == 1 and not s[0]["partial"], s
assert sorted(map(tuple, s[0]["changed"])) == sorted([("app.py", q, ln) for q, ln in want.items()]), s
assert s[0]["inputs"] >= 5 and s[0]["compared"] == s[0]["inputs"], s  # both gets recorded by full name
assert (s[0]["differences"], s[0]["unstable"]) == (0, 0), s
PY
CL2="$T/claims2.json"; printf '%s' '[{"name":"app.Box.twice","call":"Box.twice(21)","expect":{"result":42}}]' > "$CL2"
land T2 'import functools


class Box:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v if self.v is not None else -1

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def twice(x):
        return x + x


class Shelf:
    def __init__(self, items):
        self.items = items

    def get(self, i):
        return self.items[i] if 0 <= i < len(self.items) else None


def outer(x):
    def inner(y):
        return 1 + y
    return inner(x)
' "$CL2"
[ $? -eq 1 ] || fail "T2 (changed Box.get, no claim reaches it) was not rejected: $(cat "$T/row.T2")"
grep -q "^STRIKE$" "$T/row.T2" || fail "T2 no strike: $(cat "$T/row.T2")"
grep -q "^C1 fail: introduced app.py:8 unreached app.Box.get$" "$T/row.T2" || fail "T2 strike not by full name: $(cat "$T/row.T2")"
[ "$(grep -c "unreached" "$T/row.T2")" -eq 1 ] || fail "T2 struck more than Box.get: $(grep unreached "$T/row.T2")"
echo "PLANT c1_py38_qualname: PASS"
