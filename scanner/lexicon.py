"""Claim words and species tags for the substance scanner (S1). Fixed tables, nothing else: no model, no network.

A function's name is a claim about what it does: `is_valid` claims a check, `make_worker` claims a factory,
`mask_email` claims a transform, `get_rate` claims a lookup. The shape rules in substance.py use these words only
to decide which shape a function is measured against. A word never makes a finding on its own: the finding is
the shape (every return the same literal, a parameter handed back, a factory that makes nothing).

Species (COUNTERFEITS.md T1..T10) are for coverage counts only. The gate names the function and the rule,
`<file>:<line> <rule> <qualname>`, never the species: a species follows from the rule after the decision and
takes no part in it (CLAIM_CHECK.md, "Fact"; COUNTERFEITS.md, "Crosses").
"""

from __future__ import annotations

# A no-argument function that says it looks something up (`get_rate`, `current_user`). Measured 2026-10-05
# (public, scalar/dict return): +0 stdlib / +1 site-packages (ipykernel `get_tmp_hash_seed`, itself hard-coded).
LOOKUP_WORDS = frozenset({
    "get", "fetch", "load", "read", "detect", "current", "compute", "calc", "calculate", "query", "lookup", "find",
    "discover", "probe", "measure", "count", "report", "resolve", "now", "today", "status", "check", "poll", "scan",
    "list", "latest", "live", "env", "environ",
})

# A function that says it makes something (T2 `factory_none`).
FACTORY_PREFIXES = ("make_", "create_", "build_", "new_")
FACTORY_SUFFIXES = ("_factory",)

# A function that says it decides something (T9 `always_true`). `allow` / `auth` match without an underscore:
# allow, allowed, allows, auth, authorize, authenticate.
CHECK_PREFIXES = ("is_", "can_", "has_", "check_", "verify_", "validate_", "allow", "auth")
# A check whose name says it accepts everything is honest when it does: jsonschema `is_any(checker, instance)`
# returns True for every instance by design. Measured 2026-10-15: the one site-packages hit without this.
ACCEPT_ALL_WORDS = frozenset({"any", "anything", "all", "always", "everything", "never", "nothing", "none"})

# A function that says it transforms its input (T5 `identity_return`). Any word of the name, `_`-split.
TRANSFORM_WORDS = frozenset({
    "mask", "redact", "normalize", "normalise", "clean", "parse", "format", "translate", "sanitize", "sanitise",
    "strip",
})

# rule -> species, for coverage counts. Rules with no species (`unparsed`, `cannot_judge`, `unreached`, `run_fail`)
# name a failure to judge or to run, not a counterfeit shape, and are absent here on purpose.
RULE_SPECIES = {
    # S1, scanner/substance.py (shape)
    "const_return": "T1", "theatre_return": "T1",
    "stub_body": "T2", "factory_none": "T2",
    "swallow": "T3", "finally_return": "T3",
    "identity_return": "T5",
    "hollow_test": "T8",
    "always_true": "T9",
    # C1, pack/live/C1.py (claim)
    "answer_table": "T4", "pass_through": "T5", "fake_effect": "T6", "partial": "T7", "fake_check": "T9",
    "rigged_test": "T10",
    # judge_detection (S1, T20 first application) has no species: it is a mechanism any species can wear (code that
    # behaves only while it is judged), so it is absent here on purpose, like unparsed.
}


def bare(name: str) -> str:
    """`_make_worker` is a factory as much as `make_worker`."""
    return name.lstrip("_")


def words(name: str) -> set[str]:
    return set(bare(name).lower().split("_"))


def claims_lookup(name: str) -> bool:
    return bool(words(name) & LOOKUP_WORDS)


def claims_factory(name: str) -> bool:
    n = bare(name).lower()
    return n.startswith(FACTORY_PREFIXES) or n.endswith(FACTORY_SUFFIXES)


def claims_check(name: str) -> bool:
    return bare(name).lower().startswith(CHECK_PREFIXES) and not (words(name) & ACCEPT_ALL_WORDS)


def claims_transform(name: str) -> bool:
    return bool(words(name) & TRANSFORM_WORDS)


# Signer checklist only (bin/claims_draft.py, proposals/INGREDIENTS.md item 4). substance.py reads none of these,
# so a word added here changes no finding. Check, transform and factory reuse the tables above, widened by the
# words the checklist needs; compute and effect are classes the scanner has no rule for.
CHECKLIST_CHECK_WORDS = frozenset({"check", "validate", "verify", "allow"})
CHECKLIST_TRANSFORM_WORDS = TRANSFORM_WORDS | {"transform", "convert"}
CHECKLIST_TRANSFORM_PREFIXES = ("to_",)
COMPUTE_WORDS = frozenset({"compute", "count", "lookup", "rate", "score", "trend", "summary", "total"})
EFFECT_WORDS = frozenset({"save", "write", "send", "post", "log", "delete", "export"})


def checklist_classes(name: str) -> list[str]:
    """The claim classes a function name carries, for the signer's checklist: any of check, transform, factory,
    compute, effect, in that order. Advice to the signer; never read on the way to a decision."""
    w, n = words(name), bare(name).lower()
    out = []
    if claims_check(name) or (w & CHECKLIST_CHECK_WORDS and not w & ACCEPT_ALL_WORDS):
        out.append("check")
    if w & CHECKLIST_TRANSFORM_WORDS or n.startswith(CHECKLIST_TRANSFORM_PREFIXES):
        out.append("transform")
    if claims_factory(name) or "factory" in w:
        out.append("factory")
    if w & COMPUTE_WORDS:
        out.append("compute")
    if w & EFFECT_WORDS:
        out.append("effect")
    return out


def species_of(rule: str) -> str | None:
    """Coverage only. Never read on the way to a decision."""
    return RULE_SPECIES.get(rule)
