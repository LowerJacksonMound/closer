# RELEASE CHECKLIST

Before a pack version or a kernel change is releasable. Regenerated 2026-10-11. Every box, every time.

## Any change

- [ ] `gc selftest` prints `gc: selftest PASS` and exits 0. Every plant runs the real kernel.
- [ ] A changed rule has a plant that fails without the change and passes with it.
- [ ] `gc glossary check` exits 0. Retired names show as "reads as"; law docs are not rewritten (G1).
- [ ] New names went through `glossary add`; none duplicates a term or a retired name.
- [ ] Ledger rows are still `draft` (KERNEL L1).
- [ ] Law docs (KERNEL, PACK, WORLD, DESIGN, README) match the code.

## Pack change (K5)

- [ ] The check was a proposal first. Plants still split: honest cases pass, planted counterfeits fail.
- [ ] Signer yes.
- [ ] `pack/live/PACK.json` `pack_version` raised; each changed check's "Live in pack vN" header updated.
- [ ] Queued pack edits (PACK.md, "Queued for the next bump") are folded into the same bump.
- [ ] Outstanding tickets are known to be rejected by the bump; the signer re-mints them.

## Kernel change

- [ ] No change to the World shape without a pack bump (WORLD.md).
- [ ] K1–K5 still hold (KERNEL.md); the plants for K1 (W1), K2 (`sandbox_write_refused`) and the strike
      rules pass.
- [ ] Writer surface unchanged unless ruled: `writer-setup` launch line, `pre_tool.py` allowlist and
      `gc_mcp.py` tools still match (`cutover_denied`).
- [ ] `kernel_sha256` in new ledger rows differs from older rows; that is expected and recorded.

## Pass 2026-10-19 (kernel edits of the day: T17 writer launch, the pre-purge sweep, L1 wording)

- [x] `plants/run_all.sh`: 44 PASS on the final tree (scratch selftest_final.log).
- [x] `gc glossary check` exits 0 (71 terms, 5 retired, 6 retired uses read as their replacements).
- [x] `unjudged` went through `glossary add` (v32 go-live).
- [x] Ledger rows are `draft` (L1).
- [x] Law docs match the code: KERNEL T10-T18, PACK v31/v32 history and rows, README status, GLOSSARY rows.
- [x] Writer surface unchanged but for T17 (launch through the normal `claude`; tools, strict MCP config and hook unchanged); `cutover_denied` plant passes.
- [x] `kernel_sha256` differs from older rows: expected and recorded here.

## Pass 2026-10-21 (v33 record; the scanner emits `judge_detection` for proposal PACK_v34, not counted)

- [x] `plants/run_all.sh`: 44 PASS on the tree with the scanner change, rerun after its extension (scratch selftest_after2.log).
      The proposal's own plant (`proposals/v34/plants/s1_judge_detection.sh`, four lands) passes on a scratch copy whose
      PACK.json lists the rule.
- [x] `gc glossary check` exits 0 (72 terms, 5 retired, 6 retired uses read as their replacements).
- [x] `judge_detection` went through `glossary add`.
- [x] Ledger rows are `draft` (L1).
- [x] Law docs match the code: README Status (v33 is the live pack, said once), KERNEL Kernel files (the scanner change and the
      hash), KERNEL Known limits (the proxy tool), PACK.md unchanged (no pack change; v34 is a proposal).
- [x] Writer surface unchanged; `cutover_denied` plant passes.
- [x] `kernel_sha256` differs from older rows (`70c308a9…` to `59e670a8…`, scanner/): expected and recorded in KERNEL.md.

## Pass 2026-10-21, pack v34 (`judge_detection` in `s1_rules`; proposals/PACK_v34.md; signer's word "lets do it")

- [x] The check was a proposal first (PACK_v34.md, with its measurement); plants split: the counterfeit and its obfuscated
      twin are struck and named, the honest neighbour and the test-file case land.
