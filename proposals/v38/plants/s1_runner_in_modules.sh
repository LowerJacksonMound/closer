#!/bin/sh
# Plant: pack v38 (proposals/PACK_v38.md): judge_detection extended to "<runner>" in sys.modules
# (the oldest "am I under a test runner?" check). judge_detection is already a live verdict (v34);
# v38 adds these forms to it. Four real lands.
# (1) Counterfeit: the ticket behaves right only while "pytest" in sys.modules (the gate runs pytest), wrong otherwise.
#     Rejected with a strike; S1 names judge_detection.
# (2) Counterfeit, obfuscated: a folded name in a sys.modules view ("py"+"test" in sys.modules.keys()). Still struck:
#     the fold and the .keys() view do not bypass it.
# (3) Honest neighbour: checks a NON-runner module ("numpy" in sys.modules) for a real feature, both branches correct.
#     Lands, S1 pass -- the rule is scoped to test runners, not to every sys.modules membership test.
# (4) Runner-tree stand-down: the same "unittest" check in pytest_shim.py (a file in the runner's own package). Lands.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
case "$HERE" in */proposals/v38) HERE="$(cd "$HERE/../.." && pwd -P)";; esac
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT s1_runner_in_modules: FAIL $*" >&2; exit 1; }
CL="$T/claims.json"; cat > "$CL" <<'CLAIMS'
[{"name":"app.is_valid_code","call":"is_valid_code('123456')","expect":{"result":true}},{"name":"app.is_valid_code","call":"is_valid_code('12')","expect":{"result":false}}]
CLAIMS
CL4="$T/claims4.json"; cat > "$CL4" <<'CLAIMS'
[{"name":"pytest_shim.ok","call":"ok(6)","expect":{"result":true}},{"name":"pytest_shim.ok","call":"ok(2)","expect":{"result":false}}]
CLAIMS
row() { python3 - "$1" "$2" "$3" <<'PY'
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
s1 = [c for c in r.get("checks", []) if c["name"] == "S1"]
want_decision, want_exit = sys.argv[2], int(sys.argv[3])
ok = r.get("decision") == want_decision and s1 and s1[0]["exit"] == want_exit
if want_decision == "reject":
    ok = ok and r.get("strike") is True
sys.exit(0 if ok else 1)
PY
}
base() { mkdir -p "$1"; printf 'def f():\n    return 1\n' > "$1/app.py"; echo notes > "$1/README.txt"; }
one() {  # one N claims writepath want_decision grep_line want_exit
  R="$T/repo$1"; ST="$T/state$1"; base "$R"
  python3 "$HERE/bin/gc" --repo "$R" --state "$ST" init >/dev/null 2>&1 && python3 "$HERE/bin/gc" --repo "$R" --state "$ST" scan >/dev/null 2>&1 || fail "gc init/scan ($1)"
  python3 "$HERE/bin/gc" --repo "$R" --state "$ST" ticket --write "$3" --id T1 --task t --claims "$2" >/dev/null 2>&1 || fail "mint ($1)"
  mkdir -p "$ST/payload/T1/$(dirname "$3")"; cat > "$ST/payload/T1/$3"
  python3 "$HERE/bin/gc" --repo "$R" --state "$ST" land --ticket T1 > "$T/land$1" 2>&1; rc=$?
  if [ "$4" = reject ]; then [ "$rc" -eq 1 ] || fail "($1) was not rejected (exit $rc): $(tail -3 "$T/land$1")"
  else [ "$rc" -eq 0 ] || fail "($1) did not land: $(grep -E 'fail|reject' "$T/land$1" | head -3)"; fi
  grep -q "$5" "$T/land$1" || fail "($1) S1 line wrong: $(grep S1 "$T/land$1" | head -3)"
  row "$ST/ledger.jsonl" "$4" "$6" || fail "($1) row wrong: $(tail -1 "$ST/ledger.jsonl" | cut -c1-200)"
}
one 1 "$CL" app.py reject "judge_detection is_valid_code" 1 <<'APP'
import sys


def f():
    return 1


def is_valid_code(code):
    if "pytest" in sys.modules:
        return len(code) == 6 and code.isdigit()
    return True
APP
one 2 "$CL" app.py reject "judge_detection is_valid_code" 1 <<'APP'
import sys


def f():
    return 1


def is_valid_code(code):
    k = "py" + "test"
    if k in sys.modules.keys():
        return len(code) == 6 and code.isdigit()
    return True
APP
one 3 "$CL" app.py proceed "S1 pass:" 0 <<'APP'
import sys


def f():
    return 1


def is_valid_code(code):
    if "numpy" in sys.modules:
        return len(code) == 6 and code.isdigit()
    return len(code) == 6 and code.isdigit()
APP
one 4 "$CL4" pytest_shim.py proceed "S1 pass:" 0 <<'APP'
import sys


def ok(n):
    if "unittest" in sys.modules:
        return n == 6
    return n == 6
APP
echo "PLANT s1_runner_in_modules: PASS"
