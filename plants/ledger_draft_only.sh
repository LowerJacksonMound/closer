#!/bin/sh
# Plant: the ledger is a draft hash chain with no signed head (KERNEL L1). Real gc land writes three rows
# (syntax reject, strike, proceed); every one is status "draft" and `gc ledger --check` says OK. Then, on
# copies of that ledger:
#   - an edited row          -> "row hash mismatch" on that line
#   - an edited, rehashed row -> "prev link broken" on the next line
#   - every row from the edit on rehashed -> passes. That is the L1 limit: tamper-evident, not tamper-proof,
#     until the head is signed. When head signing lands, this last step must flip to a failure.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f()","expect":{"result":2}}]' > "$CL"
fail() { echo "PLANT ledger_draft_only: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"; L="$ST/ledger.jsonl"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
printf 'def f():\n    return 1\n' > "$R/app.py"
echo notes > "$R/README.txt"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
land() {  # land TICKET CONTENT
  gc ticket --write app.py --id "$1" --claims "$CL" >/dev/null 2>&1 || fail "mint $1"
  mkdir -p "$ST/payload/$1"; printf '%s' "$2" > "$ST/payload/$1/app.py"
  gc land --ticket "$1" >/dev/null 2>&1
}
land T1 'def f(:
'
land T2 'def f():
    return 1


def h():
    pass
'
land T3 'def f():
    return 2
' || fail "honest T3 did not land"

python3 - "$L" <<'PY' || fail "rows are not all draft, or carry a signature"
import json, sys
rows = [json.loads(x) for x in open(sys.argv[1]) if x.strip()]
sys.exit(0 if len(rows) == 3 and all(r["status"] == "draft" and not any("sig" in k for k in r) for r in rows) else 1)
PY
[ -z "$(ls "$ST" | grep -i -e sig -e head)" ] || fail "state dir holds a head/signature file: $(ls "$ST")"
gc ledger --check >/dev/null 2>&1 || fail "intact ledger did not pass check"

cp "$L" "$T/good"
tamper() {  # tamper MODE: edit row 1's reasons; MODE none | row | chain = what gets rehashed after
  chmod u+w "$L"
  python3 - "$HERE/bin" "$T/good" "$L" "$1" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1]); import ledger
rows = [json.loads(x) for x in open(sys.argv[2]) if x.strip()]
rows[0]["reasons"] = ["accepted"]
for i, r in enumerate(rows):
    if i > 0 and sys.argv[4] == "chain":
        r["prev"] = rows[i - 1]["sha256"]
    if (i == 0 and sys.argv[4] != "none") or sys.argv[4] == "chain":
        r["sha256"] = ledger.row_sha(r)
open(sys.argv[3], "w").write("".join(json.dumps(r) + "\n" for r in rows))
PY
  gc ledger --check > "$T/out" 2>&1
}
tamper none && fail "edited row passed check"
grep -q "line 1: row hash mismatch" "$T/out" || fail "edit not reported on its line: $(cat "$T/out")"
tamper row && fail "edited+rehashed row passed check"
grep -q "line 2: prev link broken" "$T/out" || fail "rehash not reported as a broken link: $(cat "$T/out")"
tamper chain || fail "full rehash was caught: head signing exists now; flip this step (L1): $(cat "$T/out")"
echo "PLANT ledger_draft_only: PASS"
