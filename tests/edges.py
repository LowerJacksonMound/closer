"""The thin rows: same() edge cases, raises forms, async and generators, and the cl_plan paths asserted (client.py only
prints them). python3 edges.py CLOSER_DIR"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, sys.argv[1]); import judge, holes
CL = sys.argv[1]
ST = {"purpose": "p", "intent": "i", "agrees": True}
bad = 0
def fresh():
    repo = tempfile.mkdtemp(); os.environ["CLOSER_HOME"] = tempfile.mkdtemp()
    os.makedirs(os.path.join(repo, "app")); open(os.path.join(repo, "app/__init__.py"), "w").write("")
    open(os.path.join(repo, "app/errs.py"), "w").write("class Boom(ValueError):\n    pass\n")
    open(os.path.join(repo, "app/m.py"), "w").write("def seed():\n    return 0\n")
    return repo
def probe(name, repo, src, checks, want, file="app/m.py"):
    global bad
    v, msg = judge.submit(repo, file, src, checks, ST, "probe-plan"); wrong = v != want
    bad += wrong; print(f"{'BAD' if wrong else 'ok '}  {name}: {v} (want {want}) {msg.splitlines()[-1][:100]}")

print("--- same(): value comparison")
r = fresh()
probe("True is not 1", r, "def t():\n    return True", [{"call": "t()", "expect": 1}], "FAIL")
probe("1 is not True", r, "def o():\n    return 1", [{"call": "o()", "expect": True}], "FAIL")
probe("0 is not False", r, "def z():\n    return 0", [{"call": "z()", "expect": False}], "FAIL")
probe("1 == 1.0 (JS client sends 1)", r, "def one():\n    return 1.0", [{"call": "one()", "expect": 1}], "PASS")
probe("float sum needs the exact value", r, "def fs():\n    return 0.1 + 0.2", [{"call": "fs()", "expect": 0.3}], "FAIL")
probe("float sum with the exact value", r, "def fs2():\n    return 0.1 + 0.2", [{"call": "fs2()", "expect": 0.30000000000000004}], "PASS")
probe("nan never matches", r, "def nn():\n    return float('nan')", [{"call": "nn()", "expect": float("nan")}], "FAIL")
probe("inf matches inf", r, "def inf():\n    return float('inf')", [{"call": "inf()", "expect": float("inf")}], "PASS")
probe("-0.0 == 0", r, "def nz():\n    return -0.0", [{"call": "nz()", "expect": 0}], "PASS")
probe("bytes are {__bytes__: text}", r, "def by():\n    return b'a,b\\n1,2\\n'", [{"call": "by()", "expect": {"__bytes__": "a,b\n1,2\n"}}], "PASS")
probe("contains reads bytes as text", r, "def by2():\n    return b'\\x89PNG\\r\\nIHDR'", [{"call": "by2()", "contains": ["PNG", "IHDR"]}], "PASS")
probe("str is not bytes", r, "def by3():\n    return 'a,b'", [{"call": "by3()", "expect": {"__bytes__": "a,b"}}], "FAIL")
os.makedirs(os.path.join(r, "ns"), exist_ok=True); open(os.path.join(r, "ns/t.py"), "w").write("class T:\n    def __init__(self, v):\n        self.v = v\n")
probe("repo package without __init__.py resolves", r, "def nv(t):\n    return t.v", [{"call": "nv(ns.t.T(4))", "expect": 4}], "PASS")
probe("tuple is a list", r, "def tp():\n    return (1, (2, 3))", [{"call": "tp()", "expect": [1, [2, 3]]}], "PASS")
probe("list vs dict", r, "def ld():\n    return [1]", [{"call": "ld()", "expect": {"0": 1}}], "FAIL")
probe("list order matters", r, "def lo():\n    return [1, 2]", [{"call": "lo()", "expect": [2, 1]}], "FAIL")
probe("list length matters", r, "def ll():\n    return [1, 2]", [{"call": "ll()", "expect": [1, 2, 3]}], "FAIL")
probe("dict key order free", r, "def dk():\n    return {'b': 1, 'a': 2}", [{"call": "dk()", "expect": {"a": 2, "b": 1}}], "PASS")
probe("dict extra key", r, "def de():\n    return {'a': 1, 'b': 2}", [{"call": "de()", "expect": {"a": 1}}], "FAIL")
probe("dict int keys become json keys", r, "def di():\n    return {1: 'x'}", [{"call": "di()", "expect": {"1": "x"}}], "PASS")
probe("dict tuple keys become json keys", r, "def dt():\n    return {(1, 2): 'x'}", [{"call": "dt()", "expect": {"[1, 2]": "x"}}], "PASS")
probe("set sorted, order free", r, "def ss():\n    return {'b', 'a'}", [{"call": "ss()", "expect": ["a", "b"]}], "PASS")
probe("None vs 0", r, "def nv():\n    return None", [{"call": "nv()", "expect": 0}], "FAIL")
probe("None vs None", r, "def nn2():\n    return None", [{"call": "nn2()", "expect": None}], "PASS")
probe("'1' vs 1", r, "def s1():\n    return '1'", [{"call": "s1()", "expect": 1}], "FAIL")
probe("bytes are not plain", r, "def by():\n    return b'x'", [{"call": "by()", "expect": "x"}], "FAIL")
probe("nested True deep inside", r, "def nt():\n    return {'a': [1, {'b': True}]}", [{"call": "nt()", "expect": {"a": [1, {"b": 1}]}}], "FAIL")
probe("object as __class__ + attrs", r, "def ob():\n    class P:\n        def __init__(self):\n            self.x = 1\n            self._h = 2\n    return P()",
      [{"call": "ob()", "expect": {"__class__": "P", "x": 1}}], "PASS")
probe("enum as __class__ + name", r, "def en():\n    import enum\n    class C(enum.Enum):\n        RED = 1\n    return C.RED", [{"call": "en()", "expect": {"__class__": "C", "name": "RED"}}], "PASS")
probe("big int exact", r, "def bi():\n    return 2 ** 70", [{"call": "bi()", "expect": 2 ** 70}], "PASS")
probe("big int off by one", r, "def bi2():\n    return 2 ** 70", [{"call": "bi2()", "expect": 2 ** 70 + 1}], "FAIL")
probe("empty string vs None", r, "def es():\n    return ''", [{"call": "es()", "expect": None}], "FAIL")

print("--- raises forms")
r = fresh()
probe("builtin name", r, "def rv():\n    raise ValueError('x')", [{"call": "rv()", "raises": "ValueError"}], "PASS")
probe("base class name matches (mro)", r, "def rb():\n    raise ValueError('x')", [{"call": "rb()", "raises": "Exception"}], "PASS")
probe("sibling class does not", r, "def rs():\n    raise ValueError('x')", [{"call": "rs()", "raises": "KeyError"}], "FAIL")
probe("subclass does not match a narrower name", r, "def rn():\n    raise Exception('x')", [{"call": "rn()", "raises": "ValueError"}], "FAIL")
probe("module.Class from stdlib", r, "def rj():\n    import json\n    return json.loads('{')", [{"call": "rj()", "raises": "json.decoder.JSONDecodeError"}], "PASS")
probe("module.Class from the repo", r, "from app.errs import Boom\n\ndef rr():\n    raise Boom('x')", [{"call": "rr()", "raises": "app.errs.Boom"}], "PASS")
probe("repo class by its base", r, "from app.errs import Boom\n\ndef rr2():\n    raise Boom('x')", [{"call": "rr2()", "raises": "ValueError"}], "PASS")
probe("bare class name of a repo exception matches too", r, "from app.errs import Boom\n\ndef rr3():\n    raise Boom('x')", [{"call": "rr3()", "raises": "Boom"}], "PASS")
probe("bare name of a sibling repo exception does not", r, "from app.errs import Boom\n\ndef rr4():\n    raise Boom('x')", [{"call": "rr4()", "raises": "Bang"}], "FAIL")
probe("returns instead of raising", r, "def nr():\n    return 1", [{"call": "nr()", "raises": "ValueError"}], "FAIL")
probe("raises instead of returning", r, "def rx():\n    raise ValueError('x')", [{"call": "rx()", "expect": 1}], "FAIL")
probe("SystemExit is caught, not an escape", r, "def se():\n    raise SystemExit(0)", [{"call": "se()", "raises": "SystemExit"}], "PASS")
probe("KeyboardInterrupt likewise", r, "def ki():\n    raise KeyboardInterrupt()", [{"call": "ki()", "raises": "KeyboardInterrupt"}], "PASS")
probe("os._exit kills the runner: did not run", r, "def ox():\n    import os\n    os._exit(0)", [{"call": "ox()", "expect": 1}], "FAIL")
probe("mixed: one expect one raises", r, "def mx(n):\n    if n < 0:\n        raise ValueError('neg')\n    return n * 2",
      [{"call": "mx(2)", "expect": 4}, {"call": "mx(-1)", "raises": "ValueError"}], "PASS")
probe("mixed: second check wrong", r, "def mx2(n):\n    return n * 2", [{"call": "mx2(2)", "expect": 4}, {"call": "mx2(-1)", "raises": "ValueError"}], "FAIL")
probe("raises must be a string", r, "def rt():\n    raise ValueError()", [{"call": "rt()", "raises": ValueError}], "REFUSED")
probe("expect and raises together", r, "def rt2():\n    raise ValueError()", [{"call": "rt2()", "raises": "ValueError", "expect": 1}], "REFUSED")

print("--- async and generators")
r = fresh()
probe("async def is awaited", r, "async def ad(n):\n    return n + 1", [{"call": "ad(1)", "expect": 2}], "PASS")
probe("async def raising", r, "async def ar():\n    raise ValueError('x')", [{"call": "ar()", "raises": "ValueError"}], "PASS")
probe("async awaiting asyncio.sleep", r, "import asyncio\n\nasync def sl():\n    await asyncio.sleep(0)\n    return 'done'", [{"call": "sl()", "expect": "done"}], "PASS")
probe("async def counterfeit", r, "async def ac():\n    return 1", [{"call": "ac()", "expect": 2}], "FAIL")
probe("generator is not plain data", r, "def gen(n):\n    yield from range(n)", [{"call": "gen(3)", "expect": [0, 1, 2]}], "FAIL")
probe("list(gen()) in the call is refused", r, "def gen2(n):\n    yield from range(n)", [{"call": "list(gen2(3))", "expect": [0, 1, 2]}], "REFUSED")
probe("def returning list(generator) passes", r, "def gl(n):\n    return list(x * 2 for x in range(n))", [{"call": "gl(3)", "expect": [0, 2, 4]}], "PASS")
probe("async generator is not plain data", r, "async def ag():\n    yield 1", [{"call": "ag()", "expect": [1]}], "FAIL")
probe("lambda returned is not plain data", r, "def lm():\n    return lambda: 1", [{"call": "lm()", "expect": 1}], "FAIL")
probe("class returned is not plain data", r, "def cr():\n    return int", [{"call": "cr()", "expect": "int"}], "FAIL")
probe("module returned is not plain data", r, "def mr():\n    import json\n    return json", [{"call": "mr()", "expect": {}}], "FAIL")

print("--- cl_plan paths (asserted)")
def session(elicit, answers):
    r = fresh()
    p = subprocess.Popen([sys.executable, f"{CL}/closer_mcp.py", r], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=os.environ)
    seen = []
    def rpc(i, method, params):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n"); p.stdin.flush()
        while True:
            m = json.loads(p.stdout.readline())
            if m.get("method") == "elicitation/create":
                seen.append(m["params"]["message"]); a = answers.pop(0)
                p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], **a}) + "\n"); p.stdin.flush(); continue
            if m.get("id") == i: return m
    rpc(0, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {"elicitation": {}} if elicit else {}})
    return rpc, p, r, seen
def tool(rpc, i, name, args):
    m = rpc(i, "tools/call", {"name": name, "arguments": args})["result"]; return m["content"][0]["text"], m.get("isError")
def check(name, cond, got=""):
    global bad; bad += not cond; print(f"{'ok ' if cond else 'BAD'}  {name} {got[:90]}")
PLAN = {"intent": "totals line items", "expectation": "add() returns the sum"}
SUB = {"file": "app/m.py", "source": "def add(a, b):\n    return a + b", "checks": [{"call": "add(1, 2)", "expect": 3}], "stance": ST}
A, D, C = {"result": {"action": "accept", "content": {}}}, {"result": {"action": "decline"}}, {"result": {"action": "cancel"}}

rpc, p, r, seen = session(True, [D, C, {"error": {"code": -1, "message": "client broke"}}, A, A, A])
t, err = tool(rpc, 1, "cl_submit", SUB); check("submit before any plan refused", err and "plan" in t.lower(), t)
t, err = tool(rpc, 2, "cl_plan", {"intent": "", "expectation": "x"}); check("empty intent refused without asking", err and len(seen) == 0, t)
t, err = tool(rpc, 3, "cl_plan", {"intent": "x", "expectation": 5}); check("non-string expectation refused", err and len(seen) == 0, t)
t, err = tool(rpc, 4, "cl_plan", PLAN); check("declined -> NOT APPROVED", err and "NOT APPROVED" in t, t)
t, err = tool(rpc, 5, "cl_plan", PLAN); check("same plan again not re-asked", err and "already declined" in t and len(seen) == 1, t)
t, err = tool(rpc, 6, "cl_plan", {**PLAN, "intent": " totals line items "}); check("whitespace-only change is the same plan", err and "already declined" in t and len(seen) == 1, t)
t, err = tool(rpc, 7, "cl_submit", SUB); check("still locked after decline", err and "plan" in t.lower(), t)
t, err = tool(rpc, 8, "cl_plan", {**PLAN, "intent": "v2"}); check("cancel (Esc) -> not approved, not written", err and "NOT APPROVED" in t and "cancel" in t, t)
t, err = tool(rpc, 9, "cl_plan", {**PLAN, "intent": "v2"}); check("cancelled plan also not re-asked", err and "already declined" in t, t)
t, err = tool(rpc, 10, "cl_plan", {**PLAN, "intent": "v3"}); check("client error on elicitation -> error, nothing approved", err and "could not ask" in t, t)
t, err = tool(rpc, 11, "cl_plan", {**PLAN, "intent": "v3"}); check("plan after a client error can be asked again", not err and "APPROVED" in t, t)
sha = t.split("(")[1].split(")")[0]
t, err = tool(rpc, 12, "cl_plan", {**PLAN, "intent": "v3"}); check("same plan after approval: already approved, not asked", not err and "already approved" in t and sha in t and len(seen) == 4, t)
t, err = tool(rpc, 12, "cl_plan", {**PLAN, "intent": "v4"}); check("changed plan after approval: asked as a revision, approved", not err and "APPROVED" in t and "already" not in t and len(seen) == 5 and "REVISED" in seen[-1], t)
sha = t.split("(")[1].split(")")[0]
t, err = tool(rpc, 13, "cl_submit", SUB); check("submit now passes", not err and "PASS" in t, t)
stdir = judge.state_dir(judge.Path(r).resolve())
plans = [x for x in holes._lines(stdir / "plans.jsonl") if x.get("action") != "asked"]; agree = holes._lines(stdir / "agree.jsonl")
check("plans.jsonl has one record per answer, approved flag right", [x["approved"] for x in plans] == [False, False, True, True], str([x.get("action") for x in plans]))
check("every plan was recorded as asked before the answer", sum(x.get("action") == "asked" for x in holes._lines(stdir / "plans.jsonl")) == 5)
check("stance carries the approved plan hash", agree and agree[-1].get("plan", "").startswith(sha), json.dumps(agree[-1])[:90])
t, err = tool(rpc, 14, "cl_submit", {**SUB, "stance": None}); check("submit without stance refused", err and "PASS" not in t, t)
t, err = tool(rpc, 15, "cl_submit", {**SUB, "stance": {"purpose": "p", "intent": "i", "agrees": "yes"}}); check("stance agrees must be bool", err and "PASS" not in t, t)
t, err = tool(rpc, 16, "cl_submit", {**SUB, "stance": {"purpose": "p", "intent": "i", "agrees": False}}); check("agrees False still judged on code, noted first", "DISAGREES" in t.splitlines()[0].upper() or "disagree" in t.lower(), t)
p.kill()

rpc, p, r, seen = session(True, [A])
p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": "pg", "method": "ping"}) + "\n"); p.stdin.flush()
m = json.loads(p.stdout.readline()); check("ping answered outside elicitation", m.get("id") == "pg" and m.get("result") == {})
t, err = tool(rpc, 1, "cl_plan", PLAN); check("plan approved in a second process independently", not err and "APPROVED" in t, t)
t, err = tool(rpc, 2, "tools/list" if False else "cl_submit", {**SUB, "file": "app/other.py"}); check("new file under the approved plan", not err and "PASS" in t, t)
p.kill()

rpc, p, r, seen = session(False, [])
t, err = tool(rpc, 1, "cl_plan", PLAN); check("no elicitation: refused, nobody asked", err and len(seen) == 0 and "elicitation" in t, t)
t, err = tool(rpc, 2, "cl_submit", SUB); check("no elicitation: submit locked", err, t)
p.kill()
print("--- holes.jsonl readers and repair")
st = judge.Path(tempfile.mkdtemp())
L = lambda **r: json.dumps(r) + "\n"
(st / "holes.jsonl").write_text(L(location="a.py::f", kind="counterfeit") + L(location="b.py::g", kind="counterfeit")
                                + L(location="a.py::f", kind="repaired", by="coderadar") + L(location="b.py::g", kind="unchecked"))
got = holes.latest_holes(st); check("latest_holes drops the repaired location, keeps the latest of two", [(h["location"], h["kind"]) for h in got] == [("b.py::g", "unchecked")], str(got))
check("is_hole false after a repaired record, true on the open one", not holes.is_hole(st, "a.py::f") and holes.is_hole(st, "b.py::g"))
(st / "plans.jsonl").write_text(L(sha256="s1", approved=True, contracts=[{"file": "a.py", "name": "f", "params": [], "checks": [], "kind": "def"}])
                                + L(sha256="s2", approved=False, contracts=[]) + L(sha256="s3", action="asked"))
ap = holes.approved_plan(st); check("approved_plan picks the last approved record, contracts keyed by location", ap and ap["sha256"] == "s1" and list(ap["contracts"]) == ["a.py::f"] and ap["contracts"]["a.py::f"]["name"] == "f", json.dumps(ap)[:90])
check("approved_plan is None with no approved record", holes.approved_plan(judge.Path(tempfile.mkdtemp())) is None)
r = fresh()
probe("repair: first fail", r, "def rp():\n    return 1", [{"call": "rp()", "expect": 2}], "FAIL")
probe("repair: second fail makes the hole", r, "def rp():\n    return 1", [{"call": "rp()", "expect": 2}], "HOLE")
probe("repair: hole refuses a plain submit", r, "def rp():\n    return 2", [{"call": "rp()", "expect": 2}], "REFUSED")
sd = judge.state_dir(judge.Path(r).resolve())
v, msg = judge.submit(r, "app/m.py", "def rp():\n    return 1", [{"call": "rp()", "expect": 2}], ST, "probe-plan", repair=True)
check("repair FAIL stays FAIL, no second hole", v == "FAIL" and "CodeRadar may file again" in msg and len(holes.read_holes(sd)) == 1, msg.splitlines()[-1][:90])
v, msg = judge.submit(r, "app/m.py", "def rp():\n    return 2", [{"call": "rp()", "expect": 2}], ST, "probe-plan", repair=True)
check("repair PASS writes and appends the repaired record", v == "PASS" and holes.read_holes(sd)[-1]["kind"] == "repaired" and not holes.is_hole(sd, "app/m.py::rp"), msg.splitlines()[-1][:90])
probe("repaired location takes plain submits again", r, "def rp():\n    return 2", [{"call": "rp()", "expect": 2}], "PASS")
print(f"\n{bad} problem(s)"); sys.exit(bad != 0)
