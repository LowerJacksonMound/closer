#!/usr/bin/env python3
"""verify_ticket — Layer-0 stub. Fail-closed. ZERO model calls. Stdlib only.

Runs the named verify with World + write_set in view (via env).
Must refuse: verify not found; verify imports apply/write; non-WORLD.md /
unfrozen / wrong world_id.
Does NOT import apply_ticket or any write helper.
WORLD.md Worlds have no absolute `root` / `started_at`; SCOPED_ROOT is only
from --scoped-root (or env already set by the caller).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, NoReturn

# Intentionally no import of apply_ticket / write helpers.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from world_v1 import load_world_v1, world_path  # noqa: E402


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"verify_ticket: {msg}", file=sys.stderr)
    raise SystemExit(code)


# Tripwire, not the boundary. These catch the plain spellings early with a clear message; a verify
# can always spell an import some other way. The boundary is run_sandboxed: whatever a verify
# imports or execs, it runs with writes denied to the kernel, the scoped repo and the gc state.
BANNED_IMPORT_RE = re.compile(
    r"(?m)^\s*(?:import\s+apply_ticket\b|from\s+apply_ticket\b"
    r"|import\s+apply\b|from\s+apply\b"
    r"|import\s+write\b|from\s+write\b)"
    r"|(?:import_module|__import__)\s*\(\s*['\"](?:apply_ticket|apply|write)['\"]"
)
BANNED_SHELL_RE = re.compile(
    r"(?m)(?:\bapply_ticket\b|\bapply_ticket\.py\b)"
)


def load_ticket(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        die(f"cannot load ticket: {e}")
    if not isinstance(data, dict):
        die("ticket is not a JSON object")
    for req in ("ticket_id", "world_id", "verify"):
        if req not in data:
            die(f"ticket missing required field: {req}")
    return data


def resolve_verify(name: str, verify_dirs: list[Path]) -> Path:
    candidates = [
        f"{name}.sh",
        f"{name}.py",
        name,
    ]
    for d in verify_dirs:
        for c in candidates:
            path = d / c
            if path.is_file():
                return path
    die(f"verify not in live/proposal/plant dirs: {name}")


def static_refuse_apply_write(verify_path: Path) -> None:
    try:
        text = verify_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        die(f"cannot read verify: {e}")
    if BANNED_IMPORT_RE.search(text):
        die(f"verify imports apply/write: {verify_path}")
    if verify_path.suffix == ".sh" and BANNED_SHELL_RE.search(text):
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if BANNED_SHELL_RE.search(line):
                die(f"verify invokes apply_ticket (forbidden): {verify_path}")


def _sb_quote(p: Path) -> str:
    return '"' + str(p).replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_only_paths(worlds_dir: Path, ticket_path: Path, scoped_root: str | None) -> list[Path]:
    """What a verify must not write: the kernel tree, the repo it judges, the Worlds, the ticket, and the
    gc state dir (ledger, tickets, payload) when the Worlds sit in one."""
    here = Path(__file__).resolve().parent.parent
    paths = [here, worlds_dir.resolve(), ticket_path.resolve().parent]
    state = worlds_dir.resolve().parent
    if (state / "ledger.jsonl").exists() or (state / "tickets").is_dir():
        paths.append(state)
    if scoped_root:
        paths.append(Path(scoped_root).resolve())
    return paths


def interpreter_roots(python: str) -> list[Path]:
    """The repo's interpreter tree (gc init --python), held read-only like the repo: its prefix as given
    (<prefix>/bin/python, a venv's root) and its prefix through symlinks (the base install), as real paths.
    Reading and executing it need no rule (the profile allows them everywhere); this only keeps a check from
    writing a venv that sits under a temp root. A prefix that would cover a temp root is left out."""
    py = Path(python)
    out = []
    for p in (py.parent.parent.resolve(), py.resolve().parent.parent):
        if p not in out and not any(t == p or p in t.parents for t in temp_roots()):
            out.append(p)
    return out


def temp_roots() -> list[Path]:
    """The only places a verify may write (scratch space), as real paths."""
    return sorted({Path("/private/var/folders"), Path("/private/tmp"), Path(tempfile.gettempdir()).resolve()})


def run_sandboxed(cmd: list[str], env: dict[str, str], deny_write: list[Path]) -> int:
    """K2 for verifies: run under sandbox-exec with loopback-only network and file writes only to temp dirs, and
    never below a deny_write path, even one inside temp (the last rule wins). Strict for every check
    because C1 and E1 run ticket code here and macOS will not apply a second sandbox inside this one
    (KERNEL.md I2). No sandbox-exec -> refuse; a verify that could write is not a verify."""
    sbx = shutil.which("sandbox-exec")
    if not sbx:
        # 75 = not run (M5a): the host's fault, not the writer's, so the land is refused without a strike.
        die("no sandbox-exec on this host: cannot hold a verify read-only, refusing to run it", 75)
    # Seatbelt matches real paths: /var -> /private/var, /tmp -> /private/tmp. Unresolved, a deny never fires.
    # The deny_write clause must stay LAST: the last matching rule wins, which is what keeps a denied
    # path nested under a temp root (e.g. a gc state dir in /tmp) unwritable.
    # I2 (re-ruled 2026-10-19): network to the outside world is denied; loopback is the machine talking to itself. One rule per operation: filters inside one rule are OR'd, and an outbound
    # rule with a `local` filter let 1.1.1.1 through. Seatbelt hosts are only `*` or `localhost` (127/8 and ::1).
    profile = ("(version 1)(allow default)(deny network*)"
               '(allow network-bind network-inbound (local ip "localhost:*"))'
               '(allow network-outbound (remote ip "localhost:*"))'
               "(deny file-write*)(allow file-write* "
               + " ".join(f"(subpath {_sb_quote(p)})" for p in temp_roots())
               + ' (literal "/dev/null") (literal "/dev/tty") (literal "/dev/dtracehelper"))'
               + "(deny file-write* " + " ".join(f"(subpath {_sb_quote(p.resolve())})" for p in deny_write) + ")")
    env = {**env, "PYTHONDONTWRITEBYTECODE": "1", "VERIFY_SANDBOX": "strict"}
    return subprocess.run([sbx, "-p", profile, *cmd], env=env).returncode


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Verify a ticket (fail-closed).")
    p.add_argument("--ticket", required=True, help="Path to ticket JSON")
    p.add_argument(
        "--worlds-dir",
        default=None,
        help="Worlds directory (default: ../worlds)",
    )
    p.add_argument(
        "--verify-dir",
        action="append",
        default=[],
        help="Directory to search for verify programs (repeatable). "
        "Default search: pack/live, proposals, and CWD.",
    )
    p.add_argument(
        "--scoped-root",
        default=None,
        help="Optional SCOPED_ROOT for pollution / verify env "
        "(WORLD.md Worlds have no absolute root field)",
    )
    p.add_argument(
        "--before-root",
        default=None,
        help="Pre-apply copy of the write_set (gc land sets it; KERNEL.md M5). Passed as BEFORE_ROOT, read-only",
    )
    p.add_argument(
        "--repo-python",
        default=None,
        help="The repo's interpreter (gc init --python). Passed as REPO_PYTHON, its tree read-only; "
        "absent, an inherited REPO_PYTHON is cleared",
    )
    p.add_argument(
        "--check",
        default=None,
        help="Run this pack check instead of the ticket's verify (pack v2 every_ticket checks)",
    )
    args = p.parse_args(argv)

    here = Path(__file__).resolve().parent.parent
    ticket = load_ticket(Path(args.ticket))
    worlds_dir = Path(args.worlds_dir) if args.worlds_dir else here / "worlds"
    try:
        wf = world_path(worlds_dir, str(ticket["world_id"]))
    except ValueError as e:
        die(str(e))

    # Fail-closed: WORLD.md v1 + frozen + id match. No retired sketch `root` fallback.
    load_world_v1(
        wf,
        expect_world_id=str(ticket["world_id"]),
        require_frozen=True,
        tool="verify_ticket",
    )

    verify_dirs: list[Path] = [Path(d) for d in args.verify_dir]
    if not verify_dirs:
        verify_dirs = [here / "pack" / "live", here / "proposals", Path.cwd()]

    name = args.check or str(ticket["verify"])
    verify_path = resolve_verify(name, verify_dirs)
    static_refuse_apply_write(verify_path)

    env = os.environ.copy()
    env["WORLD_FILE"] = str(wf.resolve())
    env["TICKET_ID"] = str(ticket["ticket_id"])
    env["TICKET_FILE"] = str(Path(args.ticket).resolve())
    write_set = ticket.get("write_set") or []
    env["WRITE_SET"] = json.dumps(write_set)
    if args.scoped_root:
        env["SCOPED_ROOT"] = str(Path(args.scoped_root).resolve())
    if args.before_root:
        env["BEFORE_ROOT"] = str(Path(args.before_root).resolve())
    # REPO_PYTHON comes from the manifest only (gc passes --repo-python); never from the caller's environment.
    env.pop("REPO_PYTHON", None)
    if args.repo_python:
        env["REPO_PYTHON"] = args.repo_python
    # Do NOT invent SCOPED_ROOT from retired sketch key `root` (WORLD.md has roots[] only).

    if verify_path.suffix == ".py":
        cmd = [sys.executable, str(verify_path)]
    else:
        cmd = ["sh", str(verify_path)]

    print(f"verify_ticket: running {verify_path} WORLD_FILE={env['WORLD_FILE']}", flush=True)
    deny = read_only_paths(worlds_dir, Path(args.ticket), args.scoped_root)
    if args.before_root:
        deny.append(Path(args.before_root).resolve())
    if args.repo_python:
        deny += interpreter_roots(args.repo_python)
    rc = run_sandboxed(cmd, env, deny)
    if rc != 0:
        print(
            f"verify_ticket: FAIL ticket_id={ticket['ticket_id']} "
            f"verify={name} exit={rc}",
            file=sys.stderr,
        )
        return rc

    print(f"verify_ticket: PASS ticket_id={ticket['ticket_id']} verify={name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
