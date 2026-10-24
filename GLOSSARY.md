# GLOSSARY

Canonical names for getting-close. One element, one name. Regenerated 2026-10-11 from
`CLOSER_SPEC_2026-10-10/` and the code in this tree. `gc glossary check` validates this file.

## Rules

- Names compare case-blind, with `-`, `_`, `.`, space and `[]` treated alike.
- A new name that matches any term or retired name is rejected. The first name for an element stands:
  a second name for the same element (`glossary add --for`) is always rejected.
- G1: law docs are not rewritten when a name changes. A retired name in a law doc is read as the term
  its Retired row names. This file is the authority.

## Terms

| Term | Kind | Means | Source |
|---|---|---|---|
| `World` | object | Frozen snapshot of a scan. Written once, never edited in place (K1). | Condensed spec; WORLD.md |
| `world_id` | key | A World's id, `scan_<UTC>_<4 hex>`, e.g. `scan_20261010T120000_a1b2`. | Condensed spec |
| `units` | key | Every file the walk kept, including files with no defs. | Condensed spec; R6-4 |
| `unreadable` | key | Files and dirs the walk could not read, kept in the World as data, not dropped. | scanner/scan.py |
| `path identity` | concept | Freshness is the World's path identity, not a timestamp (R2). | Condensed spec; R2 |
| `Ticket` | object | The only legal write intent: a write_set bound to one World and one verify. Signer mints; writer cannot. | Condensed spec |
| `ticket_id` | key | A ticket's id. | bin/apply_ticket.py |
| `write_set` | key | The repo paths a ticket may write. Nothing else may change. | Condensed spec |
| `verify` | key | The check a ticket names; runs on its land, sandboxed. | Condensed spec |
| `task` | key | The task a ticket belongs to. A ticket without one is its own task. Strikes count per task (M3). | bin/gc |
| `Land` | command | `gc land`: the only way the repo changes. Governor, apply, verify, every-ticket checks, ledger; rolls back on any failure. | Condensed spec |
| `Governor` | tool | Pure decision on a land: reject over reroute over verify. A program, not a personality. | bin/governor.py |
| `proceed` | verdict | Land accepted and applied. `gc land` exit 0. | bin/governor.py |
| `reject` | verdict | Land refused and rolled back. `gc land` exit 1. | bin/governor.py |
| `reroute` | verdict | Ticket is on an older World than the latest, a write_set file is not staged, or it overlaps a merged ticket on its World. `gc land` exit 3. | bin/governor.py |
| `strike` | verdict | Rejected by an every-ticket check. Closes the ticket (M2). | Condensed spec |
| `not run` | verdict | A check exited 75: it could not run. No strike; since pack v32 (T16) the land proceeds if nothing struck and the row lists the check under `not_run`. Only no `sandbox-exec` on the host still refuses the land. | M5a, T16; bin/gc |
| `gets_through_anyway` | key | Max struck tickets per task before gc stops minting for it. Default 2. Set by the signer (`gc policy`). | Condensed spec; M3 |
| `signer` | role | The human who mints tickets, sets policy, and signs pack versions and rulings. | Condensed spec |
| `writer` | role | The agent. Reads, stages and lands only through the gc MCP tools. | Condensed spec; C1 |
| `cutover` | concept | Writer sessions use only the `gc writer-setup` launch line; any other edit is a kernel bug (KERNEL C1). | bin/gc writer-setup |
| `kernel` | concept | The code that holds the gate, listed in KERNEL.md. Off limits to the writer. | KERNEL.md |
| `Pack` | object | Versioned checks. Live checks are the ones `pack/live/PACK.json` lists (V1). | Condensed spec |
| `every_ticket` | key | PACK.json list of checks run on every land; non-zero rejects. | Condensed spec |
| `named` | key | PACK.json list of checks run only when a ticket names them. | Condensed spec |
| `pack_version` | key | The live pack's version. A ticket is bound to it; a change rejects outstanding tickets. | bin/gc |
| `proposal` | concept | A check in `proposals/`, not live. Goes live only through a new pack version, signer yes, and plants still split (K5). | Condensed spec |
| `plant` | concept | A script in `plants/` that runs the real kernel on a planted case to prove a rule. Signer-only (R4). | TheRefactor2; R4 |
| `BEFORE_ROOT` | key | Read-only copy of the write_set as it was before apply, made by `gc land` for S1 (M5). | TheRefactor4 |
| `sandbox` | concept | `sandbox-exec` profile every verify runs under: loopback-only network (I2), no writes outside temp, kernel/repo/Worlds/state re-denied. No sandbox, no verify (K2). | TheRefactor3/4 |
| `ledger` | object | Hash-chained JSONL of every land. Tamper evident, not tamper proof. | Condensed spec |
| `draft` | key | Every ledger row's status: the spec's draft ledger, a tamper-evident chain with no signed head (KERNEL L1). | TheRefactor4 |
| `Stop hook` | concept | Blocks the writer saying done until `gc-writer check` exits 0 (R9). Fails open for writes. | Condensed spec |
| `S1` | rule | Static substance check: fails only on findings the ticket introduces. | Condensed spec; B3 |
| `G18` | rule | Launch pollution: no `.pyc`/`.pyo`/mypy cache paths in the World or write_set. | pack/live/G18.sh |
| `W1` | rule | K1 as a check: a second write to a World id fails. | pack/live/W1.sh |
| `stub_body` | finding | S1: a placeholder body (pass, `...`, raise NotImplementedError, TODO). | scanner/substance.py |
| `const_return` | finding | S1: returns a constant where a computed value is expected. | Condensed spec |
| `swallow` | finding | S1: a handler that swallows the exception. | Condensed spec |
| `hollow_test` | finding | S1: a test with no check at all. | Condensed spec |
| `unparsed` | finding | S1: a file in the write_set that no longer parses. | pack/live/S1.sh |
| `E1` | rule | Every-ticket check (pack v23): the repo's tests pass on the patched tree, before-ticket and own. | pack/live/E1.sh; T4, T5 |
| `run_fail` | finding | E1: a test fails or does not collect on the patched tree, named `(before-ticket)` or `(own)`. A strike. (Was S2's; S2 is withdrawn.) | pack/live/E1.sh |
| `withdrawn` | concept | A check or finding removed from the live pack by ruling. A retired name that reads as withdrawn names nothing live; its text is history (PACK.md). | Signer, 2026-10-15; PACK.md v22 |
| `gap` | concept | What a function was required to do that it does not do: the required outcomes (inputs to results, effects to where they must be observable) the code fails to produce, plus the outcomes it produces that the requirement forbids. A relation between code and a requirement, never a property of the code alone. Honest: the gap is empty. Shape species: the gap is total, so it shows without the requirement. Claim species: the gap is partial and the writer's own tests sit entirely outside it, so it shows only against a point of the requirement the writer did not choose. | Signer, 2026-10-15; COUNTERFEITS.md |
| `claim` | object | What the code in a ticket's write_set is required to do, stated by the signer at mint (T5): a list of small sealed tests, each a dotted name, an optional setup, a call and an expect (result, raises or true). Stored at <state>/claims/<ticket>.json, bound to the ticket by claims_sha256, recorded in the ledger row, and never readable by the writer. | T5; bin/gc claim_problems; adapters/claude_code/pre_tool.py |
| `C1` | rule | Every-ticket check (pack v24): the ticket's claims hold. Each claim runs in a fresh python3 (`REPO_PYTHON` when set, v29) inside the sandbox under a clock and a line budget; out of time or budget is cannot_judge, let through and recorded (T16, v32). | pack/live/C1.py; T4, T5 |
| `pass_through` | finding | C1: the result is the call's own argument, unchanged, where the claim expected something else (T5). | pack/live/C1.py |
| `fake_check` | finding | C1: the claim expected an exception and nothing was raised (T9). | pack/live/C1.py |
| `answer_table` | finding | C1: two or more claims on one name expect different results and the code returns the same one to all (T4). | pack/live/C1.py |
| `fake_effect` | finding | C1: the claim's predicate is false after the call (T6). | pack/live/C1.py |
| `partial` | finding | C1: any other mismatch between the claim and what the code did: wrong result, wrong exception, or the required name is not implemented (T7). | pack/live/C1.py |
| `cannot_judge` | finding | C1: the claim could not be run to a verdict (import, setup, clock, budget). Not a strike since pack v32 (T16): `C1 unjudged: ...`, filed and counted, the land proceeds; never silence. A function only such a claim would have reached is `unreached`. | pack/live/C1.py; T5, T16 |
| `evidence` | object | What a check was given, expected and observed per claim, printed on '<check> evidence:' lines and filed by gc under <state>/evidence/<ticket>.<seq>.json. Signer-only; never in the row, never shown to the writer. | bin/gc run_check; decision 2, 2026-10-15 |
| `unreached` | finding | C1: a function the ticket introduces (new, or body changed against BEFORE_ROOT; tests, lambdas, abstract and overload stubs excepted) that no claim reached while running. A strike: the gate judges every changed function (T5). | pack/live/C1.py; T5 |
| `claims_draft` | tool | Signer tool (bin/claims_draft.py): drafts claims from a task's acceptance criteria by fixed tables, no model. Backticked names resolved against the repo, verbs rejects/returns/logs/accepts, backticked literals as arguments; what it cannot fill is a <FILL: ...> placeholder, which gc refuses to mint. Absent, never wrong. | T5; bin/claims_draft.py |
| `theatre_return` | finding | S1 (pack v26): computes from its input into locals through side-effect-free builtins, then returns a literal; nothing reads the locals (T1 computation theatre). | scanner/substance.py; proposals/S1_v23_shape_rules.md |
| `factory_none` | finding | S1 (pack v26): a function named make_ / create_ / build_ / new_ / _factory whose every return is None, with no call and no store to an attribute or a subscript: it makes nothing (T2). | scanner/substance.py; scanner/lexicon.py |
| `finally_return` | finding | S1 (pack v26): return, break or continue inside finally. It runs after a raise and discards it (T3). | scanner/substance.py |
| `always_true` | finding | S1 (pack v26): a function named is_ / can_ / has_ / check_ / verify_ / validate_ / allow / auth that takes input and returns the same literal on every path with nothing in the body that could raise or act. A name that says accept-all (is_any) is not judged (T9). | scanner/substance.py; scanner/lexicon.py |
| `identity_return` | finding | S1 (pack v26): a function named mask / redact / normalize / clean / parse / format / translate / sanitize / strip that returns one parameter unchanged on every path, with no call and no store to it (T5). | scanner/substance.py; scanner/lexicon.py |
| `s1_rules` | key | PACK.json list of the S1 rule ids that count at land. The scanner emits every rule it has; S1 reads only these, on both sides, so a scanner rule goes live only through the pack (K5). Pack v26. | pack/live/PACK.json; pack/live/S1.sh |
| `lexicon` | concept | scanner/lexicon.py: the claim words a function name can carry (lookup, factory, check, transform, accept-all) and the rule-to-species map. Species is coverage only and takes no part in a decision (K8). | scanner/lexicon.py; pack v26 |
| `thin` | key | C1 evidence (pack v27): a flag on an introduced function reached by at most one claim, with at most one distinct input and no negative (a raises claim, or a true predicate the signer wrote as 'not ...' or '... is False'). A pointer for the signer, never a strike. | pack/live/C1.py; proposals/INGREDIENTS.md 2a |
| `holds_before` | finding | C1 evidence (pack v27): a claim that held on the patched tree also holds on the before-tree (SCOPED_ROOT copied to temp with BEFORE_ROOT laid over it): it discriminates nothing about the task, a regression guard or vacuous. A claim whose name is new in the ticket is absent, exempt. Never a strike. | pack/live/C1.py; proposals/INGREDIENTS.md 3 |
| `checklist` | concept | Signer advice in the claims_draft notes: per function the criteria name or --changed names, the lines its claims should cover, from its name words (lexicon checklist_classes) plus three every function gets. claims_draft --check prints the lines no claim covers, by the claims' shape. Exit 0; never a refusal (T5). | bin/claims_draft.py; scanner/lexicon.py; proposals/INGREDIENTS.md 4 |
| `U1` | rule | Every-ticket check (pack v28, evidence only): a pre-existing function whose body the ticket changed is run by the same drivers (the repo's tests, the claims) on the before-tree and the patched tree under a recording tracer; an input whose outcome differs is a difference, declared when a claim names the function. No strike until ruled. | pack/live/U1.py; T4; INGREDIENTS 2b |
| `undeclared_change` | finding | U1 evidence (pack v28): a recorded input on a changed pre-existing function whose outcome on the patched tree differs from the before-tree, on a function no claim names. Evidence only; no strike until ruled. | pack/live/U1.py; T4; INGREDIENTS 2b |
| `REPO_PYTHON` | key | The repo's own interpreter, from the manifest's python (gc init --python), passed by gc land, gc verify and gc check to every check's env; E1's pytest, C1's claims and U1's drivers run under it, the checks' own logic stays on gc's python. Absent, an inherited one is cleared (pack v29). | bin/verify_ticket.py; INGREDIENTS 6b |
| `python` | key | Manifest key (gc init --python PATH): the absolute path of the repo's own interpreter, kept as given (a venv's bin/python is not resolved). Absent, the checks run on gc's python as before (pack v29). | bin/gc; INGREDIENTS 6b |
| `unjudged` | finding | C1 could not bring a claim to a verdict (cannot_judge: import, setup, clock, budget). Since pack v32 (T16) not a strike: said as C1 unjudged, filed in the evidence, listed in the ledger row under unjudged, shown on the signer's page; the land proceeds. A function only such a claim would have reached is still unreached. | pack/live/C1.py; bin/gc; T16 |
| `judge_detection` | finding | S1 (pack v34; KERNEL T20 first application): code in a non-test file that asks whether it is being judged: sys.gettrace / getprofile, the gate's runner environment names or PYTEST_CURRENT_TEST read as an environment key, the literal <setup>, a stack walk in a scope (module constants included) that names pytest, unittest, <setup> or <string>, setattr on sys or threading with a trace name, or a walk over os.environ beside a prefix of a runner name, or (pack v38) a test runner's name in sys.modules -- "pytest" in sys.modules and its siblings (_pytest, unittest, nose, nose2) by membership, not in, sys.modules.get, subscript, or a .keys() / list() view. Strings are read folded (concatenation, f-strings, join, bytes.decode, a name bound once). sys._getframe alone is not a hit; a non-runner module name in sys.modules (e.g. "numpy") is not a hit; docstrings are not read; a module named as a debugger, tracer, profiler or coverage tool, or a file inside a test runner's own package (pytest, _pytest, nose, unittest), is not judged. | scanner/substance.py; proposals/PACK_v34.md; proposals/PACK_v38.md |
| `dynamic_code` | finding | S1 advisory (pack v35; PACK.json s1_advisory): code in a non-test file that builds or runs code at runtime: exec, eval, compile, or a FunctionType / CodeType made by hand. Said as an S1 note on stdout and shown on the signer's page and by closer inspect, never a strike. A constant string handed to exec / eval / compile is parsed and the judge_detection probes run over it; a probe inside is a judge_detection strike cited at the outer line with the probe's line and text. | scanner/substance.py; proposals/v35/S1.sh; proposals/PACK_v35.md |
| `trace_replaced` | finding | S1 (pack v37): a plain sys.settrace / sys.setprofile / threading.settrace / threading.setprofile call in a non-test file not named as a tracer, debugger, profiler or coverage tool: it replaces or blinds the tracer C1 judges by. Measured 0 in application code. | scanner/substance.py; proposals/PACK_v37.md |
| `probe_unfoldable` | finding | S1 advisory (pack v37; PACK.json s1_advisory): getattr or setattr on sys or threading itself with an attribute name the scanner cannot fold to a constant: the one way left to reach gettrace / settrace that folding cannot read, and also how honest code redirects stdout (setattr(sys, self._stream, ...)), so a note the signer sees, not a strike. Measured 0 in application code, honest hits in the stdlib's contextlib and pytest's capture. | scanner/substance.py; proposals/PACK_v37.md |

## Retired

| Retired | Read as | Why |
|---|---|---|
| `scan_id` | `world_id` | Renamed with the WORLD.md cutover. |
| `started_at` | `path identity` | R2: freshness is path identity, not a timestamp. |
| `files_scanned` | `units` | Every kept file is a unit, defless ones included (R6-4). |
| `handoff_after` | `gets_through_anyway` | M3 rename. gc still reads it from an old policy.json when the new key is absent. |
| `S2` | `withdrawn` | Signer, 2026-10-15 (KERNEL.md T1): S2 withdrawn from the live pack (v22). It guessed; a check that does not catch is trash. |
