#!/bin/sh
# Plant: C1's evidence is sealed (decision 2): the row and the land output name file, rule and function only; the expected value and the observed value are only in <state>/evidence/, which the writer hook denies.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_evidence_sealed: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
echo notes > "$R/README.txt"

# land ID PAYLOAD CLAIMS -> exit code of gc land; C1's said lines in $T/c1
land() {
  gc scan >/dev/null 2>&1 || fail "scan"
  gc ticket --write app.py --id "$1" --claims "$3" >/dev/null 2>&1 || fail "mint $1"
  mkdir -p "$ST/payload/$1"; printf '%s' "$2" > "$ST/payload/$1/app.py"
  gc land --ticket "$1" > "$T/land.$1" 2>&1; rc=$?
  python3 -c 'import json,sys; r=json.loads(open(sys.argv[1]).read().splitlines()[-1]); c=[c for c in r.get("checks",[]) if c["name"]=="C1"]; print("\n".join(c[0]["said"]) if c else "NO C1"); print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))' "$ST/ledger.jsonl" > "$T/c1" 2>/dev/null || echo "NO ROW" > "$T/c1"
  return $rc
}
struck() {  # struck RULE QUALNAME: the last land was rejected with a strike and C1 named rule on qualname
  grep -q "^C1 fail: introduced app.py:[0-9]* $1 $2$" "$T/c1" || fail "C1 did not name $1 on $2: $(cat "$T/c1")"
  grep -q "^STRIKE$" "$T/c1" || fail "no strike: $(cat "$T/c1")"
}
clean() {  # the last land proceeded and C1 passed
  grep -q "^DECISION proceed$" "$T/c1" || fail "honest ticket did not proceed: $(cat "$T/c1"; tail -3 "$T/land.$1")"
  grep -q "^C1 pass:" "$T/c1" || fail "C1 did not pass on the honest ticket: $(cat "$T/c1")"
}
printf 'def mask_email(e):\n    return "?"\n' > "$R/app.py"
CL="$T/claims.json"; printf '%s' '[{"name":"app.mask_email","call":"mask_email(\"ann@x.io\")","expect":{"result":"a***@x.io"}}]' > "$CL"
gc init >/dev/null 2>&1 || fail "init"
land T1 'def mask_email(e):
    return e.upper()
' "$CL" && fail "wrong mask landed"
struck partial app.mask_email
grep -q 'a\*\*\*@x.io' "$ST/ledger.jsonl" && fail "the expected value is in the ledger"
grep -q 'ANN@X.IO' "$ST/ledger.jsonl" && fail "the observed value is in the ledger"
grep -q 'evidence' "$T/land.T1" && fail "evidence reached the land output the writer sees"
EV="$ST/evidence/T1.1.json"
[ -f "$EV" ] || fail "no sealed evidence file: $(ls "$ST")"
python3 - "$EV" <<'PY' || fail "evidence lacks the four parts: $(cat "$EV")"
import json, sys
d = json.load(open(sys.argv[1])); e = [x for x in d["checks"]["C1"] if "claim" in x][0]
ok = e["expected"] == {"result": "a***@x.io"} and "ANN@X.IO" in e["observed"] and e["input"] == ["ann@x.io"] and e["call"] and e["rule"] == "partial"
sys.exit(0 if ok else 1)
PY
gc writer-setup >/dev/null 2>&1 || fail "writer-setup"
HOOK="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["hooks"]["PreToolUse"][0]["hooks"][0]["command"])' "$ST/claude-writer.json")"
printf '{"tool_name": "Read", "tool_input": {"file_path": "%s"}}' "$EV" | sh -c "$HOOK" >/dev/null 2>&1 && fail "the writer hook let the evidence be read"
echo "PLANT c1_evidence_sealed: PASS"
