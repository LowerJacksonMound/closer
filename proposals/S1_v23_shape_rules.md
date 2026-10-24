# Proposal: S1 shape rules for pack v23 (working notes, 2026-10-15)

**Built 2026-10-15 as pack v26.** The five new rules are live in `scanner/substance.py` (name words in
`scanner/lexicon.py`), listed in PACK.json `s1_rules`, each with a struck and an honest plant (`plants/s1_*.sh`).
Measured on real code before going live: 0 hits from the five on the stdlib, site-packages, the two CLOSER_APPS and
httpie (PACK.md, v26). One condition was added in the build: `always_true` stands down when the name says accept-all
(`is_any`), the one honest hit found.

What survived of step 3. Pure AST in `scanner/substance.py`, behind the filters S1 already has (test trees,
abstracts, conditionals, nested callbacks, dunders, `.pyi`). Each rule lands with two plants: a counterfeit it
strikes and an honest neighbour it leaves alone. Zero honest strikes is the bar; a rule that cannot meet it on
its honest plant does not go live.

| Rule | Species | Catches | Condition that keeps it honest-safe |
|---|---|---|---|
| `const_return` (live) | T1 | literal / module-constant / canned return | as now; still off for methods |
| `theatre_return` (new) | T1 | computes into locals it never reads, then returns a literal | every local assigned is unread and the return is a literal; no call with a side effect in between |
| `stub_body` (live) | T2 | pass / `...` / NotImplemented / TODO | as now |
| `factory_none` (new) | T2 | a function named make_/create_/build_/new_/_factory whose every return is None or bare | body has no call and no attribute store (an honest factory that registers something has one) |
| `swallow` (live) | T3 | broad except / suppress returning a value | as now |
| `finally_return` (new) | T3 | `return`, `break` or `continue` inside `finally` | none needed; it always masks the raise |
| `hollow_test` (live) | T8 | no assert / vacuous / mock-only | as now |
| `always_true` (new) | T9 | a function named is_/can_/has_/check_/verify_/validate_/allow/auth whose every return is the same literal True (or the same literal) | at least one return; **no `raise` anywhere in the body** (an honest validator raises on failure and returns True) |
| `identity_return` (new) | T5 | a function named mask/redact/normalize/clean/parse/format/translate/sanitize/strip that returns one of its parameters unchanged on every path | every return is a bare parameter name; no call and no store to that parameter before the return |

Dropped from step 3, with why:
- `near_const` as "a two-value map from a trivial feature": a ternary over a flag is how honest labels, plurals
  and arrows are written. Static code cannot tell the counterfeit trend text from the honest one. Only the
  claim check can, because only the claim says what the two values should depend on.
- `length_only`: a test that asserts only `len(x)` or non-emptiness is a common honest smoke test. It is hollow
  only relative to its name, which is a claim. Not a shape rule.
- "no comparison" as a form of `always_true`: too vague to plant.

Noted, not in scope: `x == x` stays non-vacuous on purpose (reflexivity tests). `assert f(x) == f(x)` through a
helper is a rigged test by claim, not by shape.
