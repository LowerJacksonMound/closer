#!/bin/sh
# Plant: the signer's MCP (closer-mcp.sh) lists its seven tools, and cl_go is refused before cl_claims has shown the task
# and refused again without the person's yes. No model, no writer: both refusals come before anything runs.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
trap 'rm -rf "$T"' EXIT
fail() { echo "PLANT mcp_outer_gate: FAIL $*" >&2; exit 1; }
printf 'task\n' > "$T/TASK.md"; mkdir -p "$T/repo"
{
  printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"plant","version":"0"}}}'
  printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
  printf '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"cl_go","arguments":{"repo":"%s","task":"%s","approved":true}}}\n' "$T/repo" "$T/TASK.md"
  printf '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"cl_go","arguments":{"repo":"%s","task":"TASK.md","approved":true}}}\n' "$T/repo"
} | sh "$HERE/closer-mcp.sh" > "$T/out" 2>"$T/err" || fail "server exit $? $(cat "$T/err")"
python3 - "$T/out" <<'PY' || fail "$(cat "$T/err")"
import json, sys
r = {d["id"]: d for d in (json.loads(l) for l in open(sys.argv[1]) if l.strip())}
tools = [t["name"] for t in r[2]["result"]["tools"]]
assert tools == ["cl_doctor", "cl_task", "cl_claims", "cl_go", "cl_status", "cl_inspect", "cl_stop"], tools
t3 = r[3]["result"]; assert t3["isError"] and "cl_claims first" in t3["content"][0]["text"], t3
t4 = r[4]["result"]; assert t4["isError"] and "absolute" in t4["content"][0]["text"], t4
PY
echo "PLANT mcp_outer_gate: PASS"
