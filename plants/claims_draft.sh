#!/bin/sh
# Plant: claims_draft drafts by fixed rules and never mints (T5). On a task whose criteria name `check_volume`
# (rejects 11 with a ValueError; returns True for 5) and `save` (writes the file), it drafts a raises claim with
# the exception filled, a result claim with the literal filled, and an effect claim with a placeholder; a clause
# with no table verb drafts nothing and says so in the notes. gc refuses to mint the draft while a placeholder
# remains; the same file with the placeholder replaced by the signer mints.
# Checklist (INGREDIENTS item 4): on a repo with a backlog whose task names `check_code`, the notes carry its
# negative and positive lines; `--check` on claims holding only a result claim on it reports the negative line
# uncovered, a raises claim clears it, and `--changed` adds a block for `save_code`, which the criteria do not name.
# `--check` exits 0 either way: it is advice, never a refusal.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT claims_draft: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R/src/pkg"
printf 'def save(path, text):\n    return 0\n' > "$R/src/pkg/io.py"; : > "$R/src/pkg/__init__.py"
echo notes > "$R/README.txt"
cat > "$T/task.md" <<'MD'
## 3. Volume check

**Acceptance criteria**
- `check_volume` rejects `11` with a `ValueError`; returns `True` for `5`.
- `save` writes the text to the path.
- `Settings` gains a `volume` field.
- Tests: both branches.
MD
python3 "$HERE/bin/claims_draft.py" --repo "$R" --task-file "$T/task.md" --out "$T/draft.json" > "$T/out" 2>&1 || fail "claims_draft failed: $(cat "$T/out")"
python3 - "$T/draft.json" "$T/draft.notes.txt" <<'PY' || fail "draft wrong: $(cat "$T/draft.json"; cat "$T/draft.notes.txt")"
import json, sys
d = json.load(open(sys.argv[1])); notes = open(sys.argv[2]).read()
by = {(c["name"], next(iter(c["expect"]))): c for c in d}
r = by.get(("<FILL: module>.check_volume", "raises")) or by.get(("pkg.io.check_volume", "raises"))
v = by.get(("<FILL: module>.check_volume", "result")) or by.get(("pkg.io.check_volume", "result"))
s = by.get(("pkg.io.save", "true"))
ok = r and r["expect"] == {"raises": "ValueError"} and r["call"] == "check_volume(11)" \
    and v and v["expect"] == {"result": True} and v["call"] == "check_volume(5)" \
    and s and s["expect"]["true"].startswith("<FILL:") \
    and "nothing drafted" in notes and "`Settings` gains" in notes and "skipped (tests" in notes
sys.exit(0 if ok else 1)
PY
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "init/scan"
gc ticket --write src/pkg/io.py --id T1 --claims "$T/draft.json" >/dev/null 2>"$T/err" && fail "a draft with placeholders was minted"
grep -q "<FILL: ...> placeholder" "$T/err" || fail "refusal does not name the placeholder: $(cat "$T/err")"
printf '%s' '[{"name":"pkg.io.save","setup":["import os, tempfile","p = os.path.join(tempfile.mkdtemp(), \"x\")"],"call":"save(p, \"hi\")","expect":{"true":"open(p).read() == \"hi\""}}]' > "$T/filled.json"
gc ticket --write src/pkg/io.py --id T1 --claims "$T/filled.json" >/dev/null 2>&1 || fail "the filled claims did not mint"
R2="$T/repo2"; mkdir -p "$R2/src/pkg"; : > "$R2/src/pkg/__init__.py"
printf 'def check_code(code):\n    if not code.isdigit():\n        raise ValueError(code)\n    return True\n\n\ndef save_code(path, code):\n    with open(path, "w") as f:\n        f.write(code)\n' > "$R2/src/pkg/codes.py"
cat > "$T/BACKLOG.md" <<'MD'
# Backlog

## 1. Codes

**Acceptance criteria**
- `check_code` rejects `abc` with a `ValueError`; returns `True` for `123`.
MD
CD() { python3 "$HERE/bin/claims_draft.py" --repo "$R2" --backlog "$T/BACKLOG.md" --task 1 "$@"; }
CD --out "$T/d2.json" --changed src/pkg/codes.py:save_code > "$T/out" 2>&1 || fail "checklist draft failed: $(cat "$T/out")"
N="$T/d2.notes.txt"
grep -q '^## pkg.codes.check_code (criteria; check)' "$N" || fail "no checklist block for check_code: $(cat "$N")"
grep -q '^- check_code \[negative, T9\]: a negative case' "$N" || fail "no negative line for check_code: $(cat "$N")"
grep -q '^- check_code \[positive, T1\]: the positive case passes' "$N" || fail "no positive line for check_code: $(cat "$N")"
grep -q '^- check_code \[set_up, T8\]' "$N" || fail "no always-line for check_code: $(cat "$N")"
grep -q '^## pkg.codes.save_code (changed; effect)' "$N" || fail "--changed added no block for save_code: $(cat "$N")"
grep -q '^- save_code \[sink, T6\]' "$N" || fail "no sink line for save_code: $(cat "$N")"
grep -q '^- save_code \[negative' "$N" && fail "save_code is not check-named but got a negative line"
printf '%s' '[{"name":"pkg.codes.check_code","call":"check_code(\"123\")","expect":{"result":true}}]' > "$T/c1.json"
CD --check "$T/c1.json" > "$T/k1" 2>&1 || fail "--check exited non-zero: $(cat "$T/k1")"
grep -q '^uncovered pkg.codes.check_code \[negative, T9\]' "$T/k1" || fail "a result-only claim set did not report the negative uncovered: $(cat "$T/k1")"
grep -q '^uncovered pkg.codes.check_code \[positive' "$T/k1" && fail "the result claim did not cover the positive line"
printf '%s' '[{"name":"pkg.codes.check_code","call":"check_code(\"123\")","expect":{"result":true}},{"name":"pkg.codes.check_code","call":"check_code(\"abc\")","expect":{"raises":"ValueError"}}]' > "$T/c2.json"
CD --check "$T/c2.json" > "$T/k2" 2>&1 || fail "--check exited non-zero: $(cat "$T/k2")"
grep -q '\[negative' "$T/k2" && fail "a raises claim did not clear the negative line: $(cat "$T/k2")"
grep -q '^claims_draft --check: ' "$T/k2" || fail "no final count: $(cat "$T/k2")"
CD --check "$T/c2.json" --changed src/pkg/codes.py:save_code > "$T/k3" 2>&1 || fail "--check with --changed exited non-zero"
grep -q '^uncovered pkg.codes.save_code \[sink, T6\]' "$T/k3" || fail "--changed function not checked: $(cat "$T/k3")"
echo "PLANT claims_draft: PASS"
