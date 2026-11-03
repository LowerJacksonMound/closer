#!/usr/bin/env python3
"""closer: the signer's front door. One command from a task to a watched land.

    closer doctor                is this machine ready? (python, pytest, Claude Code, the sandbox; and this repo's tests)
    closer demo                  run the whole path on a bundled sample repo, about a minute
    closer task NAME             write a TASK.md skeleton to fill in
    closer claims TASK.md        draft the claims and show them (nothing minted)
    closer go TASK.md            in the repo: register (first time, after you confirm the interpreter and test folder),
                                 scan, draft claims, pause for you to read them, mint, open the live page, launch the
                                 restricted writer, report the verdict in plain words
    closer status                what the live page shows now, as text
    closer inspect [TICKET]      one ticket's verdict in plain words: each check, each claim, what was not judged,
                                 where the evidence is (default: the newest ticket); --raw adds the gate's own lines
    closer amend                 change what the repo was registered with (--python, --pytest-args) and rescan;
                                 with no option, show the registration
    closer watch [--every N]     watch the repo for changes made outside the gate (started by `go` too): the page
                                 and `inspect` say which files differ from the frozen World and what is new in them
    closer forget [--gone]       list registered repos whose tree no longer exists; --gone removes their state dirs
    closer stop                  stop the live page server and the watcher

A wrapper over the signer's existing commands (bin/gc, bin/claims_draft.py, ui/session_server.py). It adds no rule
and touches no kernel file. The claims are drafted by a siloed claim agent (T5) from the task and the repo, then
checked by claims_draft --check, and you read them before anything is minted. The task, the claims and the writer's
log live under the state dir (<state>/signer/), which the writer's hook refuses to read.

Options for `go`: --python PATH (the repo's interpreter; default ./.venv or ./venv, else this python), --pytest-args
ARGS (default the repo's own config, else "tests"/"test" when that folder exists), --write PATH (extra write-set
file, repeatable), --port N (default 8766), --yes (no pauses), --chat (an interactive writer session: you type the
request), --no-launch, --no-open, --redraft, --raw (the gate's own lines beside the plain words).
Given again on a registered repo, --python and --pytest-args replace what the first run guessed.
"""
import argparse, json, os, platform, re, shlex, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent.parent
GC = [sys.executable, str(HERE / "bin" / "gc")]
PY = sys.executable
sys.path.insert(0, str(HERE / "bin"))


def say(msg):
    print(f"closer: {msg}", flush=True)


def die(msg, code=2) -> NoReturn:
    print(f"closer: {msg}", file=sys.stderr, flush=True); sys.exit(code)


def ask(prompt, default_yes=True):
    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        return default_yes
    return (ans in ("y", "yes")) if ans else default_yes


def run(cmd, cwd=None, env=None, check=True, capture=True):
    r = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=capture)
    if check and r.returncode != 0:
        die(f"{' '.join(shlex.quote(c) for c in cmd[-3:])} failed:\n{(r.stdout or '') + (r.stderr or '')}".strip())
    return r


# ---- the repo ---------------------------------------------------------------

def state_dir(repo):
    """The state dir gc uses for this repo, or None when not registered."""
    home = Path(os.environ.get("GETTING_CLOSE_HOME") or (Path.home() / ".getting-close"))
    for d in home.glob(f"{repo.name}-*"):
        mf = json.loads((d / "manifest.json").read_text()) if (d / "manifest.json").is_file() else {}
        if mf.get("repo") == str(repo):
            return d
    return None


def has_pytest(python):
    return subprocess.run([str(python), "-c", "import pytest"], capture_output=True).returncode == 0


def pick_python(repo, given):
    cands = ([Path(given).expanduser()] if given else []) + [repo / ".venv/bin/python", repo / "venv/bin/python", Path(PY)]
    for p in cands:
        if p.is_file() and has_pytest(p):
            return str(p)
    if given:
        die(f"{given} cannot import pytest; give --python an interpreter that can")
    die("no interpreter with pytest found (looked for ./.venv, ./venv, and this python): give --python /path/to/the/repo's/python")


def pick_pytest_args(repo, given):
    if given is not None:
        return given
    for f, pat in (("pytest.ini", r"testpaths"), ("setup.cfg", r"\[tool:pytest\][^\[]*testpaths"),
                   ("tox.ini", r"\[pytest\][^\[]*testpaths"), ("pyproject.toml", r"\[tool\.pytest\.ini_options\][^\[]*testpaths")):
        p = repo / f
        if p.is_file() and re.search(pat, p.read_text(), re.S):
            return ""  # the repo says where its tests are
    for d in ("tests", "test"):
        if (repo / d).is_dir():
            return d
    return ""


def collection(repo, python, pytest_args):
    """Dry-run collection with the interpreter and args the gate will use. The environment mistake, caught up front."""
    r = subprocess.run([python, "-m", "pytest", "--co", "-q", "-p", "no:cacheprovider"] + shlex.split(pytest_args),
                       cwd=repo, text=True, capture_output=True)
    out = r.stdout + r.stderr
    if r.returncode != 0 or re.search(r"^ERROR ", out, re.M):
        errs = [l for l in out.splitlines() if l.startswith("ERROR") or "ModuleNotFoundError" in l or "ImportError" in l][:6]
        return None, "\n".join(errs) or out[-800:]
    m = re.search(r"(\d+) tests? collected", out)
    return int(m.group(1)) if m else 0, ""


