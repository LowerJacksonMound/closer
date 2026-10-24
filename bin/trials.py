#!/usr/bin/env python3
"""The page during trials (INGREDIENTS item 9): the signer's dashboard, rebuilt whenever the gate writes.

A watcher, not a server. It polls the run folders and state dirs it is given, re-renders the page through
`bin/dash.py` when any of their files change, and writes one HTML file atomically. The page reloads itself on a
timer, keeps its scroll position, and says when the watcher has stopped. No network module (K6): the browser
re-reads a file. Read-only on everything it watches.

    python3 bin/trials.py --run ~/Desktop/CLOSER_PROVING/runs/<stamp> [--run ...] [--state DIR ...]
                          [--out FILE] [--every 5] [--once]

Mid-run, before prove.py has written results.json, the page is built from the per-ticket files it has written so
far (land.log, row.json, *.error.log, demos/*/drive.json). Once results.json exists the full run section from
dash.py takes over. A demo that is driving the screen is shown as a banner: the watcher tries the runner's demo
lock without blocking, and a held lock means hands off.
"""
import argparse, datetime, fcntl, html, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dash  # the renderer; this file only decides when to call it

E = html.escape
WATCH_NAMES = {"land.log", "row.json", "results.json", "RESULTS.md", "drive.json", "driver.txt",
               "ledger.jsonl", "LATEST", "policy.json", "manifest.json"}


# ---- what changed -----------------------------------------------------------

def fingerprint(paths):
    """(path, mtime_ns, size) of every watched file under the given roots. Cheap enough to run every few seconds."""
    seen = []
    for root in paths:
        if not root.exists():
            seen.append((str(root), -1, -1)); continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in ("__pycache__", "shots")]
            for f in fns:
                rel = Path(dp).relative_to(root).parts
                if f in WATCH_NAMES or f.endswith(".error.log") or any(x in ("payload", "tickets", "claims", "evidence") for x in rel):
                    p = Path(dp) / f
                    try:
                        st = p.stat(); seen.append((str(p), st.st_mtime_ns, st.st_size))
                    except OSError:
                        seen.append((str(p), -2, -2))
    return tuple(sorted(seen))


def demo_driving(run):
    """True while prove.py holds its demo lock (a demo has the mouse and keyboard)."""
    lock = run.parent.parent / ".demos.lock"
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
        return False
    return False


# ---- the in-progress view (before results.json) -----------------------------

def ticket_state(d):
    """One landed ticket folder -> (badge, detail) from row.json, or the error log."""
    row = dash.jload(d / "row.json")
    if row:
        dec = row.get("decision") or "?"
        strike = bool(row.get("strike"))
        kind = "red" if strike else ("green" if dec == "proceed" else "amber")
        fails = [s for c in row.get("checks", []) if c.get("exit") not in (0, 75) for s in c.get("said", [])]
        checks = " ".join(f"{c.get('name')}:{c.get('exit')}" for c in row.get("checks", []))
        return dash.badge(f"{dec}{' · strike' if strike else ''}", kind), checks, fails[:6]
    if (d / "land.log").is_file():
        return dash.badge("landed, no row", "amber"), "", []
    return dash.badge("in progress", "grey"), "", []


def demo_states(d):
    out = []
    dd = d / "demos"
    if not dd.is_dir():
        return out
    for n in sorted(p.name for p in dd.iterdir() if p.is_dir()):
        dj = dash.jload(dd / n / "drive.json")
        if dj is None:
            out.append((n, dash.badge("running", "amber")))
        else:
            ok = dj.get("driver_exit", dj.get("exit")) == 0 if isinstance(dj, dict) else False
            out.append((n, dash.badge("ok" if ok else "failed", "green" if ok else "red")))
    return out


