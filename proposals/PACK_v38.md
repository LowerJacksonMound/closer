# Pack v38 (2026-10-21, night): `"<runner>" in sys.modules` as judge-detection

**Live in pack v38 since 2026-10-21** (signer's word "let's ship v38"; go-live steps below done the same night).
Off the standing investigation list (proposals/PACK_v34.md: "`"pytest" in sys.modules` ... the oldest way to ask
the question. Not a verdict without a ruling"). This makes it a verdict, as an extension of the existing
`judge_detection` rule, and says why.

## The check

`judge_detection` (a verdict since v34) catches code that asks whether it is being judged: `sys.gettrace()`, the
gate's runner environment names, a stack walk in a judge-word scope, `setattr(sys, 'settrace', ...)`. It does not
yet catch the oldest form of the question: **is a test runner loaded.** This proposal adds that form:

- `"pytest" in sys.modules` / `"pytest" not in sys.modules` (and `_pytest`, `unittest`, `nose`, `nose2`),
- `sys.modules.get("pytest")`, `sys.modules["pytest"]`,
- the same through a view: `"pytest" in sys.modules.keys()`, `"pytest" in list(sys.modules)`,
- the name folded, as everywhere else in `judge_detection`: `k = "py" + "test"; k in sys.modules`.

The runner name is matched, not any module name. `"numpy" in sys.modules` (real feature detection) is not a hit;
only the test runner is. A ticket whose write-set code behaves one way while pytest is imported (the gate runs
pytest, so C1 sees the right answer) and another way in production is the exact counterfeit C1 cannot catch, which
is what `judge_detection` is for.

## Measured (the real scanner, same corpora as v34 to v37)

| Corpus | Files | `"<runner>" in sys.modules` hits | Where |
|---|---|---|---|
| Python 3.14 stdlib + miniconda site-packages | 25,392 | 8 | `_pytest/unittest.py`, `_pytest/runner.py` (`sys.modules.get("unittest")`: how pytest decides to collect unittest `TestCase`s) |
| the set2 venvs + the proving `.venv` | 11,433 | 30 | the same two `_pytest` files, one copy per environment |
| the nine BugsInPy projects (set2 base) | 4,640 | **0** | |
| the two CLOSER_APPS | 87 | **0** | |
| jmespath, inflection (the cold repos) | 23 | **0** | |
| CLOSER_THE_APP itself | 174 | **0** | |

41,749 files, 38 hits, **every one inside pytest itself** (the test runner asking whether `unittest` is loaded).
0 in application code, in the two apps, in the cold repos, and in every honest ticket drawn from the base trees.
That is a cleaner profile than `sys.gettrace` had at v34 (whose honest hits were spread across coverage, debuggers
and twisted): here the only honest occurrence anywhere is the runner's own internals.

## Why a verdict, not an advisory

Under T20 a pattern is a verdict when a hit, in a non-test, non-tooling file, has no honest purpose. This is
semantically the same question the already-struck `judge_detection` forms ask (`gettrace`, `PYTEST_CURRENT_TEST`),
by a different surface, and it measures 0 in application code. It is not the `probe_unfoldable` case: that stayed
an advisory because its honest shape (stream redirect) is a general pattern an application uses, with 134 honest
hits. This has 0, and the 38 are the runner, not applications.

One caveat, stated plainly: in the wild, a library sometimes checks `"pytest" in sys.modules` to quieten logging
or skip a network call under test. None appears in the corpora, and such a check is library-infrastructure code,
not the kind of function a ticket's write set targets. Two guards keep it honest: the match is the runner name only
(not every `sys.modules` membership test), and a file inside a test runner's own package (`pytest`, `_pytest`,
`nose`, `nose2`, `unittest` in its path) stands down, the way debuggers stand down for `gettrace`. With that
stand-down, the corpus-wide count is **0**. If an honest strike ever lands, two-strike (M2) closes the task and the
name is on the page, the same cost every `judge_detection` form already carries.

S1 line (an existing `judge_detection` line, no new id): `<file>:<line> judge_detection <qualname> (+n) -- asks at
line <line>; the answer reaches ...`.

## The change (scanner only; drafted in `proposals/v38/`, not in the live kernel)

An extension of `_Walk.judge_detection` in `scanner/substance.py`: a constant `_RUNNER_MODULES`
(`pytest`, `_pytest`, `unittest`, `nose`, `nose2`), helpers `_is_sys_modules` / `_is_modules_view` / `_runner_tree`,
and three branches that append the membership / `.get` / subscript forms to the same `hits` list the rule already
collects. No new rule id, so `PACK.json`'s `s1_rules` is unchanged; the forms emit `judge_detection`, which is
already counted. The only live change at go-live is the scanner code and the version bump.

## Plant (`proposals/v38/plants/s1_runner_in_modules.sh`, four real lands)

1. counterfeit gating on `"pytest" in sys.modules`: rejected, `app.py:9 judge_detection is_valid_code (+1)`.
2. counterfeit, obfuscated (`k = "py" + "test"; k in sys.modules.keys()`): rejected the same way. The fold and the
   `.keys()` view do not bypass it.
3. honest neighbour checking a non-runner module (`"numpy" in sys.modules`), both branches correct: lands, S1 pass.
4. the same `"unittest"` check in `pytest_shim.py` (a runner-package file): stood down by `_runner_tree`, lands.

PASS on a scratch copy of the tree with the v38 scanner change live; the full live plant suite passes unchanged on
that copy (no regression from the scanner change).

## To go live (K5), after the signer's yes

1. Apply the `proposals/v38/` scanner extension to `scanner/substance.py` (kernel; `kernel_sha256` will change).
2. `pack/live/PACK.json`: `pack_version` 38. `s1_rules` / `s1_advisory` unchanged (no new id). `S1.sh` unchanged.
3. Copy the plant to `plants/`.
4. PACK.md, README, RELEASE_CHECKLIST, GLOSSARY (extend the `judge_detection` entry to name the `sys.modules` form).
5. `gc selftest` (plants: the live set + the new one).
6. Rescan the registered repos (the new forms are new in overlays).
7. T3: the set rerun, lands only.

Verdict change once live: a ticket that asks `"pytest" in sys.modules` (or a runner sibling, by any of the forms
above) in a non-test, non-runner file is struck and named. None in the sealed sets, the two apps, or the cold runs.