def ensure_registered(repo, a):
    st = state_dir(repo)
    mf = json.loads((st / "manifest.json").read_text()) if st else {}
    python = pick_python(repo, a.python or mf.get("python"))
    pytest_args = pick_pytest_args(repo, a.pytest_args if a.pytest_args is not None else mf.get("pytest_args"))
    n, err = collection(repo, python, pytest_args)
    if n is None:
        die(f"the repo's tests do not collect under {python} with pytest args {pytest_args!r}:\n{err}\n"
            f"fix the environment, or give --pytest-args (a folder, or --ignore=... words) / --python, then rerun")
    where = pytest_args or "the repo's own pytest settings"
    if st is None:
        say(f"first run on this repo. Interpreter: {python}. Tests: {where} ({n} collect).")
        if not a.yes and not ask("  Register the repo with these? [Y/n] "):
            die("not registered; rerun with --python and/or --pytest-args")
        cmd = GC + ["--repo", str(repo), "init", "--python", python, "--exclude", "__pycache__", "--exclude", ".pytest_cache",
                    "--exclude", ".git"] + (["--pytest-args", pytest_args] if pytest_args else [])
        r = run(cmd, cwd=repo)
        m = re.search(r"gc: state (\S+)", r.stdout + r.stderr)
        st = Path(m.group(1)) if m else state_dir(repo)
        if st is None:
            die(f"gc init gave no state dir:\n{r.stdout}{r.stderr}")
        say(f"registered; state {st}")
    else:
        changed = []
        if mf.get("python") != python:
            mf["python"] = python; changed.append(f"interpreter -> {python}")
        if (mf.get("pytest_args") or "") != pytest_args:
            mf["pytest_args"] = pytest_args; changed.append(f"pytest args -> {pytest_args!r}")
        if changed:  # the fields gc init writes; gc has no amend command, so the front door keeps them current
            (st / "manifest.json").write_text(json.dumps(mf, indent=2) + "\n")
            say(f"state {st}: " + "; ".join(changed) + f" ({n} tests collect)")
        else:
            say(f"state {st} ({n} tests collect under {where})")
    r = run(GC + ["--repo", str(repo), "scan"], cwd=repo)
    say((r.stdout + r.stderr).strip().splitlines()[-1])
    return st


# ---- claims -----------------------------------------------------------------

CLAIM_BRIEF = """You draft claims for a code gate. Read TASK below and the repository (Read/Grep/Glob; you have no other tools).
A claim is one JSON object: {"name": "<dotted import path of the function the task adds or changes>",
"setup": ["<python statement>", ...], "call": "<python expression>", "expect": {"result": <JSON literal>} |
{"raises": "<ExceptionName>"} | {"true": "<python predicate, may use names from setup and `result`>"}}.
Each claim runs on its own in a fresh interpreter with the repo importable; setup statements run in order, then the call.
Rules: one behaviour per claim; cover every acceptance criterion, including each error path, each named message,
ordering, types, pass-through of arguments, and the empty case; use small literal data built in setup; never read the
repo's test files for expected values; never reference a name the task does not define; no placeholders.
First, before any claim: take every worked example in TASK (each "`call` is `value`" pair) and work it out yourself,
step by step, from TASK's stated rules alone, writing the intermediate steps; compare your computed value with the
value TASK gives. Where they differ, TASK contradicts itself: do not make a claim from that example; put one short
sentence under "contradictions" ("`initials('a-b c')` is given as 'AC' but splitting on hyphens gives 'ABC'"). Then
write 6 to 14 claims from the rules.
Sharpness, learned from the proving runs (each line is a way a wrong implementation got through, or an honest one was
struck, until the claims were written this way):
- For every rule, at least one input that is NOT a worked example from TASK and not in any table TASK gives: an
  implementation that is a lookup table of the examples must fail it.
- Claim the behaviour through the public entry point as well as on the function itself, where TASK names both.
- Where a value depends on state, call twice across the state change in one claim and require the second result to
  differ from the first; an implementation that computes once and caches passes a single call.
- A negative claim ("X is not in the result") must use a needle that cannot be a substring of an honest result.
- Floats: exactly representable values, or {"true": "abs(result - 1.25) < 0.01"}; never exact equality on a computed float.
- Never consume a generator or iterator twice in one claim; materialise it with list(...) first.
- Pin only what TASK states. Not the return type beyond what it says, not an order it does not fix, not behaviour on
  inputs it never mentions, not tolerance or rejection of malformed input it is silent about. A claim on an open point
  strikes an honest writer.
- Boundaries: use TASK's own words ("older than" is strict) and claim a value on each side of the boundary.
- Each error path: the exception type TASK names and a fragment of the message TASK states, nothing more.
- A message fragment is its own claim, shaped exactly so (there is no helper): setup ["msg = ''", "try:\n    f(bad)\nexcept ValueError as e:\n    msg = str(e)"], call "msg", expect {"true": "'fragment' in result"}. The call is
  always a plain expression; never a lambda, never a generator.
- Ids and literals in setup must not collide with values the code might derive on its own (use 999, not 1).
Output your example workings as plain text, then only one fenced ```json block
holding an object {"claims": [...], "contradictions": [...], "questions": [...]} (both lists may be empty). A question
is a case a claim would need that TASK does not decide (what happens when nothing has been asked yet; an empty list;
a boundary with no example): do not invent the answer or claim it; state the case in one short sentence so the signer
can decide it before the mint.

TASK:
"""


