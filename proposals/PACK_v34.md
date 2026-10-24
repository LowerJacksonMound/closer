# Pack v34 (proposal, 2026-10-21): `judge_detection`, the first rule under KERNEL T20

**Live in pack v34 since 2026-10-21** (signer's word "lets do it"; go-live steps below done the same day). Written
as a proposal with plants and a measurement for the signer's yes (K5 step 3).

## The ruling it applies

T20 (2026-10-19): a rule is added only for counterfeit that is 90 to 100 percent counterfeit, a hit is a verdict.
"First application: `judge_detection` (code in a ticket that asks whether it is being traced, reads the runner's
environment names or `<setup>`, reads `PYTEST_CURRENT_TEST`, or walks the stack for the runner or pytest) is a
verdict and may be added as an S1 rule by proposal with plants; `sys._getframe` alone is not (logging helpers use
it); a hit in a test file does not count."

## What the rule is

Not a shape: a question the code asks. `scanner/substance.py`, `_Walk.judge_detection`, run on every file of the
write set that is not in a test tree, over every scope (module level and every function, methods, dunders, nested
functions, lambdas folded into their enclosing scope, code under `if True:` and in `except` handlers included: a
detection hidden in a branch is still a detection). A finding names `<file>:<line> judge_detection <qualname>`.

| Form (T20) | What the scanner matches | Not a hit |
|---|---|---|
| asks whether it is traced | a call to `gettrace` or `getprofile` on `sys` or `threading`, or imported bare | any other `sys` call |
| reads the runner's environment names | `os.environ["NAME"]`, `os.environ.get("NAME")` / `.pop` / `.setdefault`, `os.getenv("NAME")`, `"NAME" in os.environ`, for NAME in the gate's own runner names (`SCOPED_ROOT`, `BEFORE_ROOT`, `TICKET_FILE`, `TICKET_ID`, `WRITE_SET`, `WORLD_FILE`, `REPO_PYTHON`, `REPO_PYTEST_ARGS`, `C1_SECONDS`, `C1_LINES`, `U1_SPEC_FILE`, `U1_SECONDS`, `U1_INPUTS`, `GETTING_CLOSE_HOME`) | the same word anywhere else: a ticketing app's `"TICKET_ID"` column name is a string, not an environment read |
| reads `PYTEST_CURRENT_TEST` | the same environment forms with that name | |
| reads `<setup>` | the string literal `<setup>` (the runner's filename for a claim's setup statements) in any expression | |
| walks the stack for the runner or pytest | a call to `sys._getframe`, `inspect.currentframe`, `inspect.stack`, `inspect.getouterframes`, `traceback.extract_stack` or `traceback.walk_stack` **and**, in the same scope, a string literal containing `pytest`, `unittest`, `<setup>` or `<string>` | `sys._getframe(1).f_code.co_name` alone (T20: logging helpers); `inspect.stack()` alone; the word `pytest` in a message with no stack walk |
| (extension, 2026-10-21) replaces the tracer by name | `setattr(sys, 'settrace', ...)`, or `setattr` on `sys` / `threading` with any of the four trace names | a plain `sys.settrace(...)` call: investigation list, below |
| (extension) walks the environment looking for the runner | a `for` or comprehension over `os.environ` (or its `.keys()` / `.items()` / `.values()`, or `list(os.environ)` and the like) in a scope that also holds a string that is a runner name or a prefix of one of at least four characters (`PYTEST`, `SCOPED_R`, `C1_S`, ...) | `dict(os.environ)` handed to a subprocess; a settings loader filtering on `APP_` |

Strings are read **folded** (extension, 2026-10-21): `'get' + 'trace'`, an f-string of constants, `''.join([...])`
of constants, `b'gettrace'.decode()`, `str(...)` of one, and a name bound exactly once in its scope (or at module
level and not rebound) to such a string. So `getattr(sys, 'get' + 'trace')`, `os.getenv(k)` after
`k = 'PYTEST_' + 'CURRENT_TEST'`, and `K in os.environ` with `K` a module constant are the plain forms they spell,
and `getattr` / `setattr` with a folded name is the attribute access it is. Module-level string constants count as
every scope's words for the stack-walk form. Docstrings are not read, so a library whose documentation mentions
pytest is not struck for an honest `inspect.stack()`. What folding cannot resolve (a name from a parameter, a file,
a decode of base64, `exec` of a built string) stays on the investigation list, measured below.

