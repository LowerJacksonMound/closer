#!/usr/bin/env python3
"""Signer's dashboard: one self-contained HTML page, generated from what the gate wrote, read-only.

Sources: a proving run folder (`CLOSER_PROVING/runs/<stamp>`: results.json, and per ticket row.json, land.log,
evidence/) and any number of state dirs (`~/.getting-close/<repo>/`: tickets, ledger.jsonl, policy.json,
evidence/). It writes one file and nothing else. No server, no network module (K6): open the file in a browser.

    python3 bin/dash.py --run ~/Desktop/CLOSER_PROVING/runs/<stamp> [--state DIR ...] [--out FILE]
"""
import argparse, datetime, html, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # kernel code, read only: the chain check

E = html.escape


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def badge(text, kind):
    return f'<span class="b b-{kind}">{E(str(text))}</span>'


def not_judged(row):
    """T16 (pack v32): what a land let through unjudged, from the row: checks that exited 75 (`not_run`) and the
    `<check> unjudged:` lines (`unjudged`). "" when everything was judged (or the row predates v32)."""
    if not row:
        return ""
    parts = []
    if row.get("not_run"):
        parts.append(", ".join(str(n) for n in row["not_run"]) + " not run")
    if row.get("unjudged"):
        parts.append(f"{len(row['unjudged'])} unjudged claim(s)")
    return "; ".join(parts)


def outcome(t):
    if not t:
        return badge("not run", "grey")
    if "error" in t:
        return badge(f"error: {t['error']}", "red")
    if t.get("strike"):
        return badge("struck", "red")
    if t.get("decision") == "proceed":
        nj = not_judged(t)
        return badge(f"landed, not judged: {nj}", "amber") if nj else badge("landed clean", "green")
    return badge(t.get("decision", "?"), "amber")


def lines_block(title, lines):
    if not lines:
        return ""
    body = "\n".join(E(s) for s in lines)
    return f"<details><summary>{E(title)} ({len(lines)})</summary><pre>{body}</pre></details>"


def checks_table(row):
    if not row:
        return "<p class=muted>no ledger row</p>"
    out = ["<table class=checks><tr><th>check</th><th>exit</th><th>said</th></tr>"]
    for c in row.get("checks", []):
        ex = c.get("exit")
        k = "green" if ex == 0 else ("grey" if ex == 75 else "red")
        said = "<br>".join(E(s) for s in c.get("said", []))
        out.append(f"<tr><td>{E(c['name'])}</td><td>{badge('75 not run' if ex == 75 else ex, k)}</td><td class=mono>{said}</td></tr>")
    out.append("</table>")
    nj = not_judged(row)
    meta = (f"seq {row.get('seq')} · decision <b>{E(str(row.get('decision')))}</b> · pack v{row.get('pack_version')} · "
            f"kernel {E(str(row.get('kernel_sha256'))[:12])} · pack {E(str(row.get('pack_sha256'))[:12])} · "
            f"claims {E(str(row.get('claims_sha256'))[:12])} · {E('; '.join(row.get('reasons') or []))}"
            + (f" · not judged (T16, let through): {E(nj)}" if nj else ""))
    unj = "".join(f"<br>{E(s)}" for s in row.get("unjudged") or [])
    return f"<p class=muted>{meta}</p>" + "".join(out) + (f"<p class=mono>{unj[4:]}</p>" if unj else "")


def c1_claims(evfile):
    """claim index -> evidence entry, plus the reach entry."""
    ev = jload(evfile, {}) or {}
    claims, reach = {}, None
    for e in (ev.get("checks") or {}).get("C1", []):
        if "reach" in e:
            reach = e["reach"]
        elif "claim" in e:
            claims[e["claim"]] = e
    return claims, reach


