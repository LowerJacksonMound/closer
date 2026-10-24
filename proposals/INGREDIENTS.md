# Proposal: the ingredients, and the build for each (2026-10-15)

Not live. What has to be in the pot for the catch rate to be expected rather than hoped, drawn from the proving
runs of 2026-10-15 (cut 2026-10-16 under T7 with the pre-purge set they ran on; the lessons stay, the numbers are
not cited). Complete: 1 (intent as claims: T5, the
extractor, C1) and 5 (the honest evidence loop: sealed evidence, `bin/dash.py`). Below: the six that are not.
No trials here; each item is a build with a plant, under K5 for pack changes.

Facts the builds rest on: `BEFORE_ROOT` holds only the write_set's prior files (gc `before_root()`), so a full
before-tree is `SCOPED_ROOT` copied to temp with those files laid over it (the sandbox permits temp writes);
`C1.introduced_functions` already splits defs into new and body-changed against `BEFORE_ROOT`; C1 already seals
per claim the functions reached and the inputs given.

## 2. A pointer to where to look (two builds, both pointers, no strike until ruled)

**2a. Claim coverage per changed function.** In C1, after the claims run, for every introduced or changed function:
how many claims reach it, how many distinct inputs reach it, whether any claim on it is a negative (`raises`, or a
predicate that forbids), whether any reads an effect. Emitted as `C1 evidence:` lines (sealed, signer-only); no
verdict change. `bin/dash.py` shows a coverage table per changed function and flags thin ones (one claim, one
input, no negative). This is the live substitute for "told which function": shown before anything lands.
Where: `pack/live/C1.py` (~60 lines), `bin/dash.py` (~40). Pack bump. Plant: a function reached by one claim with
one input is flagged; one with three inputs and a negative is not.
Built 2026-10-15 in pack v27: `coverage` entries with the `thin` flag in C1 evidence, the dash table; plant `c1_coverage`.

**2b. Undeclared behaviour change in pre-existing functions (T4, detect-run-compare).** A new every-ticket check,
name through the glossary. For every body-changed pre-existing function: trace the repo's tests and the claims on
the before-tree and record each call's inputs and outcome (return or raise, normalised as C1's `norm` does); replay
on the patched tree; any input whose outcome differs, where no claim names that function, is reported as evidence
with the input and both outcomes. Pointer first; a strike only by ruling. This is what sees the counterfeits planted
in behaviour no criterion names (task 2's character filter and phrase case, the dropped error message in `sign_in`,
the dropped branch in `poll`). Where: `pack/live/` new check (~200 lines: a recording tracer, a replay runner, the
before-tree overlay). Pack bump. Plant: a ticket that changes a prefix filter and quietly breaks a sibling filter
is reported on the sibling; the honest ticket reports nothing.
Built 2026-10-15 in pack v28 as `U1` (D1 is a ruling id): `difference` / `summary` entries (`undeclared_change`) in U1 evidence, the dash table; plants `u1_undeclared`, `u1_declared`, `u1_clean`.

## 3. Discriminating claims

In C1, run every claim a second time on the before-tree overlay, same sandbox and budget. A claim that holds on
both trees discriminates nothing about the task: it is a regression guard or vacuous. Listed in evidence and on the
page as "holds before and after"; a claim whose `name` is a new function is exempt (it cannot run before). No
strike by default; a policy number (`gc policy`) can later refuse mint when too few claims discriminate. This is
the check that would have flagged the guest-export claims before any land. Where: `pack/live/C1.py` (~50 lines),
`bin/dash.py` (~15). Same pack bump as 2a. Plant: the vacuous guest claim is listed, the guest-with-watches claim
is not.
Built 2026-10-15 in pack v27: `before` / `before_summary` entries (`holds_before`, `absent`) in C1 evidence, the dash badge; plant `c1_holds_before`.

## 4. The per-function claim checklist

`bin/claims_draft.py` gains two things. (i) For every function the criteria name, and every `--changed FILE:QUALNAME`
the signer passes when sharpening, a checklist in the notes file built from `scanner/lexicon.py`'s claim words:
check or validate → a negative case and a positive case; parse, format, transform, normalise → output differs from
input in the required way, plus odd inputs; factory or make → collaborators actually wired, observed by effect;
compute or lookup → at least two inputs with hand-derived values; save, send, log, delete → the effect read at
its sink; and always: what the function did before this task is kept, a failure of another kind surfaces, every
negative is set up so the forbidden outcome could occur. (ii) `claims_draft.py --check CLAIMS.json` reports which
checklist lines have no claim, by name and expect form. Signer tool; no pack change. ~120 lines. Plant: grows
`claims_draft` (a check-named function with no raises claim is reported).
Built 2026-10-15, no pack change: `--changed`, the notes checklist and `--check` in `bin/claims_draft.py`, `checklist_classes` in `scanner/lexicon.py`; plant `claims_draft` grown.

