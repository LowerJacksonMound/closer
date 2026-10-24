# Proposal: the signer's console (U-B), written 2026-10-21 for ruling after MVP (MVP_PLAN.md C4)

No build. This is the proposal MVP_PLAN section 5 asked for, written against what exists on 2026-10-21, not against
the 2026-10-19 state the U-B row described.

## What U-B asked for, and what already exists

U-B (MVP_PLAN.md, UI track): "a local page where the signer does the signer's steps: init, scan, see the extractor's
draft, fill placeholders in a form, mint, copy the launch line, watch lands, read evidence. Needs a localhost
process." Since then the front door and the session page took most of those steps, on the terminal and on one page:

| U-B step | Where it is now | Gap |
|---|---|---|
| init, scan | `closer go` registers on first run after showing the interpreter and the test count; `closer amend` changes them; both rescan | none |
| see the draft | `closer claims TASK.md` and the pause in `closer go` print every claim in words, plus contradictions and the `--check` lines | the claims are read on the terminal, not on the page |
| fill placeholders | `closer task NAME` writes the template; `go` refuses while a `<FILL>` remains; the claim agent drafts from the rules (no placeholders left for the signer) | editing claims means editing `<state>/signer/claims.json` by hand |
| mint | `closer go` mints after the signer says yes | none |
| copy the launch line | `go` launches the writer itself (headless or `--chat`); the line is in `<state>/signer/LAUNCH_LINE.txt` | none |
| watch lands | `ui/session_server.py` on localhost, opened by `go`: minted, staged, checks running, accepted or rejected, every check and claim in words, four seconds behind the ledger | none |
| read evidence | the page's collapsed "internal terms" section; `closer inspect` on the terminal | the per-claim expected and observed values are on the page; the raw evidence file is a path |

What is left of U-B is therefore one thing: **the signer's decisions on the page instead of the terminal**: read
and edit the claims there, say yes to the mint there, and get the rejection reasons with a "run again" there.

## The constraint that decides the shape

K6: kernel, scanner, pack and adapters import no network module. The session server already lives in `ui/`, outside
the four K6 dirs, and shells out to nothing: it reads the state dir through `bin/session.py` (dash.py readers,
ledger.check). The ruling U-B asked for ("is a localhost server outside the four K6 dirs allowed") was answered in
practice on 2026-10-19 when `ui/session_server.py` became part of step 5 (T19): it is allowed, loopback only (I2).

A console that *acts* (mints, launches) needs the server to run signer commands. That is a different thing from a
server that reads: a POST handler that runs `gc ticket` is a second path to the signer's authority, on a port.
Two ways to keep T5 (nothing is minted that the signer did not state):

| | A: read-only page + terminal | B: acting page |
|---|---|---|
| mint | `closer go` on the terminal, as now | a button; the server runs `gc ticket` and `writer-setup` |
| edit claims | the file, or the terminal pause | a text area; saved to `<state>/signer/claims.json` |
| launch | `closer go` | a button; the server runs the writer subprocess |
| who can act | whoever has the shell | whoever can reach 127.0.0.1:<port> on this machine, any local process included |
| new rule needed | none | one: the console port is the signer; a process on the loopback is the signer (I2 covers the network side, not the local-process side) |
| cost | half a session (the claims table on the page; a "closer go again" hint on a rejection) | one to two sessions, plus the ruling |

## Recommendation

A. Finish the read side on the page (the claims as a table before any land, the contradiction list, the `--check`
lines, the rejection with the "example quoted in the task" note that `closer go` prints) and leave every act on
the terminal, where the shell's own permissions are the boundary. B stays open until a ruling says a loopback
process is the signer; nothing in the kernel changes either way.

Built on 2026-10-21 toward A, outside this proposal: `closer inspect` (the verdict in words on the terminal) and
`closer amend`. Not built: the page's claims table before a land (the page shows the minted claims only in a
collapsed section) and the on-page "run again".

## Built 2026-10-21 (evening): A, the read-only page, on the signer's word

The page now carries the signer's whole read side, no flag, no mode: before any ticket, the drafted claims as a table
with the task's contradictions in red and the claim checker's lines; on every state, a "next:" line that names the one
thing the signer does next (fix TASK.md / read the claims then mint / wait / read the Look here lines / read the
reason then run again / closer amend) with the shell command, since the act itself stays in the shell; every verdict,
claim, evidence path, advisory note, stand-down and watcher line as before; and an "advisory load" line (how many
lands carried a note, by rule; how many changes the watcher reported, how many with a finding). `closer status`
prints the same text. No new kernel surface; B (the acting page) stays open for a ruling.

## Ruled 2026-10-21 (Ian): B is not built. The page stays a viewer; decisions stay in the shell. Revisit only if the
shell round-trip becomes the actual friction after real use.
