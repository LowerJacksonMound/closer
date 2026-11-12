#!/usr/bin/env python3
"""closer_gate v6 (2026-11-10, t118): Claude Code PreToolUse hook. Code in Python, web (HTML/JS/TS) and Python+web
repos changes only through the CLOSER MCP server's one tool, cl_submit. Stdlib only. No git anywhere: no git commands, no .git lookups, no git-specific cases.

Not wired by this file. Ian removed the hooks from ~/.claude/settings.json on 2026-11-10; the proposed wiring and the
sandbox block live in ~/.claude/hooks/closer_gate_settings.PROPOSED.json (generated, not applied).

Two layers, both file level
  1. Edit / Write / MultiEdit / NotebookEdit: this hook resolves the target path and denies a gated write.
  2. Bash: Claude Code's OS sandbox (Seatbelt on macOS). `--emit-sandbox` writes sandbox.filesystem.denyWrite
     entries for every gated repo's code files plus CLOSER's sealed state, with allowUnsandboxedCommands=false.
     The OS refuses the write whatever the command looks like, so this hook does not parse shell commands.
     For Bash the hook only (a) denies dangerouslyDisableSandbox when cwd is in a gated repo and (b) checks that
     a sandbox block covering that repo is configured; if not, it allows, logs "bash-unenforced" and notifies
     (fail open, visible). The hook can't see a --settings file; set CLOSER_GATE_SANDBOX_SETTINGS=<that file>
     so the check can read it.

Scope: repos that are Python, web (HTML/JS/TS), or Python+web.
  1. Path listed in ~/.claude/closer_gate_skip.txt     -> out of scope (opt-out wins)
  2. Path listed in ~/.claude/closer_gate_roots.txt    -> gated, no classification (opt-in)
  3. Innermost CLOSER-registered repo (~/.closer/*/manifest.json "repo") or innermost folder holding a
     project marker (Python: pyproject.toml, setup.py, setup.cfg; web: package.json, deno.json), never $HOME or /
     itself and never a folder inside node_modules/site-packages/.venv/venv (a vendored package is not a repo)
                                                       -> gated if it classifies as python, web, or python+web
  4. Anything else                                     -> out of scope
  Classification (bounded walk, skip hidden/.venv/node_modules/..., WALK_CAP files):
    - DATA_EXT (.json except markers, .yaml, .toml, .css, .md, ...) are ignored.
    - .py/.pyi/.pyx and notebooks (.ipynb) count as Python; WEB_EXT files count as web.
    - WEB_MARKERS (package.json, deno.json) mark a web project root. A marker with no code file yet is a fresh
      project and is gated by the marker (pyproject.toml: python, package.json: web); only a folder with neither
      marker nor code is "no-code".
    - python / web / python+web are gated; mixed (any other language, shell scripts included) is not, unless
      opted in via roots.txt. A walk that hits WALK_CAP is "too-large" (out of scope, logged and notified).
      Cached per repo for 120 s.
  In a gated repo a write to any CODE_EXT file, any .html/.htm, or a path in ~/.claude/closer_gate_protect.txt is
  gated. ~/.claude/** and Claude's scratchpad (/tmp/claude-*/) are never gated.

The flow (one agent, 2026-11-10): the agent knows the user's intent and submits one function at a time with
  cl_submit(file, source, checks), the checks being what the intent expects that function to do. CLOSER runs it
  (run -> compare with the checks) BEFORE anything is written and writes only a pass. No direct code write is
  allowed in a gated repo: code reaches the page only through cl_submit (CLOSER's own process, outside the Bash
  sandbox). A test file is code like any other.

Always denied (Edit/Write path): CLOSER's sealed state (<state>/intent/, landed.json, strikes.jsonl,
agree.jsonl, plans.jsonl, holes.jsonl: a forged strike would turn the next first fail into a hole), the
gate's own controls (switch files, closer_gate*.py, its cache/stamps, its proposed settings, settings.json hook
edits) and content that assigns CLOSER_GATE_OFF. Under the sandbox the same paths are OS-protected for Bash
(~/.claude is a Claude Code protected path; sealed state is in the generated denyWrite list).

Fail mode: FAIL OPEN. On an internal error or unreadable input the call is allowed, logged, a systemMessage is shown
and a macOS notification fires ("CLOSER gate", at most one per 60 s). Hook timeouts SIGKILL the script, so every
run leaves a marker in ~/.claude/hooks/.closer_gate_inflight/; the next run that finds one > 10 s old notifies.

Tries (in CLOSER's judge.py, not this hook; the process is never blocked), per file::function:
  Try 1 passes → written. Try 1 fails (could not run, or ran but did not match the intent) → nothing written; the
  agent resubmits. Try 2 passes → written. Try 2 fails → NOTHING written, a hole record (location, anchor, both
  reasons) is appended to <state>/holes.jsonl, and the location takes no more submissions. CodeRadar consumes the
  hole log later.
This hook reads paths, never the contents of a repo file: the repo walk lists names, and it reads only CLOSER's
  state manifests and its own control files.
Off switch: env CLOSER_GATE_OFF=1 or the file ~/.claude/closer_gate.off. Log: ~/.claude/hooks/closer_gate.log.
Known gaps: see the KNOWN GAPS block at the end of this file.

usage: python3 closer_gate.py                     (hook; event JSON on stdin)
       python3 closer_gate.py --classify DIR       (how the gate scopes DIR)
       python3 closer_gate.py --emit-sandbox [OUT] (write the proposed settings file; default
                                                    ~/.claude/hooks/closer_gate_settings.PROPOSED.json)
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
HOOKS = HOME / ".claude" / "hooks"
LOG = HOOKS / "closer_gate.log"
CACHE = HOOKS / ".closer_gate_cache.json"
INFLIGHT = HOOKS / ".closer_gate_inflight"
NOTIFY_STAMP = HOOKS / ".closer_gate_notify.stamp"
OFF_FILE = HOME / ".claude" / "closer_gate.off"
ROOTS_FILE = HOME / ".claude" / "closer_gate_roots.txt"
SKIP_FILE = HOME / ".claude" / "closer_gate_skip.txt"
PROTECT_FILE = HOME / ".claude" / "closer_gate_protect.txt"
PROPOSED = HOOKS / "closer_gate_settings.PROPOSED.json"
CACHE_TTL, STALE_S, NOTIFY_EVERY_S, WALK_CAP = 120, 10, 60, 20000

PY_EXT = {".py", ".pyi", ".pyx"}
WEB_EXT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".vue", ".svelte", ".html", ".htm"}
CODE_EXT = {
    ".py", ".pyi", ".pyx", ".ipynb",
    ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".vue", ".svelte",
    ".go", ".rs", ".java", ".kt", ".kts", ".scala", ".groovy", ".rb", ".php", ".pl", ".pm", ".lua", ".r", ".jl",
    ".swift", ".m", ".mm", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".cs", ".fs", ".ex", ".exs", ".erl",
    ".hs", ".ml", ".clj", ".dart", ".zig", ".nim", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".sql", ".tf",
}
HTML_EXT = {".html", ".htm"}
# Ordinary data/config files never flip a repo to mixed. package.json stays a positive web marker.
DATA_EXT = {".json", ".yaml", ".yml", ".toml", ".css", ".scss", ".svg", ".lock", ".md", ".txt", ".csv"}
NONPY_MARKERS = {"package.json", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile",
                 "composer.json", "Package.swift", "CMakeLists.txt", "mix.exs", "deno.json", "pubspec.yaml"}
WEB_MARKERS = {"package.json", "deno.json"}
NONPY_MARKER_EXT = {".csproj", ".sln", ".xcodeproj"}
PY_PROJECT_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg")
PROJECT_MARKERS = PY_PROJECT_MARKERS + tuple(sorted(WEB_MARKERS))
VENDOR_DIRS = {"node_modules", "bower_components", "site-packages", ".venv", "venv"}  # never a repo root inside these
WALK_SKIP = {"venv", "env", "node_modules", "__pycache__", "build", "dist", "site-packages"}  # + every hidden dir
WRITE_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}

FLOW = ("cl_submit(file, source: one complete def, checks: what the user's intent expects it to do, e.g. "
        "call add(2, 3) expect 5), one function at a time; two tries per function")
REASON = ("closer_gate: direct code writes are blocked here ({what}). Code in {repo} reaches the page only through the "
          "CLOSER MCP tools: " + FLOW + ". CLOSER runs every function and compares it with the intent before anything is written; "
          "no approval step is needed. Do not retry this write by another route.")


class GateError(Exception):
    """A fail-open condition worth reporting."""


# ---- paths -----------------------------------------------------------------

def gc_home() -> Path:
    return Path(os.environ.get("CLOSER_HOME") or (HOME / ".closer"))


def resolve(p: str, cwd: str) -> Path:
    p = os.path.expandvars(os.path.expanduser(p))
    q = Path(p) if os.path.isabs(p) else Path(cwd or os.getcwd()) / p
    parts, cur = [], q
    while not cur.exists() and cur != cur.parent:
        parts.append(cur.name); cur = cur.parent
    out = Path(os.path.realpath(cur))
    for name in reversed(parts):
        out = out / name
    return Path(os.path.normpath(str(out)))


def under(p: Path, root: Path) -> bool:
    return p == root or str(p).startswith(str(root).rstrip("/") + "/")


def is_code(p: Path) -> bool:
    return p.suffix.lower() in CODE_EXT


def is_html(p: Path) -> bool:
    return p.suffix.lower() in HTML_EXT


def protect_globs() -> list[str]:
    try:
        lines = PROTECT_FILE.read_text().splitlines()
    except OSError:
        return []
    return [os.path.expanduser(l.strip()) for l in lines if l.strip() and not l.strip().startswith("#")]


def matches_protect(p: Path) -> bool:
    s = str(p)
    return any(s == g or fnmatch.fnmatch(s, g) for g in protect_globs())


def gateable(p: Path) -> bool:
    """A write worth routing through CLOSER in a gated repo: code, HTML, or a protected file."""
    return is_code(p) or is_html(p) or matches_protect(p)


def registered() -> dict[Path, list[Path]]:
    """repo (realpath) -> CLOSER state dirs registered for it."""
    out: dict[Path, list[Path]] = {}
    home = gc_home()
    if not home.is_dir():
        return out
    for mf in home.glob("*/manifest.json"):
        try:
            repo = json.loads(mf.read_text()).get("repo")
        except (OSError, ValueError):
            continue
        if isinstance(repo, str) and repo:
            out.setdefault(Path(os.path.realpath(repo)), []).append(mf.parent)
    return out


def list_file(f: Path) -> list[Path]:
    try:
        lines = f.read_text().splitlines()
    except OSError:
        return []
    return [Path(os.path.realpath(os.path.expanduser(l.strip()))) for l in lines if l.strip() and not l.startswith("#")]


def innermost(p: Path, roots: list[Path]) -> Path | None:
    hits = [r for r in roots if under(p, r)]
    return max(hits, key=lambda r: len(str(r))) if hits else None


def marker_root(p: Path) -> Path | None:
    """Innermost ancestor of p holding a Python or web project marker; never $HOME or / itself, and never a folder
    inside a skipped dir (node_modules/x/package.json is a vendored package, not a repo)."""
    home = Path(os.path.realpath(HOME))
    cur = p.parent
    while cur != cur.parent and cur != home:
        vendored = any(part in VENDOR_DIRS for part in cur.parts)
        if not vendored and any((cur / m).is_file() for m in PROJECT_MARKERS):
            return cur
        cur = cur.parent
    return None


def repo_root(p: Path, regs: dict[Path, list[Path]]) -> Path | None:
    """Innermost CLOSER-registered repo or project-marker folder (Python or web) containing p."""
    cands = [c for c in (innermost(p, list(regs)), marker_root(p)) if c is not None]
    return max(cands, key=lambda r: len(str(r))) if cands else None


def repo_files(root: Path) -> tuple[list[str], bool]:
    """(relative file paths, complete). Bounded walk; complete=False when WALK_CAP was hit."""
    out: list[str] = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in WALK_SKIP and not d.startswith(".")]
        rel = os.path.relpath(dp, root)
        out += [fn if rel == "." else os.path.join(rel, fn) for fn in fns]
        if len(out) > WALK_CAP:
            return out, False
    return out, True


def classify_files(files: list[str]) -> tuple[str, str]:
    """('python'|'web'|'python+web'|'mixed'|'non-Python'|'no-code', why).
    DATA_EXT files are ignored. WEB_MARKERS confirm a web project instead of excluding it.
    """
    py, web, other = 0, 0, []
    has_web_marker = has_py_marker = False
    for f in files:
        name = os.path.basename(f)
        ext = os.path.splitext(name)[1].lower()
        if name in WEB_MARKERS:
            has_web_marker = True
            continue
        if name in PY_PROJECT_MARKERS:
            has_py_marker = True
        if name in NONPY_MARKERS or ext in NONPY_MARKER_EXT:
            other.append(f)
            continue
        if ext in DATA_EXT:
            continue
        if ext in PY_EXT or ext == ".ipynb":
            py += 1
        elif ext in WEB_EXT:
            web += 1
        elif ext in CODE_EXT:
            other.append(f)
    if other:
        more = f" (+{len(other)-3})" if len(other) > 3 else ""
        return ("mixed" if (py or web) else "non-Python"), f"non-Python code/markers: {', '.join(sorted(other)[:3])}{more}"
    if py and web:
        return "python+web", f"{py} Python, {web} web file(s)"
    if py:
        return "python", f"{py} Python file(s), no other code"
    if web:
        return "web", f"{web} web file(s)" + (" + marker" if has_web_marker else "")
    if has_py_marker or has_web_marker:  # a fresh project: the code is about to be written, so gate by the marker
        kind = "python+web" if has_py_marker and has_web_marker else "python" if has_py_marker else "web"
        return kind, "no code files yet, gated by its project marker"
    return "no-code", "no Python or web code files"


def classify(root: Path) -> tuple[str, str]:
    """Cached per repo for CACHE_TTL seconds."""
    key = str(root)
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    hit = cache.get(key)
    if hit and time.time() - hit.get("ts", 0) < CACHE_TTL:
        return hit["cls"], hit["why"] + " (cached)"
    files, complete = repo_files(root)
    if complete:
        cls, why = classify_files(files)
    else:
        cls, why = "too-large", f"walk stopped at {WALK_CAP} files"
    cache = {k: v for k, v in cache.items() if time.time() - v.get("ts", 0) < CACHE_TTL}
    cache[key] = {"cls": cls, "why": why, "ts": time.time()}
    try:
        tmp = CACHE.with_name(CACHE.name + f".{os.getpid()}")
        tmp.write_text(json.dumps(cache)); os.replace(tmp, CACHE)
    except OSError:
        pass
    return cls, why


def scope(p: Path, regs: dict[Path, list[Path]]) -> tuple[Path | None, str]:
    """(gated root or None, why)."""
    skip = innermost(p, list_file(SKIP_FILE))
    if skip:
        return None, f"out of scope: opted out in closer_gate_skip.txt ({skip})"
    opt = innermost(p, list_file(ROOTS_FILE))
    if opt:
        return opt, f"opted in via closer_gate_roots.txt ({opt})"
    root = repo_root(p, regs)
    if root is None:
        return None, "out of scope: not in a CLOSER-registered repo or a Python/web project folder"
    cls, why = classify(root)
    if cls not in ("python", "web", "python+web"):
        return None, f"out of scope: {root} is {cls} ({why})"
    return root, f"gated {cls} repo {root} ({why})"



def exempt(p: Path) -> bool:
    return (under(p, Path(os.path.realpath(HOME / ".claude")))
            or re.match(r"^(/private)?/tmp/claude-[^/]+/", str(p)) is not None)


def forged_state_path(p: Path) -> bool:
    home = Path(os.path.realpath(gc_home()))
    if not under(p, home):
        return False
    rel = Path(os.path.relpath(p, home)).parts
    return len(rel) >= 2 and (rel[1] == "intent" or rel[1].startswith(("landed.json", "strikes.jsonl", "holes.jsonl", "agree.jsonl", "plans.jsonl", "holes.errors")))


def gate_protected(p: Path) -> Path | None:
    """The gate's own controls, off-limits regardless of cwd."""
    c = Path(os.path.realpath(HOME / ".claude"))
    hooks = c / "hooks"
    if p in {c / "closer_gate.off", c / "closer_gate_skip.txt", c / "closer_gate_roots.txt",
             c / "closer_gate_protect.txt", c / "settings.json"}:
        return p
    if under(p, hooks):
        if fnmatch.fnmatch(p.name, "closer_gate*.py") or fnmatch.fnmatch(p.name, "closer_gate_settings*.json"):
            return p
        if p.name in (".closer_gate_cache.json", ".closer_gate_notify.stamp"):
            return p
        if under(p, hooks / ".closer_gate_inflight") or under(p, hooks / ".closer_gate_nudged"):
            return p
    return None



