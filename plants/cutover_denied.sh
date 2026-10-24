#!/bin/sh
# Plant: a writer gets no raw write path (KERNEL.md C1). Runs the real `gc writer-setup`, then the real
# PreToolUse hook and gc-writer wrapper it generates. It does not launch Claude Code itself (that needs the
# claude CLI, an account and the network), so --tools/--restricted are checked as written, not as enforced.
# Exit 0: every non-gc tool and every signer-only gc command is refused; the gc tools still work.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
GC="$HERE/bin/gc"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT cutover_denied: FAIL $*" >&2; exit 1; }

R="$T/repo"; ST="$T/state"
mkdir -p "$R"
printf 'x = 1\n' > "$R/a.py"
python3 "$GC" --repo "$R" --state "$ST" init >/dev/null 2>&1 || fail "gc init"
python3 "$GC" --repo "$R" --state "$ST" writer-setup > "$T/setup.out" 2>&1 || fail "gc writer-setup"

# The launch line: only Read/Grep/Glob built in, only the gc MCP server, user settings ignored.
for flag in "--tools Read,Grep,Glob" "--restricted" "--strict-mcp-config" "--permission-mode dontAsk"; do
  grep -q -- "$flag" "$T/setup.out" || fail "launch line lacks $flag"
done
python3 - "$ST/claude-writer.json" <<'PY' || fail "writer settings allow more than Read/Grep/Glob/mcp__gc"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if s["permissions"]["allow"] == ["Read", "Grep", "Glob", "mcp__gc"] else 1)
PY

# The PreToolUse hook exactly as the writer session runs it.
HOOK="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["hooks"]["PreToolUse"][0]["hooks"][0]["command"])' "$ST/claude-writer.json")"
for tool in Bash Edit Write MultiEdit NotebookEdit WebFetch Agent mcp__other__write_file mcp__gc__apply; do
  printf '{"tool_name": "%s", "tool_input": {}}' "$tool" | sh -c "$HOOK" >/dev/null 2>"$T/err"
  rc=$?
  [ "$rc" -eq 2 ] || fail "hook let $tool through (exit $rc)"
  grep -q "stage / stage_edit, then land" "$T/err" || fail "$tool denied without naming the gc tools: $(cat "$T/err")"
done
for tool in Read Grep Glob mcp__gc__stage mcp__gc__stage_edit mcp__gc__land; do
  printf '{"tool_name": "%s", "tool_input": {}}' "$tool" | sh -c "$HOOK" >/dev/null 2>&1 || fail "hook denied $tool"
done
# T5: the gate's state (claims, tickets, ledger file) is sealed from the writer; the repo is not.
STR="$(cd "$ST" && pwd -P)"
for args in "{\"file_path\": \"$STR/claims/T1.json\"}" "{\"path\": \"$STR\"}" "{\"pattern\": \"$STR/**/*.json\"}" "{\"file_path\": \"$ST/tickets/T1.json\"}"; do
  printf '{"tool_name": "Read", "tool_input": %s}' "$args" | sh -c "$HOOK" >/dev/null 2>"$T/err"
  [ $? -eq 2 ] || fail "hook let a writer read the state: $args"
  grep -q "not readable by a writer" "$T/err" || fail "state read denied without saying so: $(cat "$T/err")"
done
printf '{"tool_name": "Grep", "tool_input": {"pattern": "x", "path": "%s"}}' "$STR" | sh -c "$HOOK" >/dev/null 2>&1 && fail "hook let a writer grep the state"
printf '{"tool_name": "Read", "tool_input": {"file_path": "%s/a.py"}}' "$R" | sh -c "$HOOK" >/dev/null 2>&1 || fail "hook denied a repo read"

# The gc-writer wrapper: signer-only commands do not exist there; a writer cannot point it elsewhere.
for cmd in init scan ticket policy apply writer-setup; do
  "$ST/gc-writer" "$cmd" >/dev/null 2>&1 && fail "gc-writer ran signer command $cmd"
done
"$ST/gc-writer" --repo "$T" tickets >/dev/null 2>&1 && fail "gc-writer accepted --repo"
"$ST/gc-writer" tickets >/dev/null 2>&1 || fail "gc-writer tickets failed"

echo "PLANT cutover_denied: PASS"
