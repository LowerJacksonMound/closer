#!/bin/sh
# Plant: the repo's own interpreter (pack v29, INGREDIENTS 6b). `gc init --python` names a venv's bin/python (a second
# path, a symlink, to the same Python) in the manifest. The repo's code imports a marker module installed only in that
# venv and reports sys.prefix, so E1's tests, C1's claims and U1's runs can only pass under it: an honest ticket lands,
# C1's claims hold, U1 compares every input, and `gc verify` runs E1 under it too. init refuses a relative or
# non-executable --python. A manifest without `python` behaves as before, even with REPO_PYTHON inherited from the
# caller: the checks run on gc's own python (the marker does not import).
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT repo_python: FAIL $*" >&2; exit 1; }
V="$T/venv"
python3 -m venv --without-pip --system-site-packages "$V" >/dev/null 2>&1 || fail "venv"
[ -L "$V/bin/python" ] || fail "venv python is not a second path (symlink) to the same Python"
SP="$("$V/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')" || fail "venv purelib"
printf 'WHERE = "venv"\n' > "$SP/gc_repo_python_marker.py"
python3 -c 'import gc_repo_python_marker' 2>/dev/null && fail "marker importable by gc's python3"

# --- case 1: the manifest names the venv's python ---------------------------------------------------------------
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R/tests"
echo notes > "$R/README.txt"
cat > "$R/app.py" <<'EOF'
import sys

import gc_repo_python_marker


def where():
    return gc_repo_python_marker.WHERE + ":" + sys.prefix
EOF
cat > "$R/tests/test_app.py" <<EOF
import os
import sys

from app import where


def test_where():
    assert sys.executable.startswith("$V/"), sys.executable
    assert where() == "venv:$V"
    assert os.environ.get("REPO_PYTHON") == "$V/bin/python"
EOF
gc init --python bin/python >/dev/null 2>"$T/err" && fail "init took a relative --python"
grep -q "absolute" "$T/err" || fail "relative --python refusal unclear: $(cat "$T/err")"
gc init --python "$SP/gc_repo_python_marker.py" >/dev/null 2>"$T/err" && fail "init took a non-executable --python"
grep -q "not an executable" "$T/err" || fail "non-executable --python refusal unclear: $(cat "$T/err")"
[ -e "$ST/manifest.json" ] && fail "a refused init wrote a manifest"
gc init --python "$V/bin/python" >/dev/null 2>&1 || fail "init --python"
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); assert m["python"] == sys.argv[2], m' \
  "$ST/manifest.json" "$V/bin/python" || fail "manifest python: $(cat "$ST/manifest.json")"
gc scan >/dev/null 2>&1 || fail "scan"
CL="$T/claims.json"; printf '%s' "[{\"name\":\"app.where\",\"call\":\"where()\",\"expect\":{\"result\":\"venv:$V\"}},
 {\"name\":\"app.where\",\"call\":\"where().startswith('venv:')\",\"expect\":{\"result\":true}}]" > "$CL"
gc ticket --write app.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint"
mkdir -p "$ST/payload/T1"
cat > "$ST/payload/T1/app.py" <<'EOF'
import sys

import gc_repo_python_marker


def where():
    tag = gc_repo_python_marker.WHERE
    return f"{tag}:{sys.prefix}"
EOF
gc land --ticket T1 > "$T/land" 2>&1 || fail "honest ticket did not land: $(tail -6 "$T/land")"
grep -q "^E1 pass" "$T/land" || fail "E1 did not pass: $(grep E1 "$T/land")"
grep -q "^C1 pass: 2 claim(s) held on 1 function(s)" "$T/land" || fail "C1 pass line wrong: $(grep C1 "$T/land")"
python3 - "$ST/ledger.jsonl" > "$T/u1" <<'PY' || fail "no ledger row"
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
c = [c for c in r.get("checks", []) if c["name"] == "U1"]
print("\n".join(c[0]["said"]) if c else "NO U1"); print("DECISION", r.get("decision"))
PY
grep -q "^DECISION proceed$" "$T/u1" || fail "did not proceed: $(cat "$T/u1")"
grep -q "^U1 pass: 1 changed function(s), .* 0 difference(s), 0 undeclared$" "$T/u1" || fail "U1: $(cat "$T/u1")"
EVF="$(ls "$ST/evidence/T1".*.json 2>/dev/null | tail -1)"
python3 - "$EVF" <<'PY' || fail "U1 did not run under the venv: $(cat "$EVF" 2>/dev/null)"
import json, sys
s = [e["summary"] for e in json.load(open(sys.argv[1]))["checks"]["U1"] if "summary" in e]
assert len(s) == 1 and not s[0]["partial"], s
assert s[0]["changed"] == [["app.py", "where", 6]], s
assert s[0]["inputs"] >= 1 and s[0]["compared"] == s[0]["inputs"], s  # where() imports only under the venv
assert (s[0]["differences"], s[0]["unstable"]) == (0, 0), s
PY
gc ticket --write app.py --id T2 --verify E1 --claims "$CL" >/dev/null 2>&1 || fail "mint T2"
gc verify --ticket T2 > "$T/verify" 2>&1 || fail "gc verify E1 under the venv: $(tail -4 "$T/verify")"

# --- case 2: no `python` in the manifest: as before, and an inherited REPO_PYTHON is not used ---------------------
R="$T/repo2"; ST="$T/state2"
mkdir -p "$R/tests"
echo notes > "$R/README.txt"
printf 'def add(a, b):\n    return a + b\n' > "$R/calc.py"
cat > "$R/tests/test_calc.py" <<'EOF'
import importlib.util
import os

from calc import add


def test_add():
    assert add(2, 3) == 5
    assert os.environ.get("REPO_PYTHON") is None
    assert importlib.util.find_spec("gc_repo_python_marker") is None
EOF
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "init/scan without --python"
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); assert "python" not in m, m' "$ST/manifest.json" \
  || fail "manifest has python without --python"
printf '%s' '[{"name":"calc.add","call":"add(2, 3)","expect":{"result":5}},
 {"name":"calc.add","call":"__import__(\"importlib.util\").util.find_spec(\"gc_repo_python_marker\") is None","expect":{"result":true}}]' > "$T/cl2"
gc ticket --write calc.py --id T1 --claims "$T/cl2" >/dev/null 2>&1 || fail "mint (no python)"
mkdir -p "$ST/payload/T1"
printf 'def add(a, b):\n    s = a + b\n    return s\n' > "$ST/payload/T1/calc.py"
REPO_PYTHON="$V/bin/python" gc land --ticket T1 > "$T/land2" 2>&1 \
  || fail "no-python ticket did not land (inherited REPO_PYTHON used?): $(tail -6 "$T/land2")"
grep -q "^E1 pass" "$T/land2" || fail "E1 (no python): $(grep E1 "$T/land2")"
grep -q "^C1 pass: 2 claim(s) held on 1 function(s)" "$T/land2" || fail "C1 (no python): $(grep C1 "$T/land2")"
echo "PLANT repo_python: PASS"
