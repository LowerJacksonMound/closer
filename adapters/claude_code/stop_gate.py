#!/usr/bin/env python3
"""Claude Code Stop hook for a getting-close writer session. Stdlib only.

usage (from settings): python3 stop_gate.py <state_dir>

Stop is not success: the session may end only when `gc-writer check` (every live verify
against the latest World) exits 0. Crash or timeout of the check blocks (exit 2).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import NoReturn

# Must stay under the Stop hook's own timeout in gc's writer settings (180 s). If that one fires first,
# the hook is cut off before it can return exit 2, and nothing holds the stop.
CHECK_SECONDS = 120


def block(reason: str) -> NoReturn:
    print(f"getting-close: {reason}", file=sys.stderr)
    raise SystemExit(2)


def main() -> None:
    try:
        if len(sys.argv) != 2:
            block("stop hook misconfigured: expected <state_dir>")
        state = os.path.realpath(sys.argv[1])
        wrapper = os.path.join(state, "gc-writer")
        if not os.access(wrapper, os.X_OK):
            block(f"stop hook misconfigured: no {wrapper}")
        json.loads(sys.stdin.read() or "{}")  # input must at least be JSON
        r = subprocess.run([wrapper, "check"], capture_output=True, text=True, timeout=CHECK_SECONDS)
        if r.returncode != 0:
            tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
            block(f"live check failed; not done.\n{tail}")
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 — fail closed on anything
        block(f"stop hook error ({type(e).__name__}); not done")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