# ---- file-level Bash enforcement: the sandbox block ------------------------

def sealed_state_globs() -> list[str]:
    h = str(Path(os.path.realpath(gc_home())))
    return [f"{h}/*/intent", f"{h}/*/landed.json", f"{h}/*/landed.json.*", f"{h}/*/strikes.jsonl", f"{h}/*/holes.jsonl",
            f"{h}/*/agree.jsonl", f"{h}/*/plans.jsonl", f"{h}/*/holes.errors"]


def repo_deny_globs(root: Path) -> list[str]:
    """denyWrite entries for one gated repo: every code/HTML extension anywhere in it, plus the protect-list entries
    that sit inside it. macOS Seatbelt honours * and ** here (Linux only a trailing /**). sandbox-runtime turns
    `<r>/**/*.py` into ^<r>/(.*/)?[^/]*[.]py(/.*)?$, so it covers top-level files too."""
    r = str(root).rstrip("/")
    out = []
    for ext in sorted(CODE_EXT | HTML_EXT):
        out.append(f"{r}/**/*{ext}")
    out += [g for g in protect_globs() if under(Path(g.split("*")[0].rstrip("/") or "/"), root)]
    return out


def gated_repos(regs: dict[Path, list[Path]] | None = None) -> list[tuple[Path, str]]:
    """Every existing repo the gate would gate today: roots.txt entries plus registered repos that classify python, web or python+web."""
    regs = registered() if regs is None else regs
    out: dict[Path, str] = {}
    for r in list_file(ROOTS_FILE):
        if r.is_dir():
            out[r] = "roots.txt"
    for r in regs:
        if r in out or not r.is_dir() or exempt(r / "x.py"):
            continue
        root, why = scope(r / "__probe__.py", regs)
        if root == r:
            out[r] = why
    return sorted(out.items(), key=lambda kv: str(kv[0]))


