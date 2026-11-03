# Closer in five minutes

Closer is a gate between an AI code writer and your repository. You write a short task. A separate agent turns it
into claims: concrete calls and the results they must give. A locked-down writer session builds the change and can
only hand it to the gate. The gate runs your test suite and every claim against the staged code, and either lands it
or throws it out. Nothing reaches your files except through a full pass. You watch it on a local page.

## You need

- a Mac (the gate holds its checks read-only with the macOS sandbox)
- Python 3.10 or newer with `pytest`
- Claude Code installed (`claude` on your PATH)
- a Python repo with tests that pass under some interpreter you can name

## Install

Copy this folder anywhere and put `closer` on your path, for example:

    ln -s "$PWD/closer" /usr/local/bin/closer

Or, to drive it from your own Claude Code session instead of a terminal, register the MCP server once:

    bash install_closer_mcp.sh

and ask the agent for a task: it calls `cl_doctor`, `cl_task`, `cl_claims` and shows you the claims; after your yes it
calls `cl_go`, then `cl_inspect` for the verdict (MCP.md). The rest of this page is the terminal route; the two are the
same gate.

Then check the machine:

    closer doctor

## See it work first

    closer demo

That copies a tiny sample repo to a temp folder, writes its task, drafts the claims, opens the page at
http://localhost:8766/ and runs a writer on it. About a minute. Watch the page go minted, staged, checks running,
accepted.

## Use it on your repo

    cd your-repo
    closer task add-thing          # writes add-thing.md; fill every <FILL: ...>
    closer go add-thing.md

`go` does, in order:

1. First time only: finds the interpreter and the test folder, shows you both with how many tests collect, and asks
   before registering. If it guessed wrong, say no and rerun with `--python PATH` or `--pytest-args "tests"`.
2. Drafts the claims and prints them in words. Read them. They are the whole contract: anything they do not say,
   the gate does not check. If the task contradicts itself, it tells you and stops.
3. Asks, then mints the ticket, opens the page, and launches the writer. The writer can read your repo and talk to
   the gate, nothing else.
4. Reports **Correct version accepted** (the change is in your files) or **Rejected** with the reason in plain words
   (the tree is rolled back, nothing changed).

## When it is rejected

Read the reason. Three kinds:

- the writer's code did not do what a claim says: run `closer go` again, a fresh writer gets a fresh ticket
- your task was wrong (an example that contradicts its own rule, a test folder not named): fix it, run again
- the repo's own tests fail in the gate's sandbox for an environment reason: `closer doctor` shows it; use
  `--pytest-args` to name the folder or `--ignore=` a file

Two rejections on one task close the task. That is on purpose.

## Writing a task that works

State the rule, then examples that follow the rule exactly. Name every exception and what its message contains. Say
the order when order matters. Name the test file. A wrong example becomes a wrong claim and strikes an honest writer.

## Other commands

    closer claims TASK.md    draft and show the claims, mint nothing (every function the task names gets a claim,
                             or nothing is minted)
    closer go TASK.md --chat an interactive writer session: you type the request yourself
    closer status            the page as text, with the next step and the advisory load (how often notes appear)
    closer inspect [TICKET]  one ticket's verdict in words: every check and claim, what was not judged, the evidence file
    closer amend             show or change the interpreter and test folder the repo was registered with
    closer watch             watch the repo for edits made outside the gate (go starts this too); the page shows them
    closer stop              stop the page and the watcher
    closer forget --gone     remove the state of repos that no longer exist

The long version of everything, with the rules the gate follows, is README.md and KERNEL.md.
