# Changelog

All notable changes to Closer are recorded here. The format follows Keep a Changelog; versions follow 0.x semantics, where a minor bump may break. The gate's own pack history (v26 to v38) is in PACK.md and `proposals/`; this file starts at the first release of the tree.

## [Unreleased]

### Added
- The signer's MCP server, `closer-mcp.sh` (`adapters/claude_code/closer_mcp.py`): seven tools, `cl_doctor`, `cl_task`,
  `cl_claims`, `cl_go`, `cl_status`, `cl_inspect`, `cl_stop`, each one `closer <command>` run in the repo the call names.
  Your own Claude session drives the front door; the writer's `gc` MCP is untouched and separate. The terminal's
  "[y/N]" pause is rebuilt as two refusals: `cl_go` is refused until `cl_claims` has printed the task's claims in the
  same process, and refused unless `approved` is true, which the instructions reserve for the person's word (T5).
  `install_closer_mcp.sh` registers it with Claude Code at user scope with a 50-minute tool timeout. Plant
  `mcp_outer_gate` holds the tool list and both refusals. `gc_mcp.py` lends its stdio loop (`serve`) and lets a
  subclass bring its own tool list; no behaviour change for the writer. MCP.md documents it.

- `well_formed`, a fixed rule on the claim agent's output before the signer sees it: a claim whose call does not
  parse, or is a lambda or generator rather than a call, is dropped and said. Seen 2026-11-03: a claim drafted
  as `(lambda: ...)()` with expect `True`, which no signer should be shown.
  The claim brief now shows the one shape for a message-fragment claim (setup with try/except, call `msg`), which
  the agent had been improvising as a `msg(lambda: ...)` helper that does not exist.
  `well_formed` also binds what a claim uses: a claim naming `booking.f` whose setup never imports `booking` gets
  `import booking` first, and a bare `f(...)` gets `from booking import f`; said each time. Seen 2026-11-03: a
  draft with no setup lines at all, so every claim raised NameError and one strike went to the claims.
- `task_functions` no longer takes a method on a value for a function the app must have: a dotted name in a task's
  code span counts only when its head is the task's module (`frontdesk.hand_keys(`), so `last_name.lower()` no
  longer refuses a mint over `lower`. Plant `task_functions_methods`. Seen 2026-11-03 on the hotel task.
  A dotted head that is a parameter the task's signatures declare is a value too, even when it shares the
  module's name (`quiz.clock()` in a task for `quiz.py`; the quiz build).
- The claim brief asks for `questions`: a case a claim would need that TASK.md does not decide. They are written to
  `signer/questions.txt` and said before the claims, so the signer decides them before the mint instead of the
  agent inventing an answer. Seen 2026-11-03: a deliberately undecided case drew no contradiction and a made-up claim.

### Changed
- `closer go` / `closer claims` will not mint a ticket a writer cannot pass in full. After the siloed claim agent drafts,
  every function the task names (`name(` in backticks) must have a claim that calls it (by name, or `f(` in setup, call
  or expect). Missing ones are asked of the same siloed agent, up to two more rounds; if any is still unclaimed,
  minting stops and names it. Unreached functions are still a strike at the gate (T16 unchanged): this stops the strike
  before the writer works, instead of after. Seen live: a 15-function task whose first draft missed 7 functions now
  mints with all 15 claimed; the demo mints and is accepted unchanged. No pack, check or World change.

## [0.1.0] - 2026-10-23

### Added
- The gate: a ticket is minted on a frozen World with the signer's claims; a locked-down writer stages files into the ticket's write_set and lands; the live pack runs read-only under the macOS sandbox and the land is accepted or struck. Nothing reaches the repo except through a full pass; a strike rolls the tree back and closes the ticket.
- `gc` CLI (`bin/gc`, stdlib only, zero model calls): `init`, `scan`, `worlds`, `read`, `tickets`, `ticket`, `policy`, `land` (exit 0 proceed, 1 reject, 3 reroute), `ledger` (with `--check` for the hash chain), `apply`, `verify`, `check`, `writer-setup`, `selftest`, `glossary`.
- `closer` front door (`ui/go.py`): `doctor`, `demo`, `task`, `claims`, `go`, `status`, `inspect`, `amend`, `watch`, `forget`, `stop`; the signer's live page at http://localhost:8766/ (`bin/session.py`, `ui/session_server.py`).
- Claude Code adapter (`adapters/claude_code/`): the `gc` MCP server exposing the writer's nine tools `tickets`, `worlds`, `read`, `stage`, `stage_edit`, `land`, `verify`, `check`, `ledger`; the `pre_tool.py` allowlist hook; `stop_gate.py`, so the writer cannot say done until `check` passes.
- Live pack v38 (`pack/live/PACK.json`): W1, R6-1, R6-2, R6-4, G18, S1, E1, C1, U1, R10-1, R10-2. S1 carries the five shape rules (`theatre_return`, `factory_none`, `finally_return`, `always_true`, `identity_return`), the `judge_detection` and `trace_replaced` verdicts, the `dynamic_code` and `probe_unfoldable` advisories, and `s1_stand_down`.
- Claims (T5): `bin/claims_draft.py` drafts sealed claims from a task's acceptance criteria by fixed tables, refuses to mint while a `<FILL: ...>` remains, and `--check` reports the checklist lines no claim covers. C1 runs every claim in the sandbox and names the gap (`pass_through`, `fake_check`, `answer_table`, `fake_effect`, `partial`, `unreached`).
- T16: what the gate cannot judge (a check exiting 75, a claim C1 cannot set up or finish) is let through and recorded as `not_run` / `unjudged` on the row and the page, not refused; `unreached` stays a strike.
- Hash-chained ledger (`ledger.jsonl`, rows `draft`, KERNEL L1); claims and evidence sealed under the state dir in `~/.getting-close/`, outside the repo and unreadable by the writer.
- `gc selftest`: 49 plants (`plants/run_all.sh`), each a real land through the kernel; honest cases land, planted counterfeits are struck.
- `bin/dash.py` and `bin/trials.py`: the signer's read-only HTML page from the ledger, tickets and sealed evidence; the MVP bar (proposals/MVP_BAR.md) met on 2026-10-19 and held through v38.
- Law docs: KERNEL, PACK, WORLD, DESIGN, GLOSSARY (`gc glossary check`), COUNTERFEITS, README, QUICKSTART, usage.txt, RELEASE_CHECKLIST with dated passes; `proposals/` (PACK_v30 to v38, MVP_BAR, POST_MVP) kept as history.

### Known limits
- macOS only (`sandbox-exec`). Python 3.10 or newer: `gc` refuses an older interpreter up front, and Apple's `/usr/bin/python3` (3.9.6) is refused. pytest must be importable under the repo's interpreter for E1.
- Outside the gate's hunt: species T11 (untested: crashes on an input its tests never give; KERNEL T6, left to CodeRadar), cross-function design, concurrency and scale. The gate judges whether staged code does what the claims say; it does not judge whether code that lands is correct.
- The ledger is tamper evident, not tamper proof: a ledger rewritten from an edited row onward passes `ledger --check` (L1). World v1 records a byte count per unit, not a content hash.
- The Stop hook gates the agent saying done, not writes; the PreToolUse hook is a belt and fails open on timeout. The launch flags bound the writer's tools, not its prompt.
- Ledger rows are `draft` (KERNEL L1).