Stood down, by condition, not by name of the species: test trees (pytest names, `conftest.py`, anything under
`tests/`, `test/`, `testing/`; and a non-test file that imports pytest counts as a test file, as S1 already does);
and a module whose own file name says debugger, tracer, profiler or coverage (`_TOOLING_WORDS`: debug, trace,
tracer, traceback, profile, profiler, pdb, bdb, coverage, instrument, and their inflections). The second stand-down
is the one choice in this proposal; the measurement below shows what it buys. The write set is the signer's, so a
writer cannot rename a file to reach it.

Measured on 2026-10-21 (and again after the extension the same day) over 29,431 Python files, two runs of the real scanner (`scanner.substance.extract`), one with
the stand-down and one with it disabled; the session's scratch script `measure_jd2.py`, reads only:

| Corpus | Files | Hits, stand-down on | Hits, stand-down off | Where (stand-down on) |
|---|---|---|---|---|
| Python 3.14 stdlib (site-packages excluded) | 750 | 4 | 4 | `_py_warnings.py` `warn` 3 (a stack walk naming `<string>`), `doctest.py` `DocTestRunner.run` 1 |
| site-packages, miniconda 3.14 | 12,321 | 15 | 18 | coverage 4, `_pytest` 3, conda solvers 3, mypyc crash report 1, dotenv `_is_debugger` 1, debugpy 1, IPython `_run_with_debugger` 1 |
| site-packages, CLOSER_PROVING venv | 569 | 3 | 3 | `_pytest` 3 |
| the eleven set2 venvs (py38 site-packages) | 10,864 | 46 | 48 | `_pytest` 33, `py` 9, coverage 2, `pytest_timeout.is_debugging` 2 |
| the nine set2 projects (base trees) | 4,640 | **0** | 2 | the 2 are PySnooper's `pysnooper/tracer.py` `Tracer.__enter__` (a tracing library, stood down by its file name) |
| the two CLOSER_APPS | 87 | **0** | 0 | |
| jmespath, inflection (the cold repos) | 23 | **0** | 0 | |
| this tree, the gate | 173 | 63 | 63 | `pack/live/C1.py`, `U1.py` and their `proposals/` copies read their own runner names; `scanner/substance.py` holds the name tables; `ui/go.py` reads `GETTING_CLOSE_HOME`. gc refuses to guard its own tree |

Before and after the 2026-10-21 extension, same corpora: the extension adds exactly one honest function, pytest's own
`_pytest/runner.py` `_update_current_test_var` (it sets `PYTEST_CURRENT_TEST` through a once-bound local; once in
each of twelve pytest copies), and drops pytest's `raises`, `warns` and config-warning functions, which had counted
only because their docstrings say "pytest" beside a stack walk. Application code: 0 before, 0 after.