def sandbox_block(repos: list[Path]) -> dict:
    deny: list[str] = []
    for r in repos:
        deny += repo_deny_globs(r)
    deny += sealed_state_globs()
    return {"enabled": True, "allowUnsandboxedCommands": False, "failIfUnavailable": True,
            "filesystem": {"denyWrite": list(dict.fromkeys(deny))}}


def proposed_settings(repos: list[Path]) -> dict:
    gate = str(HOOKS / "closer_gate.py")
    nudge = str(HOOKS / "closer_gate_nudge.py")
    return {
        "_comment": ("PROPOSED by closer_gate.py --emit-sandbox. NOT applied. apply_sandbox.py puts each gated repo's own "
                     "block in <repo>/.claude/settings.local.json (never the global file: a global block sandboxes every "
                     "session). Re-run apply_sandbox.py when gated repos change."),
        "sandbox": sandbox_block(repos),
        "hooks": {
            "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash",
                            "hooks": [{"type": "command", "command": f"python3 {gate}", "timeout": 10}]}],
            "SessionStart": [{"hooks": [{"type": "command", "command": f"python3 {nudge}", "timeout": 10}]}],
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": f"python3 {nudge}", "timeout": 10}]}],
        },
    }


def _settings_candidates(root: Path, cwd: str) -> list[Path]:
    c = [HOME / ".claude" / "settings.json", root / ".claude" / "settings.json", root / ".claude" / "settings.local.json"]
    if cwd:
        c += [Path(cwd) / ".claude" / "settings.json", Path(cwd) / ".claude" / "settings.local.json"]
    if os.environ.get("CLOSER_GATE_SANDBOX_SETTINGS"):
        c.append(Path(os.environ["CLOSER_GATE_SANDBOX_SETTINGS"]))
    return c