def well_formed(claims):
    """A fixed rule on the claim agent's output: a claim's call is one expression that names the function under test,
    with no lambda or generator in it. A claim that fails is dropped and said, never shown as something to sign."""
    import ast
    kept = []
    for c in claims:
        call = c.get("call") if isinstance(c, dict) else None
        try:
            tree = ast.parse(str(call), mode="eval")
        except SyntaxError:
            say(f"  dropped a claim on {c.get('name', '?') if isinstance(c, dict) else '?'}: its call does not parse: {str(call)[:80]}")
            continue
        if any(isinstance(n, (ast.Lambda, ast.GeneratorExp)) for n in ast.walk(tree)):
            say(f"  dropped a claim on {c.get('name', '?')}: its call is a lambda or generator, not a call: {str(call)[:80]}")
            continue
        # The claim names "module.function"; the call and setup must bind what they use, or every claim raises
        # NameError and the strike is the claims' fault (seen 2026-11-03: a draft with no setup lines at all).
        module, _, func = str(c.get("name", "")).rpartition(".")
        setup = list(c.get("setup") or [])
        text = "\n".join(setup + [str(call)])
        bound = "\n".join(setup)
        if module and f"{module}." in text and not re.search(rf"^\s*import {re.escape(module)}\b", bound, re.M):
            setup.insert(0, f"import {module}")
        if func and re.search(rf"(?<![\w.]){re.escape(func)}\s*\(", text) and not re.search(rf"^\s*from {re.escape(module)} import .*\b{re.escape(func)}\b", bound, re.M):
            setup.insert(0, f"from {module} import {func}")
        if setup != list(c.get("setup") or []):
            say(f"  bound the claim on {c.get('name', '?')}: added {setup[:2 if len(setup) - len(c.get('setup') or []) == 2 else 1]}")
            c = {**c, "setup": setup}
        kept.append(c)
    return kept


def draft_claims(repo, st, task_file):
    sdir = st / "signer"; sdir.mkdir(exist_ok=True)
    task = Path(task_file).read_text()
    (sdir / "TASK.md").write_text(task)
    out = sdir / "claims.json"
    say("drafting claims with a siloed claim agent (reads the repo and the task; no gate access) ...")
    r = subprocess.run(["claude", "--tools", "Read,Grep,Glob", "--strict-mcp-config", "--permission-mode", "dontAsk",
                        "-p", CLAIM_BRIEF + task], cwd=repo, text=True, capture_output=True)
    blocks = re.findall(r"```json\s*(.*?)```", r.stdout, re.S)
    if not blocks:
        die(f"the claim agent returned no JSON block:\n{(r.stdout or r.stderr)[-1500:]}")
    try:
        data = json.loads(blocks[-1])
    except json.JSONDecodeError as e:
        die(f"the claim agent's JSON does not parse ({e}):\n{blocks[-1][:1500]}")
    claims = data.get("claims") if isinstance(data, dict) else data
    contradictions = (data.get("contradictions") or []) if isinstance(data, dict) else []
    questions = [str(q) for q in (data.get("questions") or [])] if isinstance(data, dict) else []
    if not isinstance(claims, list) or not claims:
        die("the claim agent returned no claims")
    claims = well_formed(claims)
    (st / "signer" / "questions.txt").write_text("\n".join(questions) + ("\n" if questions else ""))
    if questions:
        say(f"{len(questions)} question(s) the task leaves undecided (signer/questions.txt); decide them in TASK.md or accept the silence:")
        for q in questions:
            say(f"  ? {q}")
    # Every function the task names must have a claim that calls it: a function no claim reaches is never tested,
    # and the gate refuses it after the writer has worked. Ask the same siloed agent for the missing ones, then refuse
    # to mint rather than launch a writer on a ticket that cannot be judged in full.
    for round_ in (1, 2):
        missing = unclaimed(task, claims)
        if not missing:
            break
        say(f"no claim yet for {len(missing)} function(s) the task names ({', '.join(missing)}); asking the claim agent for them ...")
        more = ask_claims(repo, CLAIM_BRIEF + task + COVER_BRIEF.format(names=", ".join(missing)))
        claims += [c for c in more if isinstance(c, dict) and c.get("call")]
    missing = unclaimed(task, claims)
    if missing:
        die(f"not minting: no claim reaches {', '.join(missing)}. Every function must be tested, so give TASK.md a "
            f"criterion or an example for each, then rerun.")
    out.write_text(json.dumps(claims, indent=1) + "\n")
    (sdir / "contradictions.txt").write_text("\n".join(contradictions) + ("\n" if contradictions else ""))
    chk = subprocess.run([PY, str(HERE / "bin" / "claims_draft.py"), "--repo", str(repo), "--task-file", str(task_file),
                          "--check", str(out)], text=True, capture_output=True)
    return claims, contradictions, (chk.stdout + chk.stderr).strip()


COVER_BRIEF = """

ADDITIONAL REQUEST: the claims so far reach every function except these: {names}. Write claims ONLY for these
functions, in the same format, at least one each that calls the function directly, covering what TASK says it does.
Reply with one ```json block holding {{"claims": [...]}}."""

_NOT_FUNCTIONS = {"print", "len", "str", "int", "float", "list", "dict", "set", "tuple", "isinstance", "range", "repr"}


def _module_of(task: str) -> str:
    """The module the task writes into: the stem of the first `*.py` it names, or ''."""
    m = re.search(r"`([A-Za-z_][\w/]*)\.py`", task)
    return m.group(1).rsplit("/", 1)[-1] if m else ""


def _params_of(task: str) -> set[str]:
    """Parameter names the task's signatures declare, `f(quiz, clock)` -> {quiz, clock}: a dotted call on one of
    them (`quiz.clock()`) is a method on a value even when it shares the module's name."""
    names: set[str] = set()
    for code in re.findall(r"`([^`]+)`", task):
        for args in re.findall(r"[a-z_]\w*\(([^()]*)\)", code):
            for a in args.split(","):
                a = a.strip().split("=")[0].strip()
                if re.fullmatch(r"[a-z_]\w*", a):
                    names.add(a)
    return names


def task_functions(task: str) -> list[str]:
    """The functions the task names: `name(` inside backticks, without builtins or Capitalized names (exceptions)."""

    found = []
    for code in re.findall(r"`([^`]+)`", task):
        for name in re.findall(r"(?<![\w.])((?:[A-Za-z_]\w*\.)*[a-z_]\w*)\(", code):
            parts = name.split(".")
            last = parts[-1]
            # `last_name.lower()` is a method on a value, not a function the app must have: a dotted name counts
            # only when its head is the module (seen 2026-11-03: a task refused over `lower`).
            if len(parts) > 1 and (parts[0] != _module_of(task) or parts[0] in _params_of(task)):
                continue
            if last not in _NOT_FUNCTIONS and last not in found and not last.startswith("test"):
                found.append(last)
    return found


