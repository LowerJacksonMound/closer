# Pack v32 (proposal, 2026-10-19; amended the same day, signer's ruling: U1's own error is exit 75, folded in, one bump; part 2 the same day: T16 built, see "Part 2" below, which amends part 1's fix-2 outcome, its plant, step 4 and step 5)

**Proposal. Nothing is live.** Nothing under `pack/live/`, `bin/`, `plants/` or the law docs is edited; the proposed
file is in `proposals/v32/`, the plants in `proposals/v32/plants/`.

Two fixes to U1, in the one file, so an honest ticket on a large module is not struck by U1 dying before it judges
anything, and no failure of U1's own can strike a ticket at all:

| # | What was wrong (v31) | v32 |
|---|---|---|
| 1 | `run_driver()` hands each driver process its spec (root, watch, want, cap, deadline, out, pytest_args) as the environment variable `U1_SPEC`. On the "after" drive `want` is every input recorded on the before-tree, strings whole (C1's `norm` does not truncate). On a ticket touching a large module the JSON exceeds the OS argv+environment limit (macOS `ARG_MAX` 1 MiB), `subprocess.Popen` raises `OSError: [Errno 7] Argument list too long`, and the honest ticket is rejected after E1 and C1 passed | the spec is written to a JSON file beside the records file under U1's own temp dir (K2) and the environment carries only its path, `U1_SPEC_FILE`; the recorder reads the file |
| 2 | an exception `main()` does not handle (the Errno 7 above, or any other of U1's own) escapes, python prints a traceback and exits 1, and gc takes 1 from an every-ticket check as a strike. U1 is evidence only; KERNEL's exit-code row 75 reads "the check's own error. No strike." | `__main__` wraps `main()`: any `Exception` prints one line `U1 not run: <type>: <message>` to stderr and exits 75. gc then rejects the land as unjudged (`U1 not run (exit 75): no strike`), rolls back, and the ticket is not struck |

| File | What |
|---|---|
| `proposals/v32/U1.py` | the full proposed U1 |
| `proposals/v32/plants/u1_large_spec.sh` | plant for fix 1: the honest large-module ticket lands |
| `proposals/v32/plants/u1_own_error_not_run.sh` | plant for fix 2: a forced internal error is exit 75, no strike; plus a one-line README |

## Evidence of the miss

`~/Desktop/CLOSER_PROVING/runs/20261019T090924/familyguy_episodes/task-01/honest/land.log` (read, not touched):

```
E1 pass: 303 test(s) passed on the patched tree
C1 pass: 13 claim(s) held on 5 function(s)
Traceback (most recent call last):
  File ".../pack/live/U1.py", line 431, in <module>  sys.exit(main())
  File ".../pack/live/U1.py", line 387, in main      arec, askip, runner, apart = drive(root, tmp, "after", watch, want, ...)
  File ".../pack/live/U1.py", line 290, in drive     rec, _, cut = run_driver(PYTEST_DRIVER, [], tree, {**base, "pytest_args": pt}, ...)
  File ".../pack/live/U1.py", line 259, in run_driver  p = subprocess.Popen([...], cwd=cwd, env=env, ...)
OSError: [Errno 7] Argument list too long: '/opt/homebrew/Caskroom/miniconda/base/bin/python3'
{"decision": "reject", "ticket_id": "familyguy_episodes-task-01-honest", "reasons": ["U1 exit 1", "rolled back", "strike: ticket closed (M2)"], "ledger_seq": 1}
```

The before drive had already run (its `want` is `null`, a small spec); the "after" drive is the one that carries every
recorded input. tower_defense task-09 (196 inputs) was under the limit and ran; `screens.py` was not. `getconf ARG_MAX`
on this host: 1048576, argv and environment together (the driver code itself is in argv: 8 KB for the pytest driver,
15 KB for the claim driver). C1 passes its spec on stdin and has no such limit.

## The change

`diff pack/live/U1.py proposals/v32/U1.py` is the header, three comment/docstring passages, and these lines of logic:

```
fix 1
v31 (recorder, in RECORDER):  _U1 = _u1_json.loads(_u1_os.environ["U1_SPEC"])
v32:                          with open(_u1_os.environ["U1_SPEC_FILE"], encoding="utf-8") as _u1_fh:
                                  _U1 = _u1_json.load(_u1_fh)

v31 (run_driver):  env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "U1_SPEC": json.dumps({**u1spec, "out": out})}
                   left = deadline - time.time()
                   if left <= 0: return {}, "", True
v32:               left = deadline - time.time()
                   if left <= 0: return {}, "", True
                   spec_file = os.path.splitext(out)[0] + ".spec.json"
                   Path(spec_file).write_text(json.dumps({**u1spec, "out": out}), encoding="utf-8")
                   env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "U1_SPEC_FILE": spec_file}

fix 2
v31:  if __name__ == "__main__":
          sys.exit(main())
v32:  if __name__ == "__main__":
          try:
              rc = main()
          except Exception as e:  # U1's own error: not run (75), never a strike; evidence that was printed stands as printed
              print(f"U1 not run: {type(e).__name__}: {str(e)[:300]}", file=sys.stderr)
              rc = 75
          sys.exit(rc)
```

Fix 1: `out` is always `<U1 temp dir>/tests-<tag>.json` or `<U1 temp dir>/claim<i>-<tag>.json`, so the spec file is
`tests-before.spec.json`, `claim3-after.spec.json` and so on, in the same `tempfile.mkdtemp(prefix="u1-")` directory the
records already go to, removed by the same `C1._rm_tree(tmp)` in `main()`'s `finally`. The same JSON is written as was
put in the environment; the recorder gets the same dict. Same records, same `U1 evidence:` lines, same `U1 pass:`
counts, same clocks.

**File, not stdin.** The brief allowed either. The claim driver already takes C1's RUNNER spec on stdin
(`spec = json.loads(sys.stdin.read())`, C1.RUNNER unchanged inside CLAIM_DRIVER), so stdin would mean framing two
documents on one pipe or rewriting the RUNNER's read; the pytest driver's stdin is DEVNULL. One file per driver keeps
both drivers the same and the RUNNER untouched.

Fix 2: `Exception`, not `BaseException`: `SystemExit` (main()'s own returns go through `sys.exit(rc)` after the
`try`) and `KeyboardInterrupt` are the host's, not U1's. The 75 path is reachable only by U1's own code failing: every
host condition U1 already names (`SCOPED_ROOT`, `BEFORE_ROOT`, pytest importable, `REPO_PYTEST_ARGS` shell words) still
returns 75 from `main()` with its own `U1 not run:` line; the wrap adds nothing to those. The two module-level loads
(`C1.py` by `importlib`, `_runner_source` building RECORDER) run before `__main__` and are outside the wrap; they can
only fail when `pack/live/` itself is broken, which is the kernel's fault, not a ticket's. Evidence lines main() printed
before the exception have already gone to stdout and are filed as printed.

The header now reads "Proposed for pack v32 (2026-10-19: ...)" and lists every change back to v28, as v31's E1 header
does (the live U1 header still reads "Proposed for pack v30"; go-live copies the file as is and changes "Proposed" to
"Live").

**K-rules.** K2: the spec file is under U1's temp dir, the one place U1 already writes; the verify sandbox allows it
(temp dirs are writable; the records file has lived there since v28). K5: this proposal. K6: stdlib only, no new import
(`Path` and `os` are already imported). K8: unchanged. T4/T5: no change in what is judged. **One verdict changes, by
correction**: an honest ticket whose before-tree records exceed the environment limit, which v31 rejected with a strike
(`U1 exit 1`) before comparing anything, is judged under v32 like any other. **One outcome changes in kind**: a land in
which U1's own code fails was a reject with a strike (M2: ticket closed); under v32 it is a reject without a strike
(`not_run: ["U1"]` in the row), the ticket stays open and can be landed again once the host is fixed, which is what gc
already does when E1 or C1 exit 75. Every other land is byte-for-byte the same evidence and the same verdict.

## Plants

Both the shape of `u1_clean.sh`: a temp repo, `gc --repo --state` into the temp dir, land through the real kernel, read
the ledger row (and the evidence file), print `PLANT <name>: PASS`. Both use the same honest ticket: `app.py` with
`def f(s): return len(s)` rewritten to `if not s: return 0` then `return len(s)` (same outcome on every input), claims
on `app.f`.

**`u1_large_spec`** (fix 1): the repo test calls `f` with N = 50 distinct strings (U1's default cap, `U1_INPUTS`: the
first 50 distinct inputs per function are recorded, so the cap does not bound this away; the strings are built in the
test, not stored) of L = `ARG_MAX / 40` characters each (26214 here), so the before-tree records come to N x L =
1.25 x ARG_MAX before the JSON framing. The plant checks that premise (`N * L > ARG_MAX`) and FAILs if a host's limit
makes it false.

| Checks | On v31 |
|---|---|
| the land succeeds; no `Traceback` and no `Argument list too long` anywhere in the land output; no `u1-*` or `c1-before-*` temp tree left behind | `PLANT u1_large_spec: FAIL honest ticket rejected: U1 died with OSError: [Errno 7] Argument list too long: '/opt/homebrew/Caskroom/miniconda/base/bin/python3'; {"decision": "reject", "ticket_id": "T1", "reasons": ["U1 exit 1", "rolled back", "strike: ticket closed (M2)"], "ledger_seq": 1}` |
| the row: decision proceed, no strike, U1 exit 0, `U1 pass: 1 changed function(s), <n> input(s) recorded, <n> compared, 0 difference(s), 0 undeclared`, not partial | (not reached) |
| the evidence file: one summary, `changed == [["app.py", "f", 1]]`, differences, undeclared, unstable, unmatched all 0, `inputs >= 50` and `compared == inputs`, no difference entries | (not reached) |

**`u1_own_error_not_run`** (fix 2): the same ticket landed with `U1_INPUTS=notanumber` in the environment for that
one `gc land` (verify_ticket copies the caller's environment to the checks; `int(os.environ.get("U1_INPUTS", "50"))`
raises `ValueError` in `main()` before any drive). A forced internal error, cheap and deterministic.

| Checks | On v31 |
|---|---|
| `gc land` exits 1 (an unjudged land is a reject); no `Traceback` in the land output; exactly one line `U1 not run: ValueError: ...`; the row: U1 exit 75, decision reject, no strike, `not_run` lists U1, a reason `U1 not run (exit 75): no strike`; E1 and C1 passed; repo rolled back; no temp tree left | `PLANT u1_own_error_not_run: FAIL U1 crashed with a traceback instead of 'not run': U1EXIT 1 ; ValueError: invalid literal for int() with base 10: 'notanumber'`; the row (read in a scratch copy of the plant): `U1EXIT 1`, `STRIKE`, `DECISION reject`, `not_run` empty, reasons `U1 exit 1 | rolled back | strike: ticket closed (M2)`, and the land output carries the full traceback ending at `cap = int(os.environ.get("U1_INPUTS", "50"))` |

## Proof

Two scratch copies of this tree (spec folder, `proposals/`, `__pycache__` and `.DS_Store` left out), never the real
tree, never a real state dir, under the session scratchpad (`.../scratchpad/v32/tree_v31`, `.../tree_v32`), 2026-10-19:

- v31 copy (`pack/live/U1.py` byte-identical to the live one by `diff`, `PACK.json` at 31, both plants in `plants/`):
  both plants FAIL as in the tables above, each in about 2 s: `u1_large_spec` with the OSError and the strike,
  `u1_own_error_not_run` with the ValueError traceback, `U1EXIT 1`, `STRIKE`.
- v32 copy (`proposals/v32/U1.py` as `pack/live/U1.py`, `PACK.json` at 32, both plants in `plants/`): both PASS in about
  2 s each. `u1_large_spec`'s row: `U1 pass: 1 changed function(s), 52 input(s) recorded, 52 compared, 0 difference(s), 0 undeclared` (50 from the test, 2 from the claims), `U1EXIT 0`, `NOSTRIKE`, `DECISION proceed`. `u1_own_error_not_run`'s row: stderr `U1 not run: ValueError: invalid literal for int() with base 10: 'notanumber'` (one line, no traceback), `U1EXIT 75`, `NOSTRIKE`, `DECISION reject`, `NOTRUN U1`, reasons `U1 not run (exit 75): no strike | rolled back`.
  `plants/run_all.sh`: 41 plants PASS, `plants: PASS`, 0 FAIL lines (39 live plus `u1_large_spec` and `u1_own_error_not_run`), 2:00 in all; `c1_py38_qualname` and `e1_pytest3_names_test` ran on the set2 venvs. Logs in the scratch directory, not here. (The run before fix 2 was folded in, with
  `u1_large_spec` alone: 40 plants PASS, `plants: PASS`, 1:57.)

## To go live (K5 steps 3 and 4, on signer yes)

1. Copy `proposals/v32/U1.py` to `pack/live/U1.py` as is. Change "Proposed for pack v32" on line 2 to "Live in pack
   v32"; the rest of the header (the list of every change) stays.
2. `pack/live/PACK.json`: `pack_version` 32. The lists do not change.
3. Copy `proposals/v32/plants/u1_large_spec.sh` and `proposals/v32/plants/u1_own_error_not_run.sh` to `plants/`.
4. PACK.md: live pack version 32; row U1 "last set in v32", add "the driver's spec in a file under U1's temp dir
   (`U1_SPEC_FILE`), not the environment; U1's own error is `U1 not run: ...`, exit 75, no strike". History line: v32
   (2026-10-19), the two fixes, plants `u1_large_spec` and `u1_own_error_not_run`, 41 plants pass. README `Status`: a
   v32 line, "Pack v32 is the live pack". KERNEL.md exit-code row 75 already reads "or the check's own error"; nothing to
   change there.
5. Hashes (bin/ledger.py): `kernel_sha256` does not change (`KERNEL_FILES` is `bin/*`, the adapters and `scanner/`;
   U1.py is none of them; live `d468b580e7ec9da870d7e82c41f957929a9559d88e9532d149b2c8d33c4bedaa`, recomputed today).
   `pack_sha256` is `tree_hash` over every file in `pack/live/`, so it changes: live
   `0abf96e200efd9aa94deced2fc27f1cedb57013ebe920a138ad52df7c74c5678` (v31's stated value, recomputed today); with the
   proposed U1 headed "Live in pack v32" (line 2 only changed) and PACK.json at 32 it is
   `e05f2d316a52e43f5c0f7ebac8aea79aa47ea4d722d786017740f6e5356a4ec6` (recompute after step 1 if the header is worded
   differently). Rows from then on carry the new value.
6. `gc selftest`. A version bump rejects every outstanding ticket.

T2/T3: v32 is a new frozen pack; CLOSER_PROVING results on v31 do not carry over. The 20261019T090924 run's
familyguy_episodes task-01 honest reject is this miss; its note closes with this.

## For the signer

- **One verdict changes, by correction**: honest tickets on modules whose recorded inputs overflow the environment
  (familyguy_episodes `screens.py` in the proving set) are judged under v32; v31 struck them without comparing.
- **One outcome changes in kind** (the ruling, fix 2): U1's own failure is a reject without a strike, as E1's and C1's
  75 already are; the ticket stays open. Before, it closed the ticket (M2) and counted toward `gets_through_anyway` (M3).
- **File over stdin**: chosen because the claim driver's stdin already carries C1's RUNNER spec; a file keeps both
  drivers alike and the RUNNER untouched. If the signer would rather stdin, it is the same two places plus a framing
  of the claim driver's pipe.
- **`Exception`, not `BaseException`**, in the wrap (above); and the two module-level loads stay outside it. Widening
  either is a one-word change if the signer wants a broken `pack/live/` to read as 75 too.
- **The plants need no venv**; `u1_large_spec` needs only `getconf ARG_MAX` and builds longer strings on a host with a
  larger limit (L = ARG_MAX/40) rather than failing its premise. The two set2-venv plants (`c1_py38_qualname`,
  `e1_pytest3_names_test`) are unchanged and ran in the proof.
- Nothing in this proposal needed more than the brief allowed; no item is left undone.


---

# Part 2 (2026-10-19): build ruling T16, let through what the gate cannot judge

**Proposal. Nothing is live.** The proposed files are `proposals/v32/C1.py`, `proposals/v32/gc.patch` (one unified diff:
`bin/gc` and `bin/governor.py`), `proposals/v32/dash.patch` (`bin/dash.py`, not kernel), three plants under
`proposals/v32/plants/` plus part 1's `u1_own_error_not_run.sh` amended, and this section. Nothing under `pack/live/`,
`bin/`, `plants/`, PACK.json or the law docs is edited (K5). Part 1 (U1) stands as written except where this part says it
amends it. `kernel_sha256` changes (bin/gc, bin/governor.py).

## The ruling (KERNEL.md T16, verbatim)

> Let through what the gate cannot judge. The gate strikes only on a verdict it reached: a claim that failed, a test that
> failed, a shape it found, an introduced function no claim reached. Whatever it could not bring to a verdict, for any
> reason (a check not run or crashed, exit 75; a claim that could not be set up, imported, or finished within its clock or
> line budget; a species it has no name for), is let through: the land proceeds, the ledger row and the signer's page
> record what was not judged, and Code Radar catches it on the backend (T6). Supersedes the 2026-10-15 decision that C1
> `cannot_judge` is a reject, and the refusal of a land on a not-run check. Built in pack v32 with a gc land change
> (kernel_sha256 changes).

## What was wrong (v31) and what changes

| # | Where | v31 | v32 |
|---|---|---|---|
| 1 | `bin/gc` cmd_land, an every-ticket or World check exits 75 | `decision` flips to REJECT with reason `<name> not run (exit 75): no strike`; rolled back; land exit 1; the ticket is not struck but cannot land until the host is fixed | the decision does not change: the land proceeds if nothing struck; the check goes in the row's `not_run` (the list already existed) and the row's `reasons` carries `<name> not run (exit 75): no strike, not judged (T16)`. A later strike keeps those reasons beside its own. `not_run` now lists every check that exited 75 in the land, World checks included (before: `every_ticket` names only), so the row says everything that was not judged |
| 2 | `bin/gc` + `bin/governor.py`, the ticket's own `verify` exits 75 | `governor.decide(facts, 75)` -> REJECT `verify exit 75`; no further check runs | `decide` returns PROCEED with the reason `verify not run (exit 75): no strike, not judged (T16)` (new constant `governor.NOT_RUN = 75`); gc adds the verify's name to `not_run` (any list, not only `every_ticket`) and runs the other checks as on a 0 |
| 3 | `bin/gc` cmd_land, no `sandbox-exec` on the host | verify_ticket.py:134 dies 75 -> `verify exit 75` -> reject, rolled back | **the one 75 kept as a refusal**: before apply, `shutil.which("sandbox-exec")` empty -> REJECT, reason `no sandbox-exec on this host: nothing can be held read-only (K2); land refused, no strike`. Nothing is applied, no rollback needed, no strike. verify_ticket.py's own die stays (plant `sandbox_write_refused` tests it directly). Without this gc would, under T16, let every ticket through unjudged on a host that cannot sandbox |
| 4 | `pack/live/C1.py`, a claim that cannot be judged (`cannot_judge`: import_error, setup_error, runner_error, predicate raised, out of time, out of line budget) | `C1 fail: introduced <file>:<line> cannot_judge <qualname>` on stderr, exit 1, a strike | `C1 unjudged: <file>:<line> cannot_judge <qualname> (<reason>)` on stdout (one per (file, rule, name), as fail lines are deduplicated), no fail line, exit 0 when every judged claim held and nothing is unreached. The evidence entry is filed as before with `rule: cannot_judge`; the `reach` evidence entry gains `unjudged: [claim indices]`; each `coverage` entry gains `unjudged: n` (unjudged claims that named the function or traced into it). `before_summary.not_run` already counts them (a claim that did not hold after is not rerun). The pass line appends `, N not judged` only when N > 0, so a land with nothing unjudged prints exactly v30's line |
| 5 | `pack/live/C1.py`, the reach rule | reach = the union of every claim's trace | reach = the union of **judged** claims' traces (held or failed). What an unjudged claim traced before it stopped is not reach, so a function only an unjudged claim would have reached is `unreached`, a strike, unless another claim reached it. `partial` for "the required name is not there" stays a verdict and a strike. Stated in the docstring |
| 6 | `bin/gc` cmd_land, the row | `not_run` only | `run_check` also returns the check's `<name> unjudged: ...` lines (`UNJUDGED_RE`), every one, not capped with `said`; the row gains `unjudged: [lines]` when any. The lines stay in `said` and reach the writer's stdout as a fail line would |
| 7 | `bin/dash.py` (not kernel) | a proceed is `landed clean` | `not_judged(row)` reads `not_run` and `unjudged`; `outcome()` shows `landed, not judged: E1, U1 not run; 1 unjudged claim(s)` (amber) instead of `landed clean`; `checks_table()` prints `75 not run` in the exit column, adds `not judged (T16, let through): ...` to the meta line and lists the unjudged lines under the table; the state view's row summary carries `not judged: ...`; the proving-run view gains a tile `honest landed, not judged (T16)` counted from each honest `row.json` |

Unchanged, as the brief rules: syntax errors (refused before apply, no strike), World-not-latest (reroute) and a struck
ticket's preflight (M2) are verdicts or reroutes, not "could not judge". `unreached` stays a strike. E1 `run_fail`, S1
findings, G18 stay strikes. E1, S1, G18, U1, W1, R6-* and R10-* are not edited; only how gc reads their 75 changes.

`diff pack/live/C1.py proposals/v32/C1.py`: the header (line 2), four docstring passages (rules, the reach rule, exit
codes, evidence) and these lines of logic in `main()`:

```
v31:  reached = {tuple(x) for _, _, r in runs for x in (r.get("reached") or [])}
v32:  unjudged_idx = {i for i, c, r, rule, obs in verdicts if rule == "cannot_judge"}
      judged_runs = [(i, c, r) for i, c, r in runs if i not in unjudged_idx]
      reached = {tuple(x) for _, _, r in judged_runs for x in (r.get("reached") or [])}

v31:  fails.append(f"C1 fail: introduced {file}:{line} {rule} {name}")             # every rule
v32:  if rule == "cannot_judge": unjudged.append(f"C1 unjudged: {where} cannot_judge {name} ({obs})")
      else:                      fails.append(f"C1 fail: introduced {where} {rule} {name}")

v32:  reach evidence: + "unjudged": sorted(unjudged_idx)
      coverage(introduced, judged_runs); each entry + "unjudged": <unjudged claims naming or tracing into it>
      for u in unjudged: print(u)                       # stdout, before the fail lines / pass line
      names from judged_runs; pass line + f", {len(unjudged_idx)} not judged" when any
```

`judge()`, `run_claim()`, the RUNNER, `answer_table`, `before_findings()` and the T5 refusals (no claims file, claims
sha mismatch: `C1 fail:`, exit 1) are unchanged. K2, K6, K8: unchanged (stdlib only; a line still names file, line,
rule, qualname).

## Plants

Format of `plants/c1_*.sh` and `gets_through_anyway.sh`: a temp repo, `gc --repo --state` into the temp dir, land through
the real kernel, read the last ledger row, `PLANT <name>: PASS`.

| Plant | What | v31 | v32 |
|---|---|---|---|
| `gc_not_run_proceeds` | `gc init --python` names a venv made with `--without-pip` (no site packages: pytest not importable by it; the plant fails on the premise if it is). Honest ticket on `app.f`, two claims. E1 exits 75 (`E1 not run: pytest is not importable by <venv>/bin/python`), so does U1 (its drivers need pytest); S1, G18, C1 run and pass. Checks: land exit 0, `decision proceed`, no strike, `not_run` has E1 (and U1), reasons carry `E1 not run (exit 75): no strike, not judged (T16)`, the patch stays applied. Guard: a second ticket landed with `PATH` = a dir holding only `python3` (gc needs it) -> no sandbox-exec -> exit 1, `decision reject`, no strike, the refusal names sandbox-exec, nothing applied | FAIL: `the land with a not-run check did not proceed (exit 1): NOSTRIKE DECISION reject NOTRUN E1 U1 REASONS E1 not run (exit 75): no strike \| U1 not run (exit 75): no strike \| rolled back` | PASS (1.4 s) |
| `c1_cannot_judge_proceeds` | replaces `plants/c1_cannot_judge.sh`. T1 (kept from it): a required name never implemented is `partial`, a verdict, still a strike. T2: an honest ticket changes `f`; claim 1 holds, claim 2's setup raises NameError: `C1 unjudged: app.py:1 cannot_judge app.f (setup_error: NameError: ...)` on stdout and in `said`, no `C1 fail:` line, `C1 pass: 1 claim(s) held on 1 function(s), 1 not judged`, C1 exit 0, land exit 0, proceed, no strike, the row's `unjudged` has that one line; evidence: claim 2 `rule: cannot_judge`, `reach.unjudged == [2]`, `reach.unreached == []`, coverage for `f` `claims 1, unjudged 1`, `before_summary.not_run == 1`. T3: `C1_SECONDS=3`, a setup that sleeps 30 s: `C1 unjudged: ?:0 cannot_judge app.f (out of time)` (a timed-out runner reports no file or line, as the v31 fail line did), proceed, no strike | FAIL at T2: `C1 fail: introduced app.py:1 cannot_judge app.f`, `C1EXIT 1`, `STRIKE`, `DECISION reject` | PASS (14 s, the 3 s clock plus two U1 drives per land) |
| `c1_unjudged_unreached_strikes` | the guard that T16 did not widen the reach rule. The ticket adds `g`; the only claim on `g` cannot be set up. T1: the setup raises before anything is called: `C1 fail: introduced app.py:5 unreached app.g`, strike, reject, rolled back. T2: the setup calls `g(2)` then raises: the unjudged claim traced into `g`, but that is not reach on v32, so `g` is still struck (`unreached`; v31 names the same claim `cannot_judge`, a strike either way; the plant accepts either rule name and requires the strike and the reject) | PASS | PASS (2.7 s) |
| `u1_own_error_not_run` (part 1's, amended) | the same forced `ValueError` in U1 (`U1_INPUTS=notanumber`), `U1 not run: ValueError: ...` once, no traceback, `U1EXIT 75`; now: land exit 0, `DECISION proceed`, `NOTRUN U1`, reasons `U1 not run (exit 75): no strike, not judged (T16)`, no strike, the patch stays applied, no temp tree left | FAIL (the traceback and the strike, as part 1 recorded) | PASS (1.5 s) |

**Retired at go-live: `plants/c1_cannot_judge.sh`.** It asserts the 2026-10-15 rule T16 supersedes (`cannot_judge`
is a strike): its T3 (a setup that fails, on an unchanged `f`) proceeds under v32 and its T2 (`while True: pass`, out of
line budget) is still struck but as `unreached app.spin`, not `cannot_judge`. Its T1 (partial) lives on as
`c1_cannot_judge_proceeds` T1. It cannot stay in `plants/` under v32 (it would fail `gc selftest`).

## Proof

Two fresh scratch copies of this tree (spec folder, `proposals/`, `__pycache__`, `.DS_Store` left out), never the real
tree, never a real state dir, under the session scratchpad `.../scratchpad/v32b/tree_v31` and `.../tree_v32`, 2026-10-19:

- v31 copy (`bin/gc` and `pack/live/C1.py` byte-identical to the live ones by `diff`, PACK.json at 31, the four plants
  above copied into `plants/`): `gc_not_run_proceeds` FAIL, `c1_cannot_judge_proceeds` FAIL, `u1_own_error_not_run` FAIL,
  `c1_unjudged_unreached_strikes` PASS, each as the table says (`.../scratchpad/v32b/plants_v31_v32.log`).
- v32 copy (part 1 + part 2 applied: `proposals/v32/U1.py` and `proposals/v32/C1.py` as `pack/live/`, `gc.patch` and
  `dash.patch` applied to `bin/`, PACK.json at 32, the five proposal plants in `plants/`, `c1_cannot_judge.sh` removed):
  the four plants PASS; `plants/run_all.sh`: 43 plants PASS, `plants: PASS`, 0 FAIL lines (39 live minus `c1_cannot_judge`, plus part 1's two and this part's three), 2:12 in all; `c1_py38_qualname` and `e1_pytest3_names_test` ran on the set2 venvs. Log `.../scratchpad/v32b/run_all_v32.log`.
- `bin/dash.py --state` on a v32 state with one unjudged claim and U1 not run renders `landed, not judged: U1 not run;
  1 unjudged claim(s)`, `75 not run` in the exit column, and the `C1 unjudged:` line (`.../scratchpad/v32b/dash_smoke/`).
- `patch -p1 --dry-run` of both patches against a copy of `bin/` applies cleanly.

**Signer's amendment at go-live (2026-10-19):** a `true` predicate that raises is a verdict, `fake_effect` (the code ran to a result and the expected effect is not there), not `cannot_judge`; one line in `judge()` (the agent's open item 4). T16 covers what the gate could not process, not what the code failed.

## To go live (K5 steps 3 and 4, on signer yes), parts 1 and 2 merged

1. Copy `proposals/v32/U1.py` and `proposals/v32/C1.py` to `pack/live/` as they are; on line 2 of each change
   "Proposed for pack v32" to "Live in pack v32"; the rest of each header stays.
2. `pack/live/PACK.json`: `pack_version` 32. The lists do not change.
3. `cd` to the tree and `patch -p1 < proposals/v32/gc.patch` (bin/gc, bin/governor.py); `patch -p1 <
   proposals/v32/dash.patch` (bin/dash.py).
4. Plants: copy `proposals/v32/plants/u1_large_spec.sh`, `u1_own_error_not_run.sh` (this part's version),
   `gc_not_run_proceeds.sh`, `c1_cannot_judge_proceeds.sh`, `c1_unjudged_unreached_strikes.sh` to `plants/`; remove
   `plants/c1_cannot_judge.sh`. 43 plants.
5. Law docs: the quoted wording under "Doc changes at go-live" below (PACK.md, README.md, GLOSSARY.md, KERNEL.md).
   Part 1's step 4 is replaced by it.
6. Hashes (bin/ledger.py), recomputed today on the scratch copy. `kernel_sha256` changes (bin/gc and bin/governor.py
   are in `KERNEL_FILES`): live `d468b580e7ec9da870d7e82c41f957929a9559d88e9532d149b2c8d33c4bedaa` ->
   `e724bc40fbc2980cc7697e95ac99c847089d6e8c68a7262c0114eb3cd282ff05` (dash.py is not a kernel file). `pack_sha256`
   changes: live `0abf96e200efd9aa94deced2fc27f1cedb57013ebe920a138ad52df7c74c5678` -> with both headers reading
   "Live in pack v32" (line 2 only changed) and PACK.json at 32:
   `9ef77a69d5053fb8666ba59b57117f6efa5f69c592e64621c1f01faf8d0bf57a` (part 1's `e05f2d31…` was U1 alone; recompute
   after step 1 if a header is worded differently). Rows from then on carry both new values; RELEASE_CHECKLIST "Kernel
   change": expected and recorded here.
7. `gc selftest`. A version bump rejects every outstanding ticket; the signer re-mints them.

T2/T3: v32 is a new frozen pack; CLOSER_PROVING results on v31 do not carry over.

## Doc changes at go-live (copy-paste; the live tree is not edited by this proposal)

**PACK.md**, line 6: `## Live pack: version 32`.

**PACK.md**, C1 row, replace `| C1 | every_ticket | v30 |` with `| C1 | every_ticket | v32 |` and append to the rule text:

> v32 (T16): `cannot_judge` is not a verdict: `C1 unjudged: <file>:<line> cannot_judge <qualname> (<reason>)` on stdout, no
> strike, filed in the evidence with the rule and counted in `reach.unjudged` and each `coverage` entry's `unjudged`; C1
> exits 0 when every judged claim held and nothing is unreached. Reach counts judged claims only: a function only an
> unjudged claim would have reached is `unreached`, a strike. `partial` for a missing required name stays a strike.

**PACK.md**, U1 row: `v30` -> `v32` and part 1's step-4 text: "the driver's spec in a file under U1's temp dir
(`U1_SPEC_FILE`), not the environment; U1's own error is `U1 not run: ...`, exit 75, no strike".

**PACK.md**, line 22, replace:

> `world`: run on every scan. `every_ticket`: run on every land; any exit but 0 or 75 rejects with a strike.

with:

> `world`: run on every scan. `every_ticket`: run on every land; any exit but 0 or 75 rejects with a strike. 75 (not run)
> is let through (T16, v32): the land proceeds if nothing struck, the row's `not_run` and `reasons` record it. The one 75
> still refused is no `sandbox-exec` on the host (gc checks before apply; nothing can be held read-only).

**PACK.md**, History, new first line:

> - v32 (2026-10-19): two U1 fixes and ruling T16 (proposals/PACK_v32.md, signer yes 2026-10-19). U1: each driver's spec
>   goes in a file under U1's temp dir (`U1_SPEC_FILE`; `U1_SPEC` in the environment overflowed ARG_MAX on a large module
>   and struck an honest ticket), and U1's own error is `U1 not run: ...`, exit 75, not a traceback and a strike. T16, let
>   through what the gate cannot judge: a check exiting 75 no longer refuses the land (bin/gc, bin/governor.py; the row's
>   `not_run` and `reasons` record it; the ticket's own verify at 75 proceeds too; no `sandbox-exec` still refuses, before
>   apply); C1 `cannot_judge` is `C1 unjudged: ...` on stdout, filed and counted, no strike, and reach counts judged
>   claims only; the row gains `unjudged`; `bin/dash.py` shows what was not judged. Plants `u1_large_spec`,
>   `u1_own_error_not_run`, `gc_not_run_proceeds`, `c1_cannot_judge_proceeds`, `c1_unjudged_unreached_strikes`;
>   `c1_cannot_judge` retired (it asserted the superseded rule). 43 plants pass. `kernel_sha256` changes (bin/gc,
>   bin/governor.py). Verdict changes: honest tickets a not-run check or an unjudged claim used to refuse now land, recorded
>   as not judged; nothing that struck before stops striking except `cannot_judge` itself (T16).

**README.md**, Claims paragraph, replace:

> At land, C1 runs
> every claim in the sandbox; a claim that does not hold is a strike naming the function and the gap (pass_through,
> fake_check, answer_table, fake_effect, partial, cannot_judge), and every function the ticket introduces must be
> reached by some claim or it is `unreached`, a strike.

with:

> At land, C1 runs
> every claim in the sandbox; a claim that does not hold is a strike naming the function and the gap (pass_through,
> fake_check, answer_table, fake_effect, partial), and every function the ticket introduces must be
> reached by some claim or it is `unreached`, a strike. A claim C1 could not bring to a verdict (its setup or import
> failed, its clock or line budget ran out) is `cannot_judge`: not a strike since pack v32 (KERNEL T16); it is said
> (`C1 unjudged: ...`), filed, recorded in the ledger row's `unjudged` and shown on the signer's page, and a function
> only such a claim would have reached is still `unreached`.

**README.md**, Status, first bullet: replace `Live pack: version 31` with `Live pack: version 32`, and replace the final
sentence `Pack v31 is the live pack.` with:

> v32 (2026-10-19) puts U1's driver spec in a file (an environment overflow struck an honest ticket), makes U1's own error
> exit 75, and builds T16: what the gate cannot judge (a check exiting 75, a claim C1 cannot set up or finish) is let
> through and recorded in the row (`not_run`, `unjudged`) and on the page, not refused; `unreached` stays a strike. Pack
> v32 is the live pack.

**GLOSSARY.md**, row `not run`, replace:

> | `not run` | verdict | A check exited 75: it could not run. No strike, and the land does not proceed. | M5a; bin/gc |

with:

> | `not run` | verdict | A check exited 75: it could not run. No strike; since pack v32 (T16) the land proceeds if nothing struck and the row lists the check under `not_run`. Only no `sandbox-exec` on the host still refuses the land. | M5a, T16; bin/gc |

**GLOSSARY.md**, row `C1`: replace `out of time or budget is cannot_judge, a reject.` with `out of time or budget is
cannot_judge, let through and recorded (T16, v32).`

**GLOSSARY.md**, row `cannot_judge`, replace:

> | `cannot_judge` | finding | C1: the claim could not be run to a verdict (import, setup, clock, budget). A reject, never silence. | pack/live/C1.py; T5 |

with:

> | `cannot_judge` | finding | C1: the claim could not be run to a verdict (import, setup, clock, budget). Not a strike since pack v32 (T16): `C1 unjudged: ...`, filed and counted, the land proceeds; never silence. A function only such a claim would have reached is `unreached`. | pack/live/C1.py; T5, T16 |

**GLOSSARY.md**, Retired, row `unjudged`: the 2026-10-15 reading is superseded. Proposed (G1: the old row is not
deleted, its reading changes):

> | `unjudged` | `not judged` (let through) | Signer, 2026-10-15: one the gate cannot judge is a reject. Superseded 2026-10-19 by T16: let through, recorded in the row (`not_run`, `unjudged`) and on the page. |

The signer may prefer `unjudged` as a live term (the row key) instead; then it is a `glossary add`, not a retired row.

**KERNEL.md**, exit-code row 75, replace:

> | 75 | not run (EX_TEMPFAIL), let through under T16 (2026-10-19; before that, land refused without a strike): no `sandbox-exec`, no pytest for the interpreter the checks run the repo's code under (`REPO_PYTHON`, else python3), or the check's own error. No strike. |

with (for the signer to confirm the exception):

> | 75 | not run (EX_TEMPFAIL), let through under T16 (2026-10-19; before that, land refused without a strike): no pytest for the interpreter the checks run the repo's code under (`REPO_PYTHON`, else python3), or the check's own error. No strike; the row's `not_run` lists the check. One exception: no `sandbox-exec` on the host is still a refusal (gc land, before apply; no strike), because nothing can be held read-only (K2) and nothing at all would be judged. |

**KERNEL.md**, M5 / M5a row: "A check that cannot run exits 75: not run, no strike." is still true; nothing to change.
**KERNEL.md**, Kernel files section, add after the v29 note:

> 2026-10-19, pack v32 (proposals/PACK_v32.md part 2, T16): `bin/gc` (a 75 is recorded, not a reject; the row's
> `unjudged`; no `sandbox-exec` refused before apply) and `bin/governor.py` (`decide` proceeds on 75 with a reason)
> changed. `kernel_sha256` goes from `d468b580…` to `e724bc40…`.

## For the signer

- **The sandbox-exec exception** (change 3 above): under T16 read literally, a host without `sandbox-exec` would let every
  ticket through with nothing judged. This proposal keeps that one 75 as a refusal before apply, no strike, and proposes
  the row-75 wording above. Confirm, or strike the exception (one `if` in cmd_land) and the land would proceed with every
  check under `not_run`.
- **Reach counts judged claims only** (change 5). The brief's words were "a function only an unjudged claim would have
  reached"; this reads them as: what an unjudged claim traced before stopping is not reach either. The stricter reading
  keeps T16 from widening the reach rule by accident; `c1_unjudged_unreached_strikes` T2 is the guard. The looser reading
  (a trace counts even from an unjudged claim) is a two-line change in `main()`.
- **`not_run` now includes World checks and a named verify** that exit 75, not only `every_ticket` names, so the row says
  everything not judged. If the signer wants the old filter back it is the `every` test on two lines.
- **`partial` for a missing required name stays a strike** (a verdict, as the brief says); so does `unreached` and every
  E1/S1/G18 failure. A predicate that raises (`expect: true`) is `cannot_judge` and now unjudged, as the brief's "for any
  reason" says; the signer may want it `partial` instead (one line in `judge()`).
- **`plants/c1_cannot_judge.sh` must be removed at go-live** (it asserts the superseded rule). Its partial case is kept in
  the new plant.
- **Part 1's u1_own_error_not_run** is amended to expect a proceed; part 1's "one outcome changes in kind" (U1's own error
  is a reject without a strike) now reads: a proceed with U1 under `not_run` (T16). Everything else in part 1 stands.
- Nothing in this part needed more than the brief allowed; no item is left undone.
