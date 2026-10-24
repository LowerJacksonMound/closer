# Post-MVP: the ten, and where each stands

Written 2026-10-21 (Ian: "find the list of the top 10 tasks to run post MVP and knock these out"). The list was
never on disk: it was the highest-impact answer given on 2026-10-19 ~19:00 (memory) plus the post-MVP queue in
KERNEL T13 / MVP_PLAN C4, plus what the v33 rerun of the external set left behind. Ordered by impact over cost.
MVP stands as recorded (KERNEL T19, pack v32); nothing here reopens it.

| # | Task | Why it is on the list | Status 2026-10-21 |
|---|---|---|---|
| 1 | `judge_detection` as an S1 rule (KERNEL T20's first application) | the one counterfeit mechanism no claim can catch: code that behaves only while judged | **LIVE as pack v34 (2026-10-21, Ian: "lets do it")**: rule extended first on the review's three points (folded strings, setattr, environ walks, module words), 0 hits in application code before and after; 45 plants; every registered repo rescanned; the T3 set rerun recorded below |
| 1b | `dynamic_code` advisory + the inner-string scan (Ian's second step under T20, 2026-10-21) | where a counterfeit hides the four probes; honest code does it 1 file in 100, so a signal, not a strike | **LIVE as pack v35 (2026-10-21, Ian: "let's move forward")**: `proposals/PACK_v35.md`; note shown by default on the page, in `closer inspect` and on `closer go`'s accept line; a probe inside a constant string is struck citing both lines; 0 probes in 29,169 files' constant strings; plant passes on a scratch copy. Needs the signer's yes, then 7 go-live steps |
| 2a | Reopen the internal set's three criteria-open items (the review's list, 2026-10-21 night) | the only remaining gap on the internal set | **CLOSED**: criteria in the BACKLOGs, pass-3 claim agents, two reruns. The first rerun showed two of my sharper criteria had gone past the gap (fg16 end wrap-around, td07 flying on after the target died) and struck the honest trees; both narrowed to the gap itself, claims trimmed as signer edits (CLAIMS_LOG). Final: honest 3 of 3 land, 7 of 7 counterfeits struck, all three T7-a items caught and named. Internal set: 0 landed, **0 criteria open**, honest 32 of 33 |
| 2b | The two probe rulings | close two ways to hide a probe | **LIVE as pack v37 (2026-10-21 night, Ian: "Yes. Ship it as proposed.")**: `proposals/PACK_v37.md`. `trace_replaced` (plain settrace / setprofile) is a verdict: 0 in application code and every honest ticket, honest hits only in debuggers, coverage, doctest, twisted's fork. `probe_unfoldable` (getattr / setattr on sys with a runtime name) is an **advisory, not a verdict**: 134 honest hits, every one a stdout / stderr swap (stdlib `redirect_stdout`, pytest capture), so T20's bar is not met; shown as a note, counted in the load, promotable later with the number beside it. Plant (4 lands) passes on a scratch copy; needs the signer's yes |
| 2c | Page wording for unreadable constant strings | distinguish "scanned, no probe" from "not parseable" | **done** (scanner, in the tree, no verdict change): `dynamic_code ... of a constant string that could not be read (not Python the scanner can parse); treated as built at runtime`; 68 such strings on the corpora had read as scanned |
| 2d | Prune the stale demo state dirs | two state dirs pointed at repos that no longer exist | **done**: `closer forget` lists them, `closer forget --gone` removes them (kills a watcher or server first); the two were removed; front door only |
| 2e | Decide whether the page can record a decision | the only blocker is the choice | **RULED 2026-10-21 (Ian): the page stays a viewer.** Decisions stay in the shell (go, inspect, amend); an acting page would need a loopback-is-the-signer ruling plus an authentication and ledger-write path, extra surface for no current need. Revisit only if the shell round-trip becomes the real friction in use |
| 1e | Console A, read-only (Ian's pick 2026-10-21 evening) | the signer's read side on one page, no act on the page | **done, front door**: drafted-not-minted section (claims, contradictions, checker lines from `signer/claims_check.txt`), a `next:` line per state with the shell command, advisory-load line; `closer status` prints it; SIGNER_CONSOLE.md updated; B still needs a ruling |
| 1f | Measure the advisory load (items 3 and 4 of the same pick) | learn whether the new evidence is rare and seen or noise | **counter built, clock started**: `session.advisory_load` counts lands with a note by rule plus the watcher's change events (new `signer/watch_log.jsonl`, one line per change of the changed-outside set); shown on the page and by `closer status`. Standing at build time: 0 notes in 25 real rows across 23 state dirs (the one honest `eval` ticket in the sets had it pre-existing). Decision point: after 50 real lands, if notes are under 1 in 10 and read, leave; if noisy, tighten the constant-string recursion or promote the useful subset. Also fixed: stand-down notes were not rendered on the page or by inspect (v36 gap, closed) |
| 1d | Data-flow evidence on every probe + a pack-level stand-down list (the review's third step, 2026-10-21 evening; Ian: evidence never a condition, both line numbers in the line) | the strike line says where the answer goes (`asks at line 10; the answer is stored in judged at line 10, which reaches the branch at line 11`); allowances are a pack list, said as notes, not a silent heuristic | **LIVE as pack v36 (2026-10-21, Ian: "Lets run 'em")**: `proposals/PACK_v36.md`; scanner half in the tree (evidence only, 0 verdict change, kernel hash 70040d7a), `proposals/v36/S1.sh` + `s1_stand_down`, plant passes on a scratch copy, 35-snippet regression exact; measured: honest tooling branches on the answer by trade (35 of 65 hits store and read it), which is why it is evidence only. Needs the signer's yes |
| 1c | The repo watcher (the review's "periodic re-scan", 2026-10-21 evening) | an edit outside the gate between the freeze and the next land is never scanned (a file no ticket touches) or charged to the writer (a file a ticket later touches) | **done, front door, no pack change**: `ui/watch.py` beside the page server (started by `closer go`, or `closer watch`; `closer stop` ends it); every 4 s it hashes the registered roots, names each .py file that differs from the frozen World and was not changed by a landed ticket, runs the scanner on it and lists the new findings with qualname, line and reason; the page shows a red/amber "CHANGED OUTSIDE THE GATE" section, `closer inspect` and `closer status` print it. Verified on a scratch repo: quiet when unchanged, a probe added outside the gate named, a landed ticket's file not flagged, a later outside edit to that file flagged |
| 2 | The external set after v33: cookiecutter 2 and 3, black 4 | v33's reason to exist was naming these; the "beside the bar" line in MVP_BAR was waiting on it | **done where it can be**: black 4 honest lands (the v33 strike was transient: 103/103 outside the gate, proceed on rerun). cookiecutter: coverage was the first cause (addopts `--cov` writes `.coverage` into the read-only tree), fixed in `set2/BASE_CHECKS.txt`; the second cause is the suite itself writing rendered projects into its own tree (K2 holds it read-only), handled by the deselect lists `set2/_tools/deselect/cookiecutter/{2,3}.txt`; the counterfeit side is caught and named on every pass. Final honest standing: see the last line of this file |
| 3 | Drafter checklist from the misses | every sharpening pass fixed a claim fault of the same ten kinds | **done**: ten sharpness lines in the claim brief (`ui/go.py` CLAIM_BRIEF), each a way a counterfeit got through or an honest tree was struck in the runs; tested on the demo task: the agent now claims off-example inputs and float tolerances |
| 4 | Cold-repo blind runs as the standing measure | the sealed sets were built with the gate in view; a repo Closer never saw is the real number | **done**: `CLOSER_PROVING/COLD_RUNS.md` (the four runs so far: jmespath twice, inflection, the contradicting task; honest 3/3 after an environment fix, counterfeit struck and named 8/8, 0 landed) and `CLOSER_PROVING/bin/coldrun.sh` (clone, doctor, go, one restricted writer per counterfeit brief, results file) |
| 5 | `inspect` and `amend` commands | the signer reads a verdict with the shell or the page; the registration could only be changed by re-running `go` | **done in the front door, not in gc**: `closer inspect [TICKET]` (every check and claim in words, not-judged, evidence path; `--raw`), `closer amend` (show or change interpreter and pytest args, rescan). In `ui/go.py`, no kernel file touched; moving them into `bin/gc` is a kernel change and waits for a word |
| 6 | C4: the signer's console proposal (U-B) | MVP_PLAN C4, "proposal exists for Ian's ruling after MVP" | **done**: `proposals/SIGNER_CONSOLE.md`; most of U-B was taken by `closer go` and the session page; what is left is the signer's decisions on the page, with a read-only recommendation (A) and the ruling an acting page (B) would need |
| 7 | Sharper text for the three criteria-open items | T18: the fix is sharper text; the set may be reopened | **done**: `CLOSER_PROVING/set/CRITERIA_OPEN.txt` carries one sharper criterion each for fg08, fg16, td07; not yet in any BACKLOG (the apps' files are the signer's) |
| 8 | The T17 open item: 38 `fsv_get` calls in the step-4 writer transcript | a tool outside the declared set, seen in a restricted session | **closed**: every call failed `No such tool available`; the proxy's marker text taught a tool the client did not have; nothing ran. Recorded in KERNEL.md Known limits |
| 9 | Law docs and the release record after v33 | README said "version 32" beside "v33 is the live pack"; no RELEASE_CHECKLIST pass for v33 | **done**: README Status line; RELEASE_CHECKLIST pass block for 2026-10-21 (plants, glossary, kernel hash recorded in KERNEL.md Kernel files) |
| 10 | Code Radar join (T13) and a Linux sandbox | both-apps rule; the gate is macOS-only (`sandbox-exec`) | **not started, by design**: T13 says after MVP and after a word; the Linux sandbox (bwrap or unshare in place of sandbox-exec, the one 75 that still refuses a land) is a kernel change and a second platform to prove. Notes only, below |

## Notes on 10

- Code Radar join: T6 holds (the two do not talk; the repo is the only shared surface). What Closer would copy
  from Code Radar (T13) is nothing it lacks today; what Code Radar would get from Closer is the ledger row and the
  evidence file per land, read-only. The join is therefore a Code Radar reader of `<state>/ledger.jsonl` and
  `<state>/evidence/`, no Closer change. The Code Radar MCP in this session's config points at a folder that no
  longer exists (`CODE_RADAR_REFURBISH`; the tree is `NEW_CODE_RADAR_REFURBISH` and `CLOSER_N_CODERADAR`).
- Linux sandbox: `bin/gc` refuses a land without `sandbox-exec` (the one 75 not let through, T16). A Linux
  equivalent needs the same three properties: the repo and interpreter trees read-only, temp writable, no network
  (I2). `bwrap --ro-bind` gives them; `unshare` alone does not give read-only. Kernel change (gc, verify_ticket), a
  plant per property, and a proving run on Linux before it is said to hold.

## Standing of the external set after this session

Pack v33, 2026-10-21: honest fixes 34 of 34 land clean (black 4 on rerun; cookiecutter 2 and 3 on pass 4, after
coverage was turned off and 68 / 71 tests that write into the tree or read outside it were named in the deselect
lists); buggy trees 34 of 34 struck, 28 named, 0 landed. Runs: `runs/post_v33-set2-black4`,
`runs/post_v33-set2-cookiecutter4`. Recorded in MVP_BAR.md beside the bar.

## T3 rerun on pack v34 (2026-10-21, `runs/full_v34` 13:09 to 13:56, `runs/full_v34-set2` 13:56 to 14:48; lands only, no
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

## T3 rerun on pack v35 (2026-10-21, `runs/full_v35` 15:18 to 16:11, `runs/full_v35-set2` 16:11 to 17:0x; lands only).
Both sets row for row as v34: internal 0 of 80 landed, the same 3 criteria open, honest 32 of 33 (tower 06);
external 34 of 34 struck (28 named), 0 landed, honest 33 of 34 (scrapy 4 still the `0.0.0.0` environment strike,
`curl` to 0.0.0.0 still refused at 17:00). `judge_detection` hits 0, `S1 note` lines 0: the one honest ticket with
an `eval` (tqdm 7) carries it in the base tree too, and a note is said only for what a ticket introduces. Pack v35
changes no verdict on either set.

## T3 rerun on pack v36 (2026-10-21, `runs/full_v36` 17:10 to 18:02, `runs/full_v36-set2` 18:02 to 18:54; lands only).
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
## T3 rerun on pack v37 (2026-10-21 night, `runs/full_v37` to 21:04, `runs/full_v37-set2` 21:04 to 21:53; lands only).
Internal 33 of 33 on the reopened set: 0 landed, 0 criteria open, honest 32 of 33 (tower 06), `trace_replaced` 0,
notes 0 — the pass-3 claims and sharper criteria standing exactly as expected. External 34 of 34 struck (28 named),
0 landed; honest 32 of 34 in the run, the two strikes scrapy 3 and 37, both at E1 baseline on
`test_ftp_download_notexist` (a network-dependent FTP test), both honest-clean on v36. scrapy 3 and 37 rerun
2026-10-21 22:13 with the network settled (VPN down, `0.0.0.0` and `127.0.0.1` bind; `runs/post_v37-set2-scrapy3`,
`runs/post_v37-set2-scrapy37`): both honest proceed, both counterfeits struck. The external set on v37 therefore
stands at 34 of 34 honest clean and 34 of 34 struck, 0 landed; the two strikes were the environment of the day, as
with scrapy 4 before. Pack v37 changes no verdict on either set.

## T3 rerun on pack v38 (2026-10-21/22 night, `runs/full_v38` 22:52 to 23:40, `runs/full_v38-set2` 23:40 to 00:27; lands only).
Internal 33 of 33: 0 landed, 0 criteria open, honest 32 of 33 (tower 06), notes 0; the per-item table is identical to
v37's line for line. External 34 of 34 struck (28 named), 0 landed; honest 34 of 34 clean in the run itself, scrapy 3
and 37 both honest proceed this time (no FTP strike, network settled all evening), which confirms the v37 strikes as
the environment of the day. Pack v38 changes no verdict on either set; no ticket in either set uses the
`"<runner>" in sys.modules` form, as expected from the 0 hits in application code.