def unclaimed(task: str, claims: list) -> list[str]:
    """Task functions no claim calls: by its name (agent.f), or by a direct call `f(` in setup, call or expect."""

    text = " ".join(" ".join([c.get("name", ""), c.get("call", ""), " ".join(c.get("setup") or []), json.dumps(c.get("expect", ""))])
                    for c in claims if isinstance(c, dict))
    names = {c.get("name", "").split(".")[-1] for c in claims if isinstance(c, dict)}
    return [f for f in task_functions(task) if f not in names and not re.search(r"(?<![\w])" + re.escape(f) + r"\(", text)]


def ask_claims(repo, prompt: str) -> list:
    r = subprocess.run(["claude", "--tools", "Read,Grep,Glob", "--strict-mcp-config", "--permission-mode", "dontAsk", "-p", prompt],
                       cwd=repo, text=True, capture_output=True)
    blocks = re.findall(r"```json\s*(.*?)```", r.stdout, re.S)
    try:
        data = json.loads(blocks[-1]) if blocks else {}
    except json.JSONDecodeError:
        return []
    got = data.get("claims") if isinstance(data, dict) else data
    return got if isinstance(got, list) else []


def expect_words(e):
    if not isinstance(e, dict) or not e:
        return json.dumps(e)
    k, v = next(iter(e.items()))
    return {"result": f"returns {json.dumps(v)}", "raises": f"raises {v}", "true": f"afterwards: {v}"}.get(k, f"{k} {json.dumps(v)}")


def show_claims(claims, contradictions, check_out):
    print()
    print("  The claims (what the code must do; the gate runs each one):")
    for i, c in enumerate(claims, 1):
        print(f"  {i:2}. {c.get('name', '?').split('.')[-1]}: after {c.get('call', '')[:90]}")
        print(f"       {expect_words(c.get('expect'))[:120]}")
    print()
    if contradictions:
        print("  THE TASK CONTRADICTS ITSELF (fix TASK.md before minting; a writer who follows the rule will be struck by the example):")
        for s in contradictions:
            print(f"   - {s}")
        print()
    if check_out:
        print("  " + "\n  ".join(check_out.splitlines()[-4:]))
        print()


# ---- the ticket --------------------------------------------------------------

def module_file(repo, dotted):
    parts = dotted.split(".")
    for k in range(len(parts), 0, -1):
        base = "/".join(parts[:k])
        for cand in (f"{base}.py", f"{base}/__init__.py", f"src/{base}.py", f"src/{base}/__init__.py"):
            if (repo / cand).is_file():
                return cand
    return None


def write_set(repo, claims, task_text, extra):
    files = []
    for c in claims:
        f = module_file(repo, c.get("name", ""))
        if f and f not in files:
            files.append(f)
    for tok in re.findall(r"`([\w./-]+\.py)`", task_text):
        # a path the task names: existing, or a test file to be created (tests/x.py, test_x.py, x_test.py)
        if tok not in files and ((repo / tok).is_file() or "/" in tok or re.match(r"(test_.*|.*_test)\.py$", Path(tok).name)):
            files.append(tok)
    for f in extra or []:
        if f not in files:
            files.append(f)
    return files


def next_ticket_id(st):
    have = {p.stem for p in (st / "tickets").glob("*.json")} if (st / "tickets").is_dir() else set()
    n = 1
    while f"t{n}" in have:
        n += 1
    return f"t{n}"


def task_label(task_text):
    m = re.search(r"^#+\s*(\S+)", task_text, re.M)
    lab = (m.group(1) if m else "task").strip(".:")
    return re.sub(r"[^\w-]+", "-", lab)[:40] or "task"


# ---- the page and the writer ------------------------------------------------

def start_server(st, port, open_it):
    sdir = st / "signer"; sdir.mkdir(exist_ok=True)
    stop_server(st, quiet=True)
    p = subprocess.Popen([PY, str(HERE / "ui" / "session_server.py"), "--state", str(st), "--port", str(port)],
                         stdout=open(sdir / "server.log", "w"), stderr=subprocess.STDOUT)
    (sdir / "server.pid").write_text(str(p.pid))
    url = f"http://localhost:{port}/"
    time.sleep(1)
    if p.poll() is not None:
        die(f"the page server did not start (port {port} busy? try --port): {(sdir / 'server.log').read_text()[-400:]}")
    say(f"live page: {url}")
    start_watch(st)
    if open_it and sys.platform == "darwin":
        subprocess.run(["open", url], capture_output=True)
    return url


def start_watch(st, every=4.0):
    """ui/watch.py beside the page server: files changed outside the gate, every few seconds, to signer/watch.json."""
    sdir = st / "signer"; sdir.mkdir(exist_ok=True)
    stop_watch(st)
    p = subprocess.Popen([PY, str(HERE / "ui" / "watch.py"), "--state", str(st), "--every", str(every)],
                         stdout=open(sdir / "watch.log", "w"), stderr=subprocess.STDOUT)
    (sdir / "watch.pid").write_text(str(p.pid))
    say("watching the repo for changes outside the gate (shown on the page; `closer stop` ends it)")


def stop_watch(st):
    pf = st / "signer" / "watch.pid"
    if pf.is_file():
        try:
            os.kill(int(pf.read_text().strip()), 15)
        except (ProcessLookupError, ValueError):
            pass
        pf.unlink()


