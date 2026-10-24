# Implementation plan: closing the gap (2026-10-15)

Builds CLAIM_CHECK.md parts A to F and S1_v23_shape_rules.md, under rulings T1 to T5. Grounded in the code as it
is: `gc ticket` already attaches signer JSON to a ticket (`--overlay`); `verify_ticket` already hands every check
`TICKET_FILE`, `WORLD_FILE`, `WRITE_SET`, `SCOPED_ROOT` and `BEFORE_ROOT` inside the sandbox; `gc land` already
records each check's exit and output lines in the row; pytest 9 is on the host; the writer's `tickets` tool prints
a one-line listing, never the ticket file.

Order: A, E, C, D, B, F throughout. S1 v23 shape rules run in parallel with any step.

## Phase 1: A, ticket claims (kernel) — DONE 2026-10-15

Landed: `gc ticket --claims`, `claim_problems`, sealed `<state>/claims/`, `claims_sha256` on the ticket and in
the row, refusal at land on a rewrite, pre_tool denies the state dir, plants `claims_required` (new) and
`cutover_denied` (grown), seven plants mint with claims. Selftest 9/9 plants.

**Claim shape**, one JSON object per claim, a sealed acceptance test the signer writes:

```json
{"name": "familyguy_episodes.accounts.Accounts.login",
 "setup": ["acc = Accounts(Store(':memory:'))", "acc.login('ann', 'wrong')", "acc.login('ann', 'wrong')"],
 "call":  "acc.login('ann', 'wrong')",
 "expect": {"raises": "LockedOut"}}
```

`expect` is one of `{"result": <literal>}`, `{"raises": "<ExceptionName>"}`, `{"true": "<predicate expression>"}`
(the effect form: the predicate reads a file, an attribute or a log after the call). `name` is the dotted path of
the function the task requires; the writer must implement that name. `setup` and `call` are Python run in the
patched tree, inside the sandbox.

Work:
1. `gc ticket --claims FILE`. Validate: a non-empty list; every claim has `name`, `call`, `expect` of one
   allowed form; every `name` resolves to a module in the write_set. Store at `<state>/claims/<tid>.json`; put
   `claims_sha256` in the ticket. Refuse mint without claims (T5).
2. `adapters/claude_code/pre_tool.py`: deny Read, Grep and Glob of any path under the state dir. Today Read is
   allowed everywhere and the writer's wrapper names the state dir, so a writer could read its own claims. The
   hook already receives `<state_dir>`; this is a few lines and a plant (`cutover_denied` grows a case).
3. The nine existing plants mint tickets; each gets a one-claim file so T5 holds in selftest.
4. Kernel checklist: `kernel_sha256` changes; K1 to K5 re-checked; `cutover_denied` passes.

## Phase 2: E, the before-ticket tests (pack check E1) — DONE 2026-10-15

Landed as pack v23: `pack/live/E1.sh`, three plants, docs. Own red test strikes (decision 3).

A `sh` check, modelled on S1.sh. Collect the test files in `BEFORE_ROOT` (the World's, which the writer did not
write) minus any file in the write_set; run pytest on them against `SCOPED_ROOT` inside the sandbox; any failure
prints `E1 fail: run_fail <nodeid>` and exits 1. Exit 75 only if pytest is missing. Then run the write_set's own
test files the same way: the writer's own red test is also a reject (a ticket said done with red tests), as a
strike, unless the signer rules it a no-strike reject (M3 counts strikes per task).

Plants: a ticket that breaks an existing test is struck; an honest ticket is clean; a ticket whose own new test
fails is rejected.

## Phase 3: C, the claim check (pack check C1) — DONE 2026-10-15

Landed as pack v24: `pack/live/C1.py`, gc seals `evidence:` lines, eight plants, docs. The runner already records
the functions each claim reaches (in the evidence), which Phase 4 turns into the reach rule.

`pack/live/C1.py`. Reads the claims file named by the ticket (`TICKET_FILE` gives the ticket; the claims path
follows from it; `claims_sha256` must match). For each claim, in a fresh subprocess inside the sandbox with
`SCOPED_ROOT` on `sys.path`: run `setup`, run `call`, compare to `expect`, under a line budget (CodeRadar's
`intent_claims` budget and "not run is never guessed" discipline, copied in; its arithmetic-only probe is not
enough for app code, so the runner imports the real modules). Timeout or budget: `C1 fail: unjudged` and exit 1.

Rules, named for the gap:
- `pass_through`: the result is the call's own argument, unchanged.
- `fake_check`: `expect.raises` named and nothing raised, or a predicate that must be false was true.
- `answer_table`: across two or more claims on one name, the same result for every input the claims give.
- `fake_effect`: an effect predicate is false after the call.
- `partial`: any other mismatch between result and expect.
- `rigged_test`: not in v23. It needs claims on tests, which is a later shape.

