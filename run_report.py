import json, collections, os, sys, glob, ast
name = sys.argv[1]
hits = sorted(glob.glob(os.path.expanduser(f"~/.closer/{name}-test-*")) or glob.glob(os.path.expanduser(f"~/.closer/{name}-*")), key=os.path.getmtime)
if not hits:
    sys.exit(f"no CLOSER state dir for {name}: no cl_plan has been made for that repo yet")
d = hits[-1]
print("state", d)
def rows(n):
    p = os.path.join(d, n); return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
pl = rows("plans.jsonl"); asked = [r for r in pl if r["action"] == "asked"]
print(len(pl), "plan events", [(r["action"], r.get("approved"), len(r.get("contracts", [])), (r.get("changed") or [])[:3] if r.get("revises") else "") for r in pl])
ag = rows("agree.jsonl"); print(len(ag), "submits", dict(collections.Counter(r["verdict"] for r in ag)))
for r in ag:
    if r["verdict"] != "PASS": print("  ", r["ts"][11:19], r["verdict"], r["location"])
st = [r for r in rows("strikes.jsonl") if r.get("event") != "clear"]; print(len(st), "strikes")
for r in st: print("  ", r["ts"][11:19], r["location"], (r.get("reason") or "")[:220])
ho = rows("holes.jsonl"); print(len(ho), "holes")
for r in ho: print("  ", r["location"], r.get("kind"), (r.get("reasons") or [""])[0][:160])
rf = rows("refused.jsonl"); print(len(rf), "refusals")
for r in rf: print("  ", r["ts"][11:19], (r.get("locked") or r.get("file") or ""), "|", (r.get("reason") or "")[:200])
approved = [r for r in pl if r.get("approved")]
locked = {c["file"] + "::" + c["name"]: c for c in approved[-1].get("contracts", [])} if approved else {}
passed = {r["location"] for r in ag if r["verdict"] == "PASS"}
print("locked", len(locked), "landed", len(set(locked) & passed), "missing:", sorted(set(locked) - passed))
print("landed unlocked:", sorted(passed - set(locked)))
print("empty contracts:", [k for k, c in locked.items() if not c["checks"]])
print("kinds:", dict(collections.Counter(c.get("kind") for c in locked.values())))
for k, c in locked.items():
    if c["name"] in ("serve", "manifest_csv", "BookingError"):
        print("--", k, [json.dumps(x)[:200] for x in c["checks"]])
gl = os.path.expanduser("~/.claude/hooks/closer_gate.log"); c = collections.Counter(); writes = []
for l in open(gl):
    try: r = json.loads(l)
    except: continue
    if f"{name}-test" in l:
        c[(r.get("decision"), r.get("tool"))] += 1
        if r.get("tool") not in ("Bash", "SessionStart") or r.get("decision") not in ("allow", "nudge"): writes.append((r.get("ts", "")[11:19], r.get("decision"), r.get("tool"), r.get("reason"), r.get("targets") or r.get("command", "")))
print("gate:", dict(c)); [print("  ", w) for w in writes[:10]]
repo = os.path.expanduser(f"~/Desktop/{name}-test")
for f in sorted(glob.glob(f"{repo}/{name}/*.py")):
    t = ast.parse(open(f).read()); print(os.path.relpath(f, repo), [n.name for n in t.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))])
tr = sorted(glob.glob(os.path.expanduser(f"~/.claude/projects/-Users-ian-Desktop-{name}-test/*.jsonl")), key=os.path.getmtime)
last = None
if tr:
    for l in open(tr[-1]):
        try: r = json.loads(l)
        except: continue
        if r.get("type") == "assistant":
            for x in r.get("message", {}).get("content", []):
                if isinstance(x, dict) and x.get("type") == "text" and len(x["text"]) > 300: last = x["text"]
print("=== opus final\n" + (last[:2800] if last else "none"))
