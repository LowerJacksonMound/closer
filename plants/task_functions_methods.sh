#!/bin/sh
# Plant: task_functions (ui/go.py) names the functions a task requires. A method on a value, `last_name.lower()`,
# is not one; `frontdesk.lookup_reservation(` and bare `lookup_reservation(` are.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { echo "PLANT task_functions_methods: FAIL $*" >&2; exit 1; }
python3 - "$HERE" <<'PY' || fail
import sys; sys.path.insert(0, sys.argv[1] + "/ui"); import go
task = ("Add functions to `frontdesk.py`.\n- `lookup_reservation(last_name)` returns the entry whose key is `last_name.lower()`.\n"
        "- `frontdesk.hand_keys(412)` is a string; `msg.strip()` is ignored; `ValueError(...)` is not a function.")
assert go.task_functions(task) == ["lookup_reservation", "hand_keys"], go.task_functions(task)
PY
echo "PLANT task_functions_methods: PASS"
