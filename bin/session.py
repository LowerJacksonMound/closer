#!/usr/bin/env python3
"""Signer's live view of one writer session: one state dir, one page, plain labels. The renderer.

A thin wrapper over dash.py's readers. Given a single gate state dir (`~/.getting-close/<repo>-<hash>/`) it
renders the active ticket, and nothing else: no run folders, no history, no earlier tickets. The page is what
is happening to the current ticket now, readable without the glossary; the internal terms (check ids, rule
ids, hashes, raw lines) sit in one collapsed section under the land.

Served live by `ui/session_server.py` (localhost only; kept out of bin/ because K6's plant forbids network
modules in the gate). `python3 bin/session.py --state DIR --print` writes the page once to stdout, for tests.
"""
import argparse, datetime, fcntl, html, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dash    # readers: jload, c1_claims, c1_v27, u1_evidence, not_judged; and the CSS
import ledger  # kernel code, read only: the chain check

E = html.escape

# ---- plain words for the gate's names ---------------------------------------

CHECK_WORDS = {
    "W1": "World is frozen and append-only",
    "R6-1": "Gate reads the frozen World, not the live tree",
    "R6-2": "Reachability comes from World edges",
    "R6-4": "Every scanned file is accounted for",
    "G18": "No compiled or cache files smuggled in",
    "S1": "No fake-shaped code (stubs, constant returns, swallowed errors, theatre)",
    "E1": "The repo's own tests pass on the changed code",
    "C1": "The ticket's claims hold: each one ran and did what it says",
    "U1": "Changed pre-existing functions still behave the same (evidence only)",
}
RULE_WORDS = {
    "fake_effect": "effect missing: the claim's predicate is false after the call",
    "partial": "wrong result, wrong exception, or the function is not implemented",
    "answer_table": "same answer for different inputs",
    "fake_check": "the check is faked",
    "pass_through": "the function passes its input through",
    "cannot_judge": "could not be checked",
    "unreached": "a new or changed function that no claim reached",
    "stub_body": "stub body", "const_return": "constant return", "swallow": "error swallowed", "hollow_test": "hollow test",
    "theatre_return": "computes, then returns a literal", "factory_none": "a maker that makes nothing",
    "finally_return": "return inside finally hides a raise", "always_true": "a checker that always says yes",
    "identity_return": "a transformer that returns its input unchanged", "unparsed": "file could not be parsed",
    "judge_detection": "code that asks whether it is being tested or traced",
    "dynamic_code": "builds or runs code at runtime",
    "trace_replaced": "replaces the tracer the gate judges by",
    "probe_unfoldable": "reaches sys or threading through a name built at runtime",
}


def badge(text, kind):
    return f'<span class="b b-{kind}">{E(str(text))}</span>'


def plain_fail(check, line):
    """One failing check line in plain words. The raw line stays in the details section."""
    parts = line.split()
    if check == "C1":
        if line.startswith("C1 unjudged:"):
            return "Could not be checked: " + line[len("C1 unjudged:"):].strip()
        # "C1 fail: introduced FILE:LINE RULE QUALNAME" or "C1 fail: claim N RULE ..." shapes
        for rule, words in RULE_WORDS.items():
            if f" {rule} " in f" {line} ":
                name = parts[-1] if parts and "." in parts[-1] else ""
                return f"Claim failed: {words}" + (f" ({name.split('.')[-1]})" if name else "")
        return "Claim failed: " + line
    if check == "E1":
        return "Repo tests failed: " + line.split(":", 1)[-1].strip()
    if check == "S1":
        why = line.split(" -- ", 1)[1].strip() if " -- " in line else ""
        for rule, words in RULE_WORDS.items():
            if rule in line:
                return f"Fake-shaped code found: {words}" + (f" ({why})" if why else "")
        return "Fake-shaped code found: " + line
    return line


def expected_words(exp):
    """{result: X} / {true: pred} / {raises: Exc} in words."""
    if not isinstance(exp, dict) or not exp:
        return E(json.dumps(exp))
    k, v = next(iter(exp.items()))
    if k == "result":
        return f"returns <span class=mono>{E(json.dumps(v))}</span>"
    if k == "raises":
        return f"raises <span class=mono>{E(str(v))}</span>"
    if k == "true":
        return f"afterwards it is true that <span class=mono>{E(str(v))}</span>"
    return f"{E(k)} <span class=mono>{E(json.dumps(v))}</span>"