def progress_section(run):
    """Built from the files prove.py writes as it goes; shown until results.json exists."""
    tasks = []
    for app in sorted(p for p in run.iterdir() if p.is_dir()):
        for task in sorted(p for p in app.iterdir() if p.is_dir()):
            tickets = sorted(p for p in task.iterdir() if p.is_dir())
            errors = sorted(task.glob("*.error.log"))
            tasks.append((app.name, task.name, tickets, errors))
    n_land = sum(1 for _, _, ts, _ in tasks for t in ts if (t / "land.log").is_file())
    n_err = sum(len(e) for _, _, _, e in tasks)
    n_strike = sum(1 for _, _, ts, _ in tasks for t in ts if (dash.jload(t / "row.json") or {}).get("strike"))
    out = [f"<h2>Run <span class=mono>{E(run.name)}</span> <span class=muted>in progress: results.json not yet written</span></h2>",
           "<div class=tiles>",
           f"<div class=tile><div class=n>{len(tasks)}</div><div class=l>tasks started</div></div>",
           f"<div class=tile><div class=n>{n_land}</div><div class=l>tickets landed</div></div>",
           f"<div class='tile t-red'><div class=n>{n_strike}</div><div class=l>struck</div></div>",
           f"<div class='tile t-amber'><div class=n>{n_err}</div><div class=l>not minted</div></div>",
           "</div>"]
    if not tasks:
        out.append("<p class=muted>nothing landed yet</p>")
    for app, task, tickets, errors in tasks:
        out.append(f"<section class=task><h3>{E(app)} · {E(task)}</h3><table><tr><th>ticket</th><th>decision</th><th>checks</th><th>said</th></tr>")
        for t in tickets:
            b, checks, fails = ticket_state(t)
            said = "<br>".join(E(f) for f in fails)
            out.append(f"<tr><td class=mono>{E(t.name)}</td><td>{b}</td><td class=mono>{E(checks)}</td><td class=mono>{said}</td></tr>")
            for n, db in demo_states(t):
                out.append(f"<tr><td class=mono>&nbsp;&nbsp;demo {E(n)}</td><td>{db}</td><td></td><td></td></tr>")
        for e in errors:
            out.append(f"<tr><td class=mono>{E(e.name.replace('.error.log', ''))}</td><td>{dash.badge('not minted', 'amber')}</td><td></td><td></td></tr>")
        out.append("</table></section>")
    return "".join(out)


# ---- the page ----------------------------------------------------------------

def render(runs, states, every, out):
    now = datetime.datetime.now()
    driving = any(demo_driving(r) for r in runs)
    parts = [f"<h1>getting-close · trials</h1>"
             f"<p class=muted>rendered <span id=stamp data-ts='{int(now.timestamp())}'>{E(now.isoformat(timespec='seconds'))}</span> · "
             f"page reloads every {every}s · read-only · built from the gate's own files</p>"
             f"<p id=stale class=b-red style='display:none;padding:8px 12px;border-radius:8px'>watcher stopped: this page is stale</p>"]
    if driving:
        parts.append("<p class='b b-amber' style='padding:8px 12px;border-radius:8px'>a demo is driving the screen: hands off the mouse and keyboard</p>")
    for run in runs:
        if not run.is_dir():
            parts.append(f"<h2>Run <span class=mono>{E(str(run))}</span></h2><p class=muted>not started: folder does not exist yet</p>")
        elif (run / "results.json").is_file():
            parts.append(dash.run_section(run))
        else:
            parts.append(progress_section(run))
    for st in states:
        parts.append(dash.state_section(st))
    js = f"""
try{{var y=sessionStorage.getItem('trials.y');if(y)window.scrollTo(0,parseInt(y,10));}}catch(e){{}}
try{{window.addEventListener('scroll',function(){{try{{sessionStorage.setItem('trials.y',String(window.scrollY));}}catch(e){{}}}});}}catch(e){{}}
(function(){{var s=document.getElementById('stamp');var ts=parseInt(s.getAttribute('data-ts'),10)*1000;
function tick(){{if(Date.now()-ts>{every}*4000)document.getElementById('stale').style.display='block';}}tick();setInterval(tick,1000);}})();
"""
    page = (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<meta http-equiv=refresh content='{every}'><title>getting-close trials</title><style>{dash.CSS}</style></head>"
            f"<body>{''.join(parts)}<script>{js}</script></body></html>")
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(page)
    os.replace(tmp, out)  # the browser never reads a half-written page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[], help="a proving run folder, repeatable; may not exist yet")
    ap.add_argument("--state", action="append", default=[], help="a gate state dir, repeatable")
    ap.add_argument("--out", help="the HTML file to keep rebuilding (default: TRIALS.html beside the first run, or in cwd)")
    ap.add_argument("--every", type=int, default=5, help="seconds between polls, and the page's reload interval")
    ap.add_argument("--once", action="store_true", help="render once and exit")
    a = ap.parse_args()
    if not a.run and not a.state:
        ap.error("give --run and/or --state")
    runs = [Path(r).expanduser().resolve() for r in a.run]
    states = [Path(s).expanduser().resolve() for s in a.state]
    out = Path(a.out).expanduser().resolve() if a.out else ((runs[0].parent if runs else Path.cwd()) / "TRIALS.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    last = None
    print(f"watching {len(runs)} run(s), {len(states)} state dir(s) -> {out}  (open it in a browser; ctrl-c to stop)")
    while True:
        fp = fingerprint(runs + states)
        driving = tuple(demo_driving(r) for r in runs)
        key = (fp, driving)
        if key != last:
            try:
                render(runs, states, a.every, out)
                print(f"{datetime.datetime.now().isoformat(timespec='seconds')} rendered")
            except Exception as ex:  # a half-written file mid-land must not kill the watcher
                print(f"{datetime.datetime.now().isoformat(timespec='seconds')} render failed: {ex!r}", file=sys.stderr)
            last = key
        if a.once:
            return
        time.sleep(a.every)


if __name__ == "__main__":
    main()
