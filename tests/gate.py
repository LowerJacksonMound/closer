"""The gate rows plus holes tolerance, venv interpreter and state-dir slugs, with the hook timed on every call.
Runs the real hook scripts as subprocesses under a throwaway HOME, so no real control file, log, cache or
notification is touched (osascript is shadowed by a stub on PATH). python3 gate.py CLOSER_DIR"""
import json, os, statistics, subprocess, sys, tempfile, time
CL = os.path.abspath(sys.argv[1]); sys.path.insert(0, CL); import judge, holes
OFF = "CLOSER_GATE_" + "OFF"  # spelled apart: the gate denies writing this file otherwise, which is the point of one probe below
HOME = tempfile.mkdtemp(); CH = os.path.join(HOME, ".closer"); os.makedirs(os.path.join(HOME, ".claude", "hooks")); os.makedirs(CH)
BIN = os.path.join(HOME, "bin"); os.makedirs(BIN); NOTE = os.path.join(HOME, "notified.txt")
open(os.path.join(BIN, "osascript"), "w").write(f"#!/bin/sh\necho \"$@\" >> {NOTE}\n"); os.chmod(os.path.join(BIN, "osascript"), 0o755)
ENV = {**os.environ, "HOME": HOME, "CLOSER_HOME": CH, "PATH": BIN + ":" + os.environ["PATH"]}; ENV.pop(OFF, None)
GATE, NUDGE = os.path.join(CL, "closer_gate.py"), os.path.join(CL, "closer_gate_nudge.py")
LOG = os.path.join(HOME, ".claude", "hooks", "closer_gate.log")
W = tempfile.mkdtemp(); times = []; bad = 0

def mk(name, files):
    root = os.path.join(W, name)
    for rel, text in files.items():
        p = os.path.join(root, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(text)
    return os.path.realpath(root)
def hook(script, event, env=None):
    t = time.time(); r = subprocess.run([sys.executable, script], input=json.dumps(event) if isinstance(event, dict) else event,
                                        capture_output=True, text=True, env=env or ENV); times.append(time.time() - t)
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip() else None), r.stderr
def last_log():
    try: return json.loads(open(LOG).read().splitlines()[-1])
    except (OSError, IndexError): return {}
def write(cwd, tool, path, **ti): return hook(GATE, {"session_id": "s1", "tool_name": tool, "cwd": cwd, "tool_input": {("notebook_path" if tool == "NotebookEdit" else "file_path"): path, **ti}})
def check(name, cond, got: object = ""):
    global bad; bad += not cond; print(f"{'ok ' if cond else 'BAD'}  {name} {str(got)[:100]}")
def denied(name, res, must=""): check(name, res[1] and res[1]["hookSpecificOutput"]["permissionDecision"] == "deny" and must in res[1]["hookSpecificOutput"]["permissionDecisionReason"], res[1] or last_log())
def allowed(name, res, why=""): check(name, res[0] == 0 and res[1] is None and why in last_log().get("reason", ""), last_log())

PY = mk("py", {"pyproject.toml": "", "a.py": "", "README.md": "", "cfg.json": "{}", "t/test_a.py": "", "web/index.html": ""})
WEB = mk("web", {"package.json": "{}", "src/app.ts": "", "index.html": ""})
BOTH = mk("both", {"pyproject.toml": "", "package.json": "{}", "a.py": "", "src/a.js": ""})
GO = mk("go", {"go.mod": "", "main.go": "", "pyproject.toml": ""})
MIXED = mk("mixed", {"pyproject.toml": "", "a.py": "", "lib.rs": ""})
FRESH = mk("fresh", {"pyproject.toml": "", "README.md": ""}); FRESHWEB = mk("freshweb", {"package.json": "{}"}); NOCODE = mk("nocode", {"README.md": "", "a.txt": ""})
REG = mk("registered", {"a.py": ""}); os.makedirs(os.path.join(CH, "registered-x")); open(os.path.join(CH, "registered-x/manifest.json"), "w").write(json.dumps({"repo": REG}))
VEND = mk("outer", {"package.json": "{}", "src/a.js": "", "node_modules/inner/pyproject.toml": "", "node_modules/inner/a.py": ""})
NESTED = mk("nest", {"pyproject.toml": "", "sub/package.json": "{}", "sub/a.js": "", "a.py": ""})
PLAIN = mk("plain", {"a.py": "", "notes.md": ""})
OPTED = mk("opted", {"x.sh": ""}); SKIP = mk("skipped", {"pyproject.toml": "", "a.py": ""})
open(os.path.join(HOME, ".claude/closer_gate_roots.txt"), "w").write(f"# c\n{OPTED}\n")
open(os.path.join(HOME, ".claude/closer_gate_skip.txt"), "w").write(f"{SKIP}\n")
open(os.path.join(HOME, ".claude/closer_gate_protect.txt"), "w").write(f"{PY}/secrets.env\n{PY}/data/*.csv\n")
BIG = mk("big", {f"pkg{i // 200}/m{i}.py": "" for i in range(3000)} | {"pyproject.toml": ""})