def claim_verdict(e):
    """What happened to one claim, as a badge and a short sentence."""
    if not e:
        return badge("not run yet", "grey"), ""
    o, rule = e.get("observed"), e.get("rule")
    if o == "held" and not rule:
        return badge("Held", "green"), "did what the claim says"
    if rule == "cannot_judge":
        return badge("Could not be checked", "grey"), json.dumps(o)[:200]
    words = RULE_WORDS.get(rule, rule or "mismatch")
    return badge(f"Failed: {words}", "red"), ("got " + json.dumps(o)[:200]) if o not in (None, "held") else ""


# ---- what is happening -------------------------------------------------------

def land_in_progress(st):
    """True while `gc land` holds the ledger lock (the checks are running)."""
    lock = st / "ledger.lock"
    if not lock.is_file():
        return False
    try:
        with open(lock, "r") as fh:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(fh, fcntl.LOCK_UN)
    except OSError:
        pass
    return False


def staged_files(st, tid):
    pay = st / "payload" / tid
    return sorted(str(p.relative_to(pay)) for p in pay.rglob("*") if p.is_file()) if pay.is_dir() else []


def ticket_card(st, t, rows, policy, landing):
    tid = str(t.get("ticket_id", ""))
    task = str(t.get("task", ""))
    write_set = t.get("write_set") or []
    staged = staged_files(st, tid)
    mine = [r for r in rows if str(r.get("ticket_id")) == tid]
    last = mine[-1] if mine else None
    strikes_task = sum(1 for r in rows if r.get("strike") and str(r.get("task")) == task)
    limit = policy.get("gets_through_anyway", 2)

    # the pipeline: minted -> staged -> checks running -> accepted / blocked
    if last and last.get("decision") == "proceed" and not last.get("strike"):
        stage, kind, verdict = "landed", "green", "Correct version accepted"
    elif last and last.get("strike"):
        stage, kind, verdict = "rejected", "red", "Rejected"
    elif last:
        stage, kind, verdict = str(last.get("decision")), "amber", str(last.get("decision"))
    elif landing and staged:
        stage, kind, verdict = "checks running", "amber", "Checks running"
    elif staged:
        stage, kind, verdict = "staged", "amber", f"Staged {len(staged)} of {len(write_set)} files"
    else:
        stage, kind, verdict = "minted", "grey", "Minted, nothing staged yet"
    steps = ["minted", "staged", "checks running", "landed" if stage != "rejected" else "rejected"]
    reached = {"minted": 0, "staged": 1, "checks running": 2, "landed": 3, "rejected": 3}.get(stage, 0)
    pipeline = " → ".join(badge(s, kind if i == reached else ("green" if i < reached else "grey")) for i, s in enumerate(steps))

    out = [f"<section class=task><h3>Ticket <span class=mono>{E(tid)}</span> · task {E(task)} · {badge(verdict, kind)}</h3>",
           f"<p>{pipeline}</p>",
           "<table><tr><th>files the writer may change</th><th>staged so far</th><th>claims minted</th><th>strikes on this task</th></tr>"
           f"<tr><td class=mono>{'<br>'.join(E(w) for w in write_set)}</td>"
           f"<td class=mono>{'<br>'.join(E(s) for s in staged) or '<span class=muted>none yet</span>'}</td>"
           f"<td>{len(dash.jload(st / 'claims' / f'{tid}.json', []) or [])} <span class=muted>(hash {E(str(t.get('claims_sha256') or '')[:12])})</span></td>"
           f"<td>{badge(f'{strikes_task} of {limit} allowed', 'red' if strikes_task >= limit else ('amber' if strikes_task else 'green'))}</td></tr></table>"]

    # the land, when there is one: ledger row in words, checks in words, claims in words
    for r in mine:
        evf = st / "evidence" / f"{tid}.{r.get('seq')}.json"
        ok = r.get("decision") == "proceed" and not r.get("strike")
        fails = [(c["name"], s) for c in r.get("checks", []) if c.get("exit") not in (0, 75) for s in c.get("said", []) if "fail" in s or "unjudged" in s]
        not_run = [c["name"] for c in r.get("checks", []) if c.get("exit") == 75]
        why = ("every check passed" if ok and not fails else
               "; ".join(plain_fail(n, s) for n, s in fails[:4]) or "; ".join(r.get("reasons") or []))
        out.append(f"<h4>{badge('Accepted' if ok else 'Rejected', 'green' if ok else 'red')} <b>{'Correct version accepted' if ok else 'Rejected'}</b> "
                   f"<span class=muted>land {r.get('seq')} at {E(str(r.get('ts')))} · {E(why)}</span></h4>")
        if not_run or r.get("unjudged"):
            nr = (", ".join(not_run) + " could not run (let through)") if not_run else ""
            un = "; ".join(("Could not be checked: " + s.split(":", 1)[-1].strip()) for s in r.get("unjudged") or [])
            out.append(f"<p>{badge('Not judged', 'amber')} {E('; '.join(x for x in (nr, un) if x))}</p>")
        # checks
        out.append("<table><tr><th>check</th><th>result</th><th>what it means</th></tr>")
        for c in r.get("checks", []):
            ex = c.get("exit")
            res = badge("passed", "green") if ex == 0 else (badge("could not run", "grey") if ex == 75 else badge("failed", "red"))
            said = c.get("said") or []
            meaning = str(CHECK_WORDS.get(c["name"], c["name"]))
            if ex not in (0, 75):
                meaning = "; ".join(plain_fail(c["name"], s) for s in said if "fail" in s or "unjudged" in s) or (said[-1] if said else meaning)
            elif ex == 0 and said:
                meaning += f" <span class=muted>({E(said[0].split(': ', 1)[-1])})</span>"
            out.append(f"<tr><td class=mono>{E(c['name'])}</td><td>{res}</td><td>{meaning}</td></tr>")
        out.append("</table>")
        # advisory notes (S1 `s1_advisory`, pack v35): said by the check, no strike; shown here by default, every land
        for c in r.get("checks", []):
            for s in c.get("said") or []:
                if s.startswith("S1 note: stood down "):
                    out.append(f"<p>{badge('Stood down', 'amber')} <span class=mono>{E(s[len('S1 note: stood down '):])}</span> "
                               f"<span class=muted>a probe finding the pack's s1_stand_down list allowed; not counted</span></p>")
                    continue
                if s.startswith("S1 note: introduced "):
                    body = s[len("S1 note: introduced "):]
                    where, _, reason = body.partition(" -- ")
                    rule = next((k for k in RULE_WORDS if f" {k} " in f" {where} "), "")
                    out.append(f"<p>{badge('Look here', 'amber')} <b>{E(RULE_WORDS.get(rule, rule or 'note'))}</b> in "
                               f"<span class=mono>{E(where.replace(' ' + rule + ' ', ' ') if rule else where)}</span>"
                               + (f" <span class=muted>{E(reason)}</span>" if reason else "") + "</p>")
        # claims
        cl, reach = dash.c1_claims(evf)
        cov, bef, bsum = dash.c1_v27(evf)
        if cl:
            held = sum(1 for e in cl.values() if e.get("observed") == "held" and not e.get("rule"))
            out.append(f"<p><b>Claims</b>: {held} of {len(cl)} held</p>"
                       "<table class=claims><tr><th>#</th><th>function</th><th>what was expected</th><th>what happened</th></tr>")
            for i, e in sorted(cl.items()):
                v, note = claim_verdict(e)
                b = bef.get(i) or {}
                before = {"absent": "new function", True: "also true before the change", False: "false before, true after"}.get(b.get("held_before"), "")
                out.append(f"<tr><td>{i}</td><td class=mono>{E(str(e.get('name', '')).split('.')[-1])}</td>"
                           f"<td>after <span class=mono>{E(str(e.get('call', ''))[:120])}</span>, {expected_words(e.get('expected'))}</td>"
                           f"<td>{v} <span class=muted>{E(note)}{(' · ' + before) if before else ''}</span></td></tr>")
            out.append("</table>")
            if reach and reach.get("unreached"):
                out.append("<p>" + badge("Unreached", "red") + " new or changed functions no claim ran: "
                           + ", ".join(f"<span class=mono>{E(q)}</span>" for _, q in reach["unreached"]) + "</p>")
        # internal terms, collapsed
        out.append("<details><summary>internal terms: ledger row, hashes, raw check lines, raw evidence</summary>"
                   + dash.checks_table(r) + dash.coverage_html(cov, bsum) + dash.u1_html(*dash.u1_evidence(evf)) + "</details>")

    if not mine:
        minted = dash.jload(st / "claims" / f"{tid}.json", []) or []
        if minted:
            out.append(f"<details open><summary>the {len(minted)} claims this ticket must satisfy (nothing has run yet)</summary>"
                       "<table class=claims><tr><th>#</th><th>function</th><th>what is expected</th></tr>"
                       + "".join(f"<tr><td>{i + 1}</td><td class=mono>{E(str(c.get('name', '')).split('.')[-1])}</td>"
                                 f"<td>after <span class=mono>{E(str(c.get('call', ''))[:120])}</span>, {expected_words(c.get('expect'))}</td></tr>"
                                 for i, c in enumerate(minted) if isinstance(c, dict)) + "</table></details>")
    out.append("</section>")
    return "\n".join(out)


