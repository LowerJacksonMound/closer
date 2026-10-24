#!/bin/sh
# Live in pack v37 (proposals/PACK_v37.md: `trace_replaced` in s1_rules, `probe_unfoldable` in s1_advisory; this file unchanged). v36 (proposals/PACK_v36.md: PACK.json `s1_stand_down`, a pack-level list of relpath patterns (fnmatch) whose
# judge_detection / dynamic_code findings are stood down before counting, each said as an `S1 note: stood down` line so the
# signer sees it; the scanner's data-flow evidence rides in each finding's `why`). v35 (proposals/PACK_v35.md: PACK.json `s1_advisory` rules are reported as `S1 note:` lines on stdout, never a
# strike; a finding's `why` is said after ` -- `, so a probe found inside a constant string handed to exec / eval / compile
# is cited with the outer line and the probe's own line and text). v34 (2026-10-21: `judge_detection` added to s1_rules, KERNEL T20 first application, proposals/PACK_v34.md;
# this file unchanged). v26 (2026-10-15, shape rules; v2 OPEN_RULINGS R1, 2026-10-05). Edit only through a new pack version (K5).
# S1 (OPEN_RULINGS B3): a patch introduces no counterfeit substance.
# Rules: stub_body, swallow, hollow_test, const_return (v2); theatre_return, factory_none, finally_return,
# always_true, identity_return (v26); judge_detection (v34); plus unparsed (a write_set .py that no longer parses). The rule ids that
# count are PACK.json `s1_rules`: the scanner emits every rule it has, S1 reads only the live ids on both sides,
# so a scanner rule goes live only through the pack (K5). Pre-existing findings do not fail; only
# per-(file, rule, qualname) increases. A finding names file, line, rule and qualname, never a species.
# No parse here (R6-1). Before facts: frozen overlay ${WORLD_FILE%.json}.substance.json, bound to
# the World by world_id + sha256 + unit bytes. After facts: the scanner emits a new scan_id over
# the write_set (R6-3). World v1 unchanged.
set -u
WORLD="${WORLD_FILE:?set WORLD_FILE to a scan_*.json}"
TREE="${SCOPED_ROOT:?set SCOPED_ROOT to the patched tree}"
WS="${WRITE_SET:?set WRITE_SET to the ticket write_set JSON}"
TID="${TICKET_ID:-ticket}"
ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
BEFORE="${WORLD%.json}.substance.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$ROOT/scanner/substance.py" after --tree "$TREE" --scan-id "after_$TID" \
  --write-set "$WS" --out "$TMP/after.json" > /dev/null || {
  echo "S1 fail: scanner could not emit the after overlay" >&2
  exit 1
}

python3 - "$WORLD" "$BEFORE" "$TMP/after.json" "$ROOT/pack/live/PACK.json" << 'PY'
import hashlib, json, os, sys
from collections import Counter

def fail(msg: str) -> None:
    print(f"S1 fail: {msg}", file=sys.stderr)
    sys.exit(1)

world_path, before_path, after_path, pack_path = sys.argv[1:5]
try:
    live = json.load(open(pack_path, encoding="utf-8")).get("s1_rules")
except (OSError, ValueError) as e:
    print(f"S1 not run: {pack_path} unreadable: {e}", file=sys.stderr)
    sys.exit(75)
if not (isinstance(live, list) and live and all(isinstance(r, str) for r in live)):
    print("S1 not run: PACK.json s1_rules must be a non-empty list of rule ids", file=sys.stderr)
    sys.exit(75)
live = set(live)
advisory = json.load(open(pack_path, encoding="utf-8")).get("s1_advisory") or []
if not (isinstance(advisory, list) and all(isinstance(r, str) for r in advisory)):
    print("S1 not run: PACK.json s1_advisory must be a list of rule ids", file=sys.stderr)
    sys.exit(75)
advisory = set(advisory) - live
stand_down = json.load(open(pack_path, encoding="utf-8")).get("s1_stand_down") or []
if not (isinstance(stand_down, list) and all(isinstance(r, str) for r in stand_down)):
    print("S1 not run: PACK.json s1_stand_down must be a list of relpath patterns", file=sys.stderr)
    sys.exit(75)
_PROBE_RULES = {"judge_detection", "dynamic_code"}


def stood_down(rel):
    """The first s1_stand_down pattern the file's relpath matches (fnmatch, whole path), else None. Only the probe
    rules stand down: a pack-level allow-list for packages that ask by trade (a vendored debugger, coverage tool,
    dotenv), beside the scanner's own file-name condition. Auditable: it is in the pack, changed by version."""
    import fnmatch
    for pat in stand_down:
        if fnmatch.fnmatchcase(rel, pat):
            return pat
    return None