- [x] Signer yes (2026-10-21).
- [x] `pack/live/PACK.json` `pack_version` 34, `s1_rules` + `judge_detection`; `S1.sh` header "Live in pack v34".
- [x] `plants/run_all.sh`: 45 plants. 43 PASS in the full run (scratch selftest_v34.log) plus `u1_large_spec` and
      `u1_undeclared`, which failed in that run on the overlap artefact (their temp-tree listing saw the T3 set rerun's
      lands) and PASS rerun alone under a private TMPDIR. `s1_judge_detection` PASS on the live tree.
- [x] `gc glossary check` exits 0; `judge_detection` through `glossary add` (its row updated for the extension).
- [x] Ledger rows are `draft` (L1).
- [x] Law docs match the code: PACK.md v34 row and History, README Status, KERNEL Kernel files (`59e670a8…`), GLOSSARY.
- [x] No queued pack edits outstanding; no outstanding tickets (every registered repo rescanned at go-live, 23 state
      dirs; 2 demo repos gone, skipped).
- [x] T3: the set rerun on v34 (runs/full_v34, runs/full_v34-set2) started 13:09; result recorded in MVP_BAR.md and
      POST_MVP.md: no verdict change on either set (scrapy 4 honest struck by the machine refusing `0.0.0.0` that day;
      reproduced outside the gate). T14: the rerun is lands only, no model calls, so the meter is not touched.

## Pass 2026-10-21, pack v35 (`dynamic_code` advisory, `s1_advisory`, the inner-string scan; proposals/PACK_v35.md; signer's word "let's move forward")

- [x] The check was a proposal first (PACK_v35.md, with its measurement); plants split: the honest `eval` ticket lands with
      the note and no strike, the probe inside a constant string is struck citing both lines, `__import__('sys')` is struck.
- [x] Signer yes (2026-10-21).
- [x] `pack/live/PACK.json` `pack_version` 35, `s1_advisory` `["dynamic_code"]`; `pack/live/S1.sh` from `proposals/v35/S1.sh`,
      header "Live in pack v35".
