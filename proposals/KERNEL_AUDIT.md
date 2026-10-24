# KERNEL_AUDIT: every KERNEL.md table row against the spec

Audit date 2026-10-19. Read-only; KERNEL.md is not changed by this file.

Ground: `CLOSER_SPEC_2026-10-10/` — `getting-close_Condensed_Spec.docx` (Condensed), `TheRefactor1..4.docx` (R1..R4),
`IMG_CLOSER_FLOWCHART.jpg` (Flowchart). Rows audited: K1..K8, C1, R2, R4, L1, R9, M2, M3, M5/M5a, G1, I2, T1..T18,
exit codes 0/1/2/3/75 (41 rows). KERNEL.md has no D*, B* rows; the brief's list of those prefixes is empty here.

Verdicts: **SPEC** = the spec says it (quote given). **AFTER** = dated 2026-10-15 or later, or a direct consequence of
such a ruling. **BEFORE** = neither: not in the spec, not dated on or after the purge. Where a SPEC row carries a
post-purge amendment the amendment is noted as "+AFTER"; it is not a BEFORE component.

## Table

| Row | Verdict | Basis (spec quote, docx / date) | What in the code depends on it |
|---|---|---|---|
| K1 | SPEC | Condensed, Safety rules: "World is append only by id. Second write to the same id fails". | `scanner/emit.py:28` (link() never replaces); `pack/live/W1.sh` ("W1 = K1"). |
| K2 | SPEC (+AFTER) | Condensed: "Every verify runs under sandbox-exec. No sandbox means no verify"; R3 §4: "denies network and all file writes except temp directories, then re-denies the kernel, repo, Worlds, ticket, and state directories". The interpreter-tree clause is pack v29, 2026-10-15 (PACK.md v29; KERNEL "Kernel files"). | `bin/verify_ticket.py:127-150` `run_sandboxed`; `bin/gc:218,617-621`; `pack/live/C1.py:58,441`; `pack/live/U1.py:33,49,262`; `plants/sandbox_write_refused.sh`, `plants/gc_not_run_proceeds.sh:9`, `plants/repo_python.sh`. |
| K3 | SPEC | Condensed: "verify must exit 0 before a ticket is recorded as merged"; Land: "Rolls back on any failure". | `bin/gc:704` ("No row, no merge (K3)"), `cmd_land` rollback; `bin/ledger.py` lock held across land. |
| K4 | SPEC | Condensed: "Live pack and kernel paths are off limits to the agent"; R3 §3: "Refuses kernel/, pack/live/, worlds/, plants/." | `bin/apply_ticket.py` `FORBIDDEN_PREFIXES`/`is_forbidden` (:27); `bin/propose_file.py:22`; `adapters/claude_code/pre_tool.py`; `plants/cutover_denied.sh`. |
| K5 | SPEC | Condensed: "Proposals never go live without a new pack version, signer yes, and plants still split". | Every `pack/live/*.sh|.py` header ("Edit only through a new pack version (K5)"); `scanner/substance.py:2`; `bin/propose_file.py:8`; `bin/ledger.py` `pack_hash`. |
| K6 | SPEC | Condensed: "Written in standard library Python. Makes no model calls." (Recorded in KERNEL 2026-10-15, CHANGES pack v26; the "no network module" wording and "the signer's claims" are that recording, T5.) | `plants/no_model_in_gate.sh`; `scanner/lexicon.py:1`; `pack/live/U1.py:33` ("Stdlib only"); `bin/trials.py:6`, `bin/dash.py:6`. |
| K7 | SPEC | R3 §2: "The scanner does not write source and refuses to emit a World if the tree moved under it."; R1: "Worlds as immutable, write-once snapshots produced by a scanner". (Recorded 2026-10-15, pack v26.) | `plants/s1_scanner_writes_nothing.sh`; `scanner/emit.py`; `scanner/scan.py` pre-walk snapshot assertion. |
| K8 | AFTER | Written into KERNEL 2026-10-15 (CHANGES_2026-10-15_pack_v26.md line 34); species table is `COUNTERFEITS.md`, "Written 2026-10-15". The "file, line, rule, qualname" half is in the spec (R3 §7: "Diffs findings (rule + qualname)"). | `scanner/lexicon.py:8-9,40-42,110` `RULE_SPECIES`, `species_of`; `pack/live/S1.sh:8`; `pack/live/U1.py:33`; `bin/claims_draft.py:210`. |
| C1 | SPEC | Condensed: "A writer session has no write tools except the gc MCP tools. After cutover any other edit is a kernel bug."; R4: "Cutover (C1, 2026-10-05) ... Read/Grep/Glob + only the gc MCP server, --restricted". (T17 amends the launch command, 2026-10-19.) | `bin/gc:804` `cmd_writer_setup`/`writer_launch`; `adapters/claude_code/gc_mcp.py`, `pre_tool.py`; `plants/cutover_denied.sh`. |
| R2 | SPEC | Condensed, World: "Freshness is the path identity of the World not a timestamp."; R4: "Path identity instead of timestamps (R2)". | `bin/governor.py:63` stale-World reroute; `pack/live/G18.sh`; `bin/world_v1.py`, `bin/read_world.py`. No `R2` tag in code. |
| R4 | SPEC | R2 (docx), plants/: "Must-pass and must-fail fixtures that prove each rule. Signer-only. Not executed by normal gc land." | `bin/apply_ticket.py:27`, `bin/propose_file.py:22` (`plants/` forbidden, tagged "KERNEL.md R4"). |
| L1 | SPEC | Condensed, Known limits: "Ledger rows are draft with no head signature"; R4: "Ledger remains draft, no head signature (R8/R12) ... Activation and signing were explicitly deferred." | `bin/ledger.py:6,8` (`status: "draft"`); `bin/gc:678`; `plants/ledger_draft_only.sh`. |
| R9 | SPEC | R3 §10: "Runs gc-writer check with a timeout. Any non-zero exit, crash, or timeout blocks the Stop hook (exit 2)." Flowchart step 6: "Stop hook (gc-writer check)". | `adapters/claude_code/stop_gate.py:7,19`; `bin/gc:815`. |
| M2 | SPEC | Condensed, Land: "One strike closes the ticket."; R4: "One strike per ticket (M2) ... The writer cannot re-stage or re-land it." | `bin/gc:209,609-612,696`; `bin/stage.py:53`; `plants/strike_closes_ticket.sh`. |
| M3 | SPEC | Condensed, Key terms: "gets_through_anyway: Max struck tickets per task before gc stops minting. Default 2"; R4: "Syntax errors rejected before apply, no strike (M3)". Flowchart: "syntax check" before BEFORE_ROOT/apply. | `bin/gc:266,452,717,901,905` (`--task`, `gc policy --gets-through-anyway`); `plants/gets_through_anyway.sh`, `plants/syntax_no_strike.sh`. |
| M5 / M5a | SPEC (+AFTER) | Condensed, S1: "Looks at the code the ticket introduces ... Only newly introduced findings fail"; R4: "Before-root snapshot for S1/S2 (M5) ... passes it as BEFORE_ROOT"; Condensed, S2: "Exit 75 means not run and does not strike." E1 (pack v23, 2026-10-15), C1 claims (v24, T5) and the sealed `evidence:` lines (v24, 2026-10-15, "Decision 2" in bin/gc:92) are AFTER. | `bin/gc:80-110,214,567,624-699` (`EVIDENCE_RE`, before-root temp tree, `<state>/evidence/`); `bin/verify_ticket.py:133,175`; `pack/live/S1.sh`, `E1.sh`, `C1.py`; `plants/before_root_used.sh`, `plants/c1_evidence_sealed.sh`, `plants/sandbox_write_refused.sh:61`. |
| G1 | SPEC | R4: "Glossary as the name authority (G1): Retired names ... are not rewritten in law docs; they are read as their current terms via GLOSSARY.md."; R1: "Docs are not rewritten for names; the glossary is the authority." | `plants/retired_world_refused.sh:6,49`; `bin/glossary.py`; `GLOSSARY.md`. |
| I2 | **BEFORE** | Not in the spec. The spec says the opposite of the carve-out: Condensed "Every verify runs under sandbox-exec"; R3 §4 "a sandbox-exec profile that denies network and all file writes except temp"; R4 "denies network and all writes except temp". The loopback exception is dated in code "I2 (2026-10-12)" (`bin/verify_ticket.py:138`): pre-purge, and its stated reason (a local client/server test falsely `run_fail`) is an S2-era finding; S2 is withdrawn (T1). No dated amendment on or after 2026-10-15. | `bin/verify_ticket.py:127-143` (`run_sandboxed` profile: `(deny network*)` then the two `localhost` allow rules); `plants/sandbox_write_refused.sh:2` (names I2/K2; tests writes, not network); `GLOSSARY.md:47` `sandbox` entry ("loopback-only network (I2)"); `proposals/CLAIM_CHECK.md:14`. C1 and E1 run ticket code under this profile, so removing the carve-out would make any ticket test that binds a local socket fail under E1/C1. |
| T1 (2026-10-15) | AFTER | Dated. | `PACK.md` "S2: withdrawn (v22, 2026-10-15)"; no S2 code in tree. |
| T2 (2026-10-15) | AFTER | Dated. | Process: `proposals/PROVING_SET.md`, `bin/trials.py`, `bin/dash.py` run pages. |
| T3 (2026-10-15) | AFTER | Dated. | Process: trial runs under `runs/`, `bin/trials.py`. |
| T4 (recorded 2026-10-15) | AFTER (flag) | Recorded 2026-10-15; the row itself says it was "ruled days before". By the brief's rule the record date places it AFTER; the signer may want to confirm the recording counts as a post-purge re-ruling. | `pack/live/U1.py:5` ("KERNEL T4, detect, run, compare"); PACK.md v28; `plants/u1_*.sh`. |
| T5 (2026-10-15; am. 10-16) | AFTER | Dated. | `bin/claims_draft.py`; `pack/live/C1.py`; `plants/claims_draft.sh`, `plants/claims_required.sh`; `bin/gc` ticket mint requires claims. |
| T6 (2026-10-16) | AFTER | Dated. | `bin/dash.py` not-Closer's column; `COUNTERFEITS.md` T11. |
| T7 (2026-10-16) | AFTER | Dated. | Process; deletions already made. |
| T8 (2026-10-16) | AFTER | Dated. | `bin/dash.py:260,280` ("KERNEL T8"); `proposals/MVP_BAR.md`. |
| T9 (2026-10-16) | AFTER | Dated. | `bin/trials.py` runner lock / demo driving. |
| T10 (2026-10-19) | AFTER | Dated. | Process: `proposals/MVP_PLAN.md`. |
| T11 (2026-10-19) | AFTER | Dated. | Process: miss loop; `bin/dash.py` columns. |
| T12 (2026-10-19) | AFTER | Dated. | `bin/dash.py` (the UI). |
| T13 (2026-10-19) | AFTER | Dated. | Process; no code tag. |
| T14 (2026-10-19) | AFTER | Dated. | Process; no code tag. |
| T15 (2026-10-19) | AFTER | Dated. | `adapters/claude_code/gc_mcp.py` (the MCP server). |
| T16 (2026-10-19) | AFTER | Dated. | `bin/gc:214,617`; `bin/governor.py:11,27,110`; `pack/live/C1.py:13`; `plants/gc_not_run_proceeds.sh`, `plants/c1_cannot_judge_proceeds.sh`, `plants/c1_unjudged_unreached_strikes.sh`; PACK.md every_ticket note. |
| T17 (2026-10-19) | AFTER | Dated. | `bin/gc` `writer_launch` (proxy kept); `adapters/claude_code/pre_tool.py`. |
| T18 (2026-10-19) | AFTER | Dated. | `bin/dash.py:248` (`CRITERIA_OPEN.txt`, "KERNEL T18"). |
| exit 0 | SPEC | R1: "Governor verdicts (proceed / reject / reroute)"; Condensed: "verify must exit 0 before a ticket is recorded as merged". | `bin/governor.py:26` `PROCEED`; every `pack/live/*` check. |
| exit 1 | SPEC | Condensed, Key terms: "strike: Rejected by an every ticket check. Closes the ticket"; Pack: "Every ticket checks run on every land and reject if non zero". | `bin/gc:209` (M2/M3 strike path); `pack/live/*` fail lines. |
| exit 2 | SPEC | R3 §10: "Any non-zero exit, crash, or timeout blocks the Stop hook (exit 2)." The PreToolUse half is the same hook convention (R2 docx lists "pre-tool" in adapters/). | `adapters/claude_code/stop_gate.py:7`; `adapters/claude_code/pre_tool.py:13`. |
| exit 3 | SPEC | R3 §5 governor: "newer World → reroute ... payload staging ... Overlap with a previously merged ticket on the same World → reroute." The verdict is spec; the number 3 is the code's encoding. | `bin/governor.py:33,63,86,105` `reroute`; `bin/gc` cmd_land maps reroute to 3. |
| exit 75 | SPEC (+AFTER) | Condensed, S2: "Exit 75 means not run and does not strike"; Known limits: "S2 without pytest reports not run rather than passing"; Condensed: "No sandbox means no verify" (the one refusal kept). Let-through is T16, 2026-10-19. | `bin/gc:214-218,617-621`; `bin/governor.py:27,110`; `bin/verify_ticket.py:133`; `pack/live/E1.sh` (75 only without pytest); `plants/gc_not_run_proceeds.sh`, `plants/sandbox_write_refused.sh:61`. |