raw = open(world_path, "rb").read()
w = json.loads(raw)
if w.get("kind") != "world" or w.get("version") != 1:
    fail("not a world v1")
if not os.path.isfile(before_path):
    fail(f"no substance overlay for World: {before_path}")
# A link can point at a file whose owner re-chmods it; the World's sha binds only what it names.
for p, what in ((world_path, "World"), (before_path, "substance overlay")):
    if os.path.islink(p):
        fail(f"{what} is a symlink; must be the frozen file itself: {p}")
    if os.access(p, os.W_OK):
        fail(f"{what} is writable; must be frozen: {p}")
b = json.load(open(before_path, encoding="utf-8"))
if b.get("kind") != "substance_overlay" or b.get("version") != 1:
    fail("before overlay is not substance_overlay v1")
if b.get("world_id") != w.get("world_id") or b.get("world_sha256") != hashlib.sha256(raw).hexdigest():
    fail("before overlay is not bound to this World (world_id / sha256)")
primary = [r["root_id"] for r in w.get("roots") or [] if r.get("role") == "primary"]
if len(primary) != 1:
    fail(f"need exactly one primary root to map write_set paths, got {primary}")
rid = primary[0]
wbytes = {u["relpath"]: u["bytes"] for u in w["units"] if u["root_id"] == rid}
prior = {}
for u in b["units"]:
    if u["root_id"] != rid:
        continue
    if wbytes.get(u["relpath"]) != u["bytes"]:
        fail(f"before overlay unit does not match World: {u['relpath']}")
    prior[u["relpath"]] = u

a = json.load(open(after_path, encoding="utf-8"))
if (live | advisory) - set(a.get("rules") or []):
    print(f"S1 not run: PACK.json s1_rules / s1_advisory names rules the scanner lacks: {sorted((live | advisory) - set(a.get('rules') or []))}", file=sys.stderr)
    sys.exit(75)


def why(findings, key):
    """The findings' own reasons for one (rule, qualname), deduplicated, after ` -- `."""
    seen = []
    for f in findings:
        w = f.get("why")
        if (f["rule"], f["qualname"]) == key and w and w not in seen:
            seen.append(w)
    return (" -- " + "; ".join(seen)) if seen else ""


hits, notes, kept = [], [], 0
for u in a["units"]:
    rel, old = u["relpath"], prior.get(u["relpath"])
    if u["reader_error"]:
        if old is None or not old["reader_error"]:
            hits.append(f"{rel}: unparsed ({u['reader_error']})")
        continue
    pat = stood_down(rel)
    if pat:
        dropped = [f for f in u["findings"] if f["rule"] in _PROBE_RULES]
        for key in sorted({(f["rule"], f["qualname"]) for f in dropped}):
            notes.append(f"stood down {rel} {key[0]} {key[1]} (s1_stand_down {pat!r})")
        u = dict(u, findings=[f for f in u["findings"] if f["rule"] not in _PROBE_RULES])
        if old:
            old = dict(old, findings=[f for f in old.get("findings", []) if f["rule"] not in _PROBE_RULES])
    was = Counter((f["rule"], f["qualname"]) for f in (old or {}).get("findings", []) if f["rule"] in live)
    now = Counter((f["rule"], f["qualname"]) for f in u["findings"] if f["rule"] in live)
    kept += sum((now & was).values())
    for key, n in (now - was).items():
        lines = ",".join(str(f["line"]) for f in u["findings"] if (f["rule"], f["qualname"]) == key)
        hits.append(f"{rel}:{lines} {key[0]} {key[1]} (+{n}){why(u['findings'], key)}")
    # advisory rules: said, never a strike (T16: the gate strikes on a verdict); the signer's page shows them
    was_a = Counter((f["rule"], f["qualname"]) for f in (old or {}).get("findings", []) if f["rule"] in advisory)
    now_a = Counter((f["rule"], f["qualname"]) for f in u["findings"] if f["rule"] in advisory)
    for key, n in (now_a - was_a).items():
        lines = ",".join(str(f["line"]) for f in u["findings"] if (f["rule"], f["qualname"]) == key)
        notes.append(f"{rel}:{lines} {key[0]} {key[1]} (+{n}){why(u['findings'], key)}")
for note in notes:
    print(f"S1 note: {note}" if note.startswith("stood down ") else f"S1 note: introduced {note}")
if hits:
    for h in hits:
        print(f"S1 fail: introduced {h}", file=sys.stderr)
    sys.exit(1)
print(f"S1 pass: {len(a['units'])} python file(s) in write_set; introduced=0 pre-existing={kept} rules={len(live)}"
      + (f" notes={len(notes)}" if notes else ""))
PY
