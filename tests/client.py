"""Fake MCP client: drives closer_mcp.py over stdio. python3 client.py CLOSER_DIR REPO"""
import json, subprocess, sys
closer, repo = sys.argv[1], sys.argv[2]
def session(elicit, answers):
    p = subprocess.Popen([sys.executable, f"{closer}/closer_mcp.py", repo], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    def rpc(i, method, params):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n"); p.stdin.flush()
        while True:
            m = json.loads(p.stdout.readline())
            if m.get("method") == "elicitation/create":
                a = answers.pop(0)
                print("   [person sees]", m["params"]["message"].splitlines(), "-> answers", a)
                if a == "HANGUP":
                    p.stdin.close(); return {"result": {"content": [{"text": "(hung up)"}]}}
                p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": a}) + "\n"); p.stdin.flush()
                continue
            if m.get("id") == i:
                return m
    caps = {"elicitation": {}} if elicit else {}
    rpc(0, "initialize", {"protocolVersion": "2025-06-18", "capabilities": caps})
    return rpc, p
def tool(rpc, i, name, args):
    r = rpc(i, "tools/call", {"name": name, "arguments": args})
    t = r["result"]["content"][0]["text"]
    print(f" {name}: {t.splitlines()[0][:120]}" + (f" | {t.splitlines()[-1][:90]}" if t.count(chr(10)) else ""))
SUB = {"file": "m.py", "source": "def add(a, b):\n    return a + b", "checks": [{"call": "add(2, 3)", "expect": 5}, {"call": "add(0.5, 0.5)", "expect": 1}],
       "stance": {"purpose": "adds two numbers", "intent": "cart totals", "agrees": True}}
PLAN = {"intent": "a shop cart that totals item prices", "expectation": "add() returns the sum"}
print("session 1: elicitation supported")
rpc, p = session(True, [{"action": "decline"},
                        {"action": "accept", "content": {}}])
tool(rpc, 1, "cl_submit", SUB)
tool(rpc, 2, "cl_plan", PLAN)
tool(rpc, 3, "cl_plan", PLAN)
PLAN = {**PLAN, "expectation": "add() returns the sum, with tax"}
tool(rpc, 31, "cl_plan", PLAN)
tool(rpc, 4, "cl_submit", SUB)
tool(rpc, 5, "cl_plan", PLAN)
p.kill()
print("session 2: new session starts locked")
rpc, p = session(True, [])
tool(rpc, 1, "cl_submit", SUB)
p.kill()
print("session 3: no elicitation")
rpc, p = session(False, [])
tool(rpc, 1, "cl_plan", PLAN); p.kill()
print("session 4: Decline, then Esc on the Changes box; then a long plan accepted")
rpc, p = session(True, [{"action": "decline"}, {"action": "accept", "content": {}}])
tool(rpc, 1, "cl_plan", {**PLAN, "intent": "x"})
tool(rpc, 2, "cl_plan", {**PLAN, "intent": "a long intent " * 40})
p.kill()
print("session 5: contracts locked with the plan")
C = [{"file": "m.py", "name": "add", "params": ["a", "b"], "checks": [{"call": "add(2, 3)", "expect": 5}]}]
rpc, p = session(True, [{"action": "accept", "content": {}}])
tool(rpc, 1, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "add", "checks": []}]})  # REFUSED: no params
tool(rpc, 2, "cl_plan", {**PLAN, "contracts": C})
tool(rpc, 3, "cl_submit", {**SUB, "source": "def add(x, y):\n    return x + y"})  # REFUSED: params differ
tool(rpc, 4, "cl_submit", {**SUB, "source": "def add(a, b):\n    return a - b", "checks": [{"call": "add(5, 3)", "expect": 2}]})  # FAIL: locked check
tool(rpc, 5, "cl_submit", SUB)  # PASS, 3 checks held, 1 locked
tool(rpc, 6, "cl_submit", {**SUB, "file": "n.py", "source": "def helper(z):\n    return z", "checks": [{"call": "helper(1)", "expect": 1}, {"call": "helper(2)", "expect": 2}]})  # PASS: no contract, allowed
p.kill()
print("session 6: contains checks; an unchecked contract is a hole")
C6 = [{"file": "m.py", "name": "page", "params": ["n"], "checks": [{"call": "page(2)", "contains": ["2 pieces queued", "data-maker"]}]},
      {"file": "m.py", "name": "script", "params": [], "checks": []}]