def next_step(st, t, rows, landing, staged):
    """Console A (read-only): the one thing the signer does next, said on the page; the act itself stays in the shell."""
    sdir = st / "signer"
    contradictions = [l for l in (sdir / "contradictions.txt").read_text().splitlines() if l.strip()] if (sdir / "contradictions.txt").is_file() else []
    if t is None:
        if contradictions:
            return badge("next: fix TASK.md", "red") + " the task contradicts itself; the claims will strike an honest writer. Edit the task, then `closer go TASK.md`."
        if (sdir / "claims.json").is_file():
            return badge("next: read the claims, then mint", "amber") + " `closer go TASK.md` mints and launches after you say yes; edit `signer/claims.json` first if a claim is wrong."
        return badge("next: write the task", "grey") + " `closer task NAME` makes TASK.md; `closer claims TASK.md` drafts the claims."
    tid = str(t.get("ticket_id", ""))
    mine = [r for r in rows if str(r.get("ticket_id")) == tid]
    last = mine[-1] if mine else None
    if last is None:
        if landing and staged:
            return badge("next: wait", "amber") + " the checks are running; the verdict appears here."
        if staged:
            return badge("next: wait for the writer", "amber") + " staged, not landed; the writer lands when it is done."
        return badge("next: wait for the writer", "grey") + " minted; nothing staged yet."
    if last.get("decision") == "proceed" and not last.get("strike"):
        notes = [x for c in last.get("checks", []) for x in c.get("said", []) if x.startswith("S1 note")]
        if notes:
            return badge("next: read the Look here lines before you trust it", "amber") + " accepted with advisory notes; then the next task."
        return badge("next: the next task", "green") + " accepted; `closer task NAME` for the next one."
    if last.get("strike"):
        lets = [x for c in last.get("checks", []) for x in c.get("said", []) if "quoted in the task" in x or "environment" in x]
        return badge("next: read the reason, then run again", "red") + " `closer go TASK.md` relaunches on the same claims; if the strike names a test folder or interpreter, `closer amend` first; if it names an example the task quotes, fix TASK.md."
    return badge("next: read what was not run", "amber") + " let through on a check that could not run (75); `closer inspect` names it; `closer amend` if it is the interpreter or test folder."