## SPEC rows (21)

K1, K2, K3, K4, K5, K6, K7, C1, R2, R4, L1, R9, M2, M3, M5/M5a, G1, exit 0, exit 1, exit 2, exit 3, exit 75.

Rows whose basis text could be reworded to cite the spec directly rather than the discarded rulings file: K2 (the
interpreter-tree clause is v29, 2026-10-15), K6 (quote "Makes no model calls"; the "no network module" clause is the
2026-10-15 recording and holds by `plants/no_model_in_gate.sh`), M5/M5a (name E1, C1 and the evidence filing as
2026-10-15 pack v23/v24 additions, not as M5), exit 75 (split spec sentence from T16).

## AFTER rows (19)

K8, T1, T2, T3, T4 (flag: ruled before the purge, recorded 2026-10-15; confirm the recording stands as the ruling),
T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18.

## BEFORE rows (1)

- **I2** (verify-sandbox loopback carve-out, code-dated 2026-10-12): **ask**. The spec's sandbox denies all network;
  the carve-out was added for an S2-era false `run_fail`, and S2 is withdrawn. Dropping it is a one-line change to the
  profile in `bin/verify_ticket.py:140-142` (remove the two `localhost` allow rules) plus the `GLOSSARY.md` `sandbox`
  entry and `proposals/CLAIM_CHECK.md:14`; it does not touch kernel_sha256's meaning beyond changing `verify_ticket.py`
  (a new hash). Keep it only if the signer re-rules it after the purge, because E1 and C1 now run ticket tests under
  this profile and a repo test that binds a local socket would otherwise `run_fail` (a strike) rather than be let through.
  If re-ruled, keep-as-dated-amendment: the row needs a 2026-10-xx date and the reason restated for E1/C1, not S2.