rpc, p = session(True, [{"action": "accept", "content": {}}])
tool(rpc, 1, "cl_plan", {**PLAN, "contracts": C6})  # APPROVED, script is a hole
tool(rpc, 2, "cl_submit", {**SUB, "source": "def script():\n    return 'x'", "checks": [{"call": "script()", "expect": "x"}]})  # REFUSED: hole
tool(rpc, 3, "cl_submit", {**SUB, "source": "def page(n):\n    return f'<p>{n} pieces queued</p>'", "checks": [{"call": "page(1)", "contains": ["1 pieces"]}]})  # FAIL: missing data-maker
tool(rpc, 4, "cl_submit", {**SUB, "source": "def page(n):\n    return f'<tr data-maker=x></tr><p>{n} pieces queued</p>'", "checks": [{"call": "page(1)", "contains": ["1 pieces"]}]})  # PASS
tool(rpc, 5, "cl_submit", {**SUB, "source": "def page(n):\n    return n", "checks": [{"call": "page(1)", "contains": [""]}]})  # REFUSED: empty string
p.kill()
print("session 7: plan-time check rules, re-plan after approval, unlandable locked check")
rpc, p = session(True, [{"action": "accept", "content": {}}, {"action": "accept", "content": {}}, {"action": "accept", "content": {}}])
tool(rpc, 1, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "add", "params": ["a", "b"], "checks": [{"call": "add(open('x').read(), 1)", "expect": 1}]}]})  # REFUSED: open
tool(rpc, 2, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "add", "params": ["a", "b"], "checks": [{"call": ["add(1, 2)", ".real"], "expect": 3}]}]})  # REFUSED: list for a def
tool(rpc, 3, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "Box", "kind": "class", "params": ["v"], "checks": [{"call": ["Box(1)", ".get()"], "expect": 1}]}]})  # APPROVED (methods unknown at plan time)
tool(rpc, 4, "cl_submit", {**SUB, "source": "class Box:\n    def __init__(self, v):\n        self.v = v\n    def val(self):\n        return self.v", "checks": [{"call": ["Box(1)", ".val()"], "expect": 1}]})  # REFUSED: locked .get() not a method; re-plan advised
tool(rpc, 5, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "Box", "kind": "class", "params": ["v"], "checks": [{"call": ["Box(1)", ".val()"], "expect": 1}]}]})  # REVISED, asked again, APPROVED
tool(rpc, 6, "cl_submit", {**SUB, "source": "class Box:\n    def __init__(self, v):\n        self.v = v\n    def val(self):\n        return self.v", "checks": [{"call": ["Box(1)", ".val()"], "expect": 1}]})  # PASS
tool(rpc, 7, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "Box", "kind": "class", "params": ["v"], "checks": [{"call": ["Box(1)", ".nope()"], "expect": 1}]}, {"file": "m.py", "name": "add", "params": ["a", "b"], "checks": [{"call": "add(1, 2)", "expect": 3}]}]})  # REVISED again
tool(rpc, 8, "cl_submit", {**SUB, "source": "def add(a, b):\n    return a + b", "checks": [{"call": "add(1, 2)", "expect": 3}]})  # PASS (1 locked)
tool(rpc, 9, "cl_submit", {**SUB, "source": "class Box:\n    def __init__(self, v):\n        self.v = v\n    def val(self):\n        return self.v", "checks": [{"call": ["Box(1)", ".val()"], "expect": 1}]})  # REFUSED: re-plan advised
tool(rpc, 10, "cl_submit", {**SUB, "source": "class Box:\n    def __init__(self, v):\n        self.v = v\n    def val(self):\n        return self.v", "checks": [{"call": ["Box(1)", ".val()"], "expect": 1}]})  # REFUSED: hole now (unlandable)
p.kill()
print("session 8: a revision merges and only tightens; drop, a lost check and changed params are refused")
C8 = [{"file": "m.py", "name": "add", "params": ["a", "b"], "checks": [{"call": "add(2, 3)", "expect": 5}]},
      {"file": "m.py", "name": "sub", "params": ["a", "b"], "checks": [{"call": "sub(3, 2)", "expect": 1}]}]
rpc, p = session(True, [{"action": "accept", "content": {}}, {"action": "accept", "content": {}}])
tool(rpc, 1, "cl_plan", {**PLAN, "contracts": C8})  # APPROVED, 2 locked
tool(rpc, 2, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "add", "params": ["a", "b"], "checks": [{"call": "add(2, 3)", "expect": 5}, {"call": "add(0, 0)", "expect": 0}]}]})  # REVISED: add gains a check, sub kept -> Locked (2)
tool(rpc, 3, "cl_submit", {**SUB, "source": "def sub(a, b):\n    return a - b", "checks": [{"call": "sub(9, 9)", "expect": 0}]})  # PASS, 1 locked: sub is still locked
tool(rpc, 4, "cl_plan", {**PLAN, "drop": ["m.py::sub"]})  # REFUSED: not dropped mid-run
tool(rpc, 5, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "add", "params": ["a", "b"], "checks": [{"call": "add(0, 0)", "expect": 0}]}]})  # REFUSED: add lost a check
tool(rpc, 6, "cl_plan", {**PLAN, "contracts": [{"file": "m.py", "name": "sub", "params": ["x", "y"], "checks": [{"call": "sub(3, 2)", "expect": 1}]}]})  # REFUSED: sub changed params
tool(rpc, 7, "cl_submit", {**SUB, "source": "def sub(x, y):\n    return x - y", "checks": [{"call": "sub(9, 9)", "expect": 0}]})  # REFUSED: still locked with (a, b)
p.kill()