print("--- classify")
def cls(d): return json.loads(subprocess.run([sys.executable, GATE, "--classify", d], capture_output=True, text=True, env=ENV).stdout)
for name, d, root, scope in [("python+html is python+web", PY, PY, "gated python+web repo"), ("web", WEB, WEB, "gated web"), ("python+js", BOTH, BOTH, "gated python+web repo"),
                             ("go beside pyproject is non-Python", GO, None, "non-Python"), ("rust file makes it mixed", MIXED, None, "mixed"),
                             ("fresh python project gated by marker", FRESH, FRESH, "gated python repo"), ("fresh web project likewise", FRESHWEB, FRESHWEB, "gated web repo"), ("no marker no code", NOCODE, None, "not in a CLOSER-registered"), ("registered without markers", REG, REG, "gated python repo"),
                             ("vendored pyproject never a root", os.path.join(VEND, "node_modules/inner"), VEND, "gated web"),
                             ("innermost marker wins", os.path.join(NESTED, "sub"), os.path.join(NESTED, "sub"), "gated web"),
                             ("no marker no registration", PLAIN, None, "not in a CLOSER-registered"), ("roots.txt opt-in", OPTED, OPTED, "opted in"),
                             ("skip.txt opt-out", SKIP, None, "opted out"), ("big repo walk", BIG, BIG, "gated python repo")]:
    c = cls(d); check(name, c["gated_root"] == root and scope in c["scope"], c["scope"])

print("--- Edit/Write/MultiEdit/NotebookEdit")
denied("first .py in a fresh project", write(FRESH, "Write", "ledger/__init__.py", content=""), "Write on ledger/__init__.py")
denied("Edit .py", write(PY, "Edit", "a.py", old_string="x", new_string="y"), "Edit on a.py")
denied("Write new .py", write(PY, "Write", "new/mod.py", content="x"))
denied("MultiEdit .py", write(PY, "MultiEdit", "a.py", edits=[]))
denied("NotebookEdit .ipynb", write(PY, "NotebookEdit", "nb.ipynb"))
denied("test file is code", write(PY, "Edit", "t/test_a.py", old_string="x", new_string="y"))
denied("html in a python repo", write(PY, "Write", "web/index.html", content=""), "HTML in a gated repo")
denied("protected file by glob", write(PY, "Write", "data/x.csv", content=""), "protected file")
denied("protected exact path", write(PY, "Write", "secrets.env", content=""), "protected file")
denied("absolute path from another cwd", write("/", "Edit", f"{PY}/a.py", old_string="x", new_string="y"))
denied(".ts in web repo", write(WEB, "Edit", "src/app.ts", old_string="x", new_string="y"))
denied(".js in python+web", write(BOTH, "Edit", "src/a.js", old_string="x", new_string="y"))
denied("registered repo", write(REG, "Edit", "a.py", old_string="x", new_string="y"))
denied("roots.txt repo gates even a .sh", write(OPTED, "Edit", "x.sh", old_string="x", new_string="y"))
allowed("README.md", write(PY, "Edit", "README.md", old_string="x", new_string="y"), "no gated code write")
allowed("cfg.json", write(PY, "Write", "cfg.json", content="{}"), "no gated code write")
allowed(".py in go repo (out of scope)", write(GO, "Write", "x.py", content=""), "non-Python")
allowed(".py in mixed repo", write(MIXED, "Edit", "a.py", old_string="x", new_string="y"), "mixed")
allowed(".py in plain folder", write(PLAIN, "Edit", "a.py", old_string="x", new_string="y"), "not in a CLOSER")
allowed("skip.txt wins", write(SKIP, "Edit", "a.py", old_string="x", new_string="y"), "opted out")
allowed("exempt: scratchpad", write(PY, "Write", "/tmp/claude-501/x/y.py", content=""), "no gated code write")
allowed("other tool", hook(GATE, {"session_id": "s1", "tool_name": "Read", "cwd": PY, "tool_input": {"file_path": "a.py"}}), "tool not gated")
allowed("no path", hook(GATE, {"session_id": "s1", "tool_name": "Edit", "cwd": PY, "tool_input": {}}), "no path")
r = write(VEND, "Edit", "node_modules/inner/a.py", old_string="x", new_string="y"); print(f"     (vendored .py inside a web repo: {last_log()['decision']}, documented either way)")

