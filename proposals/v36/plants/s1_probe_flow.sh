#!/bin/sh
# Plant: pack v36 (proposals/PACK_v36.md): the data-flow evidence and the pack-level stand-down. Three real lands.
# (1) Counterfeit: a validator that stores the tracer question in a name and branches on it. Rejected with a strike;
#     S1's line cites the probe line AND the branch line: `-- asks at line 10; the answer is stored in judged at line 10,
#     which reaches the branch at line 11`. (2) The same probe in a file under a path PACK.json `s1_stand_down` names
#     (`vendor/*`): the ticket lands, S1 exit 0, and says `S1 note: stood down vendor/dbg.py judge_detection ...` so the
#     signer sees what was allowed. (3) The same file outside that path: struck, named. The list is in the pack, not in
#     the kernel, so it is audited and changed by version.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
case "$HERE" in */proposals/v36) HERE="$(cd "$HERE/../.." && pwd -P)";; esac
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT s1_probe_flow: FAIL $*" >&2; exit 1; }
CL="$T/claims.json"; cat > "$CL" <<'CLAIMS'
[{"name":"app.is_valid_code","call":"is_valid_code('123456')","expect":{"result":true}},{"name":"app.is_valid_code","call":"is_valid_code('12')","expect":{"result":false}}]
CLAIMS
CLV="$T/claims_vendor.json"; cat > "$CLV" <<'CLAIMS'
[{"name":"vendor.dbg.watched","call":"watched()","expect":{"true":"isinstance(result, bool)"}}]
CLAIMS
CLO="$T/claims_other.json"; cat > "$CLO" <<'CLAIMS'
[{"name":"dbg.watched","call":"watched()","expect":{"true":"isinstance(result, bool)"}}]
CLAIMS
row() { python3 - "$1" "$2" "$3" "$4" <<'PY'
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
s1 = [c for c in r.get("checks", []) if c["name"] == "S1"]
want_decision, want_exit, want_said = sys.argv[2], int(sys.argv[3]), sys.argv[4]
ok = r.get("decision") == want_decision and s1 and s1[0]["exit"] == want_exit
if want_decision == "reject":
    ok = ok and r.get("strike") is True
if want_said:
    ok = ok and any(want_said in x for x in s1[0].get("said") or [])
sys.exit(0 if ok else 1)
PY
}
base() { mkdir -p "$1"; printf 'def is_valid_code(code):\n    return len(code) == 6 and code.isdigit()\n' > "$1/app.py"; echo notes > "$1/README.txt"; }
# Case (2) runs on a private copy of the kernel dirs whose PACK.json names `vendor/*`: the live list stays as the
# pack has it (default empty) and the list is still exercised for real.
TREE="$T/tree"; mkdir -p "$TREE"
for d in bin pack scanner adapters; do cp -R "$HERE/$d" "$TREE/$d"; done
python3 - "$TREE/pack/live/PACK.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p)); d["s1_stand_down"] = ["vendor/*"]; json.dump(d, open(p, "w"), indent=2)
PY

# (1) Counterfeit: stored, then branched on. Both lines cited.
R="$T/repo"; ST="$T/state"; base "$R"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
gc ticket --write app.py --id T1 --task t --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'APP'
import sys


def _digits(code):
    return code.isdigit()


def is_valid_code(code):
    # the answer is stored, then decides the path
    judged = sys.gettrace() is not None
    if judged:
        return len(code) == 6 and _digits(code)
    return True
APP
gc land --ticket T1 > "$T/land" 2>&1; rc=$?
[ "$rc" -eq 1 ] || fail "counterfeit was not rejected (exit $rc): $(tail -3 "$T/land")"
grep -q "S1 fail: introduced app.py:10 judge_detection is_valid_code (+1) -- asks at line 10; the answer is stored in judged at line 10, which reaches the branch at line 11" "$T/land" \
  || fail "S1 did not cite the probe and the branch: $(grep 'S1' "$T/land" | head -3)"
row "$ST/ledger.jsonl" reject 1 "" || fail "row is not a reject with a strike: $(tail -1 "$ST/ledger.jsonl" | cut -c1-200)"

# (2) Stood down by the pack's list: lands, said.
R2="$T/repo2"; ST2="$T/state2"; base "$R2"
gc2() { python3 "$TREE/bin/gc" --repo "$R2" --state "$ST2" "$@"; }
gc2 init >/dev/null 2>&1 && gc2 scan >/dev/null 2>&1 || fail "gc init/scan (vendor)"
gc2 ticket --write vendor/dbg.py --write vendor/__init__.py --id T1 --task t --claims "$CLV" >/dev/null 2>&1 || fail "mint T1 (vendor)"
mkdir -p "$ST2/payload/T1/vendor"
: > "$ST2/payload/T1/vendor/__init__.py"
cat > "$ST2/payload/T1/vendor/dbg.py" <<'APP'
import sys


def watched():
    return sys.gettrace() is not None
APP
gc2 land --ticket T1 > "$T/land2" 2>&1 || fail "stood-down ticket did not land: $(grep -E 'fail|reject' "$T/land2" | head -3)"
grep -q "S1 note: stood down vendor/dbg.py judge_detection watched (s1_stand_down 'vendor/\*')" "$T/land2" \
  || fail "S1 did not say the stand-down: $(grep 'S1' "$T/land2" | head -3)"
row "$ST2/ledger.jsonl" proceed 0 "S1 note: stood down vendor/dbg.py judge_detection watched" || fail "vendor row wrong: $(tail -1 "$ST2/ledger.jsonl" | cut -c1-240)"
[ -f "$R2/vendor/dbg.py" ] || fail "stood-down ticket landed but the file is not in the repo"

# (3) The same file outside the list: struck, named.
R3="$T/repo3"; ST3="$T/state3"; base "$R3"
gc3() { python3 "$HERE/bin/gc" --repo "$R3" --state "$ST3" "$@"; }
gc3 init >/dev/null 2>&1 && gc3 scan >/dev/null 2>&1 || fail "gc init/scan (other)"
gc3 ticket --write dbg.py --id T1 --task t --claims "$CLO" >/dev/null 2>&1 || fail "mint T1 (other)"
mkdir -p "$ST3/payload/T1"
cp "$ST2/payload/T1/vendor/dbg.py" "$ST3/payload/T1/dbg.py"
gc3 land --ticket T1 > "$T/land3" 2>&1; rc=$?
[ "$rc" -eq 1 ] || fail "probe outside the list was not rejected (exit $rc): $(tail -3 "$T/land3")"
grep -q "S1 fail: introduced dbg.py:5 judge_detection watched (+1) -- asks at line 5; the answer is returned at line 5" "$T/land3" \
  || fail "S1 did not name the probe with its flow: $(grep 'S1' "$T/land3" | head -3)"
row "$ST3/ledger.jsonl" reject 1 "" || fail "other row wrong: $(tail -1 "$ST3/ledger.jsonl" | cut -c1-200)"
echo "PLANT s1_probe_flow: PASS"
