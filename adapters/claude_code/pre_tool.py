#!/usr/bin/env python3
"""Claude Code PreToolUse hook for a getting-close writer session. Stdlib only.

usage (from settings): python3 pre_tool.py <state_dir>

Belt only. The writer session is launched without Bash, Edit, Write or any MCP server but
`gc` (--tools, --strict-mcp-config), so those tools do not exist to be called. This hook
repeats the same allowlist in case a launch flag is dropped. Hooks fail open on timeout or
a missing interpreter, so nothing depends on this file.

  Read / Grep / Glob       allowed, except under the state dir (claims, tickets, evidence: T5)
  mcp__gc__<known tool>    allowed (the writer's whole write surface: stage, land, ...)
  everything else          denied, exit 2 (also on any crash or bad input)
"""

from __future__ import annotations

import json
import os
import sys
from typing import NoReturn

READ_ONLY = {"Read", "Grep", "Glob"}
# Same names as TOOLS in gc_mcp.py; keep the two in step. A separate list on purpose (the belt does not
# import what it double-checks): a tool added there and missed here is denied, never allowed.
GC_TOOLS = {"tickets", "worlds", "read", "stage", "stage_edit", "land", "verify", "check", "ledger"}


def deny(reason: str) -> NoReturn:
    print(f"getting-close: {reason}", file=sys.stderr)
    raise SystemExit(2)


def _under(path: str, state: str) -> bool:
    """path (absolute; a glob is cut at its first wildcard) resolves to the state dir or inside it."""
    head = path.split("*", 1)[0].split("?", 1)[0] or "/"
    real = os.path.realpath(head)
    return real == state or real.startswith(state + os.sep)


def decide(event: dict, state: str = "") -> None:
    tool = event.get("tool_name")
    if not isinstance(tool, str):
        deny("malformed hook input")
    if tool in READ_ONLY:
        # T5 (2026-10-15): the gate's state (tickets, claims, evidence, ledger file) is sealed from the writer.
        args = event.get("tool_input")
        for v in (args.values() if isinstance(args, dict) else []):
            if isinstance(v, str) and state and v.startswith("/") and _under(v, state):
                deny("the gate's state is not readable by a writer; read the repo, and the ledger through the gc tools")
        return
    if tool.startswith("mcp__gc__") and tool[len("mcp__gc__"):] in GC_TOOLS:
        return
    deny(f"tool {tool} is not available to a getting-close writer. Write through the gc tools: "
         f"stage / stage_edit, then land.")


def main() -> None:
    try:
        if len(sys.argv) != 2:
            deny("hook misconfigured: expected <state_dir>")
        state = os.path.realpath(sys.argv[1])
        if not os.path.isfile(os.path.join(state, "manifest.json")):
            deny(f"hook misconfigured: no getting-close state at {state}")
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            deny("malformed hook input")
        decide(event, state)
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 — fail closed on anything
        deny(f"hook error ({type(e).__name__}); denying")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
