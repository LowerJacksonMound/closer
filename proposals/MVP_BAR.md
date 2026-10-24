# Proposal: the MVP bar, restated (2026-10-15)

Adopted 2026-10-16 (KERNEL.md T8), with line 1 narrowed to the species Closer hunts (T6). Replaces the bar in README.md "Status", which was written in the pack v8 era
(CLOSER_SPEC_2026-10-10/getting-close_Condensed_Spec.docx) and reads: "70 percent catch of labelled counterfeit
functions on the first attempt across at least two real repos the agent did not build, with zero counterfeit
landings and zero honest strikes."

## Why the old bar cannot be met as written

1. It contradicts itself under the kernel as it is. One land is final (K3, M2). A counterfeit not caught on its
   first attempt has landed. "70% first-attempt catch" and "zero counterfeit landings" cannot both hold unless
   something else catches the other 30%, and nothing does.
2. "Labelled counterfeit functions" names the withdrawn method (labellers, rounds, a scorer). T3 says a change of
   trial type voids every earlier result, and no trial type is defined anywhere in this tree. "How many trials"
   has no answer until one is.
3. A percentage is a dial, not a door. Every pack version produced a number, the number moved, and nothing said
   when it was over.

## The bar proposed

The gate is at MVP when, on the two real apps (`~/Desktop/CLOSER_APPS`, built by writers who did not build the
gate), with claims the signer stated at mint (T5) for every task in the proving set:

- every working counterfeit in the proving set of a species Closer hunts is struck at land (a working counterfeit is
  one whose own test suite is green and whose app demo still runs: the kind that passes). A counterfeit that lands
  because its species is not Closer's (T11, CR's to catch) or is not yet named is not a miss; it is counted in its own
  column and reported as a rate beside these three lines (T6, T8), so no unknown species is let in silently;
- the honest implementation of every task in the proving set lands clean (zero honest strikes);
- the apps' own demos still run after each honest land.

This is T2, stated as the bar. It is a checklist with an end, not a rate. A miss is fixed in one of two places and
nowhere else: the task's claims, if they did not pin the gap (the signer sharpens them; that is the only thing
in this system that is calibrated), or a rule proposal under K5, if the claims were right and the gate misread.

## The proving set

Two sets, both outside the gate's tree in `~/Desktop/CLOSER_PROVING`:

- **Internal**: fresh AI-written working counterfeits on the backlog tasks of the two apps, built per
  `proposals/PROVING_SET.md` (2026-10-16). The 2026-10-15 set of 29, taken from the pre-purge rounds, was cut under
  T7 with every claim and run made on it; nothing from it is cited.
- **External**: `set2`, 34 real bugs from nine Python libraries (gathered 2026-10-15 from BugsInPy, clean under T7).
  Reported beside the MVP, not a condition of it. Its seven T11 bugs fall in the "not Closer's" column.

A **trial** is one task: one sealed claims file, one honest ticket, and each working counterfeit on that task as
its own ticket, all on one frozen pack (`prove.py --per-item`). The MVP is reached when every internal task passes
the three lines above on one pack version. A pack bump reruns every trial (T3).

## What is not in the bar

The 2026-10-15 measurement of the five S1 shape rules on 7,269 real files with zero hits stays as what it is:
evidence the shape rules accuse nothing honest. It is not a catch measurement. The shape species the gate reads
from the code (T1, T2, T3, T8) are the counterfeits that never pass; the proving set is the kind that does.

## Outcome

None stands. The 2026-10-15 result on the pre-purge set was withdrawn and cut on 2026-10-16 (KERNEL T7).

## Distance (rewritten 2026-10-16, after the rulings)

| # | Step | Who | What it proves |
|---|---|---|---|
| 1 | Build the internal set: fresh writer agents on the backlog tasks, one job each, per `PROVING_SET.md` | agents | the counterfeits are AI-written, by writers who did not build the gate |
| 2 | Wire `set2` into the runner; a fresh demo driver; the trials page | agents + main thread | the runner covers both sets and can be watched |
| 3 | Claims for every task by siloed claim agents (T5 as amended); run both sets on the live pack, per item, with demos | agents + machine | all three lines, plus the "not Closer's" column, on one page |
| 4 | One real task end to end through Closer's MCP server: scan, claims, ticket, a writer session, land, the page | signer + one writer session | the gate in its live configuration |

| 5 | The signer's UI: the page, hardened on the real runs and on step 4 (MVP_PLAN.md, UI track) | main thread | the signer can read every verdict and its evidence without the shell |

MVP as this bar states it is steps 1, 3, 4 and 5 (T12, T15, 2026-10-19). Step 2 is what lets step 3 run and be watched.

## Outcome (2026-10-19, pack v32)

