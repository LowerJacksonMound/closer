#!/usr/bin/env python3
"""CLOSER MCP server (stdio, stdlib JSON-RPC). Two tools, in order:

  cl_plan    first, once per session: the agent's understanding of the app's intent and of the person's expectation,
             Closer shows it to the person through MCP elicitation, so the approval comes from them over
             this pipe and never passes through the agent. Until one is approved, cl_submit refuses.
  cl_submit  the agent's only way to write code into the repo. See judge.py.

The repo is fixed at launch (argv[1], else the directory the client starts this server in), so the agent cannot point
it elsewhere. The approved plan lives in this process only: a new session starts locked.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import holes  # noqa: E402
import judge  # noqa: E402

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else os.getcwd()).expanduser().resolve()
CLIENT = {"elicitation": False}
APPROVED: dict = {}  # this session's approved plan; empty = locked
TURNED_DOWN: set = set()  # hashes of plans not approved this session; the same plan is not put to the person twice
_next_id = [0]


def cartouche_plan() -> None:
    """Ian 2026-11-11: two ways to the intent. Cartouche's signed release writes its hashed intent into this repo's
    state as an approved plan (action "cartouche"); when one is there it is the plan and nothing is asked. No
    Cartouche: cl_plan asks the person. A plan approved through cl_plan stays in this process only."""
    if APPROVED:
        return
    rec = holes.approved_plan(judge.state_dir(REPO))
    if rec and rec.get("action") == "cartouche":
        APPROVED.update(rec)

TOOLS = [{
    "name": "cl_plan",
    "description": (
        "Call this FIRST: no code is written until the person approves a plan. intent: your understanding of what the "
        "person's app is for. expectation: what the person expects from this session. The person accepts it or "
        "declines; a decline means they have changes: ask them in chat, then send a revised plan. After approval cl_plan "
        "may be sent again only to tighten: add a location, or add checks to one (the rest stay locked as approved). "
        "Changing params, removing a check or dropping a location is refused; a wrong contract is a new run. contracts: one per "
        "function or class the spec names, each {file, name, kind: def|class (default def), params: [its parameter names], checks: [checks in "
        "cl_submit's form, drawn from the spec with literal inputs and outputs; a check may be {call, contains: [strings]} "
        "for a string result such as HTML]}. A contract with checks: [] says the spec gives nothing checkable: on "
        "approval that location becomes a hole (nothing can land there, it goes to CodeRadar). The person locks them with the plan: "
        "cl_submit refuses a locked name whose parameters differ and runs the locked checks with yours. A question "
        "whose answer would change a locked name, its parameters, its result or its errors is a plan change: send a "
        "revised plan, do not work around it."),
    "inputSchema": {
        "type": "object", "required": ["intent", "expectation"],
        "properties": {"intent": {"type": "string"}, "expectation": {"type": "string"},
                       "drop": {"type": "array", "items": {"type": "string"}},
                       "contracts": {"type": "array", "items": {"type": "object", "required": ["file", "name", "params", "checks"],
                           "properties": {"file": {"type": "string"}, "name": {"type": "string"}, "kind": {"type": "string", "enum": ["def", "class"]},
                                          "params": {"type": "array", "items": {"type": "string"}},
                                          "checks": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["call"]}}}}}}},
}, {
    "name": "cl_submit",
    "description": (
        f"Write ONE Python function or class into the repo at {REPO}. Direct edits to code are blocked; this is the only way in. "
        "Closer runs the function on your checks: if it does not run, or it runs but does not do what the checks say "
        "the user's intent is, it is rejected and nothing is written. Two tries per function: a pass is written to "
        "the file (replacing a def of the same name, else after the last def); a second fail is a HOLE, nothing is "
        "written, the spot is logged for cleanup, and that function takes no more submissions. "
        "source: import lines (optional; Closer adds any the file lacks to its imports), then exactly one top-level "
        "def or class. checks: what the intent "
        'expects, each {"call": "add(2, 3)", "expect": 5} or {"call": "add(\'x\', 1)", "raises": "TypeError"}. The '
        "call must be the function itself; its arguments may be literals, names from the target module, and the "
        "repo's own classes, by module path if the target module does not import them, e.g. "
        "area(pkg.shapes.Rect(2, 3)). A class is checked with call as a list: the constructor, then method steps on "
        'that instance, the last step\'s value compared: ["Cart()", ".add(Item(\'a\', 2.0))", ".total(0.1)"], or a '
        "class method directly: Receipt.from_cart(cart, 0.1). Every method must run in some check. To pass an "
        'object with state, build it under given, from the repo\'s own classes: "given": {"cart": '
        '["shop.cart.Cart()", ".add(shop.models.Item(\'a\', 2.0))"]}, then use cart in the call. '
        "The sandbox has no network: a function that talks to a server is checked against a stand-in. Give the check "
        '"serve": {"body": "1.5", "status": 200} (status optional) and call the function with the name url, e.g. '
        '{"call": "fetch_rate(url)", "serve": {"body": "1.5"}, "expect": 1.5}: every request to url gets that answer. Send two such checks with different bodies, so a constant cannot pass. '
        'A function that reads a file gets its fixture from "files": {"zones.json": "<the text>"} and is called with the path as files["zones.json"]; '
        'the files live in a scratch dir the function may also write to. '
        "An object comes back as plain data: Item('a', 2.0, 1) is "
        '{"__class__": "Item", "name": "a", "price": 2.0, "qty": 1}. Functions take no decorators; classes take '
        "@dataclass, methods @staticmethod/@classmethod/@property. Nothing may call code at import (defaults, "
        "annotations, class-level values). "
        "stance: in your own words, what this function does (purpose), the part of the app's intent it serves "
        "(intent), and whether they agree (agrees: true/false). It is shown to the person and logged; say false if "
        "they do not agree."),
    "inputSchema": {
        "type": "object", "required": ["file", "source", "checks", "stance"],
        "properties": {
            "file": {"type": "string", "description": "repo-relative .py path, e.g. pkg/math.py"},
            "source": {"type": "string", "description": "one complete def or class"},
            "checks": {"type": "array", "minItems": 1, "items": {
                "type": "object", "required": ["call"],
                "properties": {"call": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
                               "given": {"type": "object", "additionalProperties": {
                                   "anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]}},
                               "serve": {"type": "object", "properties": {"body": {"type": "string"}, "status": {"type": "integer"}}},
                               "files": {"type": "object", "additionalProperties": {"type": "string"}},
                               "expect": {}, "raises": {"type": "string"}}}},
            "stance": {"type": "object", "required": ["purpose", "intent", "agrees"], "properties": {
                "purpose": {"type": "string"}, "intent": {"type": "string"}, "agrees": {"type": "boolean"}}},
        }},
}]


def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def ask_person(message, schema):
    """Send elicitation/create and wait for the person's answer; anything else that arrives meanwhile is handled."""
    _next_id[0] += 1
    rid = f"closer-{_next_id[0]}"
    send({"jsonrpc": "2.0", "id": rid, "method": "elicitation/create",
          "params": {"message": message, "requestedSchema": schema}})
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("id") == rid and "method" not in msg:
            if "error" in msg:
                raise RuntimeError(f"the client could not ask the person: {msg['error']}")
            return msg.get("result") or {}
        if msg.get("method") == "ping" and msg.get("id") is not None:
            send({"jsonrpc": "2.0", "id": msg["id"], "result": {}})
    raise RuntimeError("the client closed the connection before the person answered")