def sandbox_covers(root: Path, cwd: str = "") -> tuple[bool, str]:
    """Is a sandbox block that write-denies root's .py files configured in a settings file the hook can read?"""
    enabled, disabled_fs, unsandboxed_ok, denies, seen = False, False, True, [], []
    for f in _settings_candidates(root, cwd):
        try:
            sb = json.loads(f.read_text()).get("sandbox") or {}
        except (OSError, ValueError, AttributeError):
            continue
        seen.append(str(f))
        enabled |= sb.get("enabled") is True
        if sb.get("allowUnsandboxedCommands") is False:
            unsandboxed_ok = False
        fs = sb.get("filesystem") or {}
        disabled_fs |= fs.get("disabled") is True
        denies += [d for d in fs.get("denyWrite") or [] if isinstance(d, str)]
    r = str(root).rstrip("/")
    covered = f"{r}/**/*.py" in denies or r in denies or f"{r}/**" in denies
    if not enabled:
        return False, "sandbox.enabled is not true in any readable settings file"
    if disabled_fs:
        return False, "sandbox.filesystem.disabled is true"
    if not covered:
        return False, f"no sandbox.filesystem.denyWrite entry covers {r}/**/*.py"
    if unsandboxed_ok:
        return False, "allowUnsandboxedCommands is not false (Claude could retry a command unsandboxed)"
    return True, "sandbox covers this repo (" + ", ".join(seen) + ")"