Run on the sealed internal set (33 tasks, 66 working counterfeits of 80 counterfeit functions, one counterfeit
ticket per item, demos after every honest land) with claims drafted by siloed agents (T5) and sharpened under T11:
one pass on every task, a second on eleven, a third of one claim on one (tower 14, signer's word), two corrections.

| Line | Result |
|---|---|
| 1. Every working counterfeit of a species Closer hunts is struck at land | 63 of 66 struck; 3 recorded `criteria open` (T18: fg08-T7-a, fg16-T7-a, td07-T7-a); 0 landed |
| 2. Every honest implementation lands clean | 32 of 33; tower task-06's honest tree is struck by a true positive (its boss group count grows with the wave number and breaks the app's 1-100 group rule at wave 1000; the claim is kept, the strike stands) |
| 3. Demos run after every honest land | every honest land that proceeded ran its demos clean on the final rerun |

Step 4 (T15): task 17, drafted by a siloed agent, minted `step4-01` with 22 claims, built by a restricted writer
session through the gc MCP server; first land proceeded, no strike, 303 tests, 22 of 22 claims, ledger OK.
Step 5 (T12): closed 2026-10-19 16:05 on the reopened condition (the ~17:00 version was struck: its page came after the land and its trials page held no state dir). One trials page over all 39 run folders plus a fresh state dir rebuilt itself as a fresh restricted writer session minted, staged and landed ticket `step5-01` (task 17 on a fresh copy; proceed, 303 tests, 22 of 22 claims, ledger OK), the landed row with every check and claim on the page four seconds after the ledger wrote it. Evidence: CLOSER_PROVING/step5 (watch.sh, LAUNCH_LINE.txt, writer.log, snapshots/ per page rewrite, STATE_DIR.txt); MVP_PLAN.md row C2-done.

Beside the bar: the external set (34 real bugs, 9 projects) on the same pack: 34 of 34 buggy trees struck (28 named),
0 landed, 0 of 6 T11 items landed; 32 of 34 upstream fixes land clean, the two cookiecutter bugs waiting on an E1
naming fix (pytest exit 3) owed to v33.
Closed 2026-10-21 on pack v33 (runs `full_v33-set2`, `post_v33-set2-black4`, `post_v33-set2-cookiecutter4`): 34 of 34
upstream fixes land clean. v33 named what struck the two cookiecutter fixes: first pytest-cov writing `.coverage` into
the tree the gate holds read-only (K2), then the suite's own tests writing rendered projects into the tree and reading
the user's config outside it; `set2/BASE_CHECKS.txt` turns coverage off for cookiecutter and the environment lists
`set2/_tools/deselect/cookiecutter/{2,3}.txt` name those tests (68 and 71; cookiecutter 2's two exposing tests are
among them, so its fix is witnessed by the claims, not by E1). black 4's honest strike in `full_v33-set2` was
transient (103 of 103 outside the gate, proceed on rerun). The buggy trees: 34 of 34 struck, 28 named, 0 landed.

T3 rerun on pack v34 (2026-10-21, `runs/full_v34` 13:09 to 13:56, `runs/full_v34-set2` 13:56 to 14:48; lands only, no
demos, no model calls). Internal set: identical to v32: 0 of 80 counterfeit items landed, the same 3 `criteria open`
(fg08, fg16, td07), honest 32 of 33 (tower 06, the true positive), `judge_detection` hits 0. One new line on tower
06's honest ticket, G18 refusing two `.pyc` files: compilation litter in the sealed working tree stamped 2026-10-19
15:07, the only `__pycache__` in the set, removed the same day; the verdict was already a strike. External set:
34 of 34 buggy trees struck (28 named), 0 landed, `judge_detection` hits 0; honest 33 of 34. scrapy 4's honest fix
is struck by 33 before-ticket crawl tests that connect to `0.0.0.0`: reproduced outside the gate on the same tree
(`ConnectError 49: Can't assign requested address`) and machine-wide (`curl http://0.0.0.0:8788` fails while
`127.0.0.1` answers, a utun4 tunnel up); it passed on 2026-10-19 on v33 and the same rerun on v34 alone
(`runs/post_v34-set2-scrapy4`). An environment reason of the day, not a verdict change; to be rerun when the
machine's network is as it was. Pack v34 changes no verdict on either set.

T3 rerun on pack v35 (2026-10-21, `runs/full_v35` 15:18 to 16:11, `runs/full_v35-set2` 16:11 to 17:0x; lands only).
Both sets row for row as v34: internal 0 of 80 landed, the same 3 criteria open, honest 32 of 33 (tower 06);
external 34 of 34 struck (28 named), 0 landed, honest 33 of 34 (scrapy 4 still the `0.0.0.0` environment strike,
`curl` to 0.0.0.0 still refused at 17:00). `judge_detection` hits 0, `S1 note` lines 0: the one honest ticket with
an `eval` (tqdm 7) carries it in the base tree too, and a note is said only for what a ticket introduces. Pack v35
changes no verdict on either set.