print("--- the gate's own controls and sealed state")
denied("assigns the off var in content", write(PLAIN, "Write", "run.sh", content=f"export {OFF}=1"), "switch the gate off")
denied("assigns the off var in an edit", write(PLAIN, "Edit", "notes.md", old_string="", new_string=f"{OFF} = 1"), "switch the gate off")
denied("off file", write(PLAIN, "Write", f"{HOME}/.claude/closer_gate.off", content=""), "gate's own controls")
denied("skip.txt", write(PLAIN, "Edit", f"{HOME}/.claude/closer_gate_skip.txt", old_string="", new_string="x"), "gate's own controls")
denied("hook script", write(PLAIN, "Write", f"{HOME}/.claude/hooks/closer_gate_nudge.py", content=""), "gate's own controls")
denied("cache file", write(PLAIN, "Write", f"{HOME}/.claude/hooks/.closer_gate_cache.json", content=""), "gate's own controls")
open(os.path.join(HOME, ".claude/settings.json"), "w").write(json.dumps({"model": "x", "hooks": {"PreToolUse": []}}))
denied("settings.json hook edit", write(PLAIN, "Edit", f"{HOME}/.claude/settings.json", old_string='"PreToolUse"', new_string='"X"'), "hooks or sandbox block")
denied("settings.json Write that drops hooks", write(PLAIN, "Write", f"{HOME}/.claude/settings.json", content=json.dumps({"model": "x"})), "hooks or sandbox block")
allowed("settings.json Write keeping hooks", write(PLAIN, "Write", f"{HOME}/.claude/settings.json", content=json.dumps({"model": "y", "hooks": {"PreToolUse": []}})), "leaves hooks")
allowed("settings.json Edit of model", write(PLAIN, "Edit", f"{HOME}/.claude/settings.json", old_string='"x"', new_string='"y"'), "leaves hooks")
for f in ("intent/x.json", "landed.json", "strikes.jsonl", "holes.jsonl", "agree.jsonl", "plans.jsonl"):
    denied(f"sealed {f}", write(PLAIN, "Write", f"{CH}/registered-x/{f}", content=""), "sealed state")
allowed("manifest.json is not sealed", write(PLAIN, "Write", f"{CH}/registered-x/manifest.json", content="{}"), "no gated code write")

print("--- Bash")
denied("dangerouslyDisableSandbox in gated repo", hook(GATE, {"session_id": "s1", "tool_name": "Bash", "cwd": PY, "tool_input": {"command": "ls", "dangerouslyDisableSandbox": True}}), "inside the sandbox")
allowed("dangerouslyDisableSandbox outside", hook(GATE, {"session_id": "s1", "tool_name": "Bash", "cwd": PLAIN, "tool_input": {"command": "ls", "dangerouslyDisableSandbox": True}}), "bash: cwd")
r = hook(GATE, {"session_id": "s1", "tool_name": "Bash", "cwd": PY, "tool_input": {"command": "echo x > a.py"}})
check("unenforced: allowed, logged, notified", r[1] is None and last_log()["decision"] == "allow-unenforced" and "osascript started" in last_log()["reason"], last_log())
for _ in range(20):
    if os.path.exists(NOTE): break
    time.sleep(0.1)
