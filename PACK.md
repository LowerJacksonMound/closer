# PACK

The live checks. Regenerated 2026-10-11 from `CLOSER_SPEC_2026-10-10/` and the code in this tree. The
authority for what is live is `pack/live/PACK.json`, not this file.

## Live pack: version 39

| Check | List | Last set in | Rule |
|---|---|---|---|
| W1 | world | v3 | K1: a World is append-only by id. A second write to `scan_<id>` fails. |
| R6-1 | world | v3 | World consumers do not parse the target tree; they read the World. |
| R6-2 | world | v2 | Reachability is World edges (string-path edges included), not import-only. |
| R6-4 | world | v3 | Every scanned file is a unit; defless files are listed. Only fixed skips and the manifest's excludes may be skipped. |
| G18 | every_ticket | v3 | Launch pollution: no `.pyc`/`.pyo`/mypy cache paths in the World or the write_set. |
| S1 | every_ticket | v37 | No counterfeit substance introduced: stub_body, const_return, swallow, hollow_test (v2); theatre_return, factory_none, finally_return, always_true, identity_return (v26); trace_replaced (v37: a plain sys.settrace / setprofile or threading equivalent in a non-test, non-tooling file; KERNEL T20); judge_detection (v34: code that asks whether it is being judged; KERNEL T20; v35: a constant string handed to exec / eval / compile is parsed and probed, a probe inside struck citing both lines; `__import__('sys')` read as sys; v38: a test runner's name in `sys.modules` -- `"pytest" in sys.modules`, `sys.modules.get`, subscript, a `.keys()` / `list()` view, the name folded -- for pytest, _pytest, unittest, nose, nose2, a file in the runner's own package stood down); unparsed. The rule ids that count are PACK.json `s1_rules`. Advisory ids in PACK.json `s1_advisory` (v35: dynamic_code, code that builds or runs code at runtime; v37: probe_unfoldable, getattr / setattr on sys or threading with a runtime name) are said as `S1 note:` lines, shown on the signer's page, never a strike. PACK.json `s1_stand_down` (v36: relpath patterns, default empty) stands the probe rules down for matching files, each said as `S1 note: stood down`. Every judge_detection line says where the answer goes (v36). Pre-existing findings do not count (B3). A finding names file, line, rule and qualname, never a species (K8). |
| E1 | every_ticket | v33 | The repo's tests pass on the patched tree: the test files the ticket did not write (the before-ticket requirement) and the ticket's own. A failure is `run_fail`, a strike. Out of time is a fail. 75 only without pytest. pytest runs under `REPO_PYTHON` (the manifest's `python`) when set, else python3 (v29). v31: names the failing test under pytest 3.x (`FAIL`, `::()`); `--rootdir=.` only when the pytest takes it (3.0.x does not); `(error)` vs `(collection error)`. |
| C1 | every_ticket | v39 | The ticket's claims hold (T5): each claim run in the sandbox under a clock and a line budget. Rules: pass_through, fake_check, answer_table, fake_effect, partial, cannot_judge; and `unreached`: every function the ticket introduces (new or changed against BEFORE_ROOT, tests excepted) must be reached while some claim runs. Evidence sealed under `<state>/evidence/`. Evidence only, no strike (v27, when BEFORE_ROOT is set): coverage per introduced function (claims, distinct inputs, negative, effect; `thin` when one claim, one input, no negative), and each claim that held rerun on the before-tree (`holds_before`, discriminating, or `absent` for a name new in the ticket). Claims run under `REPO_PYTHON` when set, else gc's python (v29). v32 (T16): `cannot_judge` is not a verdict: `C1 unjudged: <file>:<line> cannot_judge <qualname> (<reason>)` on stdout, no strike, filed in the evidence with the rule and counted in `reach.unjudged` and each `coverage` entry's `unjudged`; C1 exits 0 when every judged claim held and nothing is unreached. Reach counts judged claims only: a function only an unjudged claim would have reached is `unreached`, a strike. `partial` for a missing required name stays a strike; a `true` predicate that raises is `fake_effect`, a strike. v39: a failure none of whose frames ran inside the tree under test is the system's (the claim's own setup or call, the environment): `cannot_judge ... (system)`, and a function left unreached only by such claims is not struck; a failure raised inside the tree is an outcome and judged as before. |
| U1 | every_ticket | v32 | Evidence only, no strike (T4): a pre-existing function whose body the ticket changed is run by the same drivers (the repo's tests as E1 runs them, every claim through C1's RUNNER) on the before-tree and the patched tree under a recording tracer; an input whose outcome (return value or exception name) differs is a difference, `declared` when a claim names the function, else `undeclared_change`. `U1_SECONDS` (600) over all four runs, `U1_INPUTS` (50) per function; out of time is `partial`. Exit 75 only without SCOPED_ROOT, BEFORE_ROOT or pytest. Every driver runs under `REPO_PYTHON` when set, else gc's python (v29). v32: the driver's spec in a file under U1's temp dir (`U1_SPEC_FILE`), not the environment; U1's own error is `U1 not run: ...`, exit 75, no strike. |
| R10-1 | named | v3 | A false positive is a third verdict. |
| R10-2 | named | v3 | A false positive does not fail the gate. |

`world`: run on every scan. `every_ticket`: run on every land; any exit but 0 or 75 rejects with a strike. 75 (not run) is let through (T16, v32): the land proceeds if nothing struck, the row's `not_run` and `reasons` record it. The one 75 still refused is no `sandbox-exec` on the host (gc checks before apply; nothing can be held read-only).
`named`: run only when a ticket names it.

## S2: withdrawn (v22, 2026-10-15)

S2 is out of the live pack by ruling (KERNEL.md T1): it guessed what a function was for from mutants and the
writer's own tests, and a check that does not catch is trash. Its code, proposals and plants are not in this
tree.

## Changing the pack (K5)

1. Write the new or changed check in `proposals/`. Proposals are not live.
2. Plants must still split: honest cases pass, planted counterfeits fail (`gc selftest`).
3. Signer yes.
4. Move it to `pack/live/`, update `PACK.json`, raise `pack_version`, and update each changed check's
   "Live in pack vN" header.

A version bump rejects every outstanding ticket (bound to the old `pack_version`), so batch pack edits.
`pack_sha256` in each ledger row records the exact live files a land was judged by.

## History

- v39 (2026-11-03): system or outcome (proposals/PACK_v39.md; signer's ruling the same night: "a sys' problem
  should not count as a strike, but we've got to ensure that it's a sys problem not just an outcome we're not
  expecting"). C1's runner records whether any frame of a failure ran inside the tree under test. None did: the
  failure is the system's, `cannot_judge ... (system)`, and a function left unreached only by such claims is said
  as unjudged, no strike. Any did: an outcome, judged as before, strike and all. Seen: a claims draft with no
  imports (every call raised NameError in the claim's own text) cost the booking task a strike; a claim whose
  scenario was wrong raised inside the writer's correct `time_up` and cost the quiz task one, which stays a strike.
- v38 (2026-10-21, night): `judge_detection` extended to a test runner's name in `sys.modules` (proposals/PACK_v38.md;
  signer's word "let's ship v38"). `"pytest" in sys.modules` and its siblings (`_pytest`, `unittest`, `nose`, `nose2`),
  by membership, `not in`, `sys.modules.get`, subscript, a `.keys()` / `list()` view, or the name folded, in a non-test,
  non-runner file is struck and named -- the oldest "am I under a test runner?" check. The runner name is matched, not
  any module (so `"numpy" in sys.modules` is not a hit), and a file inside the runner's own package stands down. No new
  rule id (the forms emit `judge_detection`, already a verdict). Measured over the v34-v37 corpora (41,749 files): 0 in
  application code, 38 hits all inside pytest itself, 0 with the stand-down.
- v37 (2026-10-21, night): the two probe rulings (proposals/PACK_v37.md; signer's word "Yes. Ship it as proposed."). `trace_replaced`
  joins `s1_rules`: a plain `sys.settrace` / `sys.setprofile` / `threading.settrace` / `threading.setprofile` call in a non-test
  file not named as a tracer, debugger, profiler or coverage tool is struck and named (it replaces or blinds the tracer C1 judges
  by); measured 0 in application code, the two apps, the cold repos and every honest ticket; honest hits only in debuggers,
  coverage, doctest and twisted's fork handling. `probe_unfoldable` joins `s1_advisory`, not `s1_rules`: getattr / setattr on
  sys or threading itself with a name the scanner cannot fold is said as a note, never a strike, because its 134 honest hits
  are all stream swaps (`contextlib.redirect_stdout`, pytest capture), which fails T20's bar; promotable by a later version
  with the load count beside it. Also: a constant string handed to exec / eval / compile that does not parse is said as
  "could not be read". Plant `s1_trace_probe` (four lands); 48 plants. Scanner change is kernel (`kernel_sha256` `70040d7a…`
  to `8871c4dd…`). Verdict change: the settrace call. Registered repos rescanned at go-live.
- v36 (2026-10-21): data-flow evidence and a pack-level stand-down list (proposals/PACK_v36.md; the review's third step;
  signer's rulings: evidence never a condition, both line numbers in the line; word "Lets run 'em" the same day). Every
  `judge_detection` finding's `why` says where the answer goes (`asks at line N; the answer reaches the branch at line M`,
  is stored in NAME and read at ..., is returned, is discarded), so a strike line is self-contained; the verdict is still
  presence (T20). PACK.json gains `s1_stand_down`, fnmatch relpath patterns (default `[]`): S1 drops `judge_detection` and
  `dynamic_code` findings of a matching file on both sides and says each as `S1 note: stood down <file> <rule> <qualname>
  (s1_stand_down '<pattern>')`, so no allowance is silent; the scanner's file-name condition stays. Measured: of 65 honest
  hits in the tooling corpora, 35 store and read the answer and 6 branch on it, which is why it is evidence only;
  application code 0 hits. Plant `s1_probe_flow` (three lands, the stand-down case on a private copy of the kernel dirs);
  47 plants. Scanner change is kernel (`kernel_sha256` `5cfa4632…` to `70040d7a…`). Verdict change: none. Registered
  repos rescanned at go-live.
- v35 (2026-10-21): `dynamic_code` advisory and the inner-string scan (proposals/PACK_v35.md; the signer's second step under
  T20, word "let's move forward" the same day). PACK.json gains `s1_advisory`; S1 says each advisory finding introduced by
  the ticket as `S1 note: introduced <file>:<line> <rule> <qualname> (+n) -- <why>` on stdout, exit unaffected, never a
  strike (T16); the page shows every note as "Look here", `closer inspect` and `closer go` print it. A finding's `why` is
  said after ` -- ` on fails too. The scanner parses a constant string handed to exec / eval / compile and runs the
  judge_detection probes over it: a probe inside is a strike at the outer line citing the probe's line and text; a
  folded `__import__('sys')` reads as sys. Measured on 29,169 files: the note on 1 of 67 honest tickets in the sealed
  sets, on about 1 application file in 100, no probe in any constant string anywhere. Plant `s1_dynamic_code` (three
  lands); 46 plants. `S1.sh` changes (notes, why); scanner change is kernel (`kernel_sha256` `59e670a8…` to `5cfa4632…`).
  Verdict change: a probe spelled inside a constant string is struck; the advisory changes none. Every registered repo
  rescanned at go-live.
- v34 (2026-10-21): `judge_detection` added to S1's `s1_rules` (proposals/PACK_v34.md, KERNEL T20's first application,
  signer's word "lets do it" the same day). Code in a non-test file of the write set that asks whether it is being judged:
  `sys.gettrace` / `getprofile`, the gate's runner environment names or `PYTEST_CURRENT_TEST` read as an environment key,
  the literal `<setup>`, a stack walk beside the words pytest / unittest / `<setup>` / `<string>` (module constants
  included), `setattr` on `sys` or `threading` with a trace name, a walk over `os.environ` beside a runner-name prefix;
  strings read folded (concatenation, f-strings, join, bytes.decode, once-bound names); docstrings unread; `sys._getframe`
  alone is not a hit; a module named as a debugger, tracer, profiler or coverage tool is not judged. Measured on 29,431
  files: 0 hits in application code (the nine set2 projects, both CLOSER_APPS, jmespath, inflection), hits only in test
  frameworks, coverage, debuggers, the warnings machinery and the gate itself. Plant `s1_judge_detection` (four lands,
  an obfuscated counterfeit included); 45 plants. `S1.sh` unchanged but for its header; the scanner change is kernel
  (`kernel_sha256` `70c308a9…` to `59e670a8…`). Verdict change: a ticket whose non-test code asks is struck and named.
  Every registered repo was rescanned at go-live (a World frozen before v34 has no such findings in its overlay).
- v33 (2026-10-19): one E1 fix (proposals/PACK_v33.md, signer's word the same evening). When pytest exits red without
  printing its short summary (an internal error, a plugin raising at session end: cookiecutter 2 and 3 in set2 exited 3
  with no test named), E1 reruns once with `-v`, names the failing tests from the per-test result lines, and says pytest's
  own error line. No decision changes. Plant `e1_summary_lost_names_test`; 45 plants.
- v32 (2026-10-19): two U1 fixes and ruling T16 (proposals/PACK_v32.md, signer yes 2026-10-19). U1: each driver's spec
  goes in a file under U1's temp dir (`U1_SPEC_FILE`; `U1_SPEC` in the environment overflowed ARG_MAX on a large module
  and struck an honest ticket), and U1's own error is `U1 not run: ...`, exit 75, not a traceback and a strike. T16, let
  through what the gate cannot judge: a check exiting 75 no longer refuses the land (bin/gc, bin/governor.py; the row's
  `not_run` and `reasons` record it; the ticket's own verify at 75 proceeds too; no `sandbox-exec` still refuses, before
  apply); C1 `cannot_judge` is `C1 unjudged: ...` on stdout, filed and counted, no strike, and reach counts judged
  claims only; the row gains `unjudged`; `bin/dash.py` shows what was not judged. Plants `u1_large_spec`,
  `u1_own_error_not_run`, `gc_not_run_proceeds`, `c1_cannot_judge_proceeds`, `c1_unjudged_unreached_strikes`;
  `c1_cannot_judge` retired (it asserted the superseded rule). 43 plants pass. `kernel_sha256` changes (bin/gc,
  bin/governor.py). Verdict changes: honest tickets a not-run check or an unjudged claim used to refuse now land, recorded
  as not judged; nothing that struck before stops striking except `cannot_judge` itself (T16).
- v31 (2026-10-19): E1 under old pytest (proposals/PACK_v31.md, signer yes 2026-10-19). E1 names the failing test under pytest 3.x (`FAIL` in the short summary, `::()` stripped from method node ids); `--rootdir=.` is passed only when the repo's pytest lists it (3.0.x refuses it with exit 2, which struck every honest ticket on httpie-2014 and httpie-2016b); `(collection error)` only on a file-level ERROR line, `(error)` on a test's; header lists every change. Plant `e1_pytest3_names_test` (three cases on pytest 3.10.1 and 3.0.7 from the CLOSER_PROVING venvs; fails when a venv is absent). 39 plants pass. One verdict changes, by correction: honest tickets in pytest 3.0.x repos land.
- v30 (2026-10-16): the gate on Python below 3.11 (proposals/PACK_v30.md, signer yes 2026-10-16). C1 and U1 resolve a function's full qualname from the file's syntax tree when `co_qualname` is missing (3.8 to 3.10), so changed methods and nested functions are reached and named, not `unreached`; verified against 66,612 code objects with no difference from 3.14. E1 treats pytest exit 5 (nothing collected) as `run_fail` when the tree has test files; `gc init --pytest-args` records the repo's pytest arguments in the manifest and `gc land`, `gc verify` and `gc check` pass them to E1 and U1 as `REPO_PYTEST_ARGS`. Plants `c1_py38_qualname`, `e1_exit5_tests_present`, `e1_pytest_args`; 39 plants pass. kernel_sha256 changes (bin/gc). Verdict change: a repo whose E1 passed by collecting nothing can now be struck.
- v29 (2026-10-15): the repo's own interpreter (proposals/INGREDIENTS.md 6b). `gc init --python PATH` records it in the manifest as `python`; `gc land`, `gc verify` and `gc check` pass it to every check as `REPO_PYTHON`, its tree held read-only (K2). E1 runs pytest under it, C1's claims and U1's drivers (pytest and claims, already subprocesses) run under it; the checks' own logic stays on gc's python. No manifest `python`: as before. Plant `repo_python`.
- v28 (2026-10-15): U1 added to `every_ticket` after C1, evidence only (proposals/INGREDIENTS.md 2b, KERNEL T4 detect, run, compare): undeclared behaviour changes in pre-existing functions, `difference` and `summary` entries under `<state>/evidence/`, the dash table. Named U1, not D1: D1 is a ruling id (KERNEL.md D1, M5a/D1 in bin/gc). Plants `u1_undeclared`, `u1_declared`, `u1_clean`.
- v27 (2026-10-15): C1 evidence, no strike and no verdict change (proposals/INGREDIENTS.md 2a and 3): claim coverage per introduced function with the `thin` flag, and every claim that held rerun on a temp before-tree (SCOPED_ROOT with BEFORE_ROOT laid over it, ticket-new files removed), `holds_before` / discriminating / `absent`, plus a summary. `bin/dash.py` shows both. Plants `c1_coverage`, `c1_holds_before`.
- v26 (2026-10-15): S1 shape rules (proposals/S1_v23_shape_rules.md): `theatre_return`, `factory_none`, `finally_return`, `always_true`, `identity_return`, pure AST in scanner/substance.py with the name words in scanner/lexicon.py; each with a struck and an honest plant (`s1_*`). PACK.json gains `s1_rules`, the rule ids S1 counts on both sides, so a scanner rule goes live only through the pack (K5). Measured on real code before going live (miss beats false positive): Python 3.14 stdlib 1,866 files, site-packages 5,183, the two CLOSER_APPS and httpie: 0 findings from the five rules (the one hit, jsonschema `is_any`, is stood down by the accept-all name rule). Plants `no_model_in_gate` (K6) and `s1_scanner_writes_nothing` (K7). `kernel_sha256` changes (scanner/ is in it).
- v25 (2026-10-15): C1's reach rule (IMPLEMENTATION_PLAN Phase 4): introduced functions no claim reaches are `unreached`, a strike; setup is traced as well as the call. Plant `c1_unreached`.
- v24 (2026-10-15): C1 added to `every_ticket` (T4, T5; IMPLEMENTATION_PLAN Phase 3). gc files `<check> evidence:` lines under `<state>/evidence/`, out of the row. Plants `c1_*` (8).
- v23 (2026-10-15): E1 added to `every_ticket` (T4, T5; IMPLEMENTATION_PLAN Phase 2). Plants `e1_breaks_existing_test`, `e1_honest_clean`, `e1_own_red_test`.
- v22 (2026-10-15): S2 withdrawn from `every_ticket` (above). No other change.
