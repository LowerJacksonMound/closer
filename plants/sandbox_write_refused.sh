#!/bin/sh
# Plant: a verify cannot write (KERNEL.md I2/K2). Runs the real verify_ticket.py and sandbox-exec on a
# verify that tries to write the kernel tree, the repo, the Worlds, the ticket dir and the state dir, then
# reads the disk itself rather than trust the verify. The repo and state sit inside the temp dir, so this
# also holds the last-rule-wins deny under an allowed temp root. A write to scratch must still work, which
# proves the verify ran. Then the same run with no sandbox-exec on PATH must refuse before the verify runs.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
GC="$HERE/bin/gc"
PY="$(command -v python3)" || exit 1
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
KPROBE="$HERE/.plant_sandbox_probe"
trap 'rm -f "$KPROBE"; chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
CL="$T/claims.json"; printf '%s' '[{"name":"a.x","call":"x","expect":{"result":1}}]' > "$CL"
fail() { echo "PLANT sandbox_write_refused: FAIL $*" >&2; exit 1; }

R="$T/repo"; ST="$T/state"; V="$T/verifies"; OK="$T/scratch"
mkdir -p "$R" "$V" "$OK"
printf 'x = 1\n' > "$R/a.py"
"$PY" "$GC" --repo "$R" --state "$ST" init >/dev/null 2>&1 || fail "gc init"
"$PY" "$GC" --repo "$R" --state "$ST" scan >/dev/null 2>&1 || fail "gc scan"
# gc ticket only takes live-pack verifies; the planted one is run below through verify_ticket --check.
"$PY" "$GC" --repo "$R" --state "$ST" ticket --write a.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "gc ticket"

cat > "$V/PLANT_WRITER.sh" <<'SH'
#!/bin/sh
# Tries every write a verify must not make and ignores the errors; the plant checks the disk.
TDIR="$(dirname "$TICKET_FILE")"
for f in "$KPROBE" "$SCOPED_ROOT/a.py" "$SCOPED_ROOT/new.py" "$STATE/plant" "$STATE/worlds/plant.json" "$TDIR/plant.json"; do
  echo planted >> "$f" 2>/dev/null
done
rm -f "$SCOPED_ROOT/a.py" 2>/dev/null
mkdir "$SCOPED_ROOT/newdir" 2>/dev/null
echo ran > "$SCRATCH/ran"
exit 0
SH

run_verify() {
  KPROBE="$KPROBE" STATE="$ST" SCRATCH="$OK" "$@" "$PY" "$HERE/bin/verify_ticket.py" \
    --ticket "$ST/tickets/T1.json" --worlds-dir "$ST/worlds" --scoped-root "$R" --verify-dir "$V" --check PLANT_WRITER > "$T/log" 2>&1
}

run_verify env
rc=$?
[ -f "$OK/ran" ] || fail "the verify never ran (exit $rc): $(cat "$T/log")"
[ "$rc" -eq 0 ] || fail "verify_ticket exit $rc: $(cat "$T/log")"
[ -e "$KPROBE" ] && fail "verify wrote into the kernel tree"
[ "$(cat "$R/a.py" 2>/dev/null)" = "x = 1" ] || fail "verify changed or removed repo file a.py"
[ -e "$R/new.py" ] && fail "verify created a repo file"
[ -e "$R/newdir" ] && fail "verify created a repo dir"
[ -e "$ST/plant" ] && fail "verify wrote the state dir"
[ -e "$ST/worlds/plant.json" ] && fail "verify wrote the Worlds dir"
[ -e "$ST/tickets/plant.json" ] && fail "verify wrote the ticket dir"

# No sandbox-exec: refuse, and never run the verify unsandboxed.
rm -f "$OK/ran"
mkdir "$T/emptypath"
run_verify env PATH="$T/emptypath"
rc=$?
[ "$rc" -eq 75 ] || fail "no sandbox-exec gave exit $rc, want 75 (not run, no strike; M5a)"
[ -f "$OK/ran" ] && fail "the verify ran without a sandbox"
grep -q "no sandbox-exec" "$T/log" || fail "refusal does not name sandbox-exec: $(cat "$T/log")"

echo "PLANT sandbox_write_refused: PASS"
