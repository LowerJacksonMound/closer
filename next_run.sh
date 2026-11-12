#!/bin/sh
# One-line start of a CLOSER live run, from a terminal OUTSIDE a sandboxed Claude session:
#   bash ~/Desktop/CLOSER/next_run.sh seedbank      (or: cr | ct for the CodeRadar / Cartouche trees)
# name = prompts/<name>.md; the repo dir is ~/Desktop/<name>-test. Runs the tests, gates the dir, applies the
# sandbox, opens T2 (watcher) and T1 (claude in the dir) in Terminal, and puts the prompt on the clipboard.
set -e
NAME=${1:?usage: next_run.sh <prompt name> | next_run.sh tests}
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
S=$HOME/Desktop/IDEAS_BUSINESS_N_PLANS_PORTFOLIO/A_IDEAS/COMPLETED_SOFTWARE
case "$NAME" in  # the two real trees: cr = prompt 3, ct = prompt 5 (prompt 4's leftover is inside it)
  cr) DIR=$S/NEW_CODE_RADAR_REFURBISH; PROMPT=$HERE/prompts/3-cr_intent_from_plan.md ;;
  ct) DIR=$S/MCP-CARTOUCHE; PROMPT=$HERE/prompts/5-ct_fault_owner_and_4_tests.md ;;
  *) DIR=$HOME/Desktop/$NAME-test; PROMPT=$HERE/prompts/$NAME.md ;;
esac
[ "$NAME" = tests ] || [ -f "$PROMPT" ] || { echo "no prompt at $PROMPT"; exit 1; }

echo "== tests"
cd "$HERE"
for t in shenanigans classes brittle edges gate client; do
  printf '%-12s' "$t"
  LOG=$(mktemp); python3 "tests/$t.py" . "$(mktemp -d)" >"$LOG" 2>&1; { grep 'Traceback\|^BAD\|^BROKEN\|^MISSING\|written in total' "$LOG" || true; tail -1 "$LOG"; } | tr '\n' ' '; echo; rm -f "$LOG"
done
printf '%-12s' inplace; python3 tests/inplace.py 2>&1 | tail -1
[ "$NAME" = tests ] && exit 0

echo "== gate"
mkdir -p "$DIR"
grep -qx "$DIR" "$HOME/.claude/closer_gate_roots.txt" 2>/dev/null || echo "$DIR" >> "$HOME/.claude/closer_gate_roots.txt"
cp "$HERE/closer_gate.py" "$HOME/.claude/hooks/closer_gate.py"
cp "$HERE/closer_gate_nudge.py" "$HOME/.claude/hooks/closer_gate_nudge.py"
python3 "$HERE/closer_gate.py" --emit-sandbox "$HOME/.claude/hooks/closer_gate_settings.PROPOSED.json" >/dev/null
python3 "$HERE/apply_sandbox.py"
python3 "$HERE/closer_gate.py" --classify "$DIR"

echo "== launch"
pbcopy < "$PROMPT" && echo "prompt is on the clipboard: paste it into T1"
osascript -e "tell application \"Terminal\" to do script \"python3 $HERE/closer_watch.py $DIR\"" >/dev/null
osascript -e "tell application \"Terminal\" to do script \"cd $DIR && claude\"" >/dev/null
echo "T2 (watcher) and T1 (claude in $DIR) are open. Paste the prompt into T1."
