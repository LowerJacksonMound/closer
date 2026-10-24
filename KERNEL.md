# KERNEL

What getting-close guarantees, and the code that holds it. Regenerated 2026-10-11 from
`CLOSER_SPEC_2026-10-10/` and the code in this tree. Names are as GLOSSARY.md defines them.

## What it is

getting-close is the front half of a two-part system. It keeps counterfeit code from being written. It
takes no position on whether code that does land is correct; that is the other half's job. It does not
talk to CodeRadar.

It is not a signed audit log: the ledger is tamper evident, not tamper proof. It is not a hard stop on
writes: the Stop hook only gates the writer saying done, and fails open for writes.

## Flow

Signer: `gc init` → `gc scan` (freezes a World) → `gc ticket` (mints a write_set on that World).
Writer: `stage` / `stage_edit` → `land`. Land runs the governor, then apply, then the ticket's verify,
then every every-ticket check, then appends the ledger row. Any failure rolls the patch back.

## Invariants

| Id | Invariant | Held by |
|---|---|---|
| K1 | A World is append-only by id. A second write to the same id fails. | emit_world, read-only file; W1 |
| K2 | A verify never writes the kernel, the repo it judges, the Worlds, the ticket, the state dir, or the repo's interpreter tree (the manifest's `python`: its prefix as given and through symlinks, read-only like the repo; reading and running it need no rule). No `sandbox-exec`, no verify (exit 75, not run). Amended 2026-10-15 (pack v29): the repo's interpreter tree is read-only like the repo. | verify_ticket.run_sandboxed |
| K3 | No ledger row, no merge. From apply until the row is written, any failure rolls the patch back. | gc cmd_land |
| K4 | The writer cannot change the kernel, the live pack, plants or Worlds. Those paths are refused in every write_set. | apply_ticket.is_forbidden; launch line; pre_tool hook |
| K5 | A live check changes only through a new pack version. Proposals never go live without signer yes and plants still split. | PACK.md; ledger pack_sha256 |
| K6 | No model and no network inside the gate. The kernel, the scanner, the live pack and the adapters import no model client and no network module; fixed code decides (AST, the repo's tests, the signer's claims). Spec: "makes no model calls"; the no-network-module clause is the 2026-10-15 recording, held by `plants/no_model_in_gate.sh`. | plant no_model_in_gate |
| K7 | The scanner never writes the tree it reads. It emits one write-once, read-only overlay per scan, as K1 for Worlds. | scanner/emit.py; plant s1_scanner_writes_nothing |
| K8 | A finding names the function: file, line, rule, qualname. The species (COUNTERFEITS.md T1..T10) follows from the rule, for coverage, and takes no part in any decision. | S1.sh and C1.py fail lines; scanner/lexicon.py |

## Rulings in force