# ---- decision --------------------------------------------------------------

def decide(event: dict) -> tuple[str, str, list[str]]:
    """('allow'|'deny', reason, targets). 'allow' means no decision: the normal permission flow applies."""
    if os.environ.get("CLOSER_GATE_FORCE_CRASH") == "1":
        raise RuntimeError("forced crash (CLOSER_GATE_FORCE_CRASH=1)")
    tool = event.get("tool_name")
    ti = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    cwd = event.get("cwd") or os.getcwd()
    if tool == "Bash":
        return decide_bash(ti, cwd)
    if tool not in WRITE_TOOLS:
        return "allow", "tool not gated", []
    raw = ti.get(WRITE_TOOLS[tool]) or ti.get("file_path") or ti.get("notebook_path")
    if not isinstance(raw, str) or not raw:
        return "allow", "no path", []
    t = resolve(raw, cwd)
    shown = [str(t)]
    body = " ".join(str(ti.get(k, "")) for k in ("content", "new_string")) + json.dumps(ti.get("edits", ""))
    if re.search(r"\bCLOSER_GATE_OFF\s*=", body):
        return "deny", ("closer_gate: writing a CLOSER_GATE_OFF assignment would switch the gate off. Code changes go "
                        "through the CLOSER MCP tools: " + FLOW + "."), shown
    gp = gate_protected(t)
    if gp is not None:
        if gp.name == "settings.json" and tool in ("Edit", "MultiEdit", "Write"):
            hooky = re.compile(r"hook|closer_gate|sandbox|disableAll|PreToolUse|PostToolUse|UserPromptSubmit|"
                               r'SessionStart|SubagentStop|PreCompact|Notification|"Stop"|matcher|"command"', re.I)
            if tool == "Edit":
                touches = bool(hooky.search(str(ti.get("old_string", ""))) or hooky.search(str(ti.get("new_string", ""))))
            elif tool == "MultiEdit":
                touches = bool(hooky.search(json.dumps(ti.get("edits", ""))))
            else:
                try:
                    cur = json.loads(gp.read_text())
                    new = json.loads(str(ti.get("content", "")))
                    keys = ("hooks", "disableAllHooks", "sandbox")
                    touches = tuple(cur.get(k) for k in keys) != tuple(new.get(k) for k in keys)
                except (OSError, ValueError, AttributeError):
                    touches = True
            if not touches:
                return "allow", "settings.json edit leaves hooks and sandbox alone", shown
            return "deny", (f"closer_gate: this edit touches the hooks or sandbox block in {gp}. Those are the gate's "
                            "own wiring and are not changed from inside a Claude session."), shown
        return "deny", (f"closer_gate: {gp} is one of the gate's own controls (switches, hook scripts, cache, proposed "
                        "settings). A Claude session may not write, move, or delete it."), shown
    if forged_state_path(t):
        return "deny", (f"closer_gate: {t} is CLOSER's sealed state (intent, landed.json, strikes/agree/plans/holes). Only "
                        "CLOSER writes there."), shown
    if exempt(t) or not gateable(t):
        return "allow", "no gated code write", shown
    regs = registered()
    root, why = scope(t, regs)
    if root is None:
        if "too-large" in why:
            notify(f"repo too large to classify, write allowed: {t}")
        return "allow", why, shown
    rel = os.path.relpath(t, root)
    if is_html(t):
        what = f"{tool} on {rel} (HTML in a gated repo)"
    elif not is_code(t):
        what = f"{tool} on {rel} (protected file)"
    else:
        what = f"{tool} on {rel}"
    reason = REASON.format(what=what, repo=root)
    if not under(Path(cwd).resolve(), root):  # the server's repo is where claude started; a judge bound elsewhere cannot import this repo
        reason += (f" This session's directory is {cwd}, not {root}: CLOSER's judge is bound to the directory claude "
                   f"was started in and cannot import this repo's modules from there. Do not cl_submit; stop and start "
                   f"claude in {root}.")
    return "deny", reason, shown


