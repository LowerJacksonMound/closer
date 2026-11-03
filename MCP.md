# Closer MCP

Two MCP servers live in this tree. They are not the same server and never share a process.

- `adapters/claude_code/gc_mcp.py` is the **writer's**. `closer go` starts it inside the restricted writer session
  with the state dir fixed in the launch config. Its tools (`tickets`, `worlds`, `read`, `stage`, `stage_edit`, `land`, `verify`,
  `check`, `ledger`) are the writer's whole write surface. Nothing here changes it.
- `adapters/claude_code/closer_mcp.py` is the **signer's**: your own Claude session drives the front door through it,
  instead of you typing `closer go` in a terminal. Every tool runs `closer <command>` (ui/go.py) in the repo you name.
  It adds no rule and touches no kernel file.

One local stdio process. No port (the live page is `closer go`'s own server, on 8766 unless `port` says otherwise).
stdout is the protocol. From this folder:

```sh
sh closer-mcp.sh            # or: python3 adapters/claude_code/closer_mcp.py
bash install_closer_mcp.sh  # registers it with Claude Code at user scope; --print shows the line
```

Python 3.10 or newer, no extra package. The registration carries a 50-minute tool timeout because `cl_go` blocks
while the writer works.

## Tools

Every tool takes `repo`, the absolute path of the repository (the folder `closer go` would run in). A relative path is
refused: it would resolve against this server's directory, not your shell.

| Tool | Call |
|---|---|
| `cl_doctor` | `repo`, optional `python`, `pytest_args`. `closer doctor`: the machine, and whether the repo's tests collect. |
| `cl_task` | `repo`, `name`. `closer task NAME`: a TASK.md skeleton for the person to fill in. |
| `cl_claims` | `repo`, `task` (absolute path of the TASK.md), optional `redraft`, `python`, `pytest_args`. Registers the repo on first use with the guessed interpreter (doctor shows it), drafts the claims, prints them. Nothing is minted. |
| `cl_go` | `repo`, `task`, `approved`, optional `write` (list of extra write-set files), `port`. Mints, opens the page, runs the writer, reports the verdict. Blocks until the writer ends. |
| `cl_status` | `repo`. What the live page shows, as text. |
| `cl_inspect` | `repo`, optional `ticket`, `raw`. One ticket's verdict in plain words. |
| `cl_stop` | `repo`. Stops the live page server and the watcher. |

## The yes stays with the person (T5)

`closer go` in a terminal pauses: "Read the claims. Mint the ticket and launch the writer? [y/N]". Over MCP the
pause has to be rebuilt, because the agent could otherwise answer it. Two refusals do that:

- `cl_go` is refused until `cl_claims` has printed this repo and task's claims **in this server process**, with the
  task text unchanged since. The claims therefore reach the transcript before anything can be minted.
- `cl_go` is refused unless `approved` is `true`, and the server instructions tell the agent that `approved` is the
  person's word: the agent shows the claims and waits; it does not say yes on its own reading.

The agent in your session is not the siloed claim agent (T5's amendment): claims are still drafted by
`bin/claims_draft.py` under `closer claims`. The agent only carries them to you.

## Refusals

- `repo` not an absolute path or not a directory; `task` not an absolute path to a file.
- `cl_go` before `cl_claims`, or after TASK.md changed: "cl_claims first".
- `cl_go` with `approved` anything but `true`.
- Any `closer` exit other than 0 is returned as an error with the command's own words and `[exit N]`.

## What it does not do

It never talks to the writer. It never edits claims (edit `<state>/signer/claims.json` by hand, as before, then
`cl_go` the same task). It runs one `closer` command per call and keeps no state but the set of tasks whose claims it
has shown. The CLI is unchanged and stays the way to use Closer without an agent.