def _watch_lines(st):
    """`closer inspect` / `closer status`: the watcher's report in words, one line per changed file."""
    import session
    wf = st / "signer" / "watch.json"
    if not wf.is_file():
        return []
    try:
        w = json.loads(wf.read_text())
    except ValueError:
        return []
    if time.time() - wf.stat().st_mtime > 60:
        return [f"watcher stopped (last looked {w.get('ts', '')}); `closer watch` restarts it"]
    out = []
    for c in w.get("changed_outside_gate") or []:
        out.append(f"CHANGED OUTSIDE THE GATE: {c['relpath']} ({c['since']})")
        for f in c.get("new_findings") or []:
            out.append(f"    new: {session.RULE_WORDS.get(f['rule'], f['rule'])}: {f['qualname']} line {f.get('line')}"
                       + (f" ({f['why']})" if f.get("why") else ""))
    return out


def cmd_watch(a):
    st = state_dir(Path.cwd().resolve())
    if not st:
        die("this repo is not registered (closer go registers it)")
    start_watch(st, a.every); return 0


def stop_server(st, quiet=False):
    stop_watch(st)
    pf = st / "signer" / "server.pid"
    if pf.is_file():
        try:
            os.kill(int(pf.read_text().strip()), 15)
            if not quiet:
                say("page server stopped")
        except (ProcessLookupError, ValueError):
            pass
        pf.unlink()
    elif not quiet:
        say("no page server running for this state dir")


def writer_cmd(st, tid, task_text, chat):
    prompt = (f"You are the writer in a getting-close session. Implement the task below in this repository. You have no "
              f"shell and no direct file writes: read the code with Read/Grep/Glob, then use the gc MCP tools: list tickets "
              f"(ticket id {tid}), stage your changes with stage_edit or stage into the ticket's write set, and land ticket "
              f"{tid}. Only the ticket's write set may be changed. Write the tests the task asks for. When the land proceeds, "
              f"stop.\n\n## The task\n\n{task_text}")
    cmd = ["claude", "--restricted", "--settings", str(st / "claude-writer.json"), "--strict-mcp-config", "--mcp-config",
           str(st / "mcp.json"), "--tools", "Read,Grep,Glob", "--permission-mode", "dontAsk"]
    return cmd if chat else cmd + ["-p", prompt]


def launch_writer(repo, st, tid, task_text, chat):
    cmd = writer_cmd(st, tid, task_text, chat)
    shown = [c for c in cmd if not c.startswith("You are the writer")]
    (st / "signer" / "LAUNCH_LINE.txt").write_text(" ".join(shlex.quote(c) for c in shown) + ("" if chat else " <task>") + "\n")
    if chat:
        say(f"interactive writer on {tid} (restricted: Read, Grep, Glob + gc MCP). Type what you want built and name ticket {tid}; "
            f"the task text is in {st / 'signer' / 'TASK.md'}. Leave the session when the land is reported.")
        r = subprocess.run(cmd, cwd=repo)
    else:
        say(f"writer launched on {tid} (restricted: Read, Grep, Glob + gc MCP) ...")
        with open(st / "signer" / f"writer-{tid}.log", "w") as log:
            r = subprocess.run(cmd, cwd=repo, stdout=log, stderr=subprocess.STDOUT)
    return r.returncode


def verdict(repo, st, tid, task_text, raw):
    import session  # the page's plain-word map, reused on the terminal
    run(GC + ["--repo", str(repo), "ledger", "--check"], cwd=repo)
    rows = [json.loads(l) for l in (st / "ledger.jsonl").read_text().splitlines() if l.strip()] if (st / "ledger.jsonl").is_file() else []
    mine = [r for r in rows if r.get("ticket_id") == tid]
    if not mine:
        say(f"{tid}: the writer ended without landing (see {st / 'signer'}/writer-{tid}.log)"); return 1
    r = mine[-1]
    e1 = next((c["said"][0] for c in r["checks"] if c["name"] == "E1" and c["said"]), "")
    c1 = next((c["said"][0] for c in r["checks"] if c["name"] == "C1" and c["said"]), "")
    if r.get("decision") == "proceed" and not r.get("strike"):
        say(f"{tid}: CORRECT VERSION ACCEPTED. The change is in the repo. {e1}; {c1}")
        for note in _notes(r):
            say(f"{tid}: LOOK HERE (accepted, but read this before you trust it): {note}")
        return 0
    fails = [(c["name"], s) for c in r["checks"] for s in c.get("said", []) if c["exit"] not in (0, 75) and ("fail" in s or "unjudged" in s)]
    say(f"{tid}: REJECTED. The tree is rolled back and the ticket is closed. Why:")
    for name, s in fails[:6]:
        print(f"   - {session.plain_fail(name, s)}" + (f"   [{s}]" if raw else ""))
    # a failed claim whose expected value is quoted in the task: the task's example may be the wrong one
    evf = st / "evidence" / f"{tid}.{r.get('seq')}.json"
    cl, _ = session.dash.c1_claims(evf)
    for i, e in sorted(cl.items()):
        if (e.get("observed") != "held" or e.get("rule")) and e.get("rule") != "cannot_judge":
            exp = e.get("expected") or {}
            v = next(iter(exp.values()), None) if isinstance(exp, dict) else None
            if isinstance(v, (str, int, float)) and (f"`{v!r}`" in task_text or f"`{v}`" in task_text or f"'{v}'" in task_text):
                print(f"   note: claim {i} expects {v!r}, an example quoted in the task. If the writer followed the task's stated "
                      f"rule, the example may be the wrong one: check TASK.md before the next ticket.")
    strikes = sum(1 for x in rows if x.get("strike") and x.get("task") == r.get("task"))
    say(f"strikes on this task: {strikes} of 2 allowed. Fix the task or the claims, then `closer go` again: a new ticket, judged in full.")
    return 1


# ---- commands ----------------------------------------------------------------