check("stub notification fired", os.path.exists(NOTE) and "NOT write-protected" in open(NOTE).read(), os.listdir(HOME))
r = hook(GATE, {"session_id": "s1", "tool_name": "Bash", "cwd": PY, "tool_input": {"command": "echo y > a.py"}})
check("second notify suppressed within 60s", "suppressed" in last_log()["reason"], last_log()["reason"][-60:])
allowed("no command field", hook(GATE, {"session_id": "s1", "tool_name": "Bash", "cwd": PY, "tool_input": {}}), "no command")
PROP = os.path.join(HOME, "proposed.json"); subprocess.run([sys.executable, GATE, "--emit-sandbox", PROP], capture_output=True, text=True, env=ENV)
prop = json.load(open(PROP)); deny = prop["sandbox"]["filesystem"]["denyWrite"]
check("emit: every gated repo listed, no out-of-scope one", set(prop["_gated_repos"]) == {REG, OPTED} and f"{REG}/**/*.py" in deny, list(prop["_gated_repos"]))
check("emit: sealed state in denyWrite, hooks wired", any("holes.jsonl" in d for d in deny) and all(k in prop["hooks"] for k in ("PreToolUse", "SessionStart", "UserPromptSubmit")))
open(os.path.join(HOME, "sb.json"), "w").write(json.dumps({"sandbox": {**prop["sandbox"], "filesystem": {"denyWrite": deny + [f"{PY}/**/*.py"]}}}))
r = hook(GATE, {"session_id": "s1", "tool_name": "Bash", "cwd": PY, "tool_input": {"command": "ls"}}, {**ENV, "CLOSER_GATE_SANDBOX_SETTINGS": os.path.join(HOME, "sb.json")})
check("covered: file-level, no notify", last_log()["decision"] == "allow" and "file-level" in last_log()["reason"], last_log()["reason"])
open(os.path.join(HOME, "sb2.json"), "w").write(json.dumps({"sandbox": {"enabled": True, "filesystem": {"disabled": True, "denyWrite": [f"{PY}/**/*.py"]}}}))
r = hook(GATE, {"session_id": "s1", "tool_name": "Bash", "cwd": PY, "tool_input": {"command": "ls"}}, {**ENV, "CLOSER_GATE_SANDBOX_SETTINGS": os.path.join(HOME, "sb2.json")})
check("filesystem.disabled is not covered", last_log()["decision"] == "allow-unenforced", last_log()["reason"][:60])

print("--- off switches, fail-open, watchdog, cache")
r = hook(GATE, {"session_id": "s1", "tool_name": "Edit", "cwd": PY, "tool_input": {"file_path": "a.py"}}, {**ENV, OFF: "1"})
check("env off: allowed, logged off", r[1] is None and last_log()["decision"] == "off")
open(os.path.join(HOME, ".claude/closer_gate.off"), "w").close()
r = hook(GATE, {"session_id": "s1", "tool_name": "Edit", "cwd": PY, "tool_input": {"file_path": "a.py"}}); check("off file: allowed", r[1] is None and last_log()["decision"] == "off")
r = hook(NUDGE, {"session_id": "s9", "hook_event_name": "SessionStart", "cwd": PY}); check("off file silences the nudge", r[1] is None)
os.remove(os.path.join(HOME, ".claude/closer_gate.off"))
denied("back on after removing the file", write(PY, "Edit", "a.py", old_string="x", new_string="y"))
r = hook(GATE, "{not json"); check("bad json: exit 0, systemMessage, fail-open logged", r[0] == 0 and "crashed" in (r[1] or {}).get("systemMessage", "") and last_log()["decision"] == "error-fail-open", r[1])
r = hook(GATE, "[1,2]"); check("non-object: fail-open", r[0] == 0 and last_log()["decision"] == "error-fail-open")
r = hook(GATE, {"session_id": "s1", "tool_name": "Edit", "cwd": PY, "tool_input": {"file_path": "a.py"}}, {**ENV, "CLOSER_GATE_FORCE_CRASH": "1"})
check("internal crash: allowed with systemMessage, notified", r[0] == 0 and "systemMessage" in (r[1] or {}) and "notify" in last_log())
inflight = os.path.join(HOME, ".claude/hooks/.closer_gate_inflight"); open(os.path.join(inflight, "999-0.000"), "w").close(); os.utime(os.path.join(inflight, "999-0.000"), (1, 1))
write(PY, "Edit", "a.py", old_string="x", new_string="y"); logs = [json.loads(l) for l in open(LOG).read().splitlines()]
check("stale inflight marker reported once and removed", logs[-2]["decision"] == "watchdog" and not os.listdir(inflight), logs[-2])
cache = json.load(open(os.path.join(HOME, ".claude/hooks/.closer_gate_cache.json")))
check("classification cached per repo", any(k == PY or k.startswith(PY) for k in cache), list(cache)[:2])

