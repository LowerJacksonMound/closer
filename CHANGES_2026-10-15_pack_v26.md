# Changes, 2026-10-15: pack v26 (S1 shape rules) and invariants K6 to K8

What changed and why, in the order it matters. The plan these close is the last two items of the shape-rule plan:
"6. Invariants the stub must keep" and "7. Suggested file layout". The layout was followed where the tree had no
other answer and ignored where it did: the claim probe already exists as `pack/live/C1.py` (not
`scanner/claim_probe.py`), plants are named for the check (`s1_*`, not `s2_*`; S2 is withdrawn), and the claim
rules already live in C1.

## Code

| File | Change | Why |
|---|---|---|
| `scanner/lexicon.py` | New. The claim words a function name can carry (lookup, factory, check, transform, accept-all) and `RULE_SPECIES`, rule id to COUNTERFEITS.md species, with `species_of()`. | Plan item 7 ("claim words + species tags"). One table for the words, outside the rule code, so a word is data and never a decision on its own. The species map exists so coverage can be counted by species later; nothing in the gate reads it (K8). |
| `scanner/substance.py` | Five rules added to `RULES`: `theatre_return`, `factory_none`, `finally_return`, `always_true`, `identity_return`, each as proposed in `proposals/S1_v23_shape_rules.md`. `_LOOKUP_WORDS` moved to the lexicon. `_own()` helper (a function's own nodes, nested scopes left out). `finally_exit` hooked into `visit` on every `try`. | The proposal was written 2026-10-15 and not built (the one open item in IMPLEMENTATION_PLAN). Pure AST, behind the filters S1 already has (test trees, abstracts, conditionals, nested callbacks, dunders, `.pyi`, decorated functions). |
| `scanner/substance.py`, `always_true` | Stands down on a name that says accept-all (`is_any`, `allow_all`, `is_anything`). | Measured on site-packages before going live: jsonschema `is_any(checker, instance): return True` is honest by design and was the one hit. Miss beats false positive on real code (plan item 6). |
| `scanner/substance.py`, `always_true` and `identity_return` | Off for methods, like `const_return`. `theatre_return` and `factory_none` run on plain-class methods too. | A base class's `can_edit(self, user): return True` or `format(self, v): return v` is a default meant to be overridden; a method that computes and discards, or a factory that makes nothing, is not. |
| `scanner/substance.py`, `always_true` and `identity_return` | Stand down on any call, raise, assert, with, await or yield in the body. | An honest validator raises on failure, or calls one that does (`schema.validate(cfg); return True`). Static code cannot tell that call from a decorative one, so it is not judged. |
| `scanner/substance.py`, `theatre_return` | Only plain assignments to locals through side-effect-free builtins, then one literal return. Any other call, a `_`-named local, an attribute or subscript target stands it down. | `r = save(x); return True` may be the function's real effect. `_ = compute()` is a deliberate discard. |
| `pack/live/PACK.json` | `pack_version` 25 to 26. New `s1_rules` list: the nine rule ids S1 counts. | Plan item 7 ("add the new rule ids"), and K5: the scanner is kernel code, hashed in `kernel_sha256`, not in `pack_sha256`. Without the list, adding a rule to the scanner would change what S1 strikes with no pack version change. Now the scanner emits every rule it has and S1 counts only the ids the pack names, on both sides. |
| `pack/live/S1.sh` | Header "Live in pack v26". Reads `s1_rules` from PACK.json; a missing or malformed list, or an id the scanner lacks, is exit 75 (not run, no strike). Findings outside the live ids are ignored before and after. Pass line reports `rules=N`. | As above. 75, not 1, because a broken pack is the host's fault, not the ticket's (KERNEL exit codes). |

## Plants (all run the real kernel: `gc init`, `scan`, `ticket`, `land`)

| Plant | Proves | Why this shape |
|---|---|---|
| `s1_theatre_return`, `s1_factory_none`, `s1_finally_return`, `s1_always_true`, `s1_identity_return` | Each rule, both ways: the counterfeit is rejected with a strike and S1's line is exactly `S1 fail: introduced app.py:<line> <rule> <qualname> (+1)`; the repo is untouched. The honest neighbour lands, S1 exit 0, and C1 holds the same claims on it. | RELEASE_CHECKLIST: a changed rule has a plant that fails without it and passes with it. The honest half is what keeps the rule honest-safe (zero honest strikes is the bar). The same claims on both halves mean the honest code is real working code, not a shape that merely dodges the rule. |
| `s1_scanner_writes_nothing` | `substance.py after` and `gc scan` leave every byte of the tree as it was; the overlay is read-only; a second write to it is refused; the overlay did read the tree (its findings name the planted counterfeits). | Plan item 6, invariant 1 (now K7). It was enforced by `scanner/emit.py` but nothing proved it. |
| `no_model_in_gate` | No model client and no network module is imported anywhere in `bin/`, `scanner/`, `pack/live/`, `adapters/`; no live shell check calls curl, wget, nc, ssh. | Plan item 6, invariant 5 (now K6). |

## Law docs

| File | Change | Why |
|---|---|---|
| `KERNEL.md` | K6 (no model, no network in the gate), K7 (the scanner never writes the tree it reads), K8 (a finding names file, line, rule, qualname; species is coverage only). | Plan item 6: invariants are written into a law doc, not left in chat (standing rule). |
| `KERNEL.md`, "Kernel files" | Corrected: `scanner/**/*.py` is hashed into `kernel_sha256`. The doc said it was not; `ledger.kernel_hash` has included it all along. | RELEASE_CHECKLIST: law docs match the code. |
| `PACK.md` | Live pack 26; S1 row lists the nine rules and `s1_rules`; History v26 with the real-code measurement. | K5 record. |
| `GLOSSARY.md` | Added through `gc glossary add`: the five findings, `s1_rules` (key), `lexicon` (concept). `gc glossary check` exits 0. | New names go through the glossary before any doc uses them (Phase 6 F). |
| `README.md` | Status: live pack 26, the five rules named. | The line said version 23 and v25 at once. |
| `proposals/S1_v23_shape_rules.md`, `proposals/IMPLEMENTATION_PLAN.md` | Marked built as pack v26, with the one condition added in the build (accept-all). | So the proposal is not read as still open. |

## Measured before going live (miss beats false positive)

Real scanner over real code, findings from the five new rules only:

| Tree | Files | Hits |
|---|---|---|
| Python 3.14 stdlib | 1,866 | 0 |
| site-packages | 5,183 | 0 (1 before the accept-all condition: jsonschema `is_any`) |
| CLOSER_APPS familyguy_episodes | 45 | 0 |
| CLOSER_APPS tower_defense | 42 | 0 |
| httpie (CLOSER_SPEC copy) | 133 | 0 |

## Not done, and why

- Plan item 6, invariant 4 says the claim probe is optional. KERNEL T5 says no ticket without claims and C1 is in
  `every_ticket`. Two written rules conflict; T5 is law and stands. Bounded is kept (C1's clock and line budget).
  Ruled 2026-10-15: T5 wins (KERNEL.md T5).
- The five rules are proved on plants and measured clean on real code. T2 proving on real working counterfeits in
  the two apps is the signer's call (the labelled counterfeits are in the archive).
- Outstanding tickets on any repo minted under pack v25 are rejected by the bump and need re-minting. No state dir
  was found under this tree or CLOSER_APPS; other state dirs are the signer's to check.
