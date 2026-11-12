#!/bin/sh
# CLOSER MCP server. stdout is the protocol. Repo = $1, else the directory the client starts it in.
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null || { echo "closer-mcp.sh: python3 is missing or older than 3.9" >&2; exit 1; }
exec python3 "$ROOT/closer_mcp.py" "$@"
