# Pack v33 (proposal, 2026-10-19; signer's word "let's add it" the same evening)

**One fix to E1, in the one file.** When pytest exits red but its short summary never printed, E1 names no test. That
happened on both cookiecutter bugs in CLOSER_PROVING set2 (`full_v32-set2/cookiecutter/2` and `/3`, honest lands): pytest
exited 3 with `28 failed, 217 passed, ... 40 errors` and v32's E1 said `run_fail (pytest exit 3: <summary line>)`, so
the set2 deselect list (the v30 mechanism for known-red base tests) had no names to carry, and the two upstream fixes
stayed struck for an environment reason. Reproduced outside the gate: a conftest whose `pytest_sessionfinish` raises
prints every per-test result and then dies before the `-rfE` summary (pytest 9: exit 1; the py38 pytest: exit 3).

| | v32 | v33 |
|---|---|---|
| summary printed | names from `FAILED/ERROR <nodeid>` lines (unchanged) | unchanged |
| summary not printed, pytest red | `run_fail (pytest exit N: <last line>)`, no name | rerun once with `-v`, names from the `<nodeid> FAILED/ERROR` result lines (own / before-ticket as before), plus one line `run_fail (pytest exit N; summary not printed: <INTERNALERROR or Traceback line>)` |
| red with no failing test (the harness itself broken) | `(pytest exit N, no test named)` | the same, plus the internal-error line; still a reject (unjudged is reject) |

No decision changes: everything red stays red. What changes is that the signer sees which tests, so an environment
strike can be told from a real one and a deselect list can name them.

| File | What |
|---|---|
| `proposals/v33/E1.sh` | the full proposed E1 (header says Live in pack v33) |
| `proposals/v33/plants/e1_summary_lost_names_test.sh` | case 1: broken existing test under a dying conftest is named `(before-ticket)`, strike, rollback; case 2: honest ticket under the same conftest is still a reject with the internal error said, no passing test named |

## To go live (K5 steps 3 and 4)

1. Copy `proposals/v33/E1.sh` to `pack/live/E1.sh`. 2. `pack/live/PACK.json`: `pack_version` 33; lists unchanged.
3. Copy the plant to `plants/`. 4. PACK.md: version 33, E1 row "last set in v33" with the one line above; README Status: v33
line. 5. `kernel_sha256` unchanged (E1.sh is pack, not kernel); `pack_sha256` changes. 6. `gc selftest` (45 plants).
7. T3: a bump reruns the set. The rerun is a budget checkpoint (T14): meter first.
