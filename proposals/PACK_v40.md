# Pack v40 (2026-11-03): a claimed constant is the claim's to judge

**Live in pack v40 since 2026-11-03** (the quiet run, app 2, signer's ruling the same hour).

## The fail

The counter's `refuse_below_zero(state)`: Cartouche locks the parameter name `state`, the signed line locks the
sentence "Cannot go below zero. The count stays at zero.", and the task says the function changes nothing and
returns that sentence. The only honest body ignores `state` and returns the literal. S1 `const_return` struck it
(`S1 fail: introduced tally.py:24 const_return refuse_below_zero (+1)`) in the same land where claim 5 on that
function held. The rejected code runs the task's example correctly by hand.

## The line

S1 reads the ticket's claims file (the one C1 reads, bound by `claims_sha256`). A `const_return` finding on a
function a claim names is stood down and said: `S1 note: stood down <file>:<line> const_return <qualname>
(claimed; C1 judges it)`. Every other rule, and `const_return` on an unclaimed function (T1 hard-coded with no
claim reaching it), strikes as before.

## Why there and not wider

A hard-coded return on a claimed function is caught by C1 when the claims give that function two inputs with
different answers; when every claim expects the same literal, the honest function and the hard-coded one are the
same program and no check can tell them apart (a check that cannot tell is let through). So on a claimed function
the shape rule adds nothing but false strikes; on an unclaimed one it is the only check that looks.
