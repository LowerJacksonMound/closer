#!/usr/bin/env python3
"""closer as a stdio MCP server for the SIGNER's own Claude session. Stdlib only. ZERO model calls.

usage: python3 closer_mcp.py            (closer-mcp.sh at the tree root does this)

Every tool runs the front door, `closer <command>` (ui/go.py), inside the repo the caller names, as an argument
list, never a shell string. This process adds no rule and touches no kernel file. The writer's own MCP is gc_mcp.py
and stays separate: this server never hands the writer anything.

The yes stays with the person (T5). cl_go refuses until cl_claims has shown this repo and task's claims in this
process, and its `approved` argument is the person's word that the agent must have been given. The agent cannot
mint on its own reading of the claims.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import gc_mcp

ROOT = Path(__file__).resolve().parents[2]
GO = [sys.executable, str(ROOT / "ui" / "go.py")]

_REPO = {"type": "string", "description": "absolute path of the repo (the folder `closer go` would run in)"}
_TASK = {"type": "string", "description": "absolute path of the TASK.md (`closer task NAME` writes a skeleton)"}
_REG = {"python": {"type": "string", "description": "the repo's interpreter; default ./.venv or ./venv, else the gate's own"},
        "pytest_args": {"type": "string", "description": "pytest arguments; default the repo's own config, else tests/"}}
TOOLS = [
    {"name": "cl_doctor", "description": "Is this machine ready, and do this repo's tests collect? Run first.",
     "inputSchema": {"type": "object", "required": ["repo"], "properties": {"repo": _REPO, **_REG}}},
    {"name": "cl_task", "description": "Write a TASK.md skeleton named NAME into the repo for the person to fill in. Returns its path.",
     "inputSchema": {"type": "object", "required": ["repo", "name"], "properties": {"repo": _REPO, "name": {"type": "string"}}}},
    {"name": "cl_claims", "description": "Register the repo if new, draft the claims for a task, and show them. Nothing is minted. "
                                          "Show the person every claim as printed; they decide.",
     "inputSchema": {"type": "object", "required": ["repo", "task"], "properties": {
         "repo": _REPO, "task": _TASK, "redraft": {"type": "boolean"}, **_REG}}},
    {"name": "cl_go", "description": "Mint the ticket, open the live page, run the restricted writer, and report the verdict. "
                                      "Blocks until the writer ends (minutes). Refused until cl_claims has shown this task's claims "
                                      "and the person has said yes to them: approved is their word, not yours.",
     "inputSchema": {"type": "object", "required": ["repo", "task", "approved"], "properties": {
         "repo": _REPO, "task": _TASK,
         "approved": {"type": "boolean", "description": "true only after the person read the claims and said to mint"},
         "write": {"type": "array", "items": {"type": "string"}, "description": "extra write-set files, repo-relative"},
         "port": {"type": "integer", "description": "live page port, default 8766"}}}},
    {"name": "cl_status", "description": "What the live page shows now, as text.",
     "inputSchema": {"type": "object", "required": ["repo"], "properties": {"repo": _REPO}}},
    {"name": "cl_inspect", "description": "One ticket's verdict in plain words (default: the newest).",
     "inputSchema": {"type": "object", "required": ["repo"], "properties": {
         "repo": _REPO, "ticket": {"type": "string"}, "raw": {"type": "boolean", "description": "add the gate's own lines"}}}},
    {"name": "cl_stop", "description": "Stop the repo's live page server and watcher.",
     "inputSchema": {"type": "object", "required": ["repo"], "properties": {"repo": _REPO}}},
]


def _path(args: dict, k: str) -> Path:
    v = args.get(k)
    if not isinstance(v, str) or not v or v.startswith("-"):
        raise ValueError(f"{k} must be a non-empty path")
    p = Path(v).expanduser()
    if not p.is_absolute():
        raise ValueError(f"{k} must be absolute (relative paths resolve against this server, not your shell): {v}")
    return p.resolve()


class Outer(gc_mcp.Server):
    TOOLS, SERVER = TOOLS, {"name": "closer", "version": "1"}

    def __init__(self):
        self.shown: set[tuple[Path, Path, str]] = set()  # (repo, task, task text) cl_claims has printed
        # The front door launches `claude` for the writer; a nested Claude Code refuses to start while these are set.
        self.env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}

    def closer(self, repo: Path, *argv: str, timeout: float | None = 600) -> tuple[str, bool]:
        if not repo.is_dir():
            raise ValueError(f"repo is not a directory: {repo}")
        r = subprocess.run(GO + list(argv), cwd=repo, env=self.env, capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        out = (r.stdout + (("\n" + r.stderr) if r.stderr else "")).strip()
        return f"{out}\n[exit {r.returncode}]", r.returncode != 0

    def call(self, name: object, args: object) -> tuple[str, bool]:
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        repo = _path(args, "repo")
        reg = []
        for k, flag in (("python", "--python"), ("pytest_args", "--pytest-args")):
            if args.get(k) is not None:
                reg += [flag, gc_mcp._arg(args, k)]
        if name == "cl_doctor":
            return self.closer(repo, "doctor", *reg)
        if name == "cl_task":
            return self.closer(repo, "task", gc_mcp._arg(args, "name"))
        if name in ("cl_status", "cl_stop"):
            return self.closer(repo, name[3:])
        if name == "cl_inspect":
            argv = ["inspect"] + ([gc_mcp._arg(args, "ticket")] if args.get("ticket") is not None else [])
            return self.closer(repo, *argv, *(["--raw"] if args.get("raw") is True else []))
        if name == "cl_claims":
            task = _path(args, "task")
            if not task.is_file():
                raise ValueError(f"no such task file: {task}")
            # --yes here only accepts the registration guess (doctor shows it); `claims` never mints.
            text, err = self.closer(repo, "claims", str(task), "--yes", *reg, *(["--redraft"] if args.get("redraft") is True else []))
            if not err:
                self.shown.add((repo, task, task.read_text()))
            return text, err
        if name == "cl_go":
            task = _path(args, "task")
            if not task.is_file():
                raise ValueError(f"no such task file: {task}")
            if (repo, task, task.read_text()) not in self.shown:
                raise ValueError("cl_claims first: the person reads the claims before anything is minted (the task text changed, or was never drafted here)")
            if args.get("approved") is not True:
                raise ValueError("approved must be true, and only the person says it")
            argv = ["go", str(task), "--yes", "--no-open"]
            for w in args.get("write") or []:
                argv += ["--write", gc_mcp._arg({"w": w}, "w")]
            if args.get("port") is not None:
                if not isinstance(args["port"], int):
                    raise ValueError("port must be an integer")
                argv += ["--port", str(args["port"])]
            # No timeout: the writer's land must not be cut off between apply and its ledger row (see gc_mcp land).
            return self.closer(repo, *argv, timeout=None)
        raise ValueError(f"unknown tool {name}")


if __name__ == "__main__":
    raise SystemExit(gc_mcp.serve(Outer()))
