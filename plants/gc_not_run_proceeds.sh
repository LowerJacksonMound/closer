#!/bin/sh
# Plant: a check that cannot run is let through (KERNEL.md T16, 2026-10-19; pack v32, bin/gc). The manifest names a stub
# REPO_PYTHON, a venv made with --without-pip and no site packages, so pytest is not importable by it: E1 exits 75
# (`E1 not run: pytest is not importable by ...`), and so does U1 (its drivers need pytest). S1, G18 and C1 run (C1's
# claims are stdlib only). Under v31 gc took the first 75 as a reject: "E1 not run (exit 75): no strike", rolled back,
# land exit 1, ticket not struck. Under v32 the honest ticket LANDS: exit 0, `decision: proceed`, no strike, the row's
# `not_run` lists E1 (and U1) and its reasons record each `... not run (exit 75): no strike, not judged (T16)`.
# Guard kept (both versions): with no sandbox-exec on the PATH (a PATH holding only python3, which gc requires) the land
# is still refused before apply, with no strike, naming sandbox-exec: without it nothing can be held read-only (K2), so
# T16 does not let that 75 through.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT gc_not_run_proceeds: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
PY="$(command -v python3)" || fail "no python3"
gc() { "$PY" "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
row() {  # the last ledger row -> $T/row
  "$PY" - "$ST/ledger.jsonl" > "$T/row" 2>/dev/null <<'PYX' || echo "NO ROW" > "$T/row"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
for c in r.get("checks", []):
    print(c["name"] + "EXIT", c["exit"])
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
print("NOTRUN", " ".join(r.get("not_run", []))); print("REASONS", " | ".join(r.get("reasons", [])))
print("UNJUDGED", len(r.get("unjudged", [])))
PYX
}
V="$T/venv"
"$PY" -m venv --without-pip "$V" >/dev/null 2>&1 || fail "venv"
"$V/bin/python" -c 'import pytest' 2>/dev/null && fail "premise: pytest is importable by the stub interpreter $V/bin/python"
mkdir -p "$R/tests"
echo notes > "$R/README.txt"
printf 'def f(s):\n    return len(s)\n' > "$R/app.py"
printf 'from app import f\n\n\ndef test_f():\n    assert f("ab") == 2\n' > "$R/tests/test_app.py"
gc init --python "$V/bin/python" >/dev/null 2>&1 || fail "init --python"
gc scan >/dev/null 2>&1 || fail "scan"
CL="$T/claims.json"; printf '%s' '[{"name":"app.f","call":"f(\"ab\")","expect":{"result":2}},{"name":"app.f","call":"f(\"\")","expect":{"result":0}}]' > "$CL"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1"
printf 'def f(s):\n    if not s:\n        return 0\n    return len(s)\n' > "$ST/payload/T1/app.py"
gc land --ticket T1 > "$T/land" 2>&1; rc=$?
row
grep -q "^E1 not run: pytest is not importable by $V/bin/python" "$T/land" || fail "E1 did not say it could not run: $(grep -E '^(E1|verify_ticket)' "$T/land" | head -3)"
grep -q "^E1EXIT 75$" "$T/row" || fail "E1 did not exit 75: $(cat "$T/row")"
[ "$rc" -eq 0 ] || fail "the land with a not-run check did not proceed (exit $rc): $(grep -E '^(DECISION|STRIKE|NOSTRIKE|NOTRUN|REASONS)' "$T/row" | tr '\n' ' ')"
grep -q "^DECISION proceed$" "$T/row" || fail "row decision: $(cat "$T/row")"
grep -q "^NOSTRIKE$" "$T/row" || fail "a not-run check struck the ticket: $(cat "$T/row")"
grep -q "^NOTRUN .*E1" "$T/row" || fail "the row does not list E1 as not run: $(cat "$T/row")"
grep -q "^REASONS .*E1 not run (exit 75): no strike, not judged (T16)" "$T/row" || fail "the reason is not recorded: $(cat "$T/row")"
grep -q "^C1EXIT 0$" "$T/row" && grep -q "^S1EXIT 0$" "$T/row" || fail "C1 or S1 did not pass: $(cat "$T/row")"
grep -q "if not s" "$R/app.py" || fail "the patch was rolled back on a proceed"
grep -q '"decision": "proceed"' "$T/land" || fail "land did not print proceed: $(tail -1 "$T/land")"

# Guard: no sandbox-exec -> refused before apply, no strike, not let through (the one 75 T16 keeps).
gc scan >/dev/null 2>&1 || fail "scan 2"
gc ticket --write app.py --id T2 --claims "$CL" >/dev/null 2>&1 || fail "mint T2"
mkdir -p "$ST/payload/T2"
printf 'def f(s):\n    if not s:\n        return 0\n    return len(s)  # T2\n' > "$ST/payload/T2/app.py"
mkdir "$T/nosbx"; ln -s "$PY" "$T/nosbx/python3"
env PATH="$T/nosbx" "$PY" "$HERE/bin/gc" --repo "$R" --state "$ST" land --ticket T2 > "$T/land2" 2>&1; rc=$?
row
[ "$rc" -eq 1 ] || fail "a land with no sandbox-exec was not refused (exit $rc): $(tail -2 "$T/land2")"
grep -q "^DECISION reject$" "$T/row" || fail "no-sandbox row: $(cat "$T/row")"
grep -q "^NOSTRIKE$" "$T/row" || fail "no sandbox-exec struck the ticket: $(cat "$T/row")"
grep -qi "sandbox-exec" "$T/land2" || fail "refusal does not name sandbox-exec: $(tail -3 "$T/land2")"
grep -q "# T2" "$R/app.py" && fail "T2 was applied without a sandbox"
echo "PLANT gc_not_run_proceeds: PASS"
