#!/bin/sh
# Plant: well_formed (ui/go.py) is a fixed rule on the claim agent's output. A claim whose call is a lambda or a
# generator, or does not parse, is dropped and said; a plain call and a bare name (the `msg` binding) are kept.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { echo "PLANT claims_well_formed: FAIL $*" >&2; exit 1; }
python3 - "$HERE" <<'PY' || fail
import sys; sys.path.insert(0, sys.argv[1] + "/ui"); import go
go.say = lambda *a, **k: None
claims = [{"name": "m.f", "call": "(lambda: (lambda f: f())(lambda: None))()", "expect": {"true": "True"}},
          {"name": "m.f", "call": "(x for x in ())", "expect": {"true": "True"}},
          {"name": "m.f", "call": "f(1,", "expect": {"true": "True"}},
          {"name": "m.f", "call": "msg", "expect": {"true": "'x' in result"}},
          {"name": "m.f", "call": "f('a', 1)", "expect": {"true": "True"}}]
assert [c["call"] for c in go.well_formed(claims)] == ["msg", "f('a', 1)"]
# a claim that names its module but never imports it is bound, not dropped
c = go.well_formed([{"name": "booking.fxnA_dial", "setup": ["msg = ''", "try:\n    booking.fxnA_dial('')\nexcept ValueError as e:\n    msg = str(e)"], "call": "msg", "expect": {"true": "True"}}])[0]
assert c["setup"][0] == "import booking", c
c = go.well_formed([{"name": "booking.fxnA_dial", "setup": [], "call": "fxnA_dial('x')", "expect": {"true": "True"}}])[0]
assert c["setup"] == ["from booking import fxnA_dial"], c
c = go.well_formed([{"name": "booking.fxnA_dial", "setup": ["import booking"], "call": "booking.fxnA_dial('x')", "expect": {"true": "True"}}])[0]
assert c["setup"] == ["import booking"], c
PY
echo "PLANT claims_well_formed: PASS"