def drafted_section(st):
    """Before any ticket: the drafted claims, the contradictions and the check lines, as `closer go` prints them."""
    sdir = st / "signer"
    cf = sdir / "claims.json"
    if not cf.is_file():
        return ""
    claims = dash.jload(cf, []) or []
    contradictions = [l for l in (sdir / "contradictions.txt").read_text().splitlines() if l.strip()] if (sdir / "contradictions.txt").is_file() else []
    check = (sdir / "claims_check.txt").read_text().strip() if (sdir / "claims_check.txt").is_file() else ""
    task = (sdir / "TASK.md").read_text().splitlines()[0].strip("# ").strip() if (sdir / "TASK.md").is_file() else ""
    out = [f"<section class=task><h3>Drafted, not minted · {E(task)} · {badge(f'{len(claims)} claims', 'grey')}</h3>"]
    if contradictions:
        out.append(f"<p>{badge('THE TASK CONTRADICTS ITSELF', 'red')} a writer who follows the rule is struck by the example:</p><ul>"
                   + "".join(f"<li>{E(c)}</li>" for c in contradictions) + "</ul>")
    out.append("<table class=claims><tr><th>#</th><th>function</th><th>what is expected</th></tr>"
               + "".join(f"<tr><td>{i + 1}</td><td class=mono>{E(str(c.get('name', '')).split('.')[-1])}</td>"
                         f"<td>after <span class=mono>{E(str(c.get('call', ''))[:120])}</span>, {expected_words(c.get('expect'))}</td></tr>"
                         for i, c in enumerate(claims) if isinstance(c, dict)) + "</table>")
    if check:
        out.append("<details><summary>the claim checker's lines</summary><pre>" + E(check) + "</pre></details>")
    out.append("</section>")
    return "".join(out)