def cmd_go(a):
    repo = Path.cwd().resolve()
    task_file = Path(a.task).resolve()
    if not task_file.is_file():
        die(f"no such task file: {task_file}")
    task_text = task_file.read_text()
    if "<fill" in task_text.lower():
        die(f"{task_file.name} still has <FILL ...> placeholders from the template")
    st = ensure_registered(repo, a)
    sdir = st / "signer"; sdir.mkdir(exist_ok=True)
    cf = sdir / "claims.json"
    if cf.is_file() and (sdir / "TASK.md").is_file() and (sdir / "TASK.md").read_text() == task_text and not a.redraft:
        claims = json.loads(cf.read_text())
        cfile = sdir / "contradictions.txt"
        contradictions = [l for l in cfile.read_text().splitlines() if l.strip()] if cfile.is_file() else []
        say(f"claims already drafted for this task ({len(claims)}); --redraft to draft again")
        ck = sdir / "claims_check.txt"
        check_out = ck.read_text().strip() if ck.is_file() else ""
    else:
        claims, contradictions, check_out = draft_claims(repo, st, task_file)
        (sdir / "claims_check.txt").write_text(check_out + ("\n" if check_out else ""))  # the page reads it (console A)
    show_claims(claims, contradictions, check_out)
    if a.command == "claims":
        say(f"claims at {cf}; edit them there, then `closer go {a.task}`"); return 0
    if contradictions and not a.yes:
        die("not minting while the task contradicts itself; fix TASK.md and rerun (or --yes to mint anyway)")
    if not a.yes and not ask("  Read the claims. Mint the ticket and launch the writer? [y/N] ", default_yes=False):
        say(f"stopped before minting; claims at {cf} (edit them, then rerun)"); return 0
    files = write_set(repo, claims, task_text, a.write)
    if not files:
        die("could not work out the write set from the claims; give --write PATH for each file the task may change")
    tid = next_ticket_id(st)
    run(GC + ["--repo", str(repo), "ticket", "--id", tid, "--task", task_label(task_text), "--claims", str(cf)]
        + [x for f in files for x in ("--write", f)], cwd=repo)
    run(GC + ["--repo", str(repo), "writer-setup"], cwd=repo)
    say(f"minted {tid}: {len(claims)} claims, write set {', '.join(files)}")
    url = start_server(st, a.port, not a.no_open)
    if a.no_launch:
        ll = sdir / "LAUNCH_LINE.txt"
        say(f"not launching (--no-launch). Launch line: {ll.read_text().strip() if ll.is_file() else 'see gc writer-setup'}")
        return 0
    launch_writer(repo, st, tid, task_text, a.chat)
    rc = verdict(repo, st, tid, task_text, a.raw)
    say(f"the page stays up at {url} (closer stop to end it)")
    return rc


def cmd_doctor(a):
    ok = True

    def line(good, what, fix=""):
        nonlocal ok
        ok = ok and good
        print(f"  {'ok     ' if good else 'MISSING'} {what}" + (f"\n          -> {fix}" if not good and fix else ""))

    print("closer doctor")
    line(platform.system() == "Darwin" and shutil.which("sandbox-exec") is not None,
         f"macOS sandbox (sandbox-exec): {platform.system()}", "the gate holds every check read-only with sandbox-exec; macOS only for now")
    v = sys.version_info
    line(v >= (3, 10), f"python {v.major}.{v.minor} for the gate itself", "install Python 3.10 or newer and run closer with it")
    line(has_pytest(PY), f"pytest importable by {PY}", "pip install pytest (the gate's own checks need it)")
    cl = shutil.which("claude")
    line(cl is not None, f"Claude Code on PATH: {cl or 'not found'}", "install Claude Code; the writer is a restricted claude session")
    if cl:
        h = subprocess.run([cl, "--help"], capture_output=True, text=True)
        line("--restricted" in h.stdout + h.stderr and "--strict-mcp-config" in h.stdout + h.stderr,
             "claude supports --restricted and --strict-mcp-config", "update Claude Code")
    repo = Path.cwd().resolve()
    if (repo / "pyproject.toml").is_file() or (repo / "setup.py").is_file() or (repo / "setup.cfg").is_file() or list(repo.glob("test*")):
        try:
            py = pick_python(repo, a.python)
        except SystemExit:
            py = None
        line(py is not None, f"an interpreter with pytest for this repo: {py or 'none'}", "give --python /path/to/the/repo's/python")
        if py:
            pa = pick_pytest_args(repo, a.pytest_args)
            n, err = collection(repo, py, pa)
            line(n is not None, f"this repo's tests collect (pytest args {pa!r}): {n if n is not None else (err.splitlines()[0] if err else '?')}",
                 "fix the environment, or give --pytest-args a folder / --ignore=... words")
        st = state_dir(repo)
        print(f"  {'ok     ' if st else 'note   '} this repo is {'registered at ' + str(st) if st else 'not registered yet (closer go does that)'}")
    else:
        print("  note    not inside a repo (run closer doctor inside one to check its tests)")
    print("closer doctor: " + ("ready" if ok else "not ready"))
    return 0 if ok else 1


def cmd_task(a):
    p = Path(a.name if a.name.endswith(".md") else f"{a.name}.md")
    if p.exists():
        die(f"{p} exists")
    p.write_text(f"""## {p.stem}. <FILL: one line: what the change does>

<FILL: one paragraph: why, and where it lives (name the module and the function)>

**Acceptance criteria**
- `<FILL: module.function(args)>` <FILL: what it returns, as a rule>; for example `<FILL: a call>` is `<FILL: its value>`.
- <FILL: each error: what input raises which exception, and what its message must contain>.
- <FILL: the empty or edge case>.
- Tests in `<FILL: tests/test_x.py>` for each case above.

Rules for writing this: state the rule first, then examples that follow the rule exactly (a wrong example becomes a
wrong claim and strikes an honest writer); name every exception and message; say the order when order matters.
""")
    say(f"wrote {p}; fill every <FILL: ...>, then `closer go {p}`")
    return 0