- [x] `plants/run_all.sh`: 46 plants, 46 PASS (scratch selftest_v35.log, run under a private TMPDIR so the concurrent set
      rerun could not touch the U1 plants' temp listing). Counts corrected the same day: v33 had 44 plants, v34 45, v35 46
      (an earlier count included run_all.sh).
- [x] `gc glossary check` exits 0; `dynamic_code` through `glossary add` (73 terms).
- [x] Ledger rows are `draft` (L1). The substance overlay's findings may carry an optional `why`; older overlays compare as before.
- [x] Law docs match the code: PACK.md v35 row and History, README Status, KERNEL Kernel files (`5cfa4632…`), GLOSSARY.
- [x] Writer surface unchanged; the page (`bin/session.py`) and front door (`ui/go.py`) show every `S1 note:` by default.
- [x] No queued pack edits outstanding; every registered repo rescanned at go-live (23 state dirs; 2 demo repos gone).
- [x] T3: the set rerun on v35 (runs/full_v35, runs/full_v35-set2) started 15:18; lands only, no model calls (T14);
      result recorded in MVP_BAR.md and POST_MVP.md: both sets row for row as v34, no verdict change.

## Pass 2026-10-21, pack v36 (data-flow evidence on every probe; `s1_stand_down`; proposals/PACK_v36.md; signer's word "Lets run 'em")

- [x] The check was a proposal first (PACK_v36.md, with its measurement); plants split: the stored-then-branched counterfeit is
      struck with both lines in the reason, the stood-down file lands with its note, the same file outside the list is struck.
- [x] Signer yes (2026-10-21).
- [x] `pack/live/PACK.json` `pack_version` 36, `s1_stand_down` `[]`; `pack/live/S1.sh` from `proposals/v36/S1.sh`, header "Live in pack v36".
- [x] `plants/run_all.sh`: 47 plants, 47 PASS (scratch selftest_v36.log, private TMPDIR). `s1_probe_flow` runs its stand-down
      case on a private copy of the kernel dirs, so the live list stays empty.
- [x] `gc glossary check` exits 0 (no new finding name: `why` is a field, `s1_stand_down` a pack key).
- [x] Ledger rows are `draft` (L1).
- [x] Law docs match the code: PACK.md v36 row and History, README Status, KERNEL Kernel files (`70040d7a…`).
- [x] Writer surface unchanged; the page and front door already show every `S1 note:` (v35), stand-downs included.
- [x] No queued pack edits outstanding; every registered repo rescanned at go-live (23 state dirs; 2 demo repos gone).
- [x] T3: the set rerun on v36 (runs/full_v36, runs/full_v36-set2) started 17:10, done 18:54; lands only (T14); recorded in
      MVP_BAR.md and POST_MVP.md: both sets row for row as v35, no verdict change.
      scrapy 4 rerun with the VPN off: honest proceed (runs/post_v36-set2-scrapy4); external set 34 of 34 clean.

## Pass 2026-10-21 (night), pack v37 (`trace_replaced` verdict, `probe_unfoldable` advisory; proposals/PACK_v37.md; signer's word "Yes. Ship it as proposed.")

- [x] The check was a proposal first, with its measurement; the measurement changed one rule's shape (advisory, not verdict)
      and the proposal says why. Plants split: the settrace counterfeit struck and named, the runtime-named getattr lands
      with its note, the honest neighbour lands, the tracer-named module stands down.
- [x] Signer yes (2026-10-21, the paste "On v37. Yes. Ship it as proposed.").
- [x] `pack/live/PACK.json` `pack_version` 37, `s1_rules` + `trace_replaced`, `s1_advisory` + `probe_unfoldable`; `S1.sh`
      unchanged but for its header.
- [x] `plants/run_all.sh`: 48 plants, 48 PASS (scratch selftest_v37.log, private TMPDIR).
- [x] `gc glossary check` exits 0; `trace_replaced` and `probe_unfoldable` through `glossary add`.
- [x] Ledger rows are `draft` (L1).
- [x] Law docs match the code: PACK.md v37 row and History, README Status, KERNEL Kernel files (`8871c4dd…`), GLOSSARY.
- [x] Writer surface unchanged; the page shows the new advisory as every other note.
- [x] No queued pack edits outstanding; every registered repo rescanned at go-live (23 state dirs; the two stale ones were
      pruned earlier tonight by `closer forget --gone`).
- [x] T3: the set rerun on v37 (runs/full_v37 to 21:04, runs/full_v37-set2 21:04 to 21:53) done; lands only (T14); recorded
      in MVP_BAR.md and POST_MVP.md. Internal 0 landed, 0 criteria open, honest 32 of 33 (tower 06), trace_replaced 0,
      notes 0 — exactly the expected post-reopen standing. External 34 of 34 struck (28 named), 0 landed; the run's two
      honest strikes (scrapy 3 and 37) were E1 baseline on the network-dependent FTP test test_ftp_download_notexist, both
      honest proceed on the settled-network rerun (runs/post_v37-set2-scrapy3, -scrapy37, 22:13), so the external set stands
      34 of 34 honest clean. Pack v37 changes no verdict on either set.

## Pass 2026-10-21 (night), pack v38 (`judge_detection` extended to `"<runner>" in sys.modules`; proposals/PACK_v38.md; signer's word "let's ship v38")

- [x] The check was a proposal first, with its measurement off the v34 investigation list. 41,749 files: 0 in application
      code, 38 hits all inside pytest itself, 0 with the runner-package stand-down. Argued verdict (not advisory) under T20,
      cleaner than gettrace at v34, with the one in-the-wild caveat stated.
- [x] Signer yes (2026-10-21, the paste "let's ship v38").
- [x] Scanner extension applied to `scanner/substance.py` (kernel): `_RUNNER_MODULES`, `_is_sys_modules`,
      `_is_modules_view`, `_runner_tree`, three branches in `judge_detection`. No new rule id; the forms emit
      `judge_detection` (already a verdict), so `s1_rules`/`s1_advisory`/`s1_stand_down` unchanged. `pack_version` 38.
- [x] Plant `plants/s1_runner_in_modules.sh` (four real lands): the `"pytest" in sys.modules` counterfeit struck and named,
      the folded `.keys()` counterfeit struck, the honest `"numpy"` neighbour lands, the runner-package file stands down.
- [x] `gc selftest`: 49 plants, 49 PASS (scratch v38_live_selftest.log).
- [x] `gc glossary check` exits 0 (no new id; `judge_detection` entry extended).
- [x] Law docs match the code: PACK.md v38 row + History, README Status, GLOSSARY, KERNEL Kernel files hash (`8871c4dd…` -> `5efbc87c…`).
- [x] Writer surface unchanged; a struck runner check shows as any other `judge_detection` strike.
- [x] Every registered repo rescanned at go-live under v38 (23 state dirs, 23 scanned OK; v38_rescan.log).
- [x] T3: the set rerun on v38 (runs/full_v38 22:52 to 23:40, runs/full_v38-set2 23:40 to 00:27) done; lands only (T14); recorded
      in MVP_BAR.md and POST_MVP.md. Internal 0 landed, 0 criteria open, honest 32 of 33 (tower 06), per-item table identical
      to v37. External 34 of 34 struck (28 named), 0 landed, honest 34 of 34 clean in the run itself (scrapy 3 and 37 both
      proceed; the v37 FTP strikes were the network of the day). Pack v38 changes no verdict on either set.


## Pass 2026-10-23 (release rung 0: version control, license, packaging; no kernel, pack or scanner change)

- [x] `git init`; first commit. Excluded: `__pycache__`, `.pytest_cache`, build dirs, `.DS_Store`, `.env`, `.claude/settings.local.json`, `.archive/`, `scratch/`, `*.log`, `*.zip`, `runs/`, `.getting-close/`, `*.mp4`, and `CLOSER_SPEC_2026-10-10/cli/` (a vendored clone of HTTPie with its own test certificates; nothing in Closer references it). Tracked set 1.6 MB, nothing over 1 MB.
- [x] Secret scan before the first commit: the only private keys in the tree are HTTPie's expired self-signed test fixtures, excluded with that folder. No `/Users/ian` literal anywhere.
- [x] `LICENSE`: PolyForm Noncommercial 1.0.0, canonical SPDX text, licensor block. README carries the license paragraph.
- [x] `pyproject.toml` (`closer` 0.1.0, `requires-python >= 3.10`, no script entry: `bin/gc` finds `pack/live` relative to its checkout) and `CHANGELOG.md` 0.1.0.
- [x] A stranger's `gc selftest` passes: the two plants that need a Python 3.8 / pytest 3.x interpreter now report `NOT MEASURED` (exit 77) when no such interpreter is on the machine and no `GC_PLANT_*` names one; a named-but-wrong interpreter still FAILs. `plants/run_all.sh` counts PASS / FAIL / NOT MEASURED. Result on this machine: `47 PASS / 0 FAIL / 2 NOT MEASURED`, `gc: selftest PASS`.
- [x] `closer` refuses below Python 3.10 with one sentence naming the install path, instead of a SyntaxError from `ui/go.py` on Apple's 3.9. README says how a fresh Mac gets 3.10+.
- [ ] Still to do for rung 0: the README-only install in a real second macOS user account (rung 2 tester). Personal `~/Desktop/CLOSER_PROVING` paths remain in `bin/trials.py`, `bin/dash.py`, `KERNEL.md` and `proposals/` as documentation of where the proving runs lived; env-overridable in the two plants.

## Pass 2026-10-23, rung 1

- [x] Private repo https://github.com/LowerJacksonMound/closer, branch `main`, tag `v0.1.0`, prerelease published with install, verify and known-limits notes.
