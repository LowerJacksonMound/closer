#!/bin/sh
# Closer MCP server for the signer's own Claude session. stdout is the protocol. Run from anywhere.
# Resolves its own symlink like ./closer does.
self="$0"
while [ -L "$self" ]; do
  dir="$(cd "$(dirname "$self")" && pwd)"
  self="$(readlink "$self")"
  case "$self" in /*) ;; *) self="$dir/$self" ;; esac
done
ROOT="$(cd "$(dirname "$self")" && pwd -P)"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null || {
  echo "closer-mcp.sh: needs Python 3.10 or newer as python3; this machine's python3 is $(python3 --version 2>&1 || echo missing)." >&2
  exit 1
}
exec python3 "$ROOT/adapters/claude_code/closer_mcp.py" "$@"
