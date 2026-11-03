#!/usr/bin/env bash
# install_closer_mcp.sh — register Closer's MCP server (the signer's, not the writer's) with Claude Code once, at user scope.
#
#   bash install_closer_mcp.sh            # register (user scope: every project sees it)
#   bash install_closer_mcp.sh --print    # print the command, change nothing
#
# The entry is closer-mcp.sh next to this file: one stdio process, no extra package. Every tool names its repo.
# timeout: cl_go blocks while the writer works (minutes), so the client gets 50 minutes per call, as CodeRadar does.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
ENTRY="$ROOT/closer-mcp.sh"
NAME="closer"

if [ ! -f "$ENTRY" ]; then
  echo "install_closer_mcp.sh: $ENTRY is missing" >&2
  exit 1
fi
if [ ! -x "$ENTRY" ]; then
  echo "install_closer_mcp.sh: $ENTRY is not executable. Run:  chmod +x $ENTRY" >&2
  exit 1
fi
if [ ! -f "$ROOT/adapters/claude_code/closer_mcp.py" ]; then
  echo "install_closer_mcp.sh: $ROOT/adapters/claude_code/closer_mcp.py is missing — run this from the CARTOUCHE folder's copy" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "install_closer_mcp.sh: python3 is not on PATH; closer-mcp.sh needs Python 3.10 or newer; macOS ships 3.9, so brew install python" >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "install_closer_mcp.sh: python3 is $(python3 --version 2>&1); Closer needs 3.10 or newer" >&2
  exit 1
fi

JSON=$(printf '{"type":"stdio","command":"%s","args":[],"timeout":3000000}' "$ENTRY")

if [ "${1:-}" = "--print" ]; then
  printf "claude mcp add-json --scope user %s '%s'\n" "$NAME" "$JSON"
  exit 0
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "install_closer_mcp.sh: the claude CLI is not on PATH. Register by hand with:" >&2
  printf "  claude mcp add-json --scope user %s '%s'\n" "$NAME" "$JSON" >&2
  exit 1
fi

if claude mcp get "$NAME" >/dev/null 2>&1; then
  echo "install_closer_mcp.sh: an MCP server named '$NAME' is already registered — replacing it"
  claude mcp remove --scope user "$NAME" >/dev/null 2>&1 || true
fi

claude mcp add-json --scope user "$NAME" "$JSON"
echo
echo "Registered '$NAME' -> $ENTRY"
echo "Next: in Claude Code, in any directory, ask for a task to be drafted: the agent calls cl_doctor(repo), cl_task,"
echo "cl_claims(repo, task) and shows you the claims. You say yes; only then may it call cl_go(repo, task, approved=true)."
echo "cl_inspect(repo) tells the verdict in plain words; cl_stop(repo) ends the live page. The CLI (./closer) is unchanged."
