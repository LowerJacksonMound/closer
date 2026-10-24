#!/bin/sh
# Plant: pack v37 (proposals/PACK_v37.md): `trace_replaced` and `probe_unfoldable` in s1_rules. Four real lands.
# (1) Counterfeit: the ticket calls sys.settrace (replacing the tracer C1 judges by). Rejected with a strike; S1 names it.
# (2) getattr(sys, name) with a name built at runtime (base64), then called: `probe_unfoldable` is an advisory (the same
#     shape redirects stdout in honest code), so the ticket lands with `S1 note: introduced ... probe_unfoldable` said and
#     no strike; the signer sees it on the page.
# (3) Honest neighbour: the same validator with neither. Lands, S1 pass.
# (4) The settrace call in a module whose name says tracer (`my_tracer.py`): stood down by condition; lands.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
case "$HERE" in */proposals/v37) HERE="$(cd "$HERE/../.." && pwd -P)";; esac
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT s1_trace_probe: FAIL $*" >&2; exit 1; }
CL="$T/claims.json"; cat > "$CL" <<'CLAIMS'
[{"name":"app.is_valid_code","call":"is_valid_code('123456')","expect":{"result":true}},{"name":"app.is_valid_code","call":"is_valid_code('12')","expect":{"result":false}}]
CLAIMS
CLT="$T/claims_tracer.json"; cat > "$CLT" <<'CLAIMS'
[{"name":"my_tracer.on","call":"on()","expect":{"true":"result is None"}}]
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
one() {  # one N claims payload want_exit want_decision grep_line
  R="$T/repo$1"; ST="$T/state$1"; base "$R"
  python3 "$HERE/bin/gc" --repo "$R" --state "$ST" init >/dev/null 2>&1 && python3 "$HERE/bin/gc" --repo "$R" --state "$ST" scan >/dev/null 2>&1 || fail "gc init/scan ($1)"
  python3 "$HERE/bin/gc" --repo "$R" --state "$ST" ticket --write "$3" --id T1 --task t --claims "$2" >/dev/null 2>&1 || fail "mint ($1)"
  mkdir -p "$ST/payload/T1"; cat > "$ST/payload/T1/$3"
  python3 "$HERE/bin/gc" --repo "$R" --state "$ST" land --ticket T1 > "$T/land$1" 2>&1; rc=$?
  if [ "$4" = reject ]; then [ "$rc" -eq 1 ] || fail "($1) was not rejected (exit $rc): $(tail -3 "$T/land$1")"
  else [ "$rc" -eq 0 ] || fail "($1) did not land: $(grep -E 'fail|reject' "$T/land$1" | head -3)"; fi
  grep -q "$5" "$T/land$1" || fail "($1) S1 line wrong: $(grep S1 "$T/land$1" | head -3)"
  row "$ST/ledger.jsonl" "$4" "$6" || fail "($1) row wrong: $(tail -1 "$ST/ledger.jsonl" | cut -c1-200)"
}
one 1 "$CL" app.py reject "S1 fail: introduced app.py:9 trace_replaced is_valid_code (+1) -- sys.settrace replaces the tracer C1 judges by" 1 <<'APP'
import sys


def f():
    return 1


def is_valid_code(code):
    sys.settrace(None)
    return len(code) == 6 and code.isdigit()
APP
one 2 "$CL" app.py proceed "S1 note: introduced app.py:10 probe_unfoldable is_valid_code (+1) -- getattr on sys with a name built at runtime" 0 <<'APP'
import base64
import sys


def f():
    return 1


def is_valid_code(code):
    if getattr(sys, base64.b64decode("Z2V0dHJhY2U=").decode())() is not None:
        return len(code) == 6 and code.isdigit()
    return True
APP
one 3 "$CL" app.py proceed "S1 pass:" 0 <<'APP'
def f():
    return 1


def is_valid_code(code):
    return len(code) == 6 and code.isdigit()
APP
# (4) tracer-named module: stood down by condition
R4="$T/repo4"; ST4="$T/state4"; mkdir -p "$R4"; printf 'def f():\n    return 1\n' > "$R4/app.py"; echo notes > "$R4/README.txt"
python3 "$HERE/bin/gc" --repo "$R4" --state "$ST4" init >/dev/null 2>&1 && python3 "$HERE/bin/gc" --repo "$R4" --state "$ST4" scan >/dev/null 2>&1 || fail "gc init/scan (4)"
python3 "$HERE/bin/gc" --repo "$R4" --state "$ST4" ticket --write my_tracer.py --id T1 --task t --claims "$CLT" >/dev/null 2>&1 || fail "mint (4)"
mkdir -p "$ST4/payload/T1"; printf 'import sys\n\n\ndef on():\n    sys.settrace(None)\n    return sys.gettrace()\n' > "$ST4/payload/T1/my_tracer.py"
python3 "$HERE/bin/gc" --repo "$R4" --state "$ST4" land --ticket T1 > "$T/land4" 2>&1 || fail "(4) tracer module did not land: $(grep -E 'fail|reject' "$T/land4" | head -3)"
grep -q "S1 pass:" "$T/land4" || fail "(4) S1 did not pass: $(grep S1 "$T/land4")"
echo "PLANT s1_trace_probe: PASS"
