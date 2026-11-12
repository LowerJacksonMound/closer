#!/usr/bin/env python3
"""Live feed of CLOSER for one repo, one line per event. Run in a second terminal:  python3 closer_watch.py [REPO] [--no-selftest]
Runs selftest.sh first and stops on red.
Tails the repo's state dir (plans, verdicts, strikes, holes) and the gate log (denied or unenforced writes under the
repo). Refusals that never reach the judge (bad request, holed location) are not on disk, so they are not shown."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import judge

if "--no-selftest" not in sys.argv:  # the selftest runs before the watch unless told not to; red means fix CLOSER first
    import subprocess
    if subprocess.run(["sh", str(Path(__file__).resolve().parent / "selftest.sh")]).returncode: sys.exit("not watching: selftest failed")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
REPO = Path(args[0] if args else ".").resolve()
STATE = judge.state_dir(REPO)
GATE = Path.home() / ".claude" / "hooks" / "closer_gate.log"
FILES = {STATE / "plans.jsonl": "plan", STATE / "agree.jsonl": "verdict", STATE / "strikes.jsonl": "strike", STATE / "holes.jsonl": "hole", STATE / "refused.jsonl": "refused", GATE: "gate"}
seen = {f: (f.stat().st_size if f.exists() and f == GATE else 0) for f in FILES}  # the run's own files from the start; the gate log from now

LOCKED, LANDED = set(), set()


def page(r) -> Path:
    """The asked plan as one HTML page in the state dir, one row per contract, every check readable."""
    import html
    def chk(k):
        want = (f"= {html.escape(json.dumps(k['expect']))}" if "expect" in k else f"raises {html.escape(str(k['raises']))}" if "raises" in k
                else "contains " + ", ".join(f"<code>{html.escape(x)}</code>" for x in k["contains"]))
        extra = "".join(f"<br><small>{n}: {html.escape(json.dumps(k[n]))[:400]}</small>" for n in ("given", "serve", "files") if n in k)
        return f"<li><code>{html.escape(k['call'] if isinstance(k['call'], str) else ''.join(k['call']))}</code> &rarr; {want}{extra}</li>"
    rows = "".join(f"<tr{' class=hole' if not c['checks'] else ''}><td><b>{html.escape(c['file'])}</b><br>{html.escape(c['name'])}"
                   f"({html.escape(', '.join(c['params']))})<br><small>{c.get('kind', 'def')}</small></td>"
                   f"<td>{'<ul>' + ''.join(chk(k) for k in c['checks']) + '</ul>' if c['checks'] else '<b>NO CHECKS: HOLE</b>'}</td></tr>"
                   for c in r.get("contracts", []))
    doc = (f"<!doctype html><meta charset=utf-8><title>CLOSER plan</title><style>body{{font:15px/1.4 system-ui;margin:24px;max-width:1100px}}"
           f"table{{border-collapse:collapse;width:100%}}td{{border-top:1px solid #ccc;padding:8px;vertical-align:top}}td:first-child{{width:28%}}"
           f"code{{background:#f3f3f3;padding:1px 4px}}tr.hole{{background:#fff4e5}}ul{{margin:0;padding-left:18px}}</style>"
           f"<h2>{'Revised plan' if r.get('revises') else 'Plan'} {r.get('ts', '')[:19]}</h2><p><b>Intent:</b> {html.escape(r.get('intent', ''))}</p>"
           f"<p><b>Expect:</b> {html.escape(r.get('expectation', ''))}</p><p>{len(r.get('contracts', []))} locked contract(s)"
           + (f"; changed: {html.escape(', '.join(r['changed']))}" if r.get("changed") and r.get("revises") else "") + "</p><table>" + rows + "</table>")
    out = STATE / "plan.html"
    out.write_text(doc, encoding="utf-8")
    return out


def line(kind, r):
    t = r.get("ts", "")[11:19]
    if kind == "plan" and r.get("action") == "asked":
        where = page(r)
        locked = "".join(f"\n  LOCKED:  {c['file']}::{c['name']}({', '.join(c['params'])})  " + "; ".join(
            f"{k['call']} -> {k.get('expect', 'contains ' + str(k['contains']) if 'contains' in k else 'raises ' + str(k.get('raises')))}" for k in c["checks"]) or "NO CHECKS: HOLE" for c in r.get("contracts", []))
        return (f"{t} PLAN     put to you. Read it as a page:  open {where}\n  INTENT:  {r.get('intent', '')}\n  EXPECT:  {r.get('expectation', '')}{locked}\n")
    if kind == "plan":
        if r.get("approved"):
            LOCKED.clear(); LOCKED.update(f"{c['file']}::{c['name']}" for c in r.get("contracts", []))
        return f"{t} PLAN     {'approved' if r.get('approved') else r.get('action', 'declined')}: {r.get('intent', '')[:70]}"
    if kind == "verdict":
        if r["verdict"] == "PASS": LANDED.add(r["location"])
        tally = f"   [locked {len(LOCKED)}, landed {len(LOCKED & LANDED)}, missing {len(LOCKED - LANDED)}]" if LOCKED else ""
        return f"{t} {r['verdict']:<8} {r['location']}  agrees={r['agrees']}  {r.get('purpose', '')[:60]}{tally}"
    if kind == "strike" and r["event"] == "strike": return f"{t} strike   {r['location']}: {r.get('reason', '')[:90]}"
    if kind == "refused": return f"{t} refused  {r.get('file', '')}: {r.get('reason', '')[:90]}"
    if kind == "hole": return f"{t} HOLE     {r['location']} ({r.get('kind')}): nothing written, location closed"
    if kind == "gate" and r.get("decision") in ("deny", "allow-unenforced") and any(os.path.realpath(x).startswith(str(REPO)) for x in [r.get("cwd", "")] + r.get("targets", [])):
        return f"{t} GATE {r['decision']:<16} {r['tool']}: {r['reason'][:80]}"

print(f"watching {REPO}\n  state {STATE}\n  gate  {GATE}\n", flush=True)
while True:
    for f, kind in FILES.items():
        if not f.exists() or f.stat().st_size <= seen[f]: continue
        with open(f, "rb") as fh:
            fh.seek(seen[f]); chunk = fh.read(); seen[f] += len(chunk)
        for raw in chunk.decode("utf-8", "replace").splitlines():
            try: out = line(kind, json.loads(raw))
            except (ValueError, KeyError): continue
            if out: print(out, flush=True)
    time.sleep(0.5)