def c1_v27(evfile):
    """Pack v27 C1 evidence, if the land has it: coverage entries, claim index -> before entry, the summary.
    Older evidence has none of these and the views render as before."""
    ev = jload(evfile, {}) or {}
    cov, before, summary = [], {}, None
    for e in (ev.get("checks") or {}).get("C1", []):
        if "coverage" in e:
            cov.append(e["coverage"])
        elif "before" in e:
            before[e["before"].get("claim")] = e["before"]
        elif "before_summary" in e:
            summary = e["before_summary"]
    return cov, before, summary


def before_badge(b):
    """One claim on the before-tree: holds before and after, discriminating, absent (new), or not rerun."""
    if not b:
        return ""
    hb = b.get("held_before")
    if hb == "absent":
        return badge("absent before (new)", "grey")
    if hb is True:
        return badge("holds before and after", "amber")
    if hb is False:
        return badge("discriminating", "green")
    return badge("not rerun", "grey")


def coverage_html(cov, summary, label=""):
    """Per changed function: claims, distinct inputs, negative, effect, thin. Then the before-tree counts."""
    out = []
    if cov:
        yn = lambda v: "yes" if v else "no"
        out.append(f"<p class=muted>{E(label)}claim coverage per changed function (evidence, no strike)</p>"
                   "<table class=claims><tr><th>function</th><th>claims</th><th>inputs</th><th>negative</th>"
                   "<th>effect</th><th></th></tr>")
        for c in cov:
            out.append(f"<tr><td class=mono>{E(str(c.get('file')))}:{E(str(c.get('line')))} {E(str(c.get('qualname')))}</td>"
                       f"<td>{E(str(c.get('claims')))}</td><td>{E(str(c.get('inputs')))}</td>"
                       f"<td>{yn(c.get('negative'))}</td><td>{yn(c.get('effect'))}</td>"
                       f"<td>{badge('thin', 'amber') if c.get('thin') else ''}</td></tr>")
        out.append("</table>")
    if summary:
        txt = (f"{label}before-tree: {summary.get('discriminating', 0)} discriminating, "
               f"{summary.get('holds_before', 0)} hold before and after, {summary.get('absent', 0)} absent (new), "
               f"{summary.get('not_run', 0)} not rerun" + (f" · {summary['error']}" if summary.get("error") else ""))
        out.append(f"<p class=muted>{E(txt)}</p>")
    return "".join(out)


def u1_evidence(evfile):
    """Pack v28 U1 evidence, if the land has it: the differences and the summary. Older evidence has neither."""
    ev = jload(evfile, {}) or {}
    diffs, summary = [], None
    for e in (ev.get("checks") or {}).get("U1", []):
        if "difference" in e:
            diffs.append(e["difference"])
        elif "summary" in e:
            summary = e["summary"]
    return diffs, summary


def u1_html(diffs, summary, label=""):
    """Behaviour changes in pre-existing functions: a differences table, then the summary line."""
    if summary is None and not diffs:
        return ""
    out = []
    if diffs:
        out.append(f"<p class=muted>{E(label)}behaviour changes in pre-existing functions (U1 evidence, no strike)</p>"
                   "<table class=claims><tr><th>function</th><th>declared</th><th>input</th><th>before</th>"
                   "<th>after</th><th>driver</th></tr>")
        for d in diffs:
            dec = badge("declared", "grey") if d.get("declared") else badge("undeclared_change", "amber")
            inp = ", ".join(f"{k}={json.dumps(v)}" for k, v in (d.get("input") or {}).items())
            out.append(f"<tr><td class=mono>{E(str(d.get('file')))}:{E(str(d.get('line')))} {E(str(d.get('qualname')))}</td>"
                       f"<td>{dec}</td><td class=mono>{E(inp[:300])}</td>"
                       f"<td class=mono>{E(json.dumps(d.get('before'))[:160])}</td>"
                       f"<td class=mono>{E(json.dumps(d.get('after'))[:160])}</td>"
                       f"<td class=mono>{E(str(d.get('driver')))}</td></tr>")
        out.append("</table>")
    if summary:
        txt = (f"{label}U1: {len(summary.get('changed') or [])} changed pre-existing function(s), "
               f"{summary.get('inputs', 0)} input(s) recorded, {summary.get('compared', 0)} compared, "
               f"{summary.get('differences', 0)} difference(s), {summary.get('undeclared', 0)} undeclared"
               + (f", {summary['unmatched']} unmatched" if summary.get("unmatched") else "")
               + (f", {summary['unstable']} unstable" if summary.get("unstable") else "")
               + (" · partial (out of time)" if summary.get("partial") else "")
               + (f" · {summary['seconds']}s" if summary.get("seconds") is not None else ""))
        out.append(f"<p class=muted>{E(txt)}</p>")
    return "".join(out)