## 6. Proving material not from our own list (gathered 2026-10-15: `~/Desktop/CLOSER_PROVING/set2/`, 34 bugs, 9 projects, from BugsInPy)

Gather, do not build in the gate. Public sets of real Python bugs with the project's tests (BugsInPy or similar):
the buggy version passed its own suite, the fix came with the test that exposes it. Per bug: base = the buggy
project, criteria = the issue text, honest = the fixed files, counterfeit = the buggy files, claims drafted blind
from the issue. That is a working counterfeit nobody here designed. Where: `~/Desktop/CLOSER_PROVING/bin/` fetcher
and a `set2/` in the same layout as `set/` (~150 lines plus curation); the environment per project is the real cost
and is unknown until tried. Needs the network, so outside the gate (K6). Target: 20 to 30 bugs with small diffs.

## 7. Demos (built 2026-10-15 on the rounds' driver; that driver cut 2026-10-16 under T7; a fresh driver is owed)

`prove.py --demos` stays: after each honest land, start the app from the landed tree with a fresh `APP_HOME`, run
its `demos/*.json` (part of the kept apps), record pass or fail beside the land, one demo at a time under the lock,
unattended (T9). The driver it calls, `CLOSER_PROVING/bin/drive.py`, is rewritten fresh: start the app as
`python -m <package>`, wait for its `ready` log line, drive the window with real mouse and keys (pynput, `.venv`),
check the app's own log; exit 0 every step ran and the app exited clean, 1 a step failed or the app crashed, 2
cannot drive. Needs macOS Accessibility for the terminal that runs it.

## 8. The boundary (built 2026-10-15: COUNTERFEITS.md, "What no claim states")

A section in COUNTERFEITS.md, "What no claim states": concurrency and timing under load, cross-function design,
behaviour at a scale no demo reaches, disguises off this list. The gate says what it does not catch. Doc only.

## Order and bundling

Pack bump v27: 2a and 3 together (one bump, K5). Then 4 (no bump). Then 2b as v28. 6 gathers in parallel from the
start. 7 and 8 whenever. New names (the 2b check, "discriminates", "coverage") go through `gc glossary add` first.

## 9. The page during trials (ruled 2026-10-15: after the ingredients; built 2026-10-16: `bin/trials.py`)

`bin/dash.py` renders once from files. For trials the signer watches while lands happen, so the page must rebuild
itself: a watcher that re-renders when a run's `results.json` or a state dir's ledger changes, and a page that
reloads on a timer. Still no server and no network module (K6): a file the browser re-reads. Built after 2 to 8.
Built: `python3 bin/trials.py --run RUN [--state DIR] [--every 5]` polls the run folders and state dirs (land.log,
row.json, error logs, demos' drive.json, results.json, ledger), re-renders through dash.py on any change, writes
`TRIALS.html` atomically. Before results.json exists the page is built from the per-ticket files as they land
(tiles: tasks started, landed, struck, not minted; a row per ticket and demo); after, dash.py's full run section.
A meta refresh reloads it; scroll position is kept; a banner says "watcher stopped" when the stamp ages past four
intervals, and "a demo is driving the screen" while the runner holds `.demos.lock` (T9). Tested on a fake run.

## 6b. The repo's own interpreter (found while gathering 6)

Every set2 project runs on CPython 3.8 in its own venv (none of them install on 3.14). The gate runs its checks with
the interpreter gc runs under: C1 and U1 use `sys.executable`, E1 uses `python3` from PATH. So on a set2 repo the
checks would import nothing. Build: `gc init --python PATH` records the repo's interpreter in the manifest; gc land
exports it as `REPO_PYTHON` to every check; E1, C1 and U1 run the repo's tests and claims under it (the check's own
logic stays on gc's Python). Kernel change (manifest, gc land, verify env) plus the three checks: a pack bump.
Plant: a repo whose manifest names a different interpreter has its tests and claims run under that one (the plant
can point at the same python by a second path and prove the env var reaches the check). Required before any set2
run; not a trial.
Built 2026-10-15 in pack v29: manifest `python` (`gc init --python`), `REPO_PYTHON` to every check (`gc land`, `gc verify`, `gc check`), its tree read-only in the sandbox; E1, C1, U1 run under it; plant `repo_python`.

Also found in 6: of 34 real bugs, 25 are T7 (partial), 2 are T9, and 7 crash on an input the suite never gives.
COUNTERFEITS.md has no species for "crashes on an untested input". Real bugs in mature libraries are partial, not
hollow; the shape species (T1, T2, T3, T8) did not occur once. A species for the loud-on-untested-input case is a
COUNTERFEITS.md edit for the signer to rule on.