**Evidence is sealed from the writer.** The row's `said` line carries file, lines, rule and qualname only. The
four-part evidence (claim, input, expected, observed) goes to `<state>/evidence/<tid>.json`, signer-only, denied
to the writer by the Phase 1 hook. Otherwise one strike teaches the writer the probe, and the next ticket on the
same task is an answer table built from the ledger.

Plants: one struck and one clean per rule, on a small app module with a claims file.

## Phase 4: D, the reach rule (inside C1) — DONE 2026-10-15

Landed as pack v25. Setup is traced too, so a constructor run in a claim's setup counts as reached. Plant
`c1_unreached` (an unreached helper, a changed function no claim reaches, and a clean ticket).

While C1 runs the claims, `sys.settrace` records every function reached, by file and qualname. Introduced
functions are the defs present in `SCOPED_ROOT`'s write_set files and absent or changed in `BEFORE_ROOT`, by an
AST pass (the same split S1 uses for introduced findings). Any introduced non-test function not reached by any
claim: `C1 fail: introduced <file>:<line> unreached <qualname>`, exit 1. Test functions are not subject to reach:
E1 runs them and S1's hollow_test judges them.

Plants: a helper the claims never call is struck; a helper reached through the claimed entry point is clean.

## Phase 5: B, the claim extractor (signer tool, not a check) — DONE 2026-10-15

Landed: `bin/claims_draft.py` (tables RAISES / RESULT / EFFECT / ACCEPT, names resolved against the repo's defs,
backticked literals as arguments, conditions as setup notes, `<FILL: ...>` for everything else), gc refuses a claims
file holding a placeholder, plant `claims_draft`. On the two apps' backlogs it drafts the clauses that name a
function and a table verb and leaves the rest to the signer, as designed.

`bin/claims_draft.py`: fixed rules, no LLM, from the task's acceptance criteria text to draft claims in the
shape above. CodeRadar's `intent_file.extract_statement_facts` is the skeleton to copy (clauses, keyword tables,
evidence span, absent never wrong), but its tables yield domain, runner and entry-point facts, none of which is a
claim. New tables are the work: "after N <noun>" to a setup of N calls; "returns / gives / shows <literal>" to a
result; "raises / refuses / rejects / locks" to a raises; "must not / never" to a false predicate. Output is a
draft file the signer edits and passes to `gc ticket --claims`. Never applied automatically (T5).

## Phase 6: F, discipline, throughout

Each rule: a struck plant and a clean plant before it is live. Names through `glossary add`: `claim`, `C1`, `E1`,
the six rules, `unreached`. Pack v23: PACK.json lists `E1` and `C1` in every_ticket; PACK.md's table and the
"Live in pack v23" headers; KERNEL.md M5 names S1, E1, C1; README's status. RELEASE_CHECKLIST, every box.

## S1 shape rules (S1_v23_shape_rules.md) — DONE 2026-10-15 as pack v26

Landed: five rules in `scanner/substance.py`, name words and species tags in `scanner/lexicon.py` (species is coverage
only, K8), PACK.json `s1_rules`, plants `s1_theatre_return`, `s1_factory_none`, `s1_finally_return`, `s1_always_true`,
`s1_identity_return`; invariants K6 (no model, no network), K7 (scanner writes nothing), K8 (names the function)
recorded in KERNEL.md with plants `no_model_in_gate` and `s1_scanner_writes_nothing`. Measured clean on real code
before going live (PACK.md v26).

## Proving (T2)

Before any trial, the pack is proved on real working counterfeits in real apps. The two apps in
`~/Desktop/CLOSER_APPS` are real and the signer can write claims for their backlog tasks. The labelled
counterfeits for them exist only in the archive; whether to use them is the signer's call.

## Sizes

| Phase | New or changed code | Plants |
|---|---|---|
| A | gc ticket (~60 lines), pre_tool.py (~15), nine plants touched | 1 new, 1 grown |
| E | E1.sh (~60) | 3 |
| C | C1.py (~250, runner copied and rewritten) | 10 |
| D | inside C1 (~60) | 2 |
| B | claims_draft.py (~200) | none; it is a signer tool, checked by a doctest of its tables |
| S1 v23 | substance.py (~120) | 10 |

## Decisions, ruled 2026-10-15 (signer)

1. Claim shape: yes. Python the signer writes: setup, call, expect as result / raises / predicate.
2. Evidence sealed from the writer: yes. The row names file, rule and function only; full evidence is signer-only.
3. The writer's own red test: reject **with a strike**. A red test the writer introduced is a failed claim about
   its own code.
4. The archived labelled counterfeits are used for proving under T2. They become plants for the claim rules; they
   are not a second writer path.
5. Tightening: `claims_sha256` is recorded in the ledger row, so a later rewrite of the claims file is visible.
6. The shape-rule plan's "claim probe optional" (invariant 4) yields to T5. C1 runs on every ticket; no ticket without claims.
