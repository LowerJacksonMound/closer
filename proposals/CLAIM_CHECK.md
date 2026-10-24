# Proposal: the claim check (working notes, 2026-10-15)

What survived of steps 1 and 2. A proposal, not law: nothing here is live until it goes through K5.

## Placement

```
gc land → governor (reject / reroute, decided before apply) → apply → G18 → S1 → C1 (new) → ledger
```

- S1 stays as it is: pure AST, conservative, no execution.
- C1 is a pack check in `every_ticket`, pack v23. It goes through proposal, plants and signer yes (K5), and
  each row's `pack_sha256` keeps describing what judged it.
- C1 executes ticket code only inside the verify sandbox (I2). Exit 75 only for the host's fault.
- C1 is bounded: a timeout and an input budget. Out of time or out of budget is **reject**, the same as cannot
  judge. Never silence.
- C1 judges **every changed function** in the write set. There is no trigger pattern and no exemption.
- The claim C1 checks against comes from the **ticket**, which the signer mints and the writer cannot touch.
  Never from the code's docstrings, names or tests.
- No new World field. C1 writes what S1 writes: lines in the ledger row.

## Fact

One fact per `(file, qualname, rule)`, only for what the ticket introduced (B3), as a line in the row:

```
C1 fail: introduced <file>:<lines> <rule> <qualname>  claim=<ticket> input=<...> expected=<...> observed=<...>
```

- `file` + `qualname` is the key, as for S1. `lines` is a range.
- `rule` names what is wrong, never which check fired:
  S1: `stub_body`, `const_return`, `swallow`, `hollow_test`, `unparsed`.
  C1: `fake_effect`, `fake_check`, `pass_through`, `answer_table`, `partial`, `rigged_test`.
- Species (T1..T10) follows from the rule and is never part of the decision. Coverage counts derive it.
- Evidence has four fixed parts or there is no strike: the claim's source (the ticket), the input used, what the
  claim said should happen, what was observed. A strike the signer cannot reproduce from the line is not a strike.
- Checks keep deciding for themselves (exit 1 strikes; the governor reads exits). No new decider. If one is ever
  wanted, it is a governor change and is proposed as such.
- New names (`C1` and its six rules) go through `glossary add` before any doc uses them.

## What closes the gap: the parts to add (2026-10-15)

The claim is the required outcome per introduced function, authored by the signer, never by the writer. Six parts,
none of which exist yet. A, B and D are kernel or ticket changes; C and E are pack checks; F is the checklist.

**A. Ticket claims.** The ticket grows a `claims` list, written only at mint by the signer (`gc ticket --claims
FILE`). One claim: `{name, kind, input, expected}`; `kind` is `result` (call `name` with `input`, get `expected`) or
`effect` (call `name` with `input`, then `expected` names where the effect must be observable: a file and its
content, an attribute, a log line). `name` is the entry point the task requires, so the signer can name it before
the code exists; the writer must implement that name. A ticket with an empty claims list is refused at mint.

**B. Claim extraction from the task's criteria.** The signer already writes the task with acceptance criteria.
Fixed keyword rules (CodeRadar's statement-to-facts machinery, copied in, no LLM) turn the criteria into draft
claims: numbers, nouns, inputs and outcomes. Absent when nothing matches, never wrong. The signer approves or
edits the drafts at mint. Where the extractor is empty, the signer writes the claim by hand.

**C. C1, the claim check.** A pack check in `every_ticket`. For each claim, inside the verify sandbox, call `name`
with `input`, compare to `expected` (CodeRadar's probe runner, copied in, with the expected value taken from the
ticket instead of the docstring). Timeout or budget exhausted: reject. Rules named for the gap found:
`fake_check`, `answer_table`, `pass_through`, `partial`, `fake_effect`, `rigged_test`.

**D. The reach rule.** Every function the ticket introduces must be reached while C1 runs the claims. One that is
not reached is unjudged, and unjudged is reject. This is the no-exemption ruling made concrete: a writer cannot
add a function the claims never exercise.

**E. The before-ticket requirement.** With S2 gone, nothing at land runs the repo's tests. A pack check runs the
tests that were in the World before the ticket (the prior authors' requirement, which the writer did not write)
against the patched tree. A failure is a strike, `run_fail`. This covers changed functions for free; it says
nothing about new ones, which is what A to D are for.

**F. Discipline.** Each new rule lands with a struck plant and a clean honest plant; names through `glossary
add`; pack v23 under K5; the ticket shape change through the kernel checklist.

## Ruled

- T5 (KERNEL.md, 2026-10-15): claims stated at mint by the signer, drafted from the task's criteria by fixed rules;
  extractor empty means the signer writes by hand or refuses the ticket; no ticket without claims; no agent drafts
  claims. Parts A to F are cleared to build, in the order A, E, C, D, B, F.