def decide_bash(ti: dict, cwd: str) -> tuple[str, str, list[str]]:
    """No command parsing. Bash writes are stopped at the file level by the OS sandbox; here we only refuse to leave
    the sandbox in a gated repo and make an unenforced repo visible."""
    if not isinstance(ti.get("command"), str):
        return "allow", "no command", []
    here = resolve(cwd, cwd)
    root, why = scope(here / "__probe__.py", registered())
    if root is None:
        return "allow", f"bash: cwd {why}", []
    if ti.get("dangerouslyDisableSandbox") is True:
        return "deny", (f"closer_gate: commands in gated repo {root} must run inside the sandbox, which is what keeps "
                        "Bash from writing code files. Run it sandboxed; code changes go through the CLOSER MCP tools: "
                        + FLOW + "."), [str(root)]
    ok, how = sandbox_covers(root, cwd)
    if ok:
        return "allow", f"bash: file-level, {how}", []
    n = notify(f"Bash in gated repo {root.name} is NOT write-protected: {how}")
    return "allow-unenforced", f"bash-unenforced in {root}: {how} (notify: {n})", []


# ---- logging, notification, watchdog ---------------------------------------

def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def log(rec: dict) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def notify(msg: str) -> str:
    """macOS notification, at most one per NOTIFY_EVERY_S. Returns what happened (for the log)."""
    try:
        if NOTIFY_STAMP.exists() and time.time() - NOTIFY_STAMP.stat().st_mtime < NOTIFY_EVERY_S:
            return "suppressed (rate limit)"
        NOTIFY_STAMP.parent.mkdir(parents=True, exist_ok=True)
        NOTIFY_STAMP.write_text(now())
        safe = msg.replace("\\", "\\\\").replace('"', "'")[:180]
        script = f'display notification "{safe}" with title "CLOSER gate"'
        subprocess.Popen(["osascript", "-e", script], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return "osascript started"
    except Exception as e:  # noqa: BLE001  notifying must never break the hook
        return f"notify failed: {type(e).__name__}"


def watchdog_start() -> Path | None:
    """Report runs that started and never finished (hook timeout / SIGKILL), then mark this run in flight."""
    try:
        INFLIGHT.mkdir(parents=True, exist_ok=True)
        stale = [m for m in INFLIGHT.iterdir() if time.time() - m.stat().st_mtime > STALE_S]
        if stale:
            for m in stale:
                m.unlink(missing_ok=True)
            how = notify("previous gate run did not finish (timeout/kill) - that write was allowed")
            log({"ts": now(), "decision": "watchdog", "stale_runs": [m.name for m in stale], "notify": how})
        me = INFLIGHT / f"{os.getpid()}-{time.time():.3f}"
        me.write_text("")
        return me
    except OSError:
        return None


def crash(reason: str, raw: str) -> None:
    how = notify(f"CLOSER gate crashed - write allowed: {reason[:80]}")
    log({"ts": now(), "decision": "error-fail-open", "error": reason, "input": raw[:500], "notify": how})
    print(f"closer_gate: crashed, write allowed: {reason}", file=sys.stderr)
    print(json.dumps({"systemMessage": f"CLOSER gate crashed - write allowed: {reason[:200]}"}))


def main() -> int:
    if os.environ.get("CLOSER_GATE_OFF") == "1" or OFF_FILE.exists():
        log({"ts": now(), "decision": "off"})
        return 0
    me = watchdog_start()
    raw = ""
    try:
        raw = sys.stdin.read()
        try:
            event = json.loads(raw or "{}")
        except ValueError as e:
            raise GateError(f"unreadable hook input ({e})")
        if not isinstance(event, dict):
            raise GateError("hook input is not a JSON object")
        decision, reason, targets = decide(event)
        log({"ts": now(), "session": event.get("session_id"), "tool": event.get("tool_name"), "cwd": event.get("cwd"),
             "decision": decision, "reason": reason[:300], "targets": targets[:20],
             **({"command": str((event.get("tool_input") or {}).get("command", ""))[:200]} if decision == "allow-unenforced" else {})})
        if decision == "deny":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": reason}}))
    except Exception as e:  # noqa: BLE001  fail OPEN, logged, notified
        crash(str(e) if isinstance(e, GateError) else f"{type(e).__name__}: {e}", raw)
    finally:
        if me is not None:
            try:
                me.unlink(missing_ok=True)
            except OSError:
                pass
    return 0


def emit_sandbox(out: Path) -> dict:
    repos = gated_repos()
    data = proposed_settings([r for r, _ in repos])
    data["_gated_repos"] = {str(r): why for r, why in repos}
    out.write_text(json.dumps(data, indent=2) + "\n")
    return data


if __name__ == "__main__":
    if sys.argv[1:2] == ["--classify"] and len(sys.argv) == 3:
        d = Path(os.path.realpath(sys.argv[2]))
        root, why = scope(d / "__probe__.py", registered())
        rec = {"dir": str(d), "exists": d.is_dir(), "gated_root": str(root) if root else None, "scope": why}
        if root:
            rec["bash_sandbox"] = sandbox_covers(root, str(d))[1]
        print(json.dumps(rec))
        raise SystemExit(0)
    if sys.argv[1:2] == ["--emit-sandbox"] and len(sys.argv) in (2, 3):
        out = Path(sys.argv[2]) if len(sys.argv) == 3 else PROPOSED
        data = emit_sandbox(out)
        print(json.dumps({"wrote": str(out), "gated_repos": len(data["_gated_repos"]),
                          "denyWrite_entries": len(data["sandbox"]["filesystem"]["denyWrite"])}))
        raise SystemExit(0)
    raise SystemExit(main())

# KNOWN GAPS (v5)
# - Bash is enforced only when the proposed sandbox block is applied (settings.json or --settings). Until then a
#   Bash write in a gated repo is allowed, logged "allow-unenforced" and notified (rate-limited to 1/min).
# - The denyWrite list is a snapshot: a repo gated later (new registration, new pyproject.toml) is covered by the
#   Edit/Write hook at once, but for Bash only after --emit-sandbox is re-run and the block re-applied; the hook
#   flags that repo as unenforced in the meantime.
# - The hook can't read a --settings file; harness sessions set CLOSER_GATE_SANDBOX_SETTINGS so the check sees it.
# - Sandbox wildcard denyWrite works on macOS; on Linux only a trailing /** works (this machine is macOS).
# - Without git, repo roots are CLOSER registration, roots.txt, or a pyproject.toml/setup.py/setup.cfg/package.json/
#   deno.json folder; a bare unregistered folder of code files with none of those is out of scope.
# - Shell scripts (.sh, ...) and every non-Python/non-web language still make a repo "mixed" (not gated): CLOSER's
#   pack judges Python and web code, not shell. Opt such a repo in with roots.txt if it should be gated anyway.
# - Commands you type at Claude's ! prompt, hooks and MCP servers run outside the sandbox (by Claude Code design).