print("--- nudge")
r = hook(NUDGE, {"session_id": "n1", "hook_event_name": "SessionStart", "cwd": PY}); ctx = (r[1] or {}).get("hookSpecificOutput", {}).get("additionalContext", "")
check("SessionStart in gated repo: context with the flow", "gated repo (python+web)" in ctx and "cl_submit" in ctx and "Do not write code files with Bash" in ctx, ctx[:80])
r = hook(NUDGE, {"session_id": "n1", "hook_event_name": "UserPromptSubmit", "cwd": PY}); check("same session prompt: silent", r[1] is None)
r = hook(NUDGE, {"session_id": "n2", "hook_event_name": "UserPromptSubmit", "cwd": PY}); check("new session prompt: nudged once", r[1] is not None)
r = hook(NUDGE, {"session_id": "n3", "hook_event_name": "SessionStart", "cwd": PLAIN}); check("non-gated: silent", r[1] is None)
r = hook(NUDGE, {"session_id": "n4", "hook_event_name": "SessionStart", "cwd": OPTED}); check("opted in says so", "opted in" in (r[1] or {}).get("hookSpecificOutput", {}).get("additionalContext", ""))
r = hook(NUDGE, {"session_id": "n5", "hook_event_name": "PreToolUse", "cwd": PY}); check("other events: silent", r[1] is None)
r = hook(NUDGE, {"session_id": "n6", "hook_event_name": "SessionStart", "cwd": PY}, {**ENV, "CLOSER_GATE_SANDBOX_SETTINGS": os.path.join(HOME, "sb.json")})
check("covered repo: says Bash is OS-protected", "OS level" in (r[1] or {}).get("hookSpecificOutput", {}).get("additionalContext", ""))
r = hook(NUDGE, "garbage"); check("nudge bad input: exit 0, silent", r[0] == 0 and r[1] is None)

print("--- holes._lines tolerance, interpreter, state slugs")
p = judge.Path(HOME) / "h.jsonl"; p.write_bytes(b'{"a": 1}\nnot json\n[1, 2]\n\xff\xfe{"b": 2}\n{"c": 3}\n{"trunc')
check("holes._lines keeps the dict lines only", [list(r) for r in holes._lines(p)] == [["a"], ["c"]], holes._lines(p))
check("missing file -> []", holes._lines(judge.Path(HOME) / "none.jsonl") == [])
VR = mk("venv_repo", {"app.py": ""}); os.makedirs(os.path.join(VR, ".venv/bin")); os.symlink(sys.executable, os.path.join(VR, ".venv/bin/python"))
check("interpreter picks .venv python", judge.interpreter(judge.Path(VR)) == os.path.join(VR, ".venv/bin/python"))
os.environ["CLOSER_HOME"] = CH
v, msg = judge.submit(VR, "app.py", "def which():\n    import sys\n    return sys.executable", [{"call": "which()", "expect": os.path.join(VR, ".venv/bin/python")}], {"purpose": "p", "intent": "i", "agrees": True}, "pp")
check("checks run under the repo venv", v == "PASS", msg.splitlines()[-1][:80])
NX = mk("novenv", {"app.py": "", ".venv/bin/python": "not executable"}); check("non-executable venv python falls back", judge.interpreter(judge.Path(NX)) == sys.executable)
A1, A2 = mk("one/app", {"a.py": ""}), mk("two/app", {"a.py": ""})
check("two repos named app get different state dirs", judge.state_dir(judge.Path(A1)) != judge.state_dir(judge.Path(A2)) and judge.state_dir(judge.Path(A1)).name.startswith("app-"))

print("--- speed")
os.remove(os.path.join(HOME, ".claude/hooks/.closer_gate_cache.json"))  # classify above already cached BIG
t = time.time(); write(BIG, "Edit", "pkg0/m0.py", old_string="x", new_string="y"); cold = time.time() - t
t = time.time(); write(BIG, "Edit", "pkg0/m1.py", old_string="x", new_string="y"); warm = time.time() - t
med = statistics.median(times); p95 = sorted(times)[int(len(times) * 0.95)]
print(f"     hook calls: {len(times)}  median {med*1000:.0f} ms  p95 {p95*1000:.0f} ms  max {max(times)*1000:.0f} ms  |  3000-file repo cold {cold*1000:.0f} ms, cached {warm*1000:.0f} ms")
check("median hook call under 250 ms", med < 0.25, f"{med*1000:.0f} ms")
check("3000-file repo under 1 s cold and 250 ms cached", cold < 1.0 and warm < 0.25, f"{cold*1000:.0f}/{warm*1000:.0f} ms")
print(f"\n{bad} problem(s)"); sys.exit(bad != 0)
