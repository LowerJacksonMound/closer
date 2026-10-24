#!/bin/sh
# Plant: C1 lets through what it cannot judge (KERNEL.md T16, 2026-10-19; pack v32). Replaces plants/c1_cannot_judge.sh,
# which asserted the 2026-10-15 rule T16 supersedes (cannot_judge is a strike). T1, kept from it: a required name the
# writer never implemented is `partial`, a verdict, still a strike. T2: an honest ticket changes f; one claim on f holds,
# a second has a setup that raises (NameError): C1 prints `C1 unjudged: app.py:1 cannot_judge app.f (setup_error: ...)`
# on stdout, no `C1 fail:` line, `C1 pass: 1 claim(s) held on 1 function(s), 1 not judged`, exit 0; the land proceeds
# with no strike; the row's `unjudged` carries the line; the evidence files the claim with rule cannot_judge, the
# coverage entry for f counts `unjudged: 1`, and the reach entry lists claim 2 under `unjudged`. T3: the same with the
# clock (C1_SECONDS=3): a claim whose setup sleeps past it is `cannot_judge (out of time)`, unjudged, and the land
# proceeds (a timed-out runner reports no file or line, so that line reads `?:0`, as the v31 fail line did). Under v31 T2 and T3 are rejected with a strike (`C1 fail: introduced app.py:1 cannot_judge app.f`).
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_cannot_judge_proceeds: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
echo notes > "$R/README.txt"

# land ID PAYLOAD CLAIMS -> exit code of gc land; C1's said lines, strike, decision, unjudged in $T/c1
land() {
  gc scan >/dev/null 2>&1 || fail "scan"
  gc ticket --write app.py --id "$1" --claims "$3" >/dev/null 2>&1 || fail "mint $1"
  mkdir -p "$ST/payload/$1"; printf '%s' "$2" > "$ST/payload/$1/app.py"
  gc land --ticket "$1" > "$T/land.$1" 2>&1; rc=$?
  python3 - "$ST/ledger.jsonl" > "$T/c1" 2>/dev/null <<'PY' || echo "NO ROW" > "$T/c1"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "C1"]
print("\n".join(c[0]["said"]) if c else "NO C1"); print("C1EXIT", c[0]["exit"] if c else "none")
print("STRIKE" if r.get("strike") else "NOSTRIKE"); print("DECISION", r.get("decision"))
print("UNJUDGED", len(r.get("unjudged", [])))
for u in r.get("unjudged", []): print("ROW", u)
PY
  return $rc
}
printf 'def f():\n    return 1\n' > "$R/app.py"
gc init >/dev/null 2>&1 || fail "init"

# T1: a missing required name is a verdict (partial): still a strike.
CL="$T/claims.json"; printf '%s' '[{"name":"app.required","call":"required(1)","expect":{"result":1}}]' > "$CL"
land T1 'def f():
    return 1


def something_else(x):
    return x
' "$CL" && fail "missing required name landed"
grep -q "^C1 fail: introduced app.py:[0-9]* partial app.required$" "$T/c1" || fail "partial not named: $(cat "$T/c1")"
grep -q "^STRIKE$" "$T/c1" || fail "partial did not strike: $(cat "$T/c1")"

# T2: a claim whose setup raises is unjudged; the other claim reaches f; the land proceeds.
CL2="$T/claims2.json"; printf '%s' '[{"name":"app.f","call":"f()","expect":{"result":1}},{"name":"app.f","setup":["y = undefined_name"],"call":"f()","expect":{"result":1}}]' > "$CL2"
land T2 'def f():
    return 1 + 0
' "$CL2" || fail "a land with an unjudged claim did not proceed: $(cat "$T/c1"; tail -2 "$T/land.T2")"
grep -q "^DECISION proceed$" "$T/c1" || fail "T2 decision: $(cat "$T/c1")"
grep -q "^NOSTRIKE$" "$T/c1" || fail "an unjudged claim struck the ticket: $(cat "$T/c1")"
grep -q "^C1EXIT 0$" "$T/c1" || fail "C1 did not exit 0: $(cat "$T/c1")"
grep -q "^C1 unjudged: app.py:1 cannot_judge app.f (setup_error: NameError: " "$T/c1" || fail "no unjudged line: $(cat "$T/c1")"
grep -q "^C1 unjudged: app.py:1 cannot_judge app.f (setup_error: NameError: " "$T/land.T2" || fail "the unjudged line did not reach stdout: $(grep C1 "$T/land.T2")"
grep -q "^C1 fail:" "$T/c1" && fail "a fail line for an unjudged claim: $(grep '^C1 fail' "$T/c1")"
grep -q "^C1 pass: 1 claim(s) held on 1 function(s), 1 not judged$" "$T/c1" || fail "pass line: $(grep '^C1 pass' "$T/c1")"
grep -q "^UNJUDGED 1$" "$T/c1" || fail "the row does not carry one unjudged line: $(cat "$T/c1")"
grep -q "^ROW C1 unjudged: app.py:1 cannot_judge app.f (setup_error" "$T/c1" || fail "row unjudged text: $(grep ^ROW "$T/c1")"
EVF="$(ls "$ST/evidence/T2".*.json 2>/dev/null | tail -1)"
python3 - "$EVF" <<'PY' || fail "evidence: $(cat "$EVF" 2>/dev/null | head -40)"
import json, sys
ev = json.load(open(sys.argv[1]))["checks"]["C1"]
claims = {e["claim"]: e for e in ev if "claim" in e}
assert claims[1]["rule"] is None and claims[1]["observed"] == "held", claims[1]
assert claims[2]["rule"] == "cannot_judge" and claims[2]["observed"].startswith("setup_error: NameError"), claims[2]
reach = [e["reach"] for e in ev if "reach" in e][0]
assert reach["unjudged"] == [2] and reach["unreached"] == [] and reach["introduced"] == [["app.py", "f"]], reach
cov = [e["coverage"] for e in ev if "coverage" in e]
assert len(cov) == 1 and cov[0]["qualname"] == "f" and cov[0]["claims"] == 1 and cov[0]["unjudged"] == 1, cov
before = [e["before_summary"] for e in ev if "before_summary" in e][0]
assert before["claims"] == 2 and before["not_run"] == 1, before
PY

# T3: the clock. A setup that outlives C1_SECONDS is cannot_judge (out of time): unjudged, the land proceeds.
CL3="$T/claims3.json"; printf '%s' '[{"name":"app.f","call":"f()","expect":{"result":1}},{"name":"app.f","setup":["import time; time.sleep(30)"],"call":"f()","expect":{"result":1}}]' > "$CL3"
export C1_SECONDS=3
land T3 'def f():
    return 1 + 0 + 0
' "$CL3" || fail "a land with a timed-out claim did not proceed: $(cat "$T/c1"; tail -2 "$T/land.T3")"
unset C1_SECONDS
grep -q "^C1 unjudged: .*:[0-9]* cannot_judge app.f (out of time)$" "$T/c1" || fail "no out-of-time unjudged line: $(cat "$T/c1")"
grep -q "^NOSTRIKE$" "$T/c1" && grep -q "^DECISION proceed$" "$T/c1" || fail "T3: $(cat "$T/c1")"
echo "PLANT c1_cannot_judge_proceeds: PASS"
