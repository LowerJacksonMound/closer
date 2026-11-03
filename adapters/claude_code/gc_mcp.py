#!/usr/bin/env python3
"""getting-close writer tools as a stdio MCP server. Stdlib only. ZERO model calls.

usage (from the writer's MCP config): python3 gc_mcp.py <state_dir>

The writer session has no Bash, Edit or Write. These tools are its whole write surface
(KERNEL.md cutover set: read_world, apply_ticket via land, verify_ticket, propose_* via stage).
Commands run as `<state>/gc-writer <argv...>` with an argument list, never a shell string.
The state dir is fixed by the launch config, which the writer cannot edit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parents[2] / "bin"
sys.path.insert(0, str(BIN))
import stage as stage_mod  # noqa: E402

SERVER = {"name": "gc", "version": "1"}
KNOWN_PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
DEFAULT_PROTOCOL = "2025-06-18"
MAX_LINE = 8 * 1024 * 1024

_TICKET = {"type": "string", "description": "ticket id, e.g. T-1 (see `tickets`)"}
TOOLS = [
    {"name": "tickets", "description": "List tickets you may work on, each with its write_set and verify.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "worlds", "description": "List frozen Worlds (* = latest).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "read", "description": "Read a frozen World: stats with no keys, else the named top-level keys "
                                     "(units, edges, roots, stats...).",
     "inputSchema": {"type": "object", "properties": {
         "keys": {"type": "array", "items": {"type": "string"}},
         "world": {"type": "string", "description": "world id; default latest"}}}},
    {"name": "stage", "description": "Write the full new content of one write_set file into the ticket's "
                                      "staging area. Does not touch the repo; `land` does.",
     "inputSchema": {"type": "object", "required": ["ticket", "path", "content"], "properties": {
         "ticket": _TICKET, "path": {"type": "string", "description": "repo-relative path in the write_set"},
         "content": {"type": "string"}}}},
    {"name": "stage_edit", "description": "Exact-string edit of one write_set file, staged. Base is the staged "
                                           "copy if any, else the repo's current file.",
     "inputSchema": {"type": "object", "required": ["ticket", "path", "old_string", "new_string"], "properties": {
         "ticket": _TICKET, "path": {"type": "string"}, "old_string": {"type": "string"},
         "new_string": {"type": "string"}, "replace_all": {"type": "boolean"}}}},
    {"name": "land", "description": "Governor + apply + verify + ledger for a ticket. proceed (exit 0) changes "
                                     "the repo; reject (1) rolls back; reroute (3) needs signer action.",
     "inputSchema": {"type": "object", "required": ["ticket"], "properties": {"ticket": _TICKET}}},
    {"name": "verify", "description": "Re-run a ticket's live verify.",
     "inputSchema": {"type": "object", "required": ["ticket"], "properties": {"ticket": _TICKET}}},
    {"name": "check", "description": "Run every live verify against the latest World. Required before you stop.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "ledger", "description": "List ledger rows, or verify the hash chain.",
     "inputSchema": {"type": "object", "properties": {"check": {"type": "boolean"}}}},
]


def _arg(args: dict, k: str) -> str:
    """Required argv-bound string. A leading '-' would be parsed as a flag, so refuse it."""
    v = args.get(k)
    if not isinstance(v, str) or not v:
        raise ValueError(f"{k} must be a non-empty string")
    if v.startswith("-"):
        raise ValueError(f"{k} may not start with '-'")
    return v


class Server:
    TOOLS, SERVER = TOOLS, SERVER  # closer_mcp.py subclasses with its own list

    def __init__(self, state: Path):
        self.state = state
        self.wrapper = state / "gc-writer"
        self.repo = Path(json.loads((state / "manifest.json").read_text(encoding="utf-8"))["repo"])

    def gc(self, *argv: str, timeout: float | None = 600) -> tuple[str, bool]:
        r = subprocess.run([str(self.wrapper), *argv], capture_output=True, text=True, timeout=timeout)
        out = (r.stdout + (("\n" + r.stderr) if r.stderr else "")).strip()
        return f"{out}\n[exit {r.returncode}]", r.returncode != 0

    def call(self, name: object, args: object) -> tuple[str, bool]:
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        if name in ("tickets", "worlds", "check"):
            return self.gc(name)
        if name == "read":
            argv = ["read"]
            if args.get("world") is not None:
                argv += ["--world", _arg(args, "world")]
            keys = args.get("keys") or []
            if not isinstance(keys, list) or not all(isinstance(k, str) and not k.startswith("-") for k in keys):
                raise ValueError("keys must be a list of names")
            return self.gc(*argv, *keys)
        if name == "land":
            # No timeout: expiry is a SIGKILL, which no rollback in gc can catch, so a land cut off between
            # apply and its ledger row would stay applied and unledgered. C1 bounds itself (its clock and line budget); E1 has its own time limit.
            return self.gc("land", "--ticket", _arg(args, "ticket"), timeout=None)
        if name == "verify":
            return self.gc("verify", "--ticket", _arg(args, "ticket"))
        if name == "ledger":
            return self.gc(*(["ledger", "--check"] if args.get("check") is True else ["ledger"]))
        if name == "stage":
            return stage_mod.stage(self.state, _arg(args, "ticket"), _arg(args, "path"), _text(args, "content")), False
        if name == "stage_edit":
            return stage_mod.stage_edit(self.state, self.repo, _arg(args, "ticket"), _arg(args, "path"),
                                        _text(args, "old_string"), _text(args, "new_string"),
                                        args.get("replace_all") is True), False
        raise ValueError(f"unknown tool {name}")

    def handle(self, msg: dict) -> dict | None:
        mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
        if mid is None:
            return None  # notification (e.g. notifications/initialized)
        if method == "initialize":
            want = params.get("protocolVersion")
            return _ok(mid, {"protocolVersion": want if want in KNOWN_PROTOCOLS else DEFAULT_PROTOCOL,
                             "capabilities": {"tools": {}}, "serverInfo": self.SERVER})
        if method == "ping":
            return _ok(mid, {})
        if method == "tools/list":
            return _ok(mid, {"tools": self.TOOLS})
        if method == "tools/call":
            try:
                text, is_err = self.call(params.get("name"), params.get("arguments") or {})
            except (stage_mod.StageError, ValueError) as e:
                text, is_err = f"refused: {e}", True
            except Exception as e:  # noqa: BLE001 — a tool failure is a refusal, never a crash
                text, is_err = f"error: {type(e).__name__}: {e}", True
            return _ok(mid, {"content": [{"type": "text", "text": text}], "isError": is_err})
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}


def _text(args: dict, k: str) -> str:
    """File content / edit strings: any string, including a leading '-'."""
    v = args.get(k)
    if not isinstance(v, str):
        raise ValueError(f"{k} must be a string")
    return v


def _ok(mid, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: gc_mcp.py <state_dir>", file=sys.stderr)
        return 2
    return serve(Server(Path(sys.argv[1]).resolve()))


def serve(server) -> int:
    """The stdio loop: one JSON-RPC message per line in, one reply per line out. Shared with closer_mcp.py."""
    while True:
        line = sys.stdin.readline(MAX_LINE + 1)
        if not line:
            return 0
        if len(line) > MAX_LINE and not line.endswith("\n"):
            while (rest := sys.stdin.readline(MAX_LINE)) and not rest.endswith("\n"):
                pass  # drain the oversized line
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "request too large"}}
        elif not line.strip():
            continue
        else:
            try:
                msg = json.loads(line)
            except (ValueError, RecursionError):  # nesting bombs must not kill the server (red-team hole 5)
                reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            else:
                try:
                    reply = server.handle(msg) if isinstance(msg, dict) else None
                except RecursionError:
                    reply = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32600, "message": "too deep"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
