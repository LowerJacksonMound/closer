#!/bin/sh
# Plant: the scanner never writes the tree it reads (KERNEL K7). substance.py `after`, and `gc scan` (which runs
# `before`), leave every byte of the tree as it was, counterfeits included; what they emit is one write-once,
# read-only overlay, and a second write to the same overlay is refused. Real scanner, real gc, real files.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT s1_scanner_writes_nothing: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"; mkdir -p "$R/pkg"
printf 'def is_valid_code(code):\n    if code:\n        return True\n    return True\n\n\ndef mask_email(a):\n    return a\n' > "$R/app.py"
printf 'def make_worker(cfg):\n    return None\n\n\ndef ok(x):\n    return x + 1\n' > "$R/pkg/mod.py"
printf 'def parse_int(s):\n    try:\n        return int(s)\n    finally:\n        return 0\n' > "$R/pkg/fin.py"
echo notes > "$R/README.txt"
tree_hash() { (cd "$1" && find . -type f -not -name '.DS_Store' | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256); }
H0="$(tree_hash "$R")"

python3 "$HERE/scanner/substance.py" after --tree "$R" --scan-id after_x \
  --write-set '["app.py","pkg/mod.py","pkg/fin.py"]' --out "$T/after.json" >/dev/null 2>&1 || fail "after mode failed"
[ "$(tree_hash "$R")" = "$H0" ] || fail "after mode changed the tree"
[ -f "$T/after.json" ] || fail "no overlay emitted"
[ ! -w "$T/after.json" ] || fail "overlay is writable; it must be frozen"
python3 "$HERE/scanner/substance.py" after --tree "$R" --scan-id after_x \
  --write-set '["app.py"]' --out "$T/after.json" >/dev/null 2>"$T/err" && fail "second write to the overlay was accepted"
grep -q "refuse second write" "$T/err" || fail "second write refused without saying so: $(cat "$T/err")"
python3 - "$T/after.json" <<'PY' || fail "overlay did not read the tree: $(cat "$T/after.json")"
import json, sys
o = json.load(open(sys.argv[1]))
rules = {(u["relpath"], f["rule"], f["qualname"]) for u in o["units"] for f in u["findings"]}
need = {("app.py", "always_true", "is_valid_code"), ("app.py", "identity_return", "mask_email"),
        ("pkg/mod.py", "factory_none", "make_worker"), ("pkg/fin.py", "finally_return", "parse_int")}
sys.exit(0 if need <= rules and ("pkg/mod.py", "factory_none", "ok") not in rules else 1)
PY

gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "gc init/scan"
[ "$(tree_hash "$R")" = "$H0" ] || fail "gc scan (before mode) changed the tree"
OV="$(ls "$ST"/worlds/*.substance.json 2>/dev/null | head -1)"
[ -n "$OV" ] || fail "gc scan emitted no substance overlay"
[ ! -w "$OV" ] || fail "before overlay is writable; it must be frozen"
echo "PLANT s1_scanner_writes_nothing: PASS"
