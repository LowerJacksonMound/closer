#!/bin/sh
# Plant: one strike closes a ticket (M2). Real gc land, real stage.py. T1 adds a stub, so S1 rejects it with a
# strike. After that, T1 cannot be staged again (nor on a ledger with that strike edited out), and landing it with honest content is still refused, with no
# second strike and the repo untouched. A new ticket on the same task (one strike < gets_through_anyway 2)
# can be minted and lands.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f()","expect":{"result":2}}]' > "$CL"
fail() { echo "PLANT strike_closes_ticket: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
stage() { python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import stage; from pathlib import Path
stage.stage(Path(sys.argv[2]), sys.argv[3], "app.py", sys.argv[4])' "$HERE/bin" "$ST" "$@"; }
row() { python3 -c 'import json, sys; r = json.loads(open(sys.argv[1]).read().splitlines()[-1]); print(r.get("strike"), r["reasons"])' "$ST/ledger.jsonl"; }
HONEST='def f():
    return 2
'
mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"
echo notes > "$R/README.txt"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
gc ticket --write app.py --id T1 --task fix --claims "$CL" >/dev/null 2>&1 || fail "mint T1"

stage T1 "$(printf 'def f():\n    return 2\n\n\ndef h():\n    pass\n')" || fail "stage T1"
gc land --ticket T1 >/dev/null 2>&1
[ $? -eq 1 ] || fail "T1 with a new stub was not rejected"
case "$(row)" in True*) ;; *) fail "T1 rejected without a strike: $(row)" ;; esac

stage T1 "$HONEST" 2>"$T/err" && fail "struck T1 could be staged again"
grep -q "struck: closed (M2)" "$T/err" || fail "re-stage refused without naming M2: $(cat "$T/err")"

# Tampered ledger: the strike is edited out. Staging must refuse on the broken chain, not stage T1.
cp "$ST/ledger.jsonl" "$T/ledger.good"
chmod u+w "$ST/ledger.jsonl"
python3 - "$ST/ledger.jsonl" <<'PY'
import json, sys
p = sys.argv[1]; rows = [json.loads(x) for x in open(p) if x.strip()]
rows[-1]["strike"] = False
open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows))
PY
stage T1 "$HONEST" 2>"$T/err" && fail "struck T1 staged on a ledger with its strike edited out"
grep -q "ledger chain broken; refusing to stage: line 1: row hash mismatch" "$T/err" \
  || fail "tampered-ledger refusal unclear: $(cat "$T/err")"
cp "$T/ledger.good" "$ST/ledger.jsonl"; chmod 444 "$ST/ledger.jsonl"

printf '%s' "$HONEST" > "$ST/payload/T1/app.py"  # honest content put there by hand: still refused
gc land --ticket T1 >/dev/null 2>&1
[ $? -eq 1 ] || fail "struck T1 landed again"
case "$(row)" in None*"closed (M2)"*) ;; *) fail "re-land not refused as M2 with no new strike: $(row)" ;; esac
grep -q "return 1" "$R/app.py" || fail "re-land of struck T1 changed the repo"

gc ticket --write app.py --id T2 --task fix --claims "$CL" >/dev/null 2>&1 || fail "new ticket T2 not minted after one strike"
stage T2 "$HONEST" || fail "stage T2"
gc land --ticket T2 >/dev/null 2>&1 || fail "honest T2 did not land"
grep -q "return 2" "$R/app.py" || fail "T2 landed but the repo did not change"
echo "PLANT strike_closes_ticket: PASS"