def observed(e):
    if not e:
        return badge("not run", "grey")
    o = e.get("observed")
    r = e.get("rule")
    if o == "held" and not r:
        return badge("held", "green")
    txt = f"{r}: {json.dumps(o)[:160]}" if r else json.dumps(o)[:160]
    return badge(txt, "red")


def claims_table(h_ev, c_ev):
    hc, hr = c1_claims(h_ev)
    cc, cr = c1_claims(c_ev)
    hcov, hb, hs = c1_v27(h_ev)
    ccov, cb, cs = c1_v27(c_ev)
    idx = sorted(set(hc) | set(cc))
    if not idx:
        return "<p class=muted>no claim evidence (C1 did not run)</p>"
    out = ["<table class=claims><tr><th>#</th><th>function</th><th>setup / call</th><th>expected</th>"
           "<th>honest</th><th>counterfeit</th></tr>"]
    for i in idx:
        e = hc.get(i) or cc.get(i)
        setup = "<br>".join(E(s) for s in e.get("setup", []))
        call = E(e.get("call", ""))
        out.append(f"<tr><td>{i}</td><td class=mono>{E(e.get('name',''))}</td>"
                   f"<td class=mono>{setup}{'<br>' if setup else ''}<b>{call}</b></td>"
                   f"<td class=mono>{E(json.dumps(e.get('expected')))}</td>"
                   f"<td>{observed(hc.get(i))} {before_badge(hb.get(i))}</td>"
                   f"<td>{observed(cc.get(i))} {before_badge(cb.get(i))}</td></tr>")
    out.append("</table>")
    reach = []
    for label, r in (("honest", hr), ("counterfeit", cr)):
        if r:
            un = r.get("unreached") or []
            intro = r.get("introduced") or []
            reach.append(f"{label}: {len(intro)} introduced, {len(un)} unreached"
                         + (": " + ", ".join(q for _, q in un) if un else ""))
    return "".join(out) + (f"<p class=muted>reach · {' · '.join(E(x) for x in reach)}</p>" if reach else "") + \
        coverage_html(hcov, hs, "honest: ") + coverage_html(ccov, cs, "counterfeit: ") + \
        u1_html(*u1_evidence(h_ev), "honest: ") + u1_html(*u1_evidence(c_ev), "counterfeit: ")


def demos_html(h):
    """The honest ticket's demos (prove.py --demos): one badge per demo, exit 0 is ok."""
    demos = (h or {}).get("demos")
    if not demos:
        return ""
    parts = [f"{E(n)} {badge('ok' if v.get('ok') else 'exit ' + str(v.get('exit')), 'green' if v.get('ok') else 'red')}" for n, v in sorted(demos.items())]
    return "<div><b>demos</b> " + " ".join(parts) + "</div>"