def cmd_demo(a):
    src = HERE / "ui" / "demo"
    d = Path(tempfile.mkdtemp(prefix="closer-demo-")) / "repo"
    shutil.copytree(src / "repo", d)
    shutil.copy(src / "TASK.md", d.parent / "TASK.md")
    say(f"demo repo at {d}: a 3-function expense helper with 4 tests; the task adds split_bill with a tip")
    os.chdir(d)
    a.task = str(d.parent / "TASK.md"); a.command = "go"; a.yes = True
    return cmd_go(a)


def cmd_status(a):
    st = state_dir(Path.cwd().resolve())
    if not st:
        die("this repo is not registered")
    import session, html as _h
    t = re.sub(r"<style.*?</style>|<script.*?</script>|<details.*?</details>", "", session.fragment(st), flags=re.S)
    t = re.sub(r"(\s*\|\s*)+", " | ", _h.unescape(re.sub(r"<[^>]+>", " | ", t)))
    print(t.strip()[:1500])
    for line in _watch_lines(st):
        print(line)
    print(session.advisory_load_words(st))
    return 0


def _plain_expect(exp):
    if not isinstance(exp, dict) or not exp:
        return json.dumps(exp)
    k, v = next(iter(exp.items()))
    return {"result": f"returns {json.dumps(v)}", "raises": f"raises {v}", "true": f"afterwards {v}"}.get(k, f"{k} {json.dumps(v)}")


def _notes(row):
    """Advisory lines a check said (S1 `s1_advisory`, pack v35): no strike, shown in the normal path, in words."""
    import session
    out = []
    for c in row.get("checks", []):
        for s in c.get("said") or []:
            if s.startswith("S1 note: stood down "):
                out.append("stood down by the pack's s1_stand_down list (not counted): " + s[len("S1 note: stood down "):])
                continue
            if s.startswith("S1 note: introduced "):
                where, _, reason = s[len("S1 note: introduced "):].partition(" -- ")
                rule = next((k for k in session.RULE_WORDS if f" {k} " in f" {where} "), "")
                out.append(f"{session.RULE_WORDS.get(rule, rule or 'note')}: {where.replace(' ' + rule + ' ', ' ') if rule else where}"
                           + (f" ({reason})" if reason else ""))
    return out


def cmd_inspect(a):
    """One ticket, in words: the pipeline stage, every land with its checks and claims, what was not judged, the
    evidence file. The same readers the live page uses (bin/session.py, bin/dash.py); nothing is written."""
    import session
    st = state_dir(Path.cwd().resolve())
    if not st:
        die("this repo is not registered")
    tickets = sorted((st / "tickets").glob("*.json"), key=lambda p: p.stat().st_mtime) if (st / "tickets").is_dir() else []
    if not tickets:
        die("no ticket minted yet")
    tf = next((p for p in tickets if p.stem == a.ticket), None) if a.ticket else tickets[-1]
    if tf is None:
        die(f"no ticket {a.ticket}; have: {', '.join(p.stem for p in tickets)}")
    t = json.loads(tf.read_text()); tid = str(t.get("ticket_id"))
    rows = [json.loads(l) for l in (st / "ledger.jsonl").read_text().splitlines() if l.strip()] if (st / "ledger.jsonl").is_file() else []
    mine = [r for r in rows if str(r.get("ticket_id")) == tid]
    staged = session.staged_files(st, tid)
    claims = session.dash.jload(st / "claims" / f"{tid}.json", []) or []
    policy = session.dash.jload(st / "policy.json", {}) or {}
    strikes = sum(1 for r in rows if r.get("strike") and str(r.get("task")) == str(t.get("task")))
    print(f"ticket {tid}  task {t.get('task')}  world {t.get('world_id')}  claims {len(claims)}  "
          f"strikes on this task {strikes} of {policy.get('gets_through_anyway', 2)} allowed")
    for line in _watch_lines(st):
        print(f"  {line}")
    print(f"  files the writer may change: {', '.join(t.get('write_set') or [])}")
    print(f"  staged so far: {', '.join(staged) or 'none'}")
    if not mine:
        print("  stage: " + ("checks running" if session.land_in_progress(st) and staged else "staged, no land yet" if staged else "minted, nothing staged"))
        for i, c in enumerate(claims, 1):
            print(f"   {i:2}. {str(c.get('name', '')).split('.')[-1]}: after {str(c.get('call', ''))[:90]}; {_plain_expect(c.get('expect'))[:100]}")
        return 0
    for r in mine:
        ok = r.get("decision") == "proceed" and not r.get("strike")
        print(f"\n  land {r.get('seq')} at {r.get('ts')}: " + ("CORRECT VERSION ACCEPTED" if ok else f"REJECTED ({r.get('decision')}, strike={bool(r.get('strike'))})"))
        for c in r.get("checks", []):
            ex = c.get("exit"); said = c.get("said") or []
            res = "passed" if ex == 0 else ("could not run (let through)" if ex == 75 else "FAILED")
            meaning = session.CHECK_WORDS.get(c["name"], c["name"])
            if ex not in (0, 75):
                meaning = "; ".join(session.plain_fail(c["name"], x) for x in said if "fail" in x or "unjudged" in x) or (said[-1] if said else meaning)
            print(f"    {c['name']:5} {res:28} {meaning}")
            if a.raw:
                for x in said:
                    print(f"          | {x}")
        for x in r.get("unjudged") or []:
            print(f"    not judged: {x}")
        for note in _notes(r):
            print(f"    LOOK HERE: {note}")
        evf = st / "evidence" / f"{tid}.{r.get('seq')}.json"
        cl, reach = session.dash.c1_claims(evf)
        if cl:
            held = sum(1 for e in cl.values() if e.get("observed") == "held" and not e.get("rule"))
            print(f"  claims: {held} of {len(cl)} held")
            for i, e in sorted(cl.items()):
                o, rule = e.get("observed"), e.get("rule")
                v = ("held" if o == "held" and not rule else "could not be checked" if rule == "cannot_judge"
                     else "FAILED: " + session.RULE_WORDS.get(rule, rule or "mismatch"))
                got = "" if o in (None, "held") else f"  got {json.dumps(o)[:80]}"
                print(f"   {i:2}. {str(e.get('name', '')).split('.')[-1]}: after {str(e.get('call', ''))[:80]}; {_plain_expect(e.get('expected'))[:80]} -> {v}{got}")
            if reach and reach.get("unreached"):
                print("  unreached (new or changed functions no claim ran): " + ", ".join(q for _, q in reach["unreached"]))
        print(f"  evidence: {evf if evf.is_file() else 'none filed'}")
    return 0