| Id | Ruling |
|---|---|
| C1 | Cutover. Writer sessions use only the `gc writer-setup` launch line: `--tools Read,Grep,Glob`, the gc MCP server, `--restricted`. Any other edit path is a kernel bug. |
| R2 | Freshness is a World's path identity, not a timestamp. |
| R4 | Plants are signer-only evidence. |
| L1 | Ledger rows are `draft` (the spec's draft ledger): a hash chain that is tamper-evident, not tamper-proof. Signing the head is not built. |
| R9 | The Stop hook blocks done until `gc-writer check` exits 0. Crash or timeout blocks. |
| M2 | One strike closes the ticket. A struck ticket cannot be staged or landed again. |
| M3 | Strikes count per task. After `gets_through_anyway` struck tickets (default 2), gc mints no more for that task until the signer raises the number. Syntax errors are refused before apply, with no strike. |
| M5 / M5a | S1 judges only what the ticket introduces (`BEFORE_ROOT`); E1 runs the whole tree's tests, the ticket's own and the ones it did not write; C1 runs the ticket's claims. A check's `evidence:` lines are filed under `<state>/evidence/` by gc and never reach the row or the writer. A check that cannot run exits 75: not run, no strike. E1, C1 and the evidence filing are 2026-10-15 additions (pack v23/v24), cited as such. |
| G1 | Law docs are not rewritten when a name changes. GLOSSARY.md maps retired names. |
| I2 (re-ruled 2026-10-19) | The verify sandbox denies network to the outside world. Loopback (`localhost`, 127.0.0.0/8, `::1`, IPv4 or IPv6) is the machine talking to itself and is permitted: a verify may bind, listen and accept on it and connect to it. The prior 2026-10-12 reason (an S2-era false run_fail) is struck; S2 is withdrawn. Basis: the current meaning of "network" under K2, not the old S2 check. Code: bin/verify_ticket.py `run_sandboxed`; plant `sandbox_write_refused`. |
| T1 (2026-10-15) | A check that does not catch is trash. A check stays in the pack only while it catches counterfeits and accuses nothing honest. S2 is withdrawn (pack v22). |
| T2 (2026-10-15) | Before any trial, a pack change is proved on real working counterfeits in real apps the gate's authors did not write: every working counterfeit caught, every honest item on the same apps clean, the apps' own demos still as expected. A proving set is development evidence, not a measurement. Ruled 2026-10-15: the proving set is working counterfeit functions; counterfeit tests (hollow, rigged) are not in it, since nothing in the pack judges a test that passes on honest code. They ride inside a function's counterfeit ticket as the writer's own tests, unscored. Ruled 2026-10-16 (T7): the 2026-10-15 set, taken from the pre-purge rounds, is out, with every claim and run made on it. The internal proving set is rebuilt from fresh AI-written counterfeits (proposals/PROVING_SET.md); the external set (`CLOSER_PROVING/set2`, 34 real bugs gathered 2026-10-15) is clean and reported alongside. |
| T3 (2026-10-15) | A change of trial type invalidates every result on every pack. Results pool only within one trial type on one frozen pack. A pack used again is rerun fresh; nothing earlier carries over. |
| T4 (ruled days before 2026-10-15, recorded 2026-10-15) | Changed functions are run, not only read. Detect, run, compare: a changed function whose outcome is not the correct one is counterfeit. The signer accepted the added time as almost nothing. |
| T5 (2026-10-15; amended 2026-10-16) | Claims are stated at mint by the signer. They are drafted from the task's criteria by fixed rules (the extractor, `bin/claims_draft.py`; a draft with a `<FILL: ...>` placeholder cannot mint) or by an agent whose one job is the claims for that task: it sees the task's criteria, the base app and COUNTERFEITS.md, never the ticket, the writer or any counterfeit; it writes no code for that task, and no writer of that task drafts its claims. When the extractor is empty and no agent is assigned, the signer writes them by hand or refuses the ticket. A ticket without claims is not minted. Only the signer mints; the writer cannot alter the task or the claims; every claim that reaches land is one the signer has accepted. Ruled 2026-10-15: the shape-rule plan's "claim probe optional" yields to T5; C1 runs on every ticket. Amended 2026-10-16 by the signer: the 2026-10-15 sentence "no agent drafts claims: that would be a second writer path" and its proving exception are struck. Agents have written every part of this system; a claim-drafting agent is one job, siloed, done, not a second writer path. Kept from the exception: a claim counts only if it holds on the honest ticket. |
| T6 (2026-10-16) | Species T11 (COUNTERFEITS.md, untested: crashes on an input its tests never give) is not in Closer's hunt. A T11 counterfeit is allowed through the gate; CR (Code Radar, the backend MCP server) catches it. T2's first line reads "every working counterfeit of a species Closer hunts". A T11 that lands is not a miss on any run page; it is counted in its own column. |
| T7 (2026-10-16) | Nothing made before the 2026-10-15 purge is used again unless it is completely clean: no result, test, claim, ticket or state dir. The two apps in `~/Desktop/CLOSER_APPS` stay, as plain apps, by the 2026-10-15 ruling. The archive `~/Desktop/CLOSER_ARCHIVE_2026-10-15` and the pre-purge gate state dirs under `~/.getting-close` are deleted. Ruled the same day, on the question "what about the 29 and the driver": the purge wins; "we don't know; now is not the time to stop cutting". Cut 2026-10-16: `CLOSER_PROVING/set`, every `claims*/`, `runs/`, and `bin/drive.py` (the rounds' GUI driver). A demo driver is written fresh. |
| T8 (2026-10-16) | The MVP bar is proposals/MVP_BAR.md, adopted as written with one change: line 1 reads "every working counterfeit of a species Closer hunts is struck at land" (T6). Counterfeits that land because their species is not Closer's (T11) or is not yet named are not misses; they are counted in their own column and reported as a rate beside the three lines, so an unknown species is never let in silently. The external set is reported beside the MVP; it is not a condition of it. The pack-v8 bar in README "Status" is withdrawn. |
| T9 (2026-10-16) | Demos run unattended, one at a time under the lock, whenever the runner reaches them; nothing waits for the signer. The signer steps away when a demo is driving; the page shows when one is. |
| T10 (2026-10-19) | The plan to MVP is proposals/MVP_PLAN.md, run in the order it states (pack v31 before the proving run, then claims, the run, the miss loop, step 4). One agent per job, then done: no agent is reused for a second job. |
| T11 (2026-10-19) | The miss loop. A miss is sharpened by a new agent every pass, never one that has done a job on that task or read a set tree; the sharpening takes whatever form the miss needs. Claims are sharpened to the degree the MVP bar defines and no further: every working counterfeit of a species Closer hunts struck, every honest land clean. A landed counterfeit of a species Closer does not hunt is expected, counted in its own column (T6, T8), and not sharpened for. |
| T12 (2026-10-19; amended the same day) | The UI is part of the MVP definition. It is not a step after the others: it is placed where it fits between them (MVP_PLAN.md: during the unattended runs of session B, finished in session C) and MVP is not recorded without it. |
| T13 (2026-10-19) | The both-apps rule. Work that joins Closer and Code Radar is post-MVP. If Closer needs something Code Radar can get, that piece is copied into Closer; both stay standalone until they are connected after MVP. |
| T14 (2026-10-19) | Budget checkpoints are read from Frankensaver's meter. After a run of one type (ten claim agents, one proving run, one sharpening pass) the meter is read and the rest of that type is extrapolated from it before more is started. |
| T15 (2026-10-19) | Closer at MVP is an MCP server. MVP_BAR step 4, one real task end to end through the gc MCP server with the signer minting, stands as part of the MVP (T8). The task is one new task on one of the two apps, outside the proving set. Who writes its text and drafts its claims is open (T5: an agent may draft, siloed from the writer); the signer's side mints. Amended 2026-10-19 on the signer's word: a requirement that the signer author the task was a leftover, not a rule. |
| T16 (2026-10-19) | Let through what the gate cannot judge. The gate strikes only on a verdict it reached: a claim that failed, a test that failed, a shape it found, an introduced function no claim reached. Whatever it could not bring to a verdict, for any reason (a check not run or crashed, exit 75; a claim that could not be set up, imported, or finished within its clock or line budget; a species it has no name for), is let through: the land proceeds, the ledger row and the signer's page record what was not judged, and Code Radar catches it on the backend (T6). Supersedes the 2026-10-15 decision that C1 `cannot_judge` is a reject, and the refusal of a land on a not-run check. Built in pack v32 with a gc land change (kernel_sha256 changes). |
| T17 (2026-10-19) | The writer session launches through the signer's normal `claude` command, proxy included; the 2026-10-01 ruling that writer sessions go direct to Anthropic is purged (pre-rebuild). What the writer can do is still fixed by the launch line's tool list, the strict MCP config and the PreToolUse hook. Kernel file `bin/gc` changed (kernel_sha256 changes). |
| T18 (2026-10-19) | Criteria open. A counterfeit whose gap is a behaviour the task's text leaves open is not a counterfeit of that task: no claim written from the criteria can separate it from the honest tree, and the gate judges what the signer's text fixes (T5). After two sharpening passes (T11) such an item is recorded as `criteria open` in its own column beside caught, struck and not-Closer's, named in the run's record, and the bar's first line is read without it. The fix for the next task is sharper text, not a pack check. |
| T19 (2026-10-19; amended twice the same day) | MVP reached on pack v32 (T8, steps 1, 3, 4, 5). The ~17:00 record was struck by the signer the same day: its page was rendered after the step-4 land and its trials page held no state dir and not the final reruns; step 5 was reopened under the condition that one trials page runs over every run folder plus a state dir while a fresh restricted writer session lands a ticket. That condition was met at 16:05: `CLOSER_PROVING/step5/watch.sh` (39 run folders, sharpen3 included, plus state `~/.getting-close/repo-77deec90`) rebuilt the page as ticket `step5-01` was minted (16:03:48), staged file by file (16:04:45 to 16:05:07) and landed (ledger row 16:05:24, on the page at 16:05:28: proceed, every check's lines, 22 claims expected vs observed, chain ok); page copies per rewrite in `step5/snapshots/`, writer transcript and launch line in `step5/`. Internal set: 63 of 66 working counterfeits struck at land, 3 criteria open (T18), 0 landed; 32 of 33 honest lands clean, the one strike a true positive on the honest tree (tower task-06); demos clean after every honest land. Step 4: one real task through the gc MCP server, first land clean (ticket `step4-01`). Step 5: the signer's page showed the step-5 land as it happened, every verdict and its evidence without the shell. Outcome with its run folders: proposals/MVP_BAR.md. Pack v33 is deferred; any bump reruns the set (T3). |
| T20 (2026-10-19) | What gets added to the rules. A rule is added only for counterfeit that is 90 to 100 percent counterfeit: a hit is a verdict, never a suspicion. The cost of a wrong rule is a strike on an honest ticket, and two strikes close the task (M3), so a doubtful pattern stays on the investigation list until it is a verdict. A strike never sends code back for edits: the ticket closes (M2), the tree rolls back, and the rewrite is a new ticket with a new writer, judged in full again; nothing reaches the repo except through a full pass. First application: `judge_detection` (code in a ticket that asks whether it is being traced, reads the runner's environment names or `<setup>`, reads `PYTEST_CURRENT_TEST`, or walks the stack for the runner or pytest) is a verdict and may be added as an S1 rule by proposal with plants; `sys._getframe` alone is not (logging helpers use it); a hit in a test file does not count (tests are E1's and S1's hollow-test rule's). |

## Kernel files

`ledger.KERNEL_FILES` hashes exactly these into every ledger row (`kernel_sha256`):

- `bin/gc`, `bin/ledger.py`, `bin/governor.py`, `bin/apply_ticket.py`, `bin/verify_ticket.py`
- `bin/read_world.py`, `bin/world_v1.py`, `bin/emit_world.py`, `bin/stage.py`, `bin/safepath.py`
- `adapters/claude_code/gc_mcp.py`, `adapters/claude_code/pre_tool.py`, `adapters/claude_code/stop_gate.py`

`scanner/` is kernel code too (walk, readers, substance overlay, lexicon, path rules); every `scanner/**/*.py` is
hashed into `kernel_sha256` with the files above (`ledger.kernel_hash`).

2026-10-15, pack v29 (proposals/INGREDIENTS.md 6b): `bin/gc` (`init --python`, `REPO_PYTHON` to every check) and

2026-10-19, pack v32 (proposals/PACK_v32.md part 2, T16): `bin/gc` (a 75 is recorded, not a reject; the row's
`unjudged`; no `sandbox-exec` refused before apply) and `bin/governor.py` (`decide` proceeds on 75 with a reason)
changed. `kernel_sha256` goes from `d468b580…` to `e724bc40…`.
`bin/verify_ticket.py` (`--repo-python`, the interpreter tree read-only) changed. `kernel_sha256` goes from
`bb95f563…` to `68209e3d…`; rows from here on differ from older rows, as expected.

2026-10-21, proposal PACK_v34 (KERNEL T20 first application): `scanner/substance.py` emits a tenth rule,
`judge_detection` (code that asks whether it is being judged), and `scanner/lexicon.py` notes it has no species.
The scanner always emits every rule; S1 counts only the ids PACK.json `s1_rules` names (K5), so no verdict
changes until the pack lists it. Extended the same day (strings read folded, once-bound names, `setattr` on a
tracer, a walk over `os.environ`, module constants as scope words, docstrings unread). `kernel_sha256` goes from
`70c308a9…` to `59e670a8…` (`69b39cf0…` between the two edits, no land under it).

2026-10-21, proposal PACK_v35: `scanner/substance.py` emits an eleventh rule, `dynamic_code` (code that builds or
runs code at runtime; an advisory, said by S1 when PACK.json `s1_advisory` names it, never a strike), parses a
constant string handed to exec / eval / compile and runs the judge_detection probes over it (a probe inside is the
verdict it would be outside, cited with both lines), and reads `__import__('sys')` as `sys`. Findings may carry a
`why`. Not counted until the pack lists it (K5). `kernel_sha256` goes from `59e670a8…` to `5cfa4632…`.

2026-10-21 (evening), proposal PACK_v36: `scanner/substance.py` adds data-flow evidence to every `judge_detection`
finding's `why` (`asks at line N; the answer reaches the branch at line M` / is stored in NAME and read at ... / is
returned / is discarded), by a parent map and a conservative use search per scope. Evidence only: the verdict is
still presence (T20). `kernel_sha256` goes from `5cfa4632…` to `70040d7a…`.

2026-10-21 (night), proposal PACK_v37: `scanner/substance.py` emits two more rule ids, `trace_replaced` (a plain
`sys.settrace` / `setprofile` / `threading.settrace` / `setprofile` call in a non-test, non-tooling file) and
`probe_unfoldable` (`getattr` / `setattr` on `sys` or `threading` with a name the scanner cannot fold), both
measured at 0 in application code on 2026-10-21; counted only when PACK.json `s1_rules` names them (K5). A constant
string handed to exec / eval / compile that does not parse is now said as "could not be read" in the dynamic_code
advisory instead of "scanned, no probe". The receiver of `probe_unfoldable` was then narrowed to the module itself
(`getattr(sys.modules[m], n)` and `getattr(sys.flags, f)` are not it). `kernel_sha256` goes from `70040d7a…` to
`8871c4dd…` (`65734df5…` between the two edits, no land under it).

2026-10-21 (night), PACK_v38 (signer's word "let's ship v38"): `scanner/substance.py` extends `judge_detection`
to a test runner's name in `sys.modules` -- `"pytest" in sys.modules` and its siblings (`_pytest`, `unittest`,
`nose`, `nose2`) by membership, `not in`, `sys.modules.get`, subscript, a `.keys()` / `list()` view, or the name
folded. The runner name is matched, not any module (`"numpy" in sys.modules` is not a hit); a file in the runner's
own package stands down. No new rule id (the forms emit `judge_detection`, already a verdict); measured at 0 in
application code over 41,749 files. `kernel_sha256` goes from `8871c4dd…` to `5efbc87c…`.

Every write_set refuses these prefixes (`apply_ticket.FORBIDDEN_PREFIXES`): `kernel/`, `pack/live/`,
`worlds/`, `plants/`.

## Exit codes

| Code | Means |
|---|---|
| 0 | proceed / pass |
| 1 | reject / fail. From an every-ticket check: a strike. |
| 2 | Stop hook or PreToolUse hook: blocked or denied. |
| 3 | reroute: the ticket's World is stale, a write_set file is not staged yet, or the write_set overlaps a ticket merged on that World. |
| 75 | not run (EX_TEMPFAIL): the spec's not-run exit; let through under T16 (2026-10-19; before that, land refused without a strike): no pytest for the interpreter the checks run the repo's code under (`REPO_PYTHON`, else python3), or the check's own error. No strike; the row's `not_run` lists the check. One exception: no `sandbox-exec` on the host is still a refusal (gc land, before apply; no strike), because nothing can be held read-only (K2) and nothing at all would be judged. |

## Known limits

- A ledger rewritten from an edited row onward, every hash recomputed, passes `gc ledger --check` (L1).
- World v1 records a byte count per unit, not a content hash: a same-size edit between emit and the
  before overlay is not caught.
- The PreToolUse hook is a belt. Hooks fail open on timeout or a missing interpreter; the launch flags
  are the boundary.
- A ticket minted before its World was altered is caught at land, not at mint.
- The launch flags bound the writer's tools, not its prompt. A proxy on the signer's route can add text to the
  writer's context (Frankensaver's `fsv:<hash>` markers teach a `fsv_get` tool): in the step-4 land of 2026-10-19
  the writer called it 38 times and every call failed `No such tool available`; nothing ran, nothing was read
  (T17, closed 2026-10-21). The cost is wasted writer turns, not a hole; the belt (`pre_tool.py`) never saw a
  call because the client had no such tool to run.
