#!/bin/sh
# Live in pack v3. Edit only through a new pack version (K5).
# W1 = K1: a World is append-only by id. A second write to scan_<id> fails.
#   1. WORLD_FILE is a regular file (not a link), named scan_<id>.json, whose world_id is that id.
#   2. No write bit for anyone: writability is the freeze flag (WORLD.md "Freeze").
#   3. The kernel emitter is asked to write scan_<id>.json a second time and must refuse with the K1
#      refusal, leaving bytes and mode as they were. The attempt runs on a byte-for-byte copy under the
#      same name in a temp dir: a broken emitter must not be able to destroy the World it is checked on.
set -u
KERNEL="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
ROOT="${GROK_WORKSPACE_ROOT:-$(pwd)}"
WORLD="${WORLD_FILE:-$ROOT/worlds/scan_demo.json}"
TMP="$(mktemp -d)"
trap 'chmod -R u+w "$TMP" 2>/dev/null; rm -rf "$TMP"' EXIT

PYTHONDONTWRITEBYTECODE=1 python3 - "$KERNEL" "$WORLD" "$TMP" << 'PY'
import json, os, shutil, stat, sys
from pathlib import Path

kernel, world, tmp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(kernel))
from scanner.emit import emit_world  # the emitter gc scan uses


def fail(msg):
    print(f"W1 fail: {msg}", file=sys.stderr)
    sys.exit(1)


try:
    st = os.lstat(world)
except OSError:
    fail(f"no world at {world}")
if not stat.S_ISREG(st.st_mode):
    fail(f"{world} is not a regular file")
if st.st_mode & 0o222:
    fail(f"{world} has a write bit ({stat.filemode(st.st_mode)}); freeze must be chmod a-w after emit")
name = world.name
if not (name.startswith("scan_") and name.endswith(".json") and len(name) > len("scan_.json")):
    fail(f"{name} is not scan_<id>.json")
bare = name[len("scan_"):-len(".json")]
raw = world.read_bytes()
try:
    wid = str(json.loads(raw).get("world_id", ""))
except (ValueError, AttributeError):
    fail(f"{name} is not a JSON object")
if wid not in (bare, f"scan_{bare}"):
    fail(f"{name} holds world_id {wid!r}; the file name says {bare!r}")

copy = tmp / "worlds" / name
copy.parent.mkdir()
shutil.copyfile(world, copy)
os.chmod(copy, stat.S_IMODE(st.st_mode))
try:
    emit_world({"world_id": bare, "W1": "second write"}, copy)
except SystemExit as e:
    if "refuse second write" not in str(e):
        fail(f"second write refused, but not by K1: {e}")
else:
    fail(f"second write to {name} succeeded (K1 broken)")
if copy.read_bytes() != raw:
    fail(f"refused second write changed the bytes of {name}")
if stat.S_IMODE(os.lstat(copy).st_mode) != stat.S_IMODE(st.st_mode):
    fail(f"refused second write changed the mode of {name}")
print(f"W1 pass: {name} frozen; second write refused")
PY