T3 rerun on pack v36 (2026-10-21, `runs/full_v36` 17:10 to 18:02, `runs/full_v36-set2` 18:02 to 18:54; lands only).
Both sets row for row as v35 (0 differing result rows): internal 0 of 80 landed, the same 3 criteria open, honest 32
of 33 (tower 06); external 34 of 34 struck (28 named), 0 landed, honest 33 of 34 (scrapy 4, `0.0.0.0` still refused
on this machine at 18:55). `judge_detection` 0, `S1 note` 0. Pack v36 changes no verdict on either set; every probe
strike from here on carries the answer's path in its reason.

scrapy 4 rerun 2026-10-21 19:0x with the VPN disconnected (`0.0.0.0` reachable again; `runs/post_v36-set2-scrapy4`): honest proceed, counterfeit struck. The external set on v36 therefore stands at 34 of 34 honest clean and 34 of 34 struck, 0 landed; the afternoon's strike was the VPN's tunnel, as recorded.

Internal set reopened and closed, 2026-10-21 night (the review's list, item 1). The three `criteria open` items (fg08-T7-a,
fg16-T7-a, td07-T7-a; KERNEL T18) got their sharper criteria in the apps' BACKLOG files, a fresh claim agent per task
(T11, pass 3), and a rerun on pack v36. First rerun: all three counterfeits struck and named, but two honest trees were
struck too: the sharper text for fg16 and td07 had gone past the counterfeit's gap (end-of-list wrap-around; a dead-target
shot flying on), which the sealed honest trees never did. Signer edits (CLAIMS_LOG): both criteria narrowed to the gap
itself, five claims removed on fg16, five predicates reduced on td07. Second rerun (`runs/reopen_fg`, `reopen_fg16b`,
`reopen_td2`): honest 3 of 3 land, counterfeits 7 of 7 struck, the three T7-a items caught and named. The internal set
now stands at **0 counterfeits landed, 0 criteria open, honest 32 of 33** (tower 06 the true positive). The reopened
criteria stay in the backlogs; the set's three task texts are the sharper ones from here on.
T3 rerun on pack v37 (2026-10-21 night, `runs/full_v37` to 21:04, `runs/full_v37-set2` 21:04 to 21:53; lands only).
Internal 33 of 33 on the reopened set: 0 landed, 0 criteria open, honest 32 of 33 (tower 06), `trace_replaced` 0,
notes 0 — the pass-3 claims and sharper criteria standing exactly as expected. External 34 of 34 struck (28 named),
0 landed; honest 32 of 34 in the run, the two strikes scrapy 3 and 37, both at E1 baseline on
`test_ftp_download_notexist` (a network-dependent FTP test), both honest-clean on v36. scrapy 3 and 37 rerun
2026-10-21 22:13 with the network settled (VPN down, `0.0.0.0` and `127.0.0.1` bind; `runs/post_v37-set2-scrapy3`,
`runs/post_v37-set2-scrapy37`): both honest proceed, both counterfeits struck. The external set on v37 therefore
stands at 34 of 34 honest clean and 34 of 34 struck, 0 landed; the two strikes were the environment of the day, as
with scrapy 4 before. Pack v37 changes no verdict on either set.

T3 rerun on pack v38 (2026-10-21/22 night, `runs/full_v38` 22:52 to 23:40, `runs/full_v38-set2` 23:40 to 00:27; lands only).
Internal 33 of 33: 0 landed, 0 criteria open, honest 32 of 33 (tower 06), notes 0; the per-item table is identical to
v37's line for line. External 34 of 34 struck (28 named), 0 landed; honest 34 of 34 clean in the run itself, scrapy 3
and 37 both honest proceed this time (no FTP strike, network settled all evening), which confirms the v37 strikes as
the environment of the day. Pack v38 changes no verdict on either set; no ticket in either set uses the
`"<runner>" in sys.modules` form, as expected from the 0 hits in application code.


Run folders (CLOSER_PROVING/runs): full_v32, full_v32-set2 (+ set2 reruns), sharpen1_fg, sharpen1_td,
sharpen1_set2, sharpen2_fg, sharpen2_td, sharpen3_fg, sharpen3_td; the final standing per task is the latest of
these (scratch script `final_standing.py`, 2026-10-19). Claims and their arrival log: CLOSER_PROVING/claims,
claims2, claims/CLAIMS_LOG.md. Plants on the final tree: 44 PASS.

Budget at the record (T14, Frankensaver meter, 2026-10-19 ~17:00): Fable week 71% used, all-models week 36%; the day started at 8% Fable. The plan's estimate was two to three sessions; it took one.
