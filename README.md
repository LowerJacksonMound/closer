# getting-close

A gate that keeps counterfeit code from being written into a repo by an agent. Regenerated 2026-10-11 from
`CLOSER_SPEC_2026-10-10/` and the code in this tree.

getting-close is the front half of a two-part system: it stops stubs, constant returns, swallowed
exceptions, hollow tests and broken files from landing. It is not CodeRadar and does not talk to it, and it
does not judge whether code that lands is correct. Its ledger is tamper evident, not tamper proof. Its Stop
hook gates the agent saying done, not writes.

Needs macOS (`sandbox-exec`), Claude Code logged in (`claude` on PATH), Python 3.10+ as `python3` on PATH (macOS ships 3.9; `brew install python` or python.org gives a newer one), and pytest for E1. A repo with its own interpreter (a venv) names it at
init (`--python`); E1, C1 and U1 then run the repo's code under it, and pytest must be importable there.

## Install

Clone or copy this folder anywhere. Nothing to build. `closer` is a shell script at the top of the folder; put it
on your path or call it by its full path, and run it from inside the repo you are gating:

    ln -s /absolute/path/to/CLOSER_THE_APP/closer /usr/local/bin/closer
    cd your-repo
    closer doctor                         # the machine, and whether this repo's tests collect
    closer task add-thing                 # writes add-thing.md; fill every <FILL: ...>, including Decided
    closer go add-thing.md                # shows the claims, asks for your yes, mints, runs the writer

To drive the same front door from your own Claude Code session, register the signer's MCP server once:

    bash install_closer_mcp.sh            # --print shows the `claude mcp add-json` line; it carries a 50-minute
                                          # tool timeout because cl_go blocks while the writer works

Its tools are `cl_doctor`, `cl_task`, `cl_claims`, `cl_go`, `cl_inspect`, `cl_status`, `cl_stop` (MCP.md). Every call
runs `closer <command>` fresh, so an edit to this folder is picked up on the next call; the writer's own server
inside the restricted session is separate. `QUICKSTART.md` is the five-minute walk, with `closer demo` first.

## Use

Signer, once per repo:

```sh
gc --repo /path/to/repo init                        # manifest; add --exclude NAME, --dep ID=PATH, --python /abs/venv/bin/python
gc --repo /path/to/repo scan                        # freeze a World
python3 bin/claims_draft.py --repo /path/to/repo --backlog BACKLOG.md --task 3 --out claims.json   # draft claims from the task's criteria; fill every <FILL: ...>
gc --repo /path/to/repo ticket --write src/app.py --claims claims.json   # mint a write_set on the latest World, with its claims
gc --repo /path/to/repo writer-setup                # writer config; prints the launch line
```

Writer, in the session that launch line starts, through the gc MCP tools only:

```
tickets → stage (or stage_edit) → land → check
```

Signer, any time:

```sh
gc --repo /path/to/repo ledger --check              # verify the hash chain
gc --repo /path/to/repo tickets                     # tickets, and which are struck
gc --repo /path/to/repo policy --gets-through-anyway N
gc selftest                                         # run the plants
python3 bin/dash.py --state ~/.getting-close/<repo>-<hash> [--run <proving run>]   # the signer's page: one read-only HTML file from the ledger, tickets and sealed evidence
```

`gc land` exits 0 (proceed), 1 (reject) or 3 (reroute: rescan, re-mint). A strike closes the ticket; mint a
new one.

## Claims

A ticket is minted only with claims (T5): what the code in its write_set is required to do, as a JSON list of
small sealed tests the signer writes. Each has a dotted `name` the task requires, an optional `setup` (Python
statements), a `call` (a Python expression) and one `expect`: `{"result": <literal>}`, `{"raises": "Name"}` or
`{"true": "<expression>"}`. The claims file is sealed in the state dir, bound to the ticket by `claims_sha256`,
recorded in the ledger row, and refused at land if it was rewritten. The writer never sees it. `claims_draft.py` drafts claims from a task's acceptance criteria by fixed tables (no
model): backticked names, the verbs rejects / returns / logs / accepts, and backticked literals; what the tables
cannot fill is a `<FILL: ...>` placeholder, and gc refuses to mint while one remains. The signer edits the draft;
nothing is minted that the signer did not state (T5). Its notes also carry a checklist per function the criteria
name or `--changed FILE:QUALNAME` names (from the name's claim words in `scanner/lexicon.py`: a negative case for a
check, the effect read at its sink for a save, and so on), and `claims_draft.py --check CLAIMS.json` prints the
checklist lines no claim covers; advice only, it exits 0 and refuses nothing. At land, C1 runs
every claim in the sandbox; a claim that does not hold is a strike naming the function and the gap (pass_through,
fake_check, answer_table, fake_effect, partial), and every function the ticket introduces must be
reached by some claim or it is `unreached`, a strike. A claim C1 could not bring to a verdict (its setup or import
failed, its clock or line budget ran out) is `cannot_judge`: not a strike since pack v32 (KERNEL T16); it is said
(`C1 unjudged: ...`), filed, recorded in the ledger row's `unjudged` and shown on the signer's page, and a function
only such a claim would have reached is still `unreached`. The evidence, with the expected and observed values,
is filed under `evidence/` in the state dir, which the writer cannot read.

## Where state lives

`$GETTING_CLOSE_HOME/<repo name>-<hash>/`, default `~/.getting-close/...` (`--state` overrides):

