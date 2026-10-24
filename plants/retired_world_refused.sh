#!/bin/sh
# Plant: a World using retired names (scan_id, started_at, files_scanned) is refused, never mapped or read
# as v1. Real gc. A frozen World is rewritten to carry the retired names in place of world_id: gc read
# refuses it naming the missing key, gc ticket will not mint against it, and a ticket minted before the
# rewrite is rejected at land with no strike and the repo untouched. A bare retired-sketch file is refused.
# G1: the same names in a doc are reported as "reads as" through GLOSSARY.md; the doc is not rewritten.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
CL="$T/claims.json"; printf '%s' '[{"name":"a.x","call":"x","expect":{"result":1}}]' > "$CL"
fail() { echo "PLANT retired_world_refused: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
printf 'x = 1\n' > "$R/a.py"
echo notes > "$R/README.txt"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
WF="$(ls "$ST"/worlds/scan_*.json | head -1)"
WID="$(basename "$WF" .json)"; WID="${WID#scan_}"
gc read --world "$WID" >/dev/null 2>&1 || fail "the untouched World does not read"
gc ticket --write a.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint T1"

python3 - "$WF" <<'PY'
import json, os, sys
p = sys.argv[1]; d = json.load(open(p))
d["scan_id"] = d.pop("world_id"); d["started_at"] = "2026-01-01T00:00:00Z"; d["files_scanned"] = 2
os.chmod(p, 0o644); open(p, "w").write(json.dumps(d)); os.chmod(p, 0o444)
PY
gc read --world "$WID" >/dev/null 2>"$T/err" && fail "World with retired names was read"
grep -q "missing required WORLD.md keys: world_id" "$T/err" || fail "refusal does not name world_id: $(cat "$T/err")"
gc ticket --write a.py --id T2 --claims "$CL" >/dev/null 2>"$T/err" && fail "gc ticket minted against the retired World"
grep -q "^gc: World missing required WORLD.md keys: world_id" "$T/err" || fail "mint refusal unclear: $(cat "$T/err")"
[ -e "$ST/tickets/T2.json" ] && fail "refused mint left a ticket file"

mkdir -p "$ST/payload/T1"; printf 'x = 2\n' > "$ST/payload/T1/a.py"
gc land --ticket T1 >/dev/null 2>&1
[ $? -eq 1 ] || fail "land against the retired World was not rejected"
python3 -c 'import json, sys; r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
sys.exit(0 if r["decision"] == "reject" and not r.get("strike") else 1)' "$ST/ledger.jsonl" || fail "rejected with a strike"
grep -q "x = 1" "$R/a.py" || fail "land against the retired World changed the repo"

printf '{"scan_id": "old", "started_at": "x", "sha256": "y", "files_scanned": 1}' > "$ST/worlds/scan_old.json"
chmod 444 "$ST/worlds/scan_old.json"
gc read --world old >/dev/null 2>"$T/err" && fail "retired sketch was read"
grep -q "looks like retired sketch" "$T/err" || fail "sketch not named as retired: $(cat "$T/err")"

# G1: a law doc that still uses retired names is read through GLOSSARY.md, not failed and not rewritten.
D="$T/doc.md"
printf '# Old\n\nThe sketch had `scan_id` and `files_scanned`.\n' > "$D"
cp "$D" "$T/doc.before"
python3 "$HERE/bin/glossary.py" check "$D" > "$T/out" 2>&1 || fail "retired names in a doc failed the check: $(cat "$T/out")"
grep -q '`scan_id` reads as `world_id`' "$T/out" || fail "scan_id not read as world_id: $(cat "$T/out")"
grep -q '`files_scanned` reads as `units`' "$T/out" || fail "files_scanned not read as units: $(cat "$T/out")"
cmp -s "$D" "$T/doc.before" || fail "glossary check rewrote the doc"
python3 "$HERE/bin/glossary.py" check --strict "$D" >/dev/null 2>&1 && fail "--strict let retired names through"
echo "PLANT retired_world_refused: PASS"
