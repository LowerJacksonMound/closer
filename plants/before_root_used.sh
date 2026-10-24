#!/bin/sh
# Plant: a land judges only what the ticket changes (KERNEL.md M5). Real gc init/scan/ticket/land on a
# repo that already holds a stub. S1 tells pre-existing from introduced through the World's before overlay;
#   T1 changes f and leaves the old stub g alone -> proceed; S1 counts g as pre-existing, not introduced.
#   T2 adds a new stub h -> reject with a strike, S1 names h, and the repo is rolled back.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
GC="$HERE/bin/gc"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f()","expect":{"result":2}}]' > "$CL"
fail() { echo "PLANT before_root_used: FAIL $*" >&2; exit 1; }
gc() { python3 "$GC" --repo "$R" --state "$ST" "$@"; }

R="$T/repo"; ST="$T/state"
mkdir -p "$R"
printf 'def f():\n    return 1\n\n\ndef g():\n    pass\n' > "$R/app.py"
echo notes > "$R/README.txt"  # R6-4 wants one unit with no defs
gc init >/dev/null 2>&1 || fail "gc init"

# row FIELD CHECK: one ledger row's check result, by seq.
said() { python3 - "$ST/ledger.jsonl" "$1" "$2" <<'PY'
import json, sys
row = [json.loads(x) for x in open(sys.argv[1]) if x.strip()][int(sys.argv[2]) - 1]
c = [c for c in row["checks"] if c["name"] == sys.argv[3]][0]
print(c["exit"], " | ".join(c["said"]))
PY
}

gc scan >/dev/null 2>&1 || fail "gc scan"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "gc ticket T1"
mkdir -p "$ST/payload/T1"
printf 'def f():\n    return 2\n\n\ndef g():\n    pass\n' > "$ST/payload/T1/app.py"
gc land --ticket T1 > "$T/land1" 2>&1 || fail "T1 (old stub untouched) did not land: $(tail -3 "$T/land1")"
s1="$(said 1 S1)"
case "$s1" in "0 "*"introduced=0 pre-existing=1"*) ;; *) fail "T1 S1 did not count g as pre-existing: $s1" ;; esac

gc scan >/dev/null 2>&1 || fail "gc rescan"
gc ticket --write app.py --id T2 --claims "$CL" >/dev/null 2>&1 || fail "gc ticket T2"
mkdir -p "$ST/payload/T2"
printf 'def f():\n    return 2\n\n\ndef g():\n    pass\n\n\ndef h():\n    pass\n' > "$ST/payload/T2/app.py"
gc land --ticket T2 > "$T/land2" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "T2 (new stub h) exit $rc, want 1 (reject): $(tail -3 "$T/land2")"
s1="$(said 2 S1)"
case "$s1" in "1 "*h*) ;; *) fail "T2 S1 did not flag the new stub h: $s1" ;; esac
grep -q "def h" "$R/app.py" && fail "T2 rejected but h is still in the repo"
python3 -c 'import json, sys; r = [json.loads(x) for x in open(sys.argv[1]) if x.strip()][1]; sys.exit(0 if r.get("strike") else 1)' \
  "$ST/ledger.jsonl" || fail "T2 rejected without a strike"

echo "PLANT before_root_used: PASS"