- `manifest.json`, `manifests/`: what is scanned; `python` in `manifest.json` is the repo's interpreter, passed to
  every check as `REPO_PYTHON` (absent: the checks use gc's python).
- `worlds/`: frozen Worlds, `LATEST`, S1 overlays.
- `tickets/`, `claims/`, `payload/<ticket>/`: tickets, their sealed claims, and the files staged for them.
- `evidence/`: per land, what each claim was given, expected and got. Signer-only.
- `ledger.jsonl`: one row per land, hash-chained, read-only between appends.
- `policy.json`: `gets_through_anyway`.
- `gc-writer`, `claude-writer.json`: written by `writer-setup`.

## The writer can

Read the repo (Read, Grep, Glob). List tickets and Worlds, read a World. Stage files in a ticket's
write_set. Land a ticket. Run `verify`, `check` and `ledger`.

## The writer cannot

Run a shell, edit or write files directly, use other tools or MCP servers, mint tickets, scan, set policy,
read the gate's state (tickets, claims, ledger file), or write outside a ticket's write_set. Kernel files, `pack/live/`, `plants/` and Worlds are refused in every
write_set. It cannot say done until `check` passes.

## Status

- Live pack: version 38 (`pack/live/PACK.json`): W1, R6-1, R6-2, R6-4, G18, S1, E1, C1, U1, R10-1, R10-2. S2 was withdrawn
  on 2026-10-15; E1 (the repo's tests on the patched tree), C1 (the ticket's claims) and S1's five shape rules
  (theatre_return, factory_none, finally_return, always_true, identity_return; v26) were added the same day (PACK.md).
  v27 adds C1 evidence for the signer, no strike: claim coverage per changed function (`thin`) and claims that hold
  on the before-tree too (`holds_before`).
  v28 adds U1, evidence only: undeclared behaviour changes in pre-existing functions (before-tree vs patched tree).
  v30 (2026-10-16) makes the checks correct under Python 3.8 to 3.10 (qualname fallback in C1 and U1) and stops E1 passing on an
  empty collection; `gc init --pytest-args` carries a repo's pytest settings into E1 and U1.
  v31 (2026-10-19) makes E1 name the failing test under pytest 3.x, pass `--rootdir=.` only to a pytest that takes it (3.0.x does not), and label a test's ERROR `(error)` rather than `(collection error)`; one new plant. v32 (2026-10-19) puts U1's driver spec in a file (an environment overflow struck an honest ticket), makes U1's own error
exit 75, and builds T16: what the gate cannot judge (a check exiting 75, a claim C1 cannot set up or finish) is let
through and recorded in the row (`not_run`, `unjudged`) and on the page, not refused; `unreached` stays a strike. v33
(2026-10-19) makes E1 name the failing tests when pytest dies before its summary (a verbose rerun) and say pytest's own
error. v34 (2026-10-21) adds `judge_detection` to S1 (KERNEL T20): code that asks whether it is being judged (a tracer
  query, the runner's environment names, a stack walk for pytest or the gate, spelled plainly or through folded strings) is
  struck and named; 0 hits measured in application code. v35 (2026-10-21) adds the `dynamic_code` advisory: code that builds
  or runs code at runtime (exec, eval, compile, a function or code object made by hand) is said as an `S1 note` and shown on
  the page as "Look here", never a strike; a constant string handed to exec / eval / compile is parsed and probed, a probe
  inside struck citing both lines. v36 (2026-10-21) makes every probe strike say where the answer goes (the probe line and
  the branch, return or store it reaches) and adds `s1_stand_down`, a pack-level allow-list said as notes. v37 (2026-10-21) strikes a plain `sys.settrace` or
  `setprofile` call in non-test code (0 in application code) and notes a runtime-named `getattr` on `sys` as an advisory
  (honest code swaps streams that way). v38 (2026-10-21) extends `judge_detection` to a test runner's name in
  `sys.modules` (`"pytest" in sys.modules` and its siblings, by any form): the oldest "am I under test" check, 0 in
  application code. Pack v38 is the live pack.
- The MVP bar (proposals/MVP_BAR.md, KERNEL T8): met on pack v32 on 2026-10-19 (KERNEL T19); the outcome with its numbers is in that file. Step 5, the signer's page, was closed on a watched land: the trials page rebuilt itself as a restricted writer session minted, staged and landed a ticket. The internal set is sealed (33 tasks, 66 working counterfeits); the external set of 34 real bugs is reported beside it. On 2026-10-21 the external set stands at 34 of 34 fixes landing clean and 34 of 34 buggy trees struck (MVP_BAR.md). The same night the internal set's three criteria-open items were reopened with sharper task text and closed: 0 counterfeits landed, 0 criteria open.
- Ledger rows are `draft` (the spec's draft ledger; KERNEL L1).

## Law docs

- KERNEL.md: invariants, rulings, kernel files, exit codes, known limits.
- PACK.md: the live checks and how the pack changes.
- WORLD.md: the World contract.
- DESIGN.md: how a World is produced.
- GLOSSARY.md: canonical names and retired ones (`gc glossary check`).
- RELEASE_CHECKLIST.md: before a pack or kernel change is releasable.
- MCP.md: the signer's MCP server (`closer-mcp.sh`), its seven tools, and how the yes stays with the person.

## License

PolyForm Noncommercial 1.0.0: read, run and modify freely for noncommercial purposes; commercial use needs a license from the author. See LICENSE.