def run_section(run):
    results = jload(run / "results.json", [])
    ran = [r for r in results if "skip" not in r]
    items = [i for r in ran for i in r["items"]]
    caught = sum(1 for i in items if i.get("caught"))
    unreached = sum(1 for i in items if i.get("unreached_only"))
    struck_unnamed = sum(1 for i in items if not i.get("caught") and not i.get("unreached_only") and i.get("ticket_struck"))
    not_minted = sum(1 for i in items if i.get("error"))
    not_closers = sum(1 for i in items if i.get("not_closers"))  # T6/T8: a species Closer does not hunt (T11) that landed
    co_file = next((a / "set" / "CRITERIA_OPEN.txt" for a in run.resolve().parents if (a / "set" / "CRITERIA_OPEN.txt").is_file()), Path("/nonexistent"))  # KERNEL T18, beside the set
    co_ids = {l.split("|")[0].strip() for l in co_file.read_text().splitlines() if l.strip() and not l.startswith("#")} if co_file.is_file() else set()
    for i in items:
        i["criteria_open"] = i.get("criteria_open") or ((i.get("id") in co_ids) and not i.get("ticket_struck") and not i.get("error"))
    criteria_open = sum(1 for i in items if i.get("criteria_open"))
    landed = sum(1 for i in items if not i.get("ticket_struck") and not i.get("error") and not i.get("not_closers") and not i.get("criteria_open"))
    h_clean = sum(1 for r in ran if r.get("honest", {}).get("decision") == "proceed" and not r["honest"].get("strike"))
    h_struck = sum(1 for r in ran if r.get("honest", {}).get("strike"))
    # T16 (pack v32): honest lands that proceeded with something not judged, read from each honest row.json
    h_unjudged = sum(1 for r in ran if not_judged(jload(run / r["app"] / r["task"] / "honest" / "row.json")))
    pack = next((r["honest"].get("pack_version") for r in ran if "honest" in r), "?")
    per_item = any(r.get("per_item") for r in ran)
    struck = sum(1 for i in items if i.get("ticket_struck"))  # the bar's count (KERNEL T8): struck at land
    tiles = [("tasks run", f"{len(ran)} / {len(results)}", "grey"),
             ("counterfeits struck at land (the bar)", f"{struck} / {len(items)}", "green" if items and struck == len(items) else ("red" if landed else "amber")),
             ("of which named by a failing check", f"{caught} / {len(items)}", "grey"),
             ("unreached (claims fall short)", unreached, "amber" if unreached else "grey"),
             ("struck, function not named", struck_unnamed, "amber" if struck_unnamed else "grey"),
             ("landed (got through)", landed, "red" if landed else "green"),
             ("not Closer's (T11, CR's to catch)", not_closers, "grey"),
             ("criteria open (T18, the text's gap)", criteria_open, "grey"),
             ("not minted (claims error)", not_minted, "amber" if not_minted else "grey"),
             ("honest clean", f"{h_clean} / {len(ran)}", "green" if ran and h_clean == len(ran) else "amber"),
             ("honest struck", h_struck, "red" if h_struck else "green"),
             ("honest landed, not judged (T16)", h_unjudged, "amber" if h_unjudged else "grey")]
    with_demos = [r for r in ran if "demos" in r.get("honest", {})]
    if with_demos:
        d_ok = sum(1 for r in with_demos if r["honest"].get("demos_ok"))
        tiles.append(("honest demos ok", f"{d_ok} / {len(with_demos)}", "green" if d_ok == len(with_demos) else "amber"))
    out = [f"<h2>Proving run <span class=mono>{E(run.name)}</span> · pack v{E(str(pack))}{' · one counterfeit ticket per item' if per_item else ' · one counterfeit ticket per task'}</h2>",
           "<div class=tiles>" + "".join(f"<div class='tile t-{k}'><div class=n>{E(str(v))}</div><div class=l>{E(t)}</div></div>"
                                        for t, v, k in tiles) + "</div>",
           "<p class=muted>The bar (KERNEL T8) counts a counterfeit <b>struck at land</b>: its ticket rejected, whatever line did it. A counterfeit is <b>named</b> when a failing check names its function with a rule other than "
           "<i>unreached</i>. <i>Unreached</i> means no claim reached that function: the claims fall short, not the gate. "
           "<i>Struck, not named</i>: its ticket was rejected on another function's line. "
           "A struck honest ticket is a false positive or, with unreached, claims that fall short.</p>"]
    for r in results:
        app, task = r["app"], r["task"]
        if "skip" in r:
            out.append(f"<section class=task><h3>{E(app)} · {E(task)} {badge('skipped', 'grey')}</h3><p class=muted>{E(r['skip'])}</p></section>")
            continue
        h = r.get("honest", {})
        cfs = r.get("counterfeits") or ([r["counterfeit"]] if r.get("counterfeit") else [])
        d = run / app / task
        bylabel = {c.get("label", "counterfeit"): c for c in cfs}
        rows = ["<table class=items><tr><th>item</th><th>species</th><th>function</th><th>its ticket</th><th>result</th><th>what named it</th></tr>"]
        for it in r["items"]:
            if it.get("caught"):
                res, k = "caught", "green"
            elif it.get("unreached_only"):
                res, k = "unreached", "amber"
            elif it.get("ticket_struck"):
                res, k = "struck, not named", "amber"
            elif it.get("error"):
                res, k = "not minted", "grey"
            else:
                res, k = "LANDED", "red"
            lab = it.get("ticket", "counterfeit")
            c = bylabel.get(lab, {})
            named = it.get("named") or [s for s in c.get("fail_lines", []) if it["qualname"] in s or it["qualname"].split(".")[-1] in s.split("::")[-1]]
            rows.append(f"<tr><td>{E(it['id'])}</td><td>{E(it['type'])}</td><td class=mono>{E(it['qualname'])}</td>"
                        f"<td>{outcome(c)}</td><td>{badge(res, k)}</td><td class=mono>{'<br>'.join(E(s) for s in named)}</td></tr>")
        rows.append("</table>")
        hev = d / "honest" / "evidence" / f"{h.get('ticket', 'x')}.1.json"
        det = []
        for c in cfs:
            lab = c.get("label", "counterfeit")
            cev = d / lab / "evidence" / f"{c.get('ticket', 'x')}.1.json"
            det.append(f"<details><summary>{E(lab)} ({E(', '.join(c.get('cf_files', [])))}): claims, expected vs observed, honest beside it</summary>{claims_table(hev, cev)}</details>"
                       f"<details><summary>{E(lab)}: every check's lines</summary>{checks_table(jload(d / lab / 'row.json'))}</details>")
        labs = ["honest"] + [c.get("label", "counterfeit") for c in cfs]
        logs = "".join(f"<p class=muted>{E(lab)}</p><pre>{E((d / lab / 'land.log').read_text())}</pre>" for lab in labs if (d / lab / "land.log").is_file())
        out.append(f"""<section class=task><h3>{E(app)} · {E(task)}</h3>
<div class=pair><div><b>honest ticket</b> {outcome(h)}</div><div><b>counterfeit tickets</b> {len(cfs)}</div>{demos_html(h)}</div>
{''.join(rows)}
{''.join(det)}
<details><summary>honest ticket: every check's lines</summary>{checks_table(jload(d / 'honest' / 'row.json'))}</details>
<details><summary>land logs</summary>{logs}</details>
</section>""")
    return "\n".join(out)