Reading: every hit on real code is in a test framework, a coverage tool, a debugger, a crash reporter, the warnings
machinery, or the gate itself. In application code (the nine BugsInPy projects, the two apps, the two cold repos,
4,750 files) the rule finds nothing but PySnooper's tracer, which the file-name stand-down removes. The stand-down
buys 7 hits across 29,000 files (IPython's debugger, coverage's `debug.py`, PySnooper's tracer); the rule is
honest-safe on application code with or without it. The nearest honest miss outside tooling is `dotenv`'s
`_is_debugger` (asks `sys.gettrace()` to decide where `.env` is when run under a debugger): a verdict under T20's
words, and the kind of case the signer should know the rule will strike.

Investigation list (T20: doubtful patterns stay until they are a verdict), measured but not in the rule:

| Pattern | Non-test, non-tooling files with it | In application code (the nine projects, two apps, two cold repos) | Where |
|---|---|---|---|
| `sys.settrace(...)` / `sys.setprofile(...)` called plainly | 13 | **0** | twisted 4, coverage 4, debugpy 2, IPython 1, scipy 1, stdlib `doctest` 1 (PySnooper's tracer stands down by name) |
| `getattr` / `setattr` on `sys` or `threading` with a name folding cannot resolve | 62 | **0** | `_pytest` 14, pkg_resources 12, `py` 9, flask 3, IPython 3, click 2, pip 2, ... |
| `exec(...)` / `eval(...)` | 492 | 35 | in application code: black's vendored `blib2to3` parser generator (14 files across 7 copies), PySnooper `variables.py`; elsewhere setuptools 72, `_pytest` 63, jinja2 16, ... |
| `"pytest" in sys.modules` | **0** | **0** | none in 29,000 files |

- `sys.settrace(...)` / `sys.setprofile(...)` called plainly: a ticket that *replaces* C1's tracer blinds the
  reach rule, which is worse than asking. 0 in application code; the 13 are debuggers, coverage, twisted's
  deferred debugging and doctest. The spelled-out form by `setattr` is already a verdict (above); the plain call
  is left for a ruling with that number beside it.
- `getattr(sys, name)` with a name the scanner cannot fold (a parameter, a file, a decode): 0 in application
  code, 62 in packaging and test tooling. A verdict here would strike none of the measured application code; left
  for a ruling.
- `exec` / `eval` in a non-test file: 35 application files use them honestly (a parser generator, a variable
  evaluator), so not a verdict by shape.
- `"pytest" in sys.modules`: the oldest way to ask "am I under test". Honest libraries use it to quieten logging
  or skip a network call under test; it is also exactly what a counterfeit wants. Not a verdict without a ruling.

## Plants (`proposals/v34/plants/`)

`s1_judge_detection.sh`, four real lands through `gc init / scan / ticket / land`:

1. counterfeit: a validator that checks only while `sys.gettrace()` is set or `PYTEST_CURRENT_TEST` is in the
   environment, and says yes to everything otherwise. Rejected with a strike; S1 names
   `app.py:10 judge_detection is_valid_code (+1)`; the repo is untouched.
2. honest neighbour: the same claims, a validator that validates. Lands, `S1 pass`.
3. the same question asked inside the ticket's test file (`tests/test_app.py`): not a finding, the ticket lands.
4. the counterfeit of (1) spelled to slip a textual scan: `getattr(sys, "get" + "trace")` and the pytest marker
   built from two pieces into a local read by `os.getenv`. Rejected; S1 names `app.py:11,12 judge_detection
   is_valid_code (+2)`.

Run on 2026-10-21 against a scratch copy of this tree whose `PACK.json` listed the rule: PASS. The live tree's
plants (44) pass unchanged, since the live pack does not count the rule. The scanner's own smoke on thirty-two
snippets (sixteen planted forms, the obfuscations above included; sixteen honest neighbours: a `TICKET_ID` column
name, a bare `_getframe` caller-name helper, `inspect.stack()` with no judge words or with `pytest` only in a
docstring, a settings loader filtering `os.environ` on `APP_`, `dict(os.environ)` for a subprocess, a local rebound
after its constant, a parameter as the key, `getattr(sys, 'platform')`, a file named `my_tracer.py`, a test file)
matched exactly the planted sixteen.

## Files

| File | What |
|---|---|
| `scanner/substance.py` | `RULES` gains `judge_detection`; constants `_TRACE_ASKS`, `_STACK_WALKS`, `_JUDGE_ENV_NAMES`, `_JUDGE_LITERALS`, `_JUDGE_FRAME_WORDS`, `_TOOLING_WORDS`; `_TRACE_SETS`; `_Walk.judge_detection`; helpers `_own_with_lambdas` (docstrings unread), `_scopes`, `_env_name`, `_judge_words`, `_judge_env_fragment`, `_is_environ`, `_fold_str`, `_scope_consts`, `_statements`, `_tooling_module`. Already in the tree (the scanner emits every rule it has; K5 keeps it out of the verdict). `kernel_sha256` `70c308a9…` to `59e670a8…` (KERNEL.md, Kernel files). |
| `scanner/lexicon.py` | a note: the rule has no species (a mechanism any species can wear). |
| `bin/session.py` | the page's words for it: "code that asks whether it is being tested or traced". |
| `GLOSSARY.md` | `judge_detection` added through `gc glossary add` (72 terms). |
| `proposals/v34/plants/s1_judge_detection.sh` | the plant above. |

## To go live (K5 steps 3 and 4), after the signer's yes

1. `pack/live/PACK.json`: `s1_rules` gains `"judge_detection"`; `pack_version` 34. 2. `pack/live/S1.sh` header:
"Live in pack v34" with the one line. 3. Copy the plant to `plants/`. 4. PACK.md: version 34, S1 row "v34:
judge_detection", History entry; README Status: v34 line; RELEASE_CHECKLIST pass. 5. `gc selftest` (45 plants).
6. **Every registered repo must be rescanned (`gc scan`) before its next mint**: a World frozen before v34 has no
`judge_detection` findings in its substance overlay, so a pre-existing detection in a repo would read as introduced
by the first ticket that touches its file. 7. T3: a bump reruns the set; T14: meter first.

Verdict change once live: a ticket whose non-test code asks any of the four questions is struck and named. No
honest land in the sealed sets or the cold runs contains one (the set2 base trees and both CLOSER_APPS measure
0 with the stand-down).
