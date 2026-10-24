#!/usr/bin/env python3
"""The repo watcher (POST_MVP step 3, 2026-10-21): what changed outside the gate since the World was frozen.

The gate judges a ticket at land against the World frozen by `gc scan`. A file edited outside the gate (by hand, by
another tool) between the freeze and the next land is not seen: a probe put in a file no ticket touches is never
scanned, and one in a file a ticket later touches is charged to the writer. This process watches the registered
roots and writes `<state>/signer/watch.json` every few seconds: which .py files differ from the frozen World and
were not changed by a landed ticket, and what the scanner finds new in them (every rule, judge_detection and the
dynamic_code advisory included), each with the file, qualname, line and reason. The page (bin/session.py) shows it as
"changed outside the gate"; `closer inspect` and `closer status` print it. Read-only on the repo; outside the kernel
(K6): it imports the scanner to read, writes only its own file under signer/.

What it can and cannot say: a file whose byte count differs from the World's unit is changed since the freeze for
certain; a same-length edit made before the watcher started is seen only from the watcher's first tick (the live
tree is hashed then and on every tick). It names what it saw, and says which.
"""
import argparse, hashlib, json, os, signal, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from scanner import substance  # read only


def load_world(st):
    latest = (st / "LATEST").read_text().strip() if (st / "LATEST").is_file() else ""
    wf = st / "worlds" / f"{latest}.json"
    if not latest or not wf.is_file():
        return None, {}, 0.0
    w = json.loads(wf.read_text())
    units = {u["relpath"]: u for u in w.get("units", []) if u.get("relpath", "").endswith(".py")}
    return latest, units, wf.stat().st_mtime


def gate_changed(st, since_mtime):
    """Files a landed ticket (proceed, no strike) changed after the World was frozen: the gate's own work. Maps the
    relpath to (ticket_id, the payload file the gate applied), newest land last, so the live file can be compared
    with what the gate landed, not with the World it has outgrown."""
    import calendar
    out = {}
    lp = st / "ledger.jsonl"
    if not lp.is_file():
        return out
    for line in lp.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("decision") != "proceed" or r.get("strike"):
            continue
        try:
            ts = calendar.timegm(time.strptime(str(r.get("ts", ""))[:19], "%Y-%m-%dT%H:%M:%S"))  # the ledger stamps UTC
        except ValueError:
            ts = 0
        if ts < since_mtime - 2:
            continue
        tid = str(r.get("ticket_id"))
        tf = st / "tickets" / f"{tid}.json"
        if tf.is_file():
            for rel in json.loads(tf.read_text()).get("write_set") or []:
                out[rel] = (tid, st / "payload" / tid / rel)
    return out


def walk(roots):
    for root in roots:
        base = Path(root["path"])
        excl = set(root.get("exclude") or []) | {"__pycache__", ".git"}
        for d, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in excl]
            for f in files:
                if f.endswith(".py"):
                    p = Path(d) / f
                    yield root.get("root_id"), p.relative_to(base).as_posix(), p


def tick(st, roots, world_id, units, world_mtime, seen):
    """One pass: returns the report dict and updates `seen` (relpath -> sha256 at last tick)."""
    through_gate = gate_changed(st, world_mtime)
    changed, checked, now_hashes = [], 0, {}
    for root_id, rel, p in walk(roots):
        checked += 1
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        h = hashlib.sha256(raw).hexdigest()
        now_hashes[rel] = h
        unit = units.get(rel)
        since = None
        base_findings = (unit or {}).get("findings", [])
        if rel in through_gate:
            tid, pf = through_gate[rel]
            try:
                landed = pf.read_bytes()
            except OSError:
                landed = None
            if landed is not None and hashlib.sha256(landed).hexdigest() == h:
                continue  # exactly what the gate landed
            since = f"changed since ticket {tid} landed it"
            if landed is not None:
                try:
                    base_findings = substance.extract(landed.decode("utf-8"), rel)
                except (SyntaxError, ValueError, UnicodeDecodeError, RecursionError):
                    base_findings = []
        elif unit is None:
            since = "new since the World was frozen"
        elif unit.get("bytes") != len(raw):
            since = "changed since the World was frozen"
        elif rel in seen and seen[rel] != h:
            since = "changed while the watcher was running"
        elif rel in seen_changed:
            since = seen_changed[rel]
        if since is None:
            continue
        seen_changed[rel] = since
        try:
            findings = substance.extract(raw.decode("utf-8"), rel)
        except (SyntaxError, ValueError, UnicodeDecodeError, RecursionError) as exc:
            findings = [{"rule": "unparsed", "qualname": "<module>", "line": 0, "why": f"{type(exc).__name__}: {exc}"}]
        old = {(f["rule"], f["qualname"], f.get("line")) for f in base_findings}
        new = [f for f in findings if (f["rule"], f["qualname"], f.get("line")) not in old]
        changed.append({"relpath": rel, "since": since, "new_findings": new})
    for rel in list(units):
        if rel not in now_hashes and rel not in through_gate:
            changed.append({"relpath": rel, "since": "removed since the World was frozen", "new_findings": []})
    seen.clear(); seen.update(now_hashes)
    return {"kind": "watch", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "world_id": world_id, "checked": checked,
            "through_gate": sorted(through_gate), "changed_outside_gate": sorted(changed, key=lambda c: c["relpath"])}


seen_changed: dict = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--every", type=float, default=4.0)
    ap.add_argument("--once", action="store_true", help="one pass, print the report, exit")
    a = ap.parse_args()
    st = Path(a.state).expanduser().resolve()
    mf = json.loads((st / "manifest.json").read_text())
    roots = mf.get("roots") or [{"root_id": "app", "path": mf.get("repo")}]
    out = st / "signer" / "watch.json"; out.parent.mkdir(exist_ok=True)
    world_id, units, world_mtime = load_world(st)
    seen: dict = {}
    last_key = [None]
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True:
        latest = (st / "LATEST").read_text().strip() if (st / "LATEST").is_file() else ""
        if latest != world_id:  # a new freeze: start over against it
            world_id, units, world_mtime = load_world(st); seen.clear(); seen_changed.clear()
        rep = tick(st, roots, world_id, units, world_mtime, seen) if world_id else \
            {"kind": "watch", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "world_id": None, "checked": 0, "through_gate": [], "changed_outside_gate": []}
        tmp = out.with_suffix(".tmp"); tmp.write_text(json.dumps(rep, indent=1)); os.replace(tmp, out)
        # history: one line per change of the changed-outside set (what the signer was shown, and when), for the load count
        key = json.dumps([(c["relpath"], c["since"], [(f["rule"], f["qualname"], f.get("line")) for f in c["new_findings"]])
                          for c in rep["changed_outside_gate"]], sort_keys=True)
        if key != last_key[0]:
            with open(out.parent / "watch_log.jsonl", "a") as fh:
                fh.write(json.dumps({"ts": rep["ts"], "world_id": rep["world_id"], "files": len(rep["changed_outside_gate"]),
                                     "new_findings": sum(len(c["new_findings"]) for c in rep["changed_outside_gate"]),
                                     "rules": sorted({f["rule"] for c in rep["changed_outside_gate"] for f in c["new_findings"]})}) + "\n")
            last_key[0] = key
        if a.once:
            print(json.dumps(rep, indent=1)); return 0
        time.sleep(a.every)


if __name__ == "__main__":
    sys.exit(main())