def state_section(st):
    out = [f"<h2>State <span class=mono>{E(str(st))}</span></h2>"]
    policy = jload(st / "policy.json", {}) or {}
    latest = (st / "LATEST").read_text().strip() if (st / "LATEST").is_file() else "none"
    lpath = st / "ledger.jsonl"
    rows = ledger.read(lpath) if lpath.is_file() else []
    problems = ledger.check(lpath) if lpath.is_file() else []
    chain = badge("chain ok", "green") if lpath.is_file() and not problems else (badge("no ledger", "grey") if not lpath.is_file() else badge("chain broken", "red"))
    out.append(f"<p>latest World <span class=mono>{E(latest)}</span> · gets_through_anyway {E(str(policy.get('gets_through_anyway', 'default')))} · "
               f"ledger {len(rows)} row(s) {chain}</p>")
    if problems:
        out.append("<pre>" + "\n".join(E(p) for p in problems) + "</pre>")
    struck = {str(r.get("ticket_id")): r.get("seq") for r in rows if r.get("strike")}
    landed = {str(r.get("ticket_id")) for r in rows if r.get("decision") == "proceed"}
    tickets = sorted((st / "tickets").glob("*.json")) if (st / "tickets").is_dir() else []
    if tickets:
        out.append("<table><tr><th>ticket</th><th>task</th><th>World</th><th>write_set</th><th>claims</th><th>state</th></tr>")
        for tp in tickets:
            t = jload(tp, {}) or {}
            tid = str(t.get("ticket_id", tp.stem))
            pay = st / "payload" / tid
            staged = [p for p in pay.rglob("*") if p.is_file()] if pay.is_dir() else []  # files the writer has staged, before any land
            s = (badge(f"struck (seq {struck[tid]})", "red") if tid in struck else
                 badge("landed", "green") if tid in landed else
                 badge(f"staged ({len(staged)} file(s), not landed)", "amber") if staged else badge("minted, nothing staged", "grey"))
            out.append(f"<tr><td class=mono>{E(tid)}</td><td>{E(str(t.get('task', '')))}</td><td class=mono>{E(str(t.get('world_id', '')))}</td>"
                       f"<td class=mono>{E(', '.join(t.get('write_set') or []))}</td><td class=mono>{E(str(t.get('claims_sha256') or '')[:12])}</td><td>{s}</td></tr>")
            # the minted claims, readable before any land (UI pass, 2026-10-19): the signer sees what the ticket pins
            cf = st / "claims" / f"{tid}.json"
            minted = jload(cf, []) if cf.is_file() else []
            if isinstance(minted, list) and minted:
                def _exp(c):
                    e = c.get("expect") or {}
                    k = next(iter(e), "")
                    return f"{k}: {json.dumps(e.get(k))}"[:90] if k else ""
                rows_html = "".join(f"<tr><td>{i + 1}</td><td class=mono>{E(str(c.get('name', '')))}</td><td class=mono>{E(str(c.get('call', ''))[:90])}</td><td class=mono>{E(_exp(c))}</td></tr>"
                                    for i, c in enumerate(minted) if isinstance(c, dict))
                out.append(f"<tr><td colspan=6><details><summary>{len(minted)} claim(s) minted on <span class=mono>{E(tid)}</span></summary>"
                           f"<table class=claims><tr><th>#</th><th>function</th><th>call</th><th>expect</th></tr>{rows_html}</table></details></td></tr>")
        out.append("</table>")
    by_task = {}
    for r in rows:
        if r.get("strike"):
            by_task[str(r.get("task"))] = by_task.get(str(r.get("task")), 0) + 1
    for tp in tickets:  # every task with a ticket is listed, 0 strikes included: the limit is always in view (C2)
        by_task.setdefault(str((jload(tp, {}) or {}).get("task", "")), 0)
    if by_task:
        lim = policy.get("gets_through_anyway", 2)
        out.append("<p>strikes per task against gets_through_anyway: " + " · ".join(f"<span class=mono>{E(k)}</span> {badge(f'{v} / {lim}', 'red' if v >= lim else ('amber' if v else 'green'))}" for k, v in sorted(by_task.items())) + "</p>")
    for r in rows:
        evf = st / "evidence" / f"{r.get('ticket_id')}.{r.get('seq')}.json"
        cl, reach = c1_claims(evf)
        cov, bef, bsum = c1_v27(evf)
        claims_html = ""
        if cl:
            bh = "<th>before</th>" if bef else ""
            claims_html = f"<table class=claims><tr><th>#</th><th>function</th><th>call</th><th>expected</th><th>observed</th>{bh}</tr>" + "".join(
                f"<tr><td>{i}</td><td class=mono>{E(e.get('name',''))}</td><td class=mono>{E(e.get('call',''))}</td>"
                f"<td class=mono>{E(json.dumps(e.get('expected')))}</td><td>{observed(e)}</td>"
                + (f"<td>{before_badge(bef.get(i))}</td>" if bef else "") + "</tr>" for i, e in sorted(cl.items())) + "</table>"
        claims_html += coverage_html(cov, bsum) + u1_html(*u1_evidence(evf))
        nj = not_judged(r)
        out.append(f"<details><summary>row {r.get('seq')} · {E(str(r.get('ticket_id')))} · {E(str(r.get('decision')))}"
                   f"{' · STRIKE' if r.get('strike') else ''}{' · not judged: ' + E(nj) if nj else ''}</summary>{checks_table(r)}{claims_html}</details>")
    return "\n".join(out)