def plan(args):
    intent, expect = args.get("intent"), args.get("expectation")
    if not all(isinstance(v, str) and v.strip() for v in (intent, expect)):
        return "REFUSED: intent and expectation must be non-empty text", True
    cartouche_plan()
    if not CLIENT["elicitation"] and not APPROVED:
        return ("REFUSED: this client cannot show a plan to the person (no MCP elicitation), and Closer writes nothing "
                "without an approved plan"), True
    try:
        locked = judge.check_contracts(args.get("contracts"))
    except judge.Refused as e:
        return f"REFUSED: {e}", True
    drop = args.get("drop") or []
    if not isinstance(drop, list) or not all(isinstance(x, str) for x in drop):
        return "REFUSED: drop must be a list of locations, file::name", True
    if APPROVED:  # Ian 2026-11-11: an approved plan only tightens. Add a location or a check; never change params,
        # remove a check, or drop a location. A wrong contract is a new run: the person deletes the state dir by hand.
        if drop:
            return ("REFUSED: approved contracts are not dropped mid-run. A contract that is wrong means a new run: the "
                    "person deletes this repo's CLOSER state dir outside Claude and the plan is asked again."), True
        loosened = [k for k, c in locked.items() if k in APPROVED["contracts"] and (
            c["params"] != APPROVED["contracts"][k]["params"]
            or any(ch not in c["checks"] for ch in APPROVED["contracts"][k]["checks"]))]
        if loosened:
            return ("REFUSED: approved contracts only tighten; these change params or lose a check: "
                    + ", ".join(loosened) + ". Send only additions, or the person starts a new run."), True
        locked = {**APPROVED["contracts"], **locked}
    rec = {"intent": intent.strip(), "expectation": expect.strip(), "contracts": list(locked.values())}
    rec["sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
    if APPROVED and rec["sha256"] == APPROVED["sha256"]:
        return f"this plan is already approved ({rec['sha256'][:12]}); go ahead with cl_submit", False
    if rec["sha256"] in TURNED_DOWN:
        return ("REFUSED: this exact plan was already declined. Ask the person in chat what to change, then send a "
                "revised plan"), True
    was = APPROVED.get("contracts", {})
    changed = {k for k in set(locked) | set(was) if locked.get(k) != was.get(k)} if APPROVED else set(locked)
    judge.record_plan(REPO, {**rec, "action": "asked", "revises": APPROVED.get("sha256"), "changed": sorted(changed)})
    head = f"REVISED PLAN (replaces {APPROVED['sha256'][:12]}; {len(changed)} contract(s) changed, marked *)\n" if APPROVED else ""
    shown = "".join(f"\n  {'*' if k in changed else ' '} {k}({', '.join(c['params'])}) [{len(c['checks']) or 'NO'} check(s)" + ("" if c["checks"] else ": HOLE") + "]" for k, c in locked.items())
    ans = ask_person(f"{head}Intent: {rec['intent']}\nYou expect: {rec['expectation']}\nLocked ({len(locked)}):{shown or ' none'}"
                     "\n\nAccept, or Decline to give changes.",
                     {"type": "object", "properties": {}})
    ok = ans.get("action") == "accept"
    judge.record_plan(REPO, {**rec, "approved": ok, "action": ans.get("action")})
    if not ok:  # Decline is "changes"; the client drops anything typed with it, so they come in chat
        TURNED_DOWN.add(rec["sha256"])
        return (f"NOT APPROVED (action: {ans.get('action')}): the person has changes. Do not resend it: ask them in "
                "chat what to change, then send a revised plan. Nothing can be written until they approve one."), True
    APPROVED.clear(); APPROVED.update(rec, contracts=locked)
    holed = judge.hole_unchecked(REPO, locked)
    tail = f" {len(holed)} unchecked location(s) are holes now: {', '.join(holed)}." if holed else ""
    return f"APPROVED ({rec['sha256'][:12]}). Write with cl_submit; each stance is logged against this plan.{tail}", False


def call(name, args):
    if name == "cl_plan":
        return plan(args)
    if name != "cl_submit":
        return f"no tool {name}", True
    cartouche_plan()
    verdict, text = judge.submit(REPO, args.get("file"), args.get("source"), args.get("checks"), args.get("stance"),
                                 APPROVED.get("sha256"), APPROVED.get("contracts"))
    return text, verdict != "PASS"


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        rid, method, params = req.get("id"), req.get("method"), req.get("params") or {}
        if method == "initialize":
            CLIENT["elicitation"] = "elicitation" in (params.get("capabilities") or {})
            res = {"protocolVersion": params.get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}},
                   "serverInfo": {"name": "closer", "version": "1"}}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            try:
                text, err = call(params.get("name"), params.get("arguments") or {})
            except Exception as e:  # the agent sees a refusal, never a dead server
                text, err = f"REFUSED (Closer error, no try used): {type(e).__name__}: {e}", True
            res = {"content": [{"type": "text", "text": text}], "isError": err}
        elif rid is None:  # notifications
            continue
        elif method == "ping":
            res = {}
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"no method {method}"}}) + "\n")
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": res}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