def advisory_load(st):
    """How often the advisories appear on real lands here, and the watcher's changes: the numbers that decide whether
    the evidence is rare and seen, or noise (POST_MVP items 3 and 4, 2026-10-21)."""
    lpath = st / "ledger.jsonl"
    rows = ledger.read(lpath) if lpath.is_file() else []
    accepted = [r for r in rows if r.get("decision") == "proceed" and not r.get("strike")]
    by_rule = {}
    with_notes = 0
    for r in rows:
        said = [x for c in r.get("checks", []) for x in c.get("said", []) if x.startswith("S1 note")]
        if said:
            with_notes += 1
        for x in said:
            k = "stood down" if x.startswith("S1 note: stood down") else (x.split()[4] if len(x.split()) > 4 else "note")
            by_rule[k] = by_rule.get(k, 0) + 1
    wl = st / "signer" / "watch_log.jsonl"
    events = [json.loads(l) for l in wl.read_text().splitlines() if l.strip()] if wl.is_file() else []
    with_findings = sum(1 for e in events if e.get("new_findings"))
    return {"lands": len(rows), "accepted": len(accepted), "lands_with_notes": with_notes, "notes_by_rule": by_rule,
            "watcher_changes": len(events), "watcher_changes_with_findings": with_findings}


def advisory_load_words(st):
    a = advisory_load(st)
    rules = ", ".join(f"{k} {v}" for k, v in sorted(a["notes_by_rule"].items())) or "none"
    return (f"advisory load: {a['lands_with_notes']} of {a['lands']} land(s) carried a note ({rules}); "
            f"the watcher reported {a['watcher_changes']} change(s) outside the gate, {a['watcher_changes_with_findings']} with a new finding")


def watch_section(st):
    """What ui/watch.py saw: files changed outside the gate since the World was frozen, and what is new in them.
    Shown on every poll; red when a changed file carries a new finding, amber when a file changed, grey when quiet
    or the watcher is not running (its file older than a minute)."""
    wf = st / "signer" / "watch.json"
    if not wf.is_file():
        return ""
    try:
        w = json.loads(wf.read_text())
    except ValueError:
        return ""
    import time as _t
    stale = _t.time() - wf.stat().st_mtime > 60
    if stale:
        return f"<p>{badge('watcher stopped', 'grey')} <span class=muted>last looked {E(w.get('ts', ''))}; `closer watch` restarts it</span></p>"
    changed = w.get("changed_outside_gate") or []
    if not changed:
        return (f"<p>{badge('repo unchanged outside the gate', 'grey')} <span class=muted>{w.get('checked', 0)} python files "
                f"watched against World {E(str(w.get('world_id') or ''))}, last looked {E(w.get('ts', ''))}</span></p>")
    worst = "red" if any(c.get("new_findings") for c in changed) else "amber"
    out = [f"<p>{badge('CHANGED OUTSIDE THE GATE', worst)} <b>{len(changed)} file(s)</b> differ from the frozen World and were not "
           f"changed by a landed ticket. The gate has not judged them; the next ticket that touches one is charged with what is there.</p><ul>"]
    for c in changed:
        out.append(f"<li><span class=mono>{E(c['relpath'])}</span> <span class=muted>{E(c['since'])}</span>")
        for f in c.get("new_findings") or []:
            kind = "red" if f["rule"] == "judge_detection" else "amber"
            why = f.get("why") or ""
            out.append(f"<br>{badge('new: ' + RULE_WORDS.get(f['rule'], f['rule']), kind)} <span class=mono>{E(f['qualname'])}</span> "
                       f"line {f.get('line')}" + (f" <span class=muted>{E(why)}</span>" if why else ""))
        out.append("</li>")
    out.append("</ul>")
    return "".join(out)