CSS = """
:root{--bg:#f6f5f2;--fg:#1d1d1b;--mut:#6b6a66;--line:#d9d7d1;--card:#fff;--g:#1f7a3a;--gb:#dff3e4;--r:#a32626;--rb:#fbe2e2;--a:#8a5a00;--ab:#fff1cc;--k:#555;--kb:#e9e8e4}
@media(prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--mut:#a3a19a;--line:#33322e;--card:#1f1f1c;--g:#7fd79a;--gb:#163a22;--r:#ff9a9a;--rb:#4a1c1c;--a:#ffd27a;--ab:#4a3a10;--k:#bbb;--kb:#2c2c29}}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:15px/1.45 -apple-system,Helvetica,Arial,sans-serif;max-width:1200px;margin:auto}
h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}h3{font-size:16px;margin:0 0 8px}
.muted{color:var(--mut);font-size:13px}.mono{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;word-break:break-word}
.b{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12.5px;font-weight:600;margin:1px 0}
.b-green{color:var(--g);background:var(--gb)}.b-red{color:var(--r);background:var(--rb)}.b-amber{color:var(--a);background:var(--ab)}.b-grey{color:var(--k);background:var(--kb)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}.tile .n{font-size:24px;font-weight:700}.tile .l{font-size:12px;color:var(--mut)}
.t-green .n{color:var(--g)}.t-red .n{color:var(--r)}.t-amber .n{color:var(--a)}
section.task{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:14px 0}
.pair{display:flex;gap:24px;flex-wrap:wrap;margin-bottom:8px}
table{border-collapse:collapse;width:100%;margin:6px 0;font-size:13.5px}th{text-align:left;color:var(--mut);font-weight:600;font-size:12px}td,th{padding:5px 8px;border-top:1px solid var(--line);vertical-align:top}
details{margin:6px 0}summary{cursor:pointer;color:var(--mut);font-size:13.5px}pre{background:var(--kb);padding:10px;border-radius:6px;overflow:auto;font-size:12px;max-height:420px}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[], help="a proving run folder (CLOSER_PROVING/runs/<stamp>); repeatable, first one names the output")
    ap.add_argument("--state", action="append", default=[], help="a state dir (repeatable)")
    ap.add_argument("--out")
    a = ap.parse_args()
    if not a.run and not a.state:
        ap.error("give --run and/or --state")
    runs = [Path(r).resolve() for r in a.run]
    out = Path(a.out) if a.out else (runs[0] / "DASH.html" if runs else Path(a.state[0]) / "dash.html")
    parts = [f"<h1>getting-close · signer's view</h1><p class=muted>generated {E(datetime.datetime.now().isoformat(timespec='seconds'))} · read-only · "
             f"built from the gate's own files: ledger rows, check lines, sealed claim evidence</p>"]
    for run in runs:
        parts.append(run_section(run))
    for s in a.state:
        parts.append(state_section(Path(s).expanduser().resolve()))
    out.write_text(f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                   f"<title>getting-close</title><style>{CSS}</style></head><body>{''.join(parts)}</body></html>")
    print(out)


if __name__ == "__main__":
    main()