def cmd_amend(a):
    """The registration (gc init's manifest: python, pytest_args), shown or changed, then a rescan so the next World
    is bound to the manifest as amended. gc has no amend command; this edits the two fields gc init wrote."""
    repo = Path.cwd().resolve()
    st = state_dir(repo)
    if not st:
        die("this repo is not registered (closer go registers it)")
    mf = json.loads((st / "manifest.json").read_text())
    if a.python is None and a.pytest_args is None:
        print(f"state {st}\n  interpreter: {mf.get('python') or 'the gate\'s own python'}\n  pytest args: {mf.get('pytest_args') or '(the repo\'s own settings)'}\n"
              f"  excludes: {', '.join(mf['roots'][0].get('exclude') or []) if mf.get('roots') else ''}")
        return 0
    python = pick_python(repo, a.python or mf.get("python"))
    pytest_args = pick_pytest_args(repo, a.pytest_args if a.pytest_args is not None else mf.get("pytest_args"))
    n, err = collection(repo, python, pytest_args)
    if n is None:
        die(f"the repo's tests do not collect under {python} with pytest args {pytest_args!r}:\n{err}")
    mf["python"] = python
    if pytest_args:
        mf["pytest_args"] = pytest_args
    else:
        mf.pop("pytest_args", None)
    (st / "manifest.json").write_text(json.dumps(mf, indent=2) + "\n")
    say(f"amended: interpreter {python}; pytest args {pytest_args!r} ({n} tests collect)")
    r = run(GC + ["--repo", str(repo), "scan"], cwd=repo)
    say((r.stdout + r.stderr).strip().splitlines()[-1])
    return 0


def cmd_forget(a):
    """Registered repos whose tree no longer exists: list them, and with --gone remove their state dirs (the ledger,
    Worlds, tickets and evidence of a repo that is gone). A repo that still exists is never touched here."""
    import shutil
    home = Path(os.environ.get("GETTING_CLOSE_HOME") or (Path.home() / ".getting-close"))
    gone = []
    for d in sorted(home.glob("*-*")):
        mf = d / "manifest.json"
        if not mf.is_file():
            continue
        repo = (json.loads(mf.read_text()) or {}).get("repo") or ""
        if repo and not Path(repo).is_dir():
            gone.append((d, repo))
    if not gone:
        say("every registered repo still exists; nothing to forget"); return 0
    for d, repo in gone:
        print(f"  {d.name}: repo gone ({repo})")
    if not a.gone:
        say(f"{len(gone)} state dir(s) point at repos that no longer exist; `closer forget --gone` removes them"); return 0
    for d, repo in gone:
        for pf in (d / "signer" / "watch.pid", d / "signer" / "server.pid"):
            if pf.is_file():
                try:
                    os.kill(int(pf.read_text().strip()), 15)
                except (ProcessLookupError, ValueError):
                    pass
        shutil.rmtree(d)
        say(f"forgot {d.name} ({repo})")
    return 0


def cmd_stop(a):
    st = state_dir(Path.cwd().resolve())
    if not st:
        die("this repo is not registered")
    stop_server(st); return 0


def main():
    ap = argparse.ArgumentParser(prog="closer", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    def common(s):
        s.add_argument("--python"); s.add_argument("--pytest-args"); s.add_argument("--write", action="append", default=[])
        s.add_argument("--port", type=int, default=8766); s.add_argument("--yes", action="store_true")
        s.add_argument("--chat", action="store_true"); s.add_argument("--no-launch", action="store_true")
        s.add_argument("--no-open", action="store_true"); s.add_argument("--redraft", action="store_true")
        s.add_argument("--raw", action="store_true")

    for name in ("go", "claims"):
        s = sub.add_parser(name); s.add_argument("task"); common(s); s.set_defaults(fn=cmd_go)
    s = sub.add_parser("demo"); common(s); s.set_defaults(fn=cmd_demo)
    s = sub.add_parser("doctor"); s.add_argument("--python"); s.add_argument("--pytest-args"); s.set_defaults(fn=cmd_doctor)
    s = sub.add_parser("task"); s.add_argument("name"); s.set_defaults(fn=cmd_task)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("inspect"); s.add_argument("ticket", nargs="?"); s.add_argument("--raw", action="store_true"); s.set_defaults(fn=cmd_inspect)
    s = sub.add_parser("amend"); s.add_argument("--python"); s.add_argument("--pytest-args"); s.set_defaults(fn=cmd_amend)
    s = sub.add_parser("watch"); s.add_argument("--every", type=float, default=4.0); s.set_defaults(fn=cmd_watch)
    s = sub.add_parser("forget"); s.add_argument("--gone", action="store_true", help="remove the state dirs of repos that no longer exist"); s.set_defaults(fn=cmd_forget)
    sub.add_parser("stop").set_defaults(fn=cmd_stop)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