def fragment(st):
    """The live part of the page: the header line and the active ticket only (the newest ticket file)."""
    policy = dash.jload(st / "policy.json", {}) or {}
    lpath = st / "ledger.jsonl"
    rows = ledger.read(lpath) if lpath.is_file() else []
    problems = ledger.check(lpath) if lpath.is_file() else []
    chain = (badge("ledger intact", "green") if lpath.is_file() and not problems else
             badge("no land yet", "grey") if not lpath.is_file() else badge("LEDGER TAMPERED", "red"))
    landing = land_in_progress(st)
    tickets = sorted(((st / "tickets").glob("*.json")) if (st / "tickets").is_dir() else [], key=lambda p: p.stat().st_mtime, reverse=True)
    latest = (st / "LATEST").read_text().strip() if (st / "LATEST").is_file() else "none"
    parts = [f"<p>{chain} · {len(rows)} land(s) on record · strikes allowed per task: {E(str(policy.get('gets_through_anyway', 2)))} · "
             f"frozen World <span class=mono>{E(latest)}</span>"
             + (" · " + badge("checks running now", "amber") if landing else "") + "</p>"]
    if problems:
        parts.append("<pre>" + "\n".join(E(p) for p in problems) + "</pre>")
    parts.append(watch_section(st))
    t = (dash.jload(tickets[0], {}) or {}) if tickets else None
    staged = staged_files(st, str(t.get("ticket_id", ""))) if t else []
    parts.append(f"<p>{next_step(st, t, rows, landing, staged)}</p>")
    if not tickets:
        parts.append(drafted_section(st) or "<p class=muted>no ticket minted yet</p>")
    else:
        parts.append(ticket_card(st, t, rows, policy, landing))
    parts.append(f"<p class=muted>{E(advisory_load_words(st))}</p>")
    return "".join(parts)


def page(st, every):
    """The HTML shell: fetches /fragment every `every` seconds and swaps it in; says live or stale."""
    now = datetime.datetime.now()
    head = (f"<h1>getting-close · live session</h1>"
            f"<p class=muted><span id=live class='b b-green'>live</span> · last update <span id=stamp>{E(now.isoformat(timespec='seconds'))}</span> · "
            f"polls every {every}s · read-only, built from the gate's own files · state <span class=mono>{E(str(st))}</span></p>"
            f"<p id=stale class=b-red style='display:none;padding:8px 12px;border-radius:8px'>server not reachable: this page is stale</p>")
    js = f"""
(function(){{var every={every}*1000;var last=Date.now();
function stale(on){{document.getElementById('stale').style.display=on?'block':'none';var l=document.getElementById('live');l.textContent=on?'stale':'live';l.className=on?'b b-red':'b b-green';}}
function poll(){{fetch('/fragment',{{cache:'no-store'}}).then(function(r){{if(!r.ok)throw 0;return r.text();}}).then(function(h){{
  var open={{}};document.querySelectorAll('#body details').forEach(function(d,i){{open[i]=d.open;}});
  document.getElementById('body').innerHTML=h;document.querySelectorAll('#body details').forEach(function(d,i){{if(i in open)d.open=open[i];}});
  document.getElementById('stamp').textContent=new Date().toLocaleTimeString();last=Date.now();stale(false);}}).catch(function(){{stale(true);}});}}
setInterval(poll,every);setInterval(function(){{if(Date.now()-last>every*4)stale(true);}},1000);}})();
"""
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>getting-close live session</title><style>{dash.CSS}</style></head>"
            f"<body>{head}<div id=body>{fragment(st)}</div><script>{js}</script></body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, help="the one gate state dir to render")
    ap.add_argument("--print", action="store_true", help="write the page once to stdout (tests); the live page is ui/session_server.py")
    a = ap.parse_args()
    st = Path(a.state).expanduser().resolve()
    sys.stdout.write(page(st, 2))


if __name__ == "__main__":
    main()
