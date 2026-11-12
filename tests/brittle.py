"""Different seams from the other three probe sets: package layouts and relative imports, splice fidelity in a crowded
file, unicode, CRLF, timeouts, filesystem escapes, strike bookkeeping, parallel submissions, and the MCP pipe with a
bad path. python3 brittle.py CLOSER_DIR"""
import ast, json, os, subprocess, sys, tempfile, time
sys.path.insert(0, sys.argv[1]); import judge
CL = sys.argv[1]
ST = {"purpose": "p", "intent": "i", "agrees": True}
OPS = ('"""ops"""\nimport math\nfrom ..util import norm\n\nTAX = 0.2  # keep me\n\n\ndef first(x):\n    """first doc"""\n'
       '    return x + 1\n\n\ndef mid(x):\n    return x\n\n\ndef last(x):\n    # trailing comment\n    return math.floor(x) - TAX\n')
SEED = {"app/__init__.py": "", "app/util.py": "def norm(s):\n    return s.strip().lower()\n",
        "app/core/__init__.py": "", "app/core/ops.py": OPS,
        "app/crlf.py": "def a():\r\n    return 1\r\n\r\n\r\ndef b():\r\n    return 2\r\n"}
def fresh():
    repo = tempfile.mkdtemp(); os.environ["CLOSER_HOME"] = tempfile.mkdtemp()
    for rel, text in SEED.items():
        p = os.path.join(repo, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", newline="").write(text)
    outside = tempfile.mkdtemp(); os.symlink(outside, os.path.join(repo, "link"))
    return repo
def sub(repo, file, src, checks): return judge.submit(repo, file, src, checks, ST, "probe-plan")
def snapshot(repo): return sorted(os.path.relpath(os.path.join(d, f), repo) for d, _, fs in os.walk(repo) for f in fs)
bad = 0
def expect_not_written(name, repo, file, src, checks, verdict=None):
    global bad
    before = snapshot(repo); v, msg = sub(repo, file, src, checks)
    wrong = bool(v == "PASS" or snapshot(repo) != before or (verdict and v != verdict))
    bad += wrong; print(f"{'BAD' if wrong else 'ok '}  {name}: {v} {msg.splitlines()[-1][:110]}")
def expect_written(name, repo, file, src, checks):
    global bad
    v, msg = sub(repo, file, src, checks); wrong = v != "PASS"
    bad += wrong; print(f"{'BAD' if wrong else 'ok '}  {name}: {v} {msg.splitlines()[-1][:110]}")

print("--- paths and parse")
r = fresh()
expect_not_written("traversal", r, "../evil.py", "def f():\n    return 1", [{"call": "f()", "expect": 1}], "REFUSED")
expect_not_written("absolute", r, r + "/evil.py", "def f():\n    return 1", [{"call": "f()", "expect": 1}], "REFUSED")
expect_not_written("symlink escape", r, "link/evil.py", "def f():\n    return 1", [{"call": "f()", "expect": 1}], "REFUSED")
expect_not_written("not .py", r, "app/x.txt", "def f():\n    return 1", [{"call": "f()", "expect": 1}], "REFUSED")
expect_not_written("syntax error is a strike", r, "app/util.py", "def f(:\n    return 1", [{"call": "f()", "expect": 1}], "FAIL")
expect_not_written("two defs", r, "app/util.py", "def f():\n    return 1\ndef g():\n    return 2", [{"call": "f()", "expect": 1}], "REFUSED")
expect_not_written("call is not an expression", r, "app/util.py", "def f():\n    return 1", [{"call": "import os", "expect": 1}], "REFUSED")

print("--- sandbox")
r = fresh()
expect_not_written("writes into the real repo", r, "app/util.py",
                   f"def w():\n    open({os.path.join(r, 'app', 'planted.txt')!r}, 'w').write('x')\n    return 1", [{"call": "w()", "expect": 1}])
expect_not_written("__file__ points at the real repo", r, "app/util.py", "def here():\n    return __file__", [{"call": "here()", "expect": os.path.join(r, "app", "util.py")}])
expect_not_written("reads CLOSER state", r, "app/util.py",
                   f"def peek():\n    import os\n    return os.listdir({str(judge.state_dir(judge.Path(r)))!r})", [{"call": "peek()", "expect": []}])
expect_not_written("reaches a real host", r, "app/util.py",
                   "def ping():\n    import socket\n    socket.create_connection(('1.1.1.1', 80), timeout=3)\n    return 1", [{"call": "ping()", "expect": 1}])
t = time.time()
expect_not_written("infinite loop", r, "app/util.py", "def spin():\n    while True:\n        pass", [{"call": "spin()", "expect": 1}])
print(f"     (timeout took {time.time() - t:.0f}s, CHECK_SECS={judge.CHECK_SECS})")
expect_not_written("subprocess child is still sandboxed", r, "app/util.py",
                   f"def sp():\n    import subprocess\n    return subprocess.run(['sh', '-c', 'echo x > {os.path.join(r, 'app', 'planted.txt')} && echo wrote'], capture_output=True, text=True).stdout.strip()",
                   [{"call": "sp()", "expect": "wrote"}])

print("--- splice fidelity, relative imports, encodings")
r = fresh()
expect_written("replace mid of ops.py", r, "app/core/ops.py", "def mid(x):\n    return x * 2", [{"call": "mid(4)", "expect": 8}])
new = open(os.path.join(r, "app/core/ops.py")).read()
for piece in ('"""ops"""\nimport math\nfrom ..util import norm\n\nTAX = 0.2  # keep me\n', 'def first(x):\n    """first doc"""\n    return x + 1\n',
              'def last(x):\n    # trailing comment\n    return math.floor(x) - TAX\n'):
    if piece not in new: bad += 1; print("BAD  splice lost:", piece.splitlines()[0])
if "return x * 2" not in new or new.count("def mid") != 1: bad += 1; print("BAD  mid not replaced exactly once")
ast.parse(new); print("ok   rest of ops.py intact")
expect_written("uses the module's relative import", r, "app/core/ops.py", "def shout(s):\n    return norm(s).upper()", [{"call": "shout('  Hi ')", "expect": "HI"}])
expect_written("calls a sibling def in the same file", r, "app/core/ops.py", "def both(x):\n    return first(x) + mid(x)", [{"call": "both(2)", "expect": 7}])
expect_written("unicode", r, "app/util.py", "def greet(n):\n    return f'héllo {n} ✓'", [{"call": "greet('Zoë')", "expect": "héllo Zoë ✓"}])
assert "héllo" in open(os.path.join(r, "app/util.py"), encoding="utf-8").read()
expect_written("star args and kw-only", r, "app/util.py", "def join(*parts, sep=', '):\n    return sep.join(parts)", [{"call": "join('a', 'b', sep='-')", "expect": "a-b"}])
expect_written("CRLF file", r, "app/crlf.py", "def b():\n    return 3", [{"call": "b()", "expect": 3}])
crlf = open(os.path.join(r, "app/crlf.py"), newline="").read(); ast.parse(crlf)
print(f"     (crlf after splice: a() still CRLF={'def a():\r\n' in crlf}, parses)")
expect_written("new file in a new dir", r, "app/new/deep.py", "def d():\n    return 1", [{"call": "d()", "expect": 1}])
expect_written("new file with its own import", r, "app/fresh.py", "from app.util import norm\n\ndef low(s):\n    return norm(s)", [{"call": "low(' A ')", "expect": "a"}])
expect_written("set returned", r, "app/util.py", "def st():\n    return {2, 1}", [{"call": "st()", "expect": [1, 2]}])
expect_written("big nested expect", r, "app/util.py", "def big(n):\n    return {'rows': [[i, str(i), i % 2 == 0] for i in range(n)], 'n': n}",
               [{"call": "big(300)", "expect": {"rows": [[i, str(i), i % 2 == 0] for i in range(300)], "n": 300}}])
expect_written("serve: json body, two bodies", r, "app/util.py", "def price(url):\n    import json, urllib.request\n    return json.load(urllib.request.urlopen(url))['p']",
               [{"call": "price(url)", "serve": {"body": '{"p": 2.5}'}, "expect": 2.5}, {"call": "price(url)", "serve": {"body": '{"p": 9}'}, "expect": 9}])
expect_written("serve: two requests in one call", r, "app/util.py", "def twice(url):\n    import urllib.request\n    return sum(float(urllib.request.urlopen(url).read()) for _ in range(2))",
               [{"call": "twice(url)", "serve": {"body": "1.5"}, "expect": 3.0}])
open(os.path.join(r, "app/core/boom.py"), "w").write("from app.core import Boom\n\ndef fire():\n    raise Boom('x')\n")
expect_written("package __init__ is one module: sibling's import of its class is the same class", r, "app/core/__init__.py",
               "class Boom(Exception):\n    def __init__(self, m):\n        self.m = m\n    def text(self):\n        return self.m", [{"call": ["Boom('a')", ".text()"], "expect": "a"}])
expect_written("package __init__ catches its own class raised by a sibling", r, "app/core/__init__.py",
               "def safe():\n    from app.core.boom import fire  # inside: a top-level import here would be circular in plain Python too\n    try:\n        fire()\n    except Boom:\n        return 'caught'\n    return 'missed'", [{"call": "safe()", "expect": "caught"}])
expect_written("imports merged by name, not by line", r, "app/core/ops.py",
               "import math\nfrom decimal import Decimal\nfrom ..util import norm\nimport json\n\ndef dec(x):\n    return str(Decimal(x) + 1)", [{"call": "dec('1.5')", "expect": "2.5"}])
imps = [l for l in open(os.path.join(r, "app/core/ops.py")).read().splitlines() if l.startswith(("import ", "from "))]
if imps != ["import math", "from ..util import norm", "from decimal import Decimal", "import json"]: bad += 1; print("BAD  import merge:", imps)
else: print("ok   import block after merge:", imps)
expect_written("files: read a json fixture", r, "app/util.py", "import json\n\ndef load(path):\n    return json.load(open(path))['n']",
               [{"call": "load(files['z.json'])", "files": {"z.json": "{\"n\": 7}"}, "expect": 7}, {"call": "load(files['z.json'])", "files": {"z.json": "{\"n\": 8}"}, "expect": 8}])
expect_written("files: write beside the fixture, subdir name", r, "app/util.py", "def conv(src):\n    out = src + '.out'\n    open(out, 'w').write(open(src).read().upper())\n    return open(out).read()",
               [{"call": "conv(files['d/in.txt'])", "files": {"d/in.txt": "abc"}, "expect": "ABC"}])
expect_written("files: missing file still raises", r, "app/util.py", "def rd(p):\n    return open(p).read()", [{"call": "rd('/nonexistent/x')", "raises": "FileNotFoundError"}])
expect_not_written("files: name escapes", r, "app/util.py", "def rd2(p):\n    return open(p).read()", [{"call": "rd2(files['../x'])", "files": {"../x": "a"}, "expect": "a"}], "REFUSED")
expect_not_written("files: unknown key in the call", r, "app/util.py", "def rd3(p):\n    return open(p).read()", [{"call": "rd3(files['other'])", "files": {"x": "a"}, "expect": "a"}])
expect_not_written("files: counterfeit ignoring the file", r, "app/util.py", "def rd4(p):\n    return 'a'", [{"call": "rd4(files['x'])", "files": {"x": "a"}, "expect": "a"}, {"call": "rd4(files['x'])", "files": {"x": "b"}, "expect": "b"}])
expect_not_written("decorated def (lru_cache)", r, "app/util.py", "import functools\n\n@functools.lru_cache\ndef fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)", [{"call": "fib(10)", "expect": 55}])

print("--- strike bookkeeping")
r = fresh()
F, G = "app/util.py", [{"call": "f()", "expect": 1}]
expect_not_written("f fail 1", r, F, "def f():\n    return 0", G, "FAIL")
expect_written("g passes between", r, F, "def g():\n    return 1", [{"call": "g()", "expect": 1}])
expect_written("f passes (clears)", r, F, "def f():\n    return 1", G)
expect_not_written("f fail again is try 1 not hole", r, F, "def f():\n    return 0", G, "FAIL")
expect_not_written("f fail -> hole", r, F, "def f():\n    return 0", G, "HOLE")
expect_not_written("g unaffected by f's hole", r, F, "def g():\n    return 0", [{"call": "g()", "expect": 1}], "FAIL")
holes = open(os.path.join(os.environ["CLOSER_HOME"], os.listdir(os.environ["CLOSER_HOME"])[0], "holes.jsonl")).read().count("\n")
print(f"     holes.jsonl records: {holes} (expect 1)"); bad += holes != 1

print("--- parallel submissions")
r = fresh()
code = f"import sys; sys.path.insert(0, {CL!r}); import judge; print(judge.submit({r!r}, 'app/util.py', 'def p%d():\\n    return %d', [{{'call': 'p%d()', 'expect': %d}}], {ST!r}, 'probe-plan')[0])"
procs = [subprocess.Popen([sys.executable, "-c", code % (i, i, i, i)], stdout=subprocess.PIPE, text=True, env=os.environ) for i in range(8)]
outs = [p.communicate()[0].strip() for p in procs]
text = open(os.path.join(r, "app/util.py")).read(); ast.parse(text)
missing = [i for i in range(8) if f"def p{i}" not in text]
bad += bool(missing) or outs.count("PASS") != 8
print(f"{'BAD' if missing or outs.count('PASS') != 8 else 'ok '}  8 parallel: verdicts={outs.count('PASS')} PASS, missing defs={missing}, file parses, norm kept={'def norm' in text}")

print("--- MCP pipe: repo is fixed, bad paths refused")
r = fresh()
p = subprocess.Popen([sys.executable, f"{CL}/closer_mcp.py", r], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=os.environ)
def rpc(i, method, params):
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n"); p.stdin.flush()
    while True:
        m = json.loads(p.stdout.readline())
        if m.get("method") == "elicitation/create":
            p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": {"action": "accept", "content": {}}}) + "\n"); p.stdin.flush(); continue
        if m.get("id") == i: return m
rpc(0, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {"elicitation": {}}})
names = [t["name"] for t in rpc(1, "tools/list", {})["result"]["tools"]]
print("ok " if names == ["cl_plan", "cl_submit"] else "BAD", "tools:", names); bad += names != ["cl_plan", "cl_submit"]
rpc(2, "tools/call", {"name": "cl_plan", "arguments": {"intent": "i", "expectation": "e"}})
for name, args in [("absolute file", {"file": "/etc/x.py"}), ("traversal", {"file": "../x.py"}), ("missing checks", {"file": "app/util.py", "checks": None}),
                   ("huge garbage", {"file": "app/util.py", "source": "x" * 200000, "checks": [{"call": "f()", "expect": 1}]})]:
    a = {"file": "app/util.py", "source": "def f():\n    return 1", "checks": [{"call": "f()", "expect": 1}], "stance": ST, **args}
    t = rpc(3, "tools/call", {"name": "cl_submit", "arguments": a})["result"]["content"][0]["text"]
    ok = "PASS" not in t; bad += not ok; print(f"{'ok ' if ok else 'BAD'}  {name}: {t.splitlines()[-1][:100]}")
t = rpc(4, "tools/call", {"name": "nope", "arguments": {}}); print("ok " if "error" in t or "PASS" not in json.dumps(t) else "BAD", "unknown tool:", json.dumps(t)[:100])
p.kill(); print(f"\n{bad} problem(s)"); sys.exit(bad != 0)
