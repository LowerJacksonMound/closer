# Proposal: the plan to MVP, and the UI (2026-10-19)

Ian ruled on D1 to D5 on 2026-10-19 (KERNEL.md T10 to T14); the plan runs in this order. T15: step 4 stands, one new signer-written task. T12: the UI is in the MVP definition, placed as rows B2a and C2 below. Turns the note "two to three sessions: claims; the run and first miss loop; a
short one for step 4; 10 to 15 meter points if the miss loop stays small" into numbered steps with inputs,
outputs and a done-when each, and adds the UI track that was never written down. Rulings it needs are listed
first (standing rule: a ruling is written into a law doc before other work).

## 0. Where it stands (facts, 2026-10-19)

- Live pack v30, 39/39 plants. Pack v31 owed: E1 names no failing test under pytest < 5 (set2's four old venvs);
  the decision is right, the name is wrong. Evidence-naming fix, needs one plant.
- Internal set sealed: 33 honest trees (familyguy 16, tower 17), 66 counterfeits, 80 counterfeit functions, every
  item checked WORKING with demos (`set/WORKING_COUNTERFEITS.txt`, 2026-10-16).
- External set2: 34 real bugs, 9 projects, 6 of species T11 (not Closer's, own column).
- Runner ready: `prove.py --per-item --demos`, `prove.py --set2`, `--claims-dir`, `--rescore`; smoke-tested on
  set2 (thefuck/21, tqdm/3). `bin/trials.py` tested on a fake run only, never on a real one.
- Claims: `CLOSER_PROVING/claims/` and `claims2/` do not exist. prove.py skips a task without a claims file.
  So nothing can run until step 1 below is done: 33 + 34 = 67 claims files.
- MVP (MVP_BAR.md, T8): steps 1 and 2 done; steps 3 and 4 remain. MVP = 1, 3, 4.
- UI on record: `bin/dash.py` (the signer's read-only page from a state dir or a run folder) and `bin/trials.py`
  (the same page rebuilt while a run is going). Added 2026-10-19 16:31: `bin/session.py` (renderer: one state dir, the active
  ticket only, plain labels, no run history) served live by `ui/session_server.py` on localhost (outside bin/, K6's plant);
  first watched land through the server: CLOSER_PROVING/step7 (SERVER_CMD.txt, LAUNCH_LINE.txt, poll.log). The static
  page + watcher form of 16:23 (step6) is superseded. 2026-10-19 17:35: `closer` (root script -> `ui/go.py`), the signer's
  front door: `closer go TASK.md` registers (with a pytest collection dry-run first), scans, drafts claims through a siloed
  claim agent, pauses for the signer to read them, mints, starts the page, launches the restricted writer, reports the
  verdict; `closer claims`, `status`, `stop`. First run on a fresh jmespath copy: 13 claims, accepted (CLOSER_PROVING/newrepo2/closer_go.log). Nothing else: no UI plan in the tree, the spec folder, the
  proposals, or the published artifacts. Step 4 names "the page" and that is the only mention of a UI in the bar.

## 1. Rulings to write before session A

| # | Question | Recommendation |
|---|---|---|
| D1 | Pack v31 before the run or after? T3: a pack bump reruns every trial. | Before. It is small and already decided; running on v30 means a rerun the day v31 goes live. One agent builds the proposal and plant; Ian's yes; then the run is on the pack that will stand. |
| D2 | The miss loop. On a miss, who sharpens the claims and what may they see? | A fresh claim agent per task with a miss (never the one that wrote the first claims, never one that has read a set tree). It sees what the first one saw plus the ledger's finding lines for that task: the qualname that landed or was struck and the species line from WORKING_COUNTERFEITS.txt. Never the counterfeit tree, never the honest tree. The new file replaces the old; the whole task reruns per item on the same pack. Cap: two sharpening passes per task. A miss that survives two passes is a gate question: a K5 proposal, counted as one of the "pack bump or two". |
| D3 | UI scope for MVP. | U-A below: the page is the MVP UI; the console is written as a proposal, not built. |
| D4 | Step 4's task. Every backlog task of both apps is in the proving set. | Ian writes one new task (a paragraph of acceptance criteria) for one of the two apps. Ian states the claims himself for this one (the live configuration: signer, not agent). |
| D5 | Budget checkpoints. | After the first 10 claim agents, read the meter and extrapolate to 67; after the internal run; before any pack bump. A checkpoint that blows the 10 to 15 estimate stops the session and re-plans; no "one more". |

## 2. Session A: claims (step 3, first half)

| # | Step | Who | Input | Output | Done when |
|---|---|---|---|---|---|
| A0 | Write D1 to D5 into KERNEL.md (rulings) and this file's header | Ian + main thread | this proposal | KERNEL.md rows | rows exist |
| A1 | (if D1 = before) pack v31: E1 names the failing test under pytest < 5, one plant | one agent, then Ian's yes | pack/live/E1.sh, the smoke run's land.log | proposals/v31/, then live | 40/40 plants; PACK.md entry; kernel_sha256 noted |
| A2 | Claim briefs: one self-contained .md per task (33) and per bug (34), the writer-brief pattern | main thread | BACKLOG entry or set2 `criteria/<p>/<bug>.md`; base app path; COUNTERFEITS.md; README "Claims"; the non-vacuous-negative rule; the forbidden list (set/, payload/, working/, WORKING_COUNTERFEITS.txt, other agents' output, runs/) | `CLOSER_PROVING/briefs/claims/<id>.md` | 67 brief files |
| A3 | Claim agents, two at a time, one task each, T5 as amended | general-purpose agents | one brief file each | `claims/<app>/task-NN.json`, `claims2/<project>/<bug>.json` | 67 files delivered |
| A4 | Arrival check per file, mechanical | main thread | each claims file | a line in `CLOSER_PROVING/claims/CLAIMS_LOG.md` | valid JSON; no `<FILL:`; `claims_draft.py --check` lines recorded; every function the criteria name has at least one claim; a negative case per check-type function |
| A5 | Smoke before the full run | machine | one fg task, one td task, one set2 bug, `--per-item`, no demos | three small run folders | honest proceeds, counterfeits struck or the gap is a claims format error fixed here |

Checkpoint D5 after A3's first ten agents. Writers cost 77k to 125k tokens and 5 to 12 minutes each; claim
agents should be under that (no code, no demos). If ten claim agents cost more than a third of the session's
budget, stop and re-plan the remaining 57 (bigger batches per agent, or the extractor plus Ian for the rest).

Exit of session A: 67 claims files, smoke clean, meter read and written down.

## 3. Session B: the run and the first miss loop (step 3, second half)

| # | Step | Who | Input | Output | Done when |
|---|---|---|---|---|---|
| B1 | Start the watcher on the run folder (its first real run) | main thread | `bin/trials.py --run RUN --every 5` | TRIALS.html, open in the browser | page rebuilds as lands arrive; demo banner shows while the lock is held |
| B2a | UI, while B2 and B3 run unattended: harden dash.py and trials.py from what the live page shows (U-A list in section 5); no kernel file touched; the run is not paused for it | main thread | TRIALS.html of the live run | bin/dash.py, bin/trials.py | the U-A list is done or the remainder is written into C2 |
| B2a-done (2026-10-19) | Done on the live runs: the page watches five run folders at once; v32 added the not-judged column and tile; the signer's state view now lists every minted claim under its open ticket (function, call, expect) before any land. Left for C2: a visual pass with the signer on the real step-4 state dir, and the demo banner checked while a demo drives. | | | | |
| B2 | Internal run | machine, unattended (T9) | `prove.py --per-item --demos` on the live pack | `runs/<stamp>/` RESULTS.md, results.json, DASH.html, per-ticket evidence | 33 honest lands + 66 counterfeit lands + demos after each honest land, all recorded |
| B3 | External run | machine, unattended | `prove.py --set2` | `runs/<stamp>-set2/` | 34 honest + 34 counterfeit lands; T11 rows in their own column |
| B4 | Read the page, classify every miss | main thread, then Ian | the two run folders | `runs/<stamp>/MISSES.md`: one row per miss with its class | every row classed as (a) hunted counterfeit landed: claims gap or gate gap; (b) honest struck: claims fault or gate false positive; (c) demo failed after an honest land; (d) not Closer's (not a miss) |
| B5 | First miss loop per D2 | fresh sharpener agents, two at a time | brief + ledger finding lines for that task | replaced claims files; rerun of those tasks per item on the same pack | each rerun task's rows replace the old on the page (`dash.py --run` is repeatable; keep both run folders) |
| B6 | Second pass if needed, same rule; after that a K5 proposal (pack v32), written not built unless the meter allows | agents + Ian's yes | | `proposals/PACK_v32.md` | a pack bump reruns B2 and B3 fresh (T3) |

Checkpoint D5 after B3 and before B6. Exit of session B: one run folder per set on one pack where the three lines
hold (every hunted counterfeit struck, every honest clean, demos run), or MISSES.md naming exactly what does not
and why, with its class.

## 4. Session C: step 4 and the MVP record (short)

| # | Step | Who | Done when |
|---|---|---|---|
| C1 | The real task (D4): `gc init` (with `--python` and `--pytest-args` as the app needs), `gc scan`, `claims_draft.py` then Ian fills every placeholder, `gc ticket --write ... --claims`, `gc writer-setup`, launch the writer session, writer stages and lands through the gc MCP tools, `check` passes, Stop hook releases | Ian as signer, one real Claude Code writer session | `gc ledger --check` clean; `bin/dash.py --state` shows the ticket, the claims' evidence, the ledger row |
| C1-done (2026-10-19) | Done. Task 17 (watchlist prune) drafted by a siloed agent, minted `step4-01` with 22 claims and a 4-file write set, restricted writer session run headless through the signer's normal `claude` (T17); first land: proceed, no strike, E1 303 tests, C1 22/22, ledger OK. State `~/.getting-close/repo-cdf54915`, page `CLOSER_PROVING/step4/STATE.html`. | | |
| C2 | UI finished (T12): what B2a left, plus what C1 showed the signer needed | main thread | one trials page (`bin/trials.py`) is running with both the run folders (every pass, sharpen3 included) and a state dir; a fresh restricted writer session lands a ticket through the gc MCP server while that page is updating; the signer reads the live ticket, its claims, the evidence per claim, the checks, any strike or not-judged item and the ledger row on that page without the shell; MVP is not recorded (C3) before this row (T19 as amended) |
| C2 reopened (2026-10-19) | The C2-done row of ~17:00 is struck by the signer: the step-4 page (`step4/STATE.html`) was rendered 22 minutes after the land, the trials page watched six run folders and no state dir, and no file held a run and a state dir together. KERNEL T19 amended. | | |
| C2-done, C3-done (2026-10-19, 16:05, on the reopened condition) | `CLOSER_PROVING/step5/watch.sh` ran `bin/trials.py` over all 39 current run folders (full_v32, set2 and its rerun, sharpen1 to sharpen3) plus the fresh state dir `~/.getting-close/repo-77deec90` (one page, `runs/TRIALS.html`, 14 MB, 1 s per rebuild). While it ran, ticket `step5-01` (task 17 again, 22 claims, 4-file write set, fresh repo copy) was minted and a fresh restricted writer session (`step5/LAUNCH_LINE.txt`: `--restricted --settings claude-writer.json --strict-mcp-config --tools Read,Grep,Glob --permission-mode dontAsk`, through the normal `claude`, T17) landed it on the first land: proceed, 303 tests, 22 of 22 claims, ledger OK. The page rewrites, copied as they happened (`step5/snapshots/`): minted, nothing staged 16:03:48; staged 1, 2, 3, 4 files 16:04:45 to 16:05:07; landed with row 1, every check's lines and the per-claim evidence 16:05:28 (ledger row 16:05:24). Writer transcript: `~/.claude/projects/-Users-ian-Desktop-CLOSER-PROVING-step5-repo/` (Read 4, Grep 3, gc tickets 1, stage_edit 5, land 1, check 1; nothing else). Page generator changes only (`bin/dash.py`: staged state, strikes against the limit always shown; `bin/trials.py`: staged files, tickets, claims and evidence trigger a rebuild); no kernel file touched (kernel hash unchanged since 15:26). Record rewritten: KERNEL T19, MVP_BAR Outcome, README Status. C4 (the console proposal) is post-MVP. | | |
| C3 | The MVP record: README Status, MVP_BAR "Outcome" (pack version, run stamps, the three lines, the not-Closer's rate), KERNEL ruling "MVP reached on pack vN", RELEASE_CHECKLIST pass, closer-status memory | main thread + Ian | written in the law docs, not in chat |
| C4 | Write `proposals/SIGNER_CONSOLE.md` (U-B below), no build | main thread | proposal exists for Ian's ruling after MVP |

## 5. The UI track

What exists, as built:

- `bin/dash.py`: one self-contained HTML file, no server, no network module (K6), from any number of state dirs
  (tickets, ledger chain check, policy, per-claim evidence with expected and observed, coverage and `thin`,
  `holds_before`, U1 differences) and from a run folder (per task: honest and counterfeit rows, checks table,
  demos tile, not-Closer's tile). Read-only on everything.
- `bin/trials.py`: a watcher that re-renders through dash.py when any watched file changes, writes TRIALS.html
  atomically, meta-refresh, scroll kept, "watcher stopped" and "a demo is driving the screen" banners.
- Constraints every UI option inherits: K6 (kernel, scanner, pack and adapters import no network module); K7
  (the scanner writes nothing); evidence and the ledger file are signer-only and the writer never reads them;
  the writer session has no tools but Read, Grep, Glob and the gc MCP server.

Three scopes:

| | What | Cost | Kernel change |
|---|---|---|---|
| U-A: the page is the MVP UI | Harden dash.py and trials.py on their first real run (B1) and on step 4 (C1): a signer's-state section (which tasks have claims, which are minted, strikes per task against gets_through_anyway), evidence drill-down per claim, run and set2 and state dir on one file. | inside sessions B and C | none |
| U-B: the signer's console | A local page where the signer does the signer's steps: init, scan, see the extractor's draft, fill placeholders in a form, mint, copy the launch line, watch lands, read evidence. Needs a localhost process. To keep K6 as written it lives in a new top-level dir (`console/`), outside the four K6 dirs, and shells out to `gc`; it never imports kernel code that would then import a network module. Ruling needed: is a localhost server outside the four K6 dirs allowed. | one to two sessions | none in the kernel; a K6 clarification |
| U-C: a shared page with Code Radar | Code Radar's dashboard is Dash/Plotly on :8080, its own system. T6: the two do not talk; the repo is the only shared surface. | out of scope until CR work | not applicable |

Ruled (T12): the UI is part of the MVP definition; U-A is its scope, done in B2a and C2. U-B written as a
proposal in C4 and ruled on after MVP. U-C not before CR.

If a UI plan was made earlier somewhere not on disk (a chat, a doc elsewhere), it was not found by this search of
the tree, `CLOSER_SPEC_2026-10-10/`, `proposals/`, `~/Desktop`, and the published artifacts; point at it and it
is folded in here.

## 6. Budget, as Ian stated it

Two to three sessions, 10 to 15 meter points if the miss loop stays small, room for a pack bump or two. This plan
keeps those numbers and adds the D5 checkpoints so an overrun is caught at a known place, not at the end.
