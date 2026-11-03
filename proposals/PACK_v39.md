# Pack v39 (2026-11-03): a system problem is not a strike; an outcome is

**Live in pack v39 since 2026-11-03** (signer's ruling the same night).

## The ruling

"If it is a problem with the system, not a problem caused by possible counterfeit code being run, a system problem
should not count as a strike. But we have to ensure that it is a system problem, not just an outcome we are not
expecting."

## The line

C1's runner already runs each claim in a fresh python with the patched tree importable. v39 adds one fact to each
failure: whether any frame of the exception ran inside the tree under test (the scoped root, site-packages aside).

- **None did**: the failure came from the claim's own setup or call text (a name the claim never bound, a bad
  literal), or from the environment. That is the system's. The claim is `cannot_judge ... (system)` and a function
  left unreached only by such claims is `C1 unjudged: <file>:<line> cannot_judge <name> (unreached: its claims could
  not run; system)`. No strike; the land proceeds if nothing else struck; the signer fixes the claims.
- **Any did**: the code under test was on the stack when it failed. That is an outcome, expected or not, and is
  judged exactly as before: `partial`, `cannot_judge` with reach lost, `unreached`, strike and all.

## Why the line is there and not wider

A claim whose scenario is wrong can make correct code raise (the quiz: a repeated wrong answer the claim did not
expect made `time_up` raise early). The writer took that strike. Under v39 it still does, because the writer's
code raised: the gate cannot tell a wrong claim from wrong code by looking at the exception alone, and a rule that
forgave every setup error would forgive a writer whose function raises on the first call. The signer reads the
evidence and corrects the claim, as happened.

## What changed

- `pack/live/C1.py`: `where()` in the runner; `judge()` marks `(system)` and turns a call-text failure into
  `cannot_judge`; `main()` says a system-only unreached function as unjudged instead of a fail.
- Plant `c1_system_vs_outcome.sh` replaces `c1_unjudged_unreached_strikes.sh`: a setup NameError (system) lands
  without a strike and names the function as not judged; a setup that calls into the tree and the tree raises
  (outcome) is still struck `unreached`.
- `PACK.json` 38 -> 39. Outstanding tickets bound to v38 are rejected by the bump, as always.
