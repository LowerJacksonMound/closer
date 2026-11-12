#!/usr/bin/env python3
"""closer_gate_nudge (2026-11-10, t118): SessionStart / UserPromptSubmit hook. Tells Claude up front that the repo it
is working in is gated and that code goes in through cl_submit, so it goes straight to the CLOSER flow instead of
finding out from a denied Edit/Write.

Reuses closer_gate.py's scope (same skip/roots lists, CLOSER registration, Python/web project-marker roots, the
python / web / python+web classification walk; no git). When cwd is inside a gated repo it prints hookSpecificOutput.additionalContext; otherwise it prints
nothing. SessionStart always says it (startup, resume, clear, compact). UserPromptSubmit says it once per session
(stamp in ~/.claude/hooks/.closer_gate_nudged/), which covers sessions that started elsewhere and cd'd in.
FAIL OPEN and silent: any error prints nothing, exits 0, and is logged to closer_gate.log as nudge-error.
Respects the gate's off switch. Not wired: see closer_gate_settings.PROPOSED.json.

usage: python3 closer_gate_nudge.py            (hook; event JSON on stdin)
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAMPS = Path.home() / ".claude" / "hooks" / ".closer_gate_nudged"


def load_gate():
    spec = importlib.util.spec_from_file_location("closer_gate", HERE / "closer_gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def message(g, root: Path, cwd: str, kind: str = "Python/web code") -> str:
    covered, _how = g.sandbox_covers(root, cwd)
    bash = ("Bash runs in a sandbox that refuses writes to this repo's code files at the OS level."
            if covered else
            "Do not write code files with Bash either (redirects, sed -i, scripts); that bypasses CLOSER.")
    return (f"CLOSER gate: {root} is a gated repo ({kind}). Code reaches the page only through the CLOSER MCP tool: "
            f"{g.FLOW}. CLOSER runs each function and compares it with your checks (the user's intent) before anything "
            f"is written; a function that fails twice is not written and is logged as a hole. No approval step is needed. "
            f"Direct Edit/Write/MultiEdit/NotebookEdit on code, HTML or protected files in this repo will be denied. "
            f"{bash} Docs and config (.md, .toml, .json, .txt) can be edited normally. Give cl_plan a contract (name, "
            f"parameters, spec checks) for every function or class the spec names; a question whose answer would change "
            f"one is a plan change: send a revised plan.")


def decide(event: dict, g=None) -> str | None:
    """The additionalContext to emit, or None."""
    g = g or load_gate()
    name = event.get("hook_event_name")
    if name not in ("SessionStart", "UserPromptSubmit"):
        return None
    cwd = event.get("cwd") or os.getcwd()
    here = g.resolve(cwd, cwd)
    if g.exempt(here / "x.py"):
        return None
    root, why = g.scope(here / "__probe__.py", g.registered())
    if root is None:
        return None
    sid = str(event.get("session_id") or "nosession").replace("/", "_")[:120]
    stamp = STAMPS / sid
    if name == "UserPromptSubmit" and stamp.exists():
        return None
    try:
        STAMPS.mkdir(parents=True, exist_ok=True)
        stamp.write_text(str(root))
        for old in STAMPS.iterdir():
            if time.time() - old.stat().st_mtime > 2 * 86400:
                old.unlink(missing_ok=True)
    except OSError:
        pass
    kind = next((k for k in ("python+web", "python", "web") if why.startswith(f"gated {k} ")), "opted in")
    return message(g, root, cwd, kind)


def main() -> int:
    g = None
    try:
        g = load_gate()
        if os.environ.get("CLOSER_GATE_OFF") == "1" or g.OFF_FILE.exists():
            return 0
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            return 0
        ctx = decide(event, g)
        if ctx:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": event["hook_event_name"], "additionalContext": ctx}}))
            g.log({"ts": g.now(), "session": event.get("session_id"), "tool": event.get("hook_event_name"),
                   "cwd": event.get("cwd"), "decision": "nudge"})
    except Exception as e:  # noqa: BLE001  fail open, silent to Claude
        try:
            if g is not None:
                g.log({"ts": g.now(), "decision": "nudge-error", "error": f"{type(e).__name__}: {e}"})
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
