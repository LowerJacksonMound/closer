# Pack v30 (proposal, 2026-10-16)

**Live as pack v30 since 2026-10-16 (signer yes). The files under `proposals/v30/` are the record; `pack/live/` is the law.**

Two fixes to the live checks that the external bug set (`~/Desktop/CLOSER_PROVING/set2`, every project on CPython
3.8.20) exposed. Not live. Nothing under `pack/live/`, `bin/` or the law docs was edited; the proposed files are in
`proposals/v30/`, the gc change is a patch file, and the plants are in `proposals/v30/plants/`.

| File | What |
|---|---|
| `proposals/v30/C1.py` | full proposed C1 (fix 1) |
| `proposals/v30/U1.py` | full proposed U1 (fix 1, and REPO_PYTEST_ARGS from fix 2) |
| `proposals/v30/E1.sh` | full proposed E1 (fix 2) |
| `proposals/v30/gc.patch` | unified diff against `bin/gc` (fix 2: `gc init --pytest-args`, `REPO_PYTEST_ARGS`) |
| `proposals/v30/plants/` | three new plants and a one-line README |

## Fix 1 (blocking): reached names below Python 3.11

**What was wrong.** C1's runner records every call into the tree as (file, qualname) with
`getattr(frame.f_code, "co_qualname", frame.f_code.co_name)` (v29 `C1.py:134`). `co_qualname` arrived in 3.11. Under
a 3.8, 3.9 or 3.10 `REPO_PYTHON` the recorded name is the bare `co_name` (`__bool__`), and the reach rule compares
it against the full qualname from the file's syntax tree (`tqdm.__bool__`), so every changed method, and every
changed nested function, comes out `unreached`. That is a reject with a strike on an honest ticket. Module-level
functions were unaffected because their bare name is their qualname. The `coverage` evidence counted 0 claims for
the same functions, wrongly.

U1 had a weaker fallback (v29 `U1.py:94-97`): the short name stood in only when it was unique among the watched
functions. Two changed methods with the same short name in one file (`Box.get`, `Shelf.get`) were both missed, so
U1 recorded no inputs for them. Evidence only, no strike, but wrong evidence.

**The change.** Two new functions inside C1's `RUNNER` (so they run under `REPO_PYTHON`, stdlib only):

- `qualnames_in(path)`: parses the file with `ast` and maps (name, first line) to the qualname for every def and
  class, spelled as `co_qualname` spells it: `C.m`, `f.<locals>.g`, `f.<locals>.C.m`. The first line is the one
  `co_firstlineno` gives, which is the first decorator's line when the def is decorated (from 3.8, `ast` gives the
  `def` line as `lineno`, so the key uses `min(lineno, decorator lines)`). Decorators, bases, defaults and
  annotations are walked in the enclosing scope; bodies in their own scope. A name declared `global` in the
  enclosing def or class gets its bare name, as the compiler does. Keys two different qualnames share are dropped.
  `{}` when the file cannot be read or parsed.
- `qualname_of(code, path=None)`: `code.co_qualname` when it exists; else `qualnames_in` for the file, cached once
  per file, looked up by (`co_name`, `co_firstlineno`); else `co_name` (a lambda, a comprehension, exec'd code).

The tracer line becomes `q = qualname_of(frame.f_code)`. U1's recorder already takes `norm()` out of C1's RUNNER;
v30 takes `norm`, `qualnames_in` and `qualname_of` the same way (`_runner_source`, replacing `_norm_source`), and
`_u1_where` calls `qualname_of(code, f)`. The `_u1_byname` short-name table is removed. Both checks now resolve
names by one function.

**Checked against the real thing.** For every def and class code object in the 3.8 stdlib (704 files) and all of
set2's base trees (4,640 files), the 3.8 fallback was compared with 3.14's `co_qualname` for the same
(file, name, first line): 66,612 code objects, 0 differences. The only difference before the `global` rule was
`uuid._load_system_functions`'s `global _generate_time_safe`. The scripts are in the scratch directory, not here.

**K-rules.** K6: stdlib only (`ast`), no model, no network. K2: the runner reads the repo's file, writes nothing; C1
still writes only under its temp dir. K8: findings still name file, line and qualname, now the right qualname on
3.8. K5: this proposal. T4 and T5 are unchanged in meaning; the reach rule now judges what it was meant to judge.

**Evidence, before and after** (scratch repo: `Bar.__bool__` and a decorated `@staticmethod @lru_cache Bar.twice`
changed, the nested `outer.<locals>.inner` changed, claims reach all of them; `REPO_PYTHON` the set2 tqdm-py38):

```
v29 C1, 3.8:   C1 fail: introduced app.py:8 unreached app.Bar.__bool__
               C1 fail: introduced app.py:13 unreached app.Bar.twice
               C1 fail: introduced app.py:18 unreached app.outer.<locals>.inner          (exit 1)
               coverage Bar.__bool__ claims 0, Bar.twice claims 0, outer.<locals>.inner claims 0
v30 C1, 3.8:   C1 pass: 4 claim(s) held on 3 function(s)                                  (exit 0)
               coverage Bar.__bool__ claims 2, Bar.twice claims 1, outer.<locals>.inner claims 1
v30 C1, 3.10 and 3.14: the same pass line and the same coverage.
```

On the real tqdm/3 change (set2 base, `working/tqdm/3/tqdm/_tqdm.py` adds `tqdm.__bool__` and `__nonzero__`), with
three claims that reach them:

```
v29 C1, 3.8:   C1 fail: introduced tqdm/_tqdm.py:950 unreached tqdm._tqdm.tqdm.__bool__
               C1 fail: introduced tqdm/_tqdm.py:958 unreached tqdm._tqdm.tqdm.__nonzero__
v30 C1, 3.8:   C1 pass: 3 claim(s) held on 2 function(s)
               coverage tqdm.__bool__ claims 3 inputs 2; tqdm.__nonzero__ claims 1 inputs 1
```

U1, the same-short-name case (`Box.get`, `Shelf.get` changed, 3.8):

```
v29 U1: U1 pass: 2 changed function(s), 0 input(s) recorded, 0 compared, 0 difference(s), 0 undeclared
v30 U1: U1 pass: 2 changed function(s), 4 input(s) recorded, 4 compared, 0 difference(s), 0 undeclared
```

## Fix 2: pytest exit 5, and the repo's own pytest settings

**What was wrong.** E1 treated pytest exit 5 (no tests collected) as a pass (v29 `E1.sh:35`). tqdm names its tests
`tests_*.py` and needs `-o python_files=tests_*.py`; pytest collected nothing and E1 printed
`E1 pass: no tests in the tree` on a tree with six `tests_*.py` files. Tests that exist and were not run are unjudged, and
unjudged is reject. Separately, the gate had no way to give pytest the repo's own settings, so E1 and U1 could not
run such a suite at all.

**The change.**

1. E1: on exit 5, look for test files in the patched tree: `test_*.py`, `*_test.py`, `tests_*.py`, or any `.py`
   other than `__init__.py` and `conftest.py` under a `tests/` or `test/` directory (hidden dirs, `__pycache__`,
   `site-packages`, `node_modules` and venvs skipped). Found: `E1 fail: run_fail (pytest exit 5: ...)`, naming up to
   three of them and the pytest args used: a reject with a strike, like any E1 fail. None found: still
   `E1 pass: no tests in the tree`.
2. `gc init --pytest-args "ARGS"` (one string of shell words) is recorded in the manifest as `pytest_args`. It is
   refused at init when it is empty or not shell words. gc exports it to every check as `REPO_PYTEST_ARGS`, from the
   manifest only: `gc land` (the ticket's verify and every pack check), `gc verify` and `gc check`. An inherited
   `REPO_PYTEST_ARGS` is dropped, as `REPO_PYTHON` already is. `verify_ticket.py` is unchanged: it already passes its
   environment to the check.
3. E1 adds `shlex.split(REPO_PYTEST_ARGS)` after its own flags (v29 `E1.sh:27`). U1's pytest driver adds the same
   words before its test paths (v29 `U1.py:281`). Both exit 75 (not run) if the words do not parse, which can only
   happen if the manifest was edited by hand.

The gc diff is `proposals/v30/gc.patch` (`patch -p1 < proposals/v30/gc.patch` from the tree root). It touches the
manifest docstring, `run_check` (takes `env`), a new `pytest_args_env`, `check_env` (adds it), `cmd_init`, the two
verify calls in `cmd_land`, `cmd_verify`, and the init parser.

**K-rules.** K5: this proposal. `bin/gc` is a kernel file, so `kernel_sha256` changes: `68209e3d…` (live) to
`d468b580e7ec9da870d7e82c41f957929a9559d88e9532d149b2c8d33c4bedaa` (with the patch). Rows from then on differ from
older rows, as at v29; KERNEL.md's kernel-files note should record it. K2: REPO_PYTEST_ARGS reaches pytest only as
argv inside the existing verify sandbox, so it does not widen what a check can write. K4: the setting is in the
manifest, which is state; the writer cannot reach it. K6: no change (`shlex`, `os.walk`).

**Evidence, before and after** (scratch repo `pkg/tests/tests_calc.py`, 3.8):

```
v29 E1, no args:                     E1 pass: no tests in the tree                                      (exit 0)
v30 E1, no args:                     E1 fail: run_fail (pytest exit 5: no tests collected, but the tree has test
                                     files: pkg/tests/tests_calc.py; pytest args: none; the repo's own pytest
                                     settings go in gc init --pytest-args)                              (exit 1)
v30 E1, REPO_PYTEST_ARGS='-o python_files=tests_*.py':
                                     E1 pass: 1 test(s) passed on the patched tree                      (exit 0)
v30 E1, same args, add broken:       E1 fail: run_fail pkg/tests/tests_calc.py::test_add (before-ticket) (exit 1)
v30 E1, no test files in the tree:   E1 pass: no tests in the tree                                      (exit 0)
```

On the real tqdm/3 fixed tree: v29 `E1 pass: no tests in the tree`; v30 with no args `E1 fail: run_fail (pytest exit
5: no tests collected, but the tree has test files: tqdm/tests/tests_main.py, tqdm/tests/tests_pandas.py,
tqdm/tests/tests_perf.py; ...)`. With BASE_CHECKS' args (`-o 'python_files=tests_*.py'
--ignore=tqdm/tests/tests_perf.py tqdm/tests`) E1 runs the suite. It then fails on tests that fail in this
environment on the base tree as well (see "For the signer" below).

## Plants

All three follow the existing plants' shape: a temp repo, `gc --repo --state` into the temp dir, land through the
real kernel, read the ledger row, print `PLANT <name>: PASS`. They go in `plants/`.

| Plant | Proves | On v29 |
|---|---|---|
| `c1_py38_qualname` | `gc init --python <3.8>`. T1 (clean) changes `Box.get` and `Shelf.get` (same short name), the decorated static `Box.twice` and the nested `outer.<locals>.inner`, and its claims reach them all: C1 `pass: 4 claim(s) held on 4 function(s)`, no `unreached`, land proceeds, coverage has each qualname at the right line with 1 claim, U1 records and compares inputs for all five changed functions. T2 (struck) changes `Box.get` and claims only `Box.twice`: exactly one strike, `C1 fail: introduced app.py:8 unreached app.Box.get`, by its full name. Needs a 3.8 with pytest (`GC_PLANT_PY38`, default set2's tqdm-py38); it checks that interpreter has no `co_qualname`. | FAIL: T1 rejected, four `unreached` lines |
| `e1_exit5_tests_present` | Case 1 (struck): `pkg/tests/tests_calc.py`, no settings: exit 5 is `E1 fail: run_fail (pytest exit 5: ... pkg/tests/tests_calc.py; ...`, reject, strike, rolled back. Case 2 (clean): only `tests/conftest.py`: still `E1 pass: no tests in the tree`. | FAIL: `E1 pass: no tests in the tree`, land proceeds |
| `e1_pytest_args` | Case 1 (clean): `gc init --pytest-args "-o python_files=tests_*.py"` is in the manifest; land gives `E1 pass: 1 test(s) passed` with a junk inherited `REPO_PYTEST_ARGS` in the caller's env, which is ignored; U1 records 2 inputs (the test's and the claim's); `gc verify` with E1 also collects. Case 2 (struck): a ticket that breaks the tested input gives `E1 fail: run_fail pkg/tests/tests_calc.py::test_add (before-ticket)` and a strike. Case 3: no `--pytest-args`, `REPO_PYTEST_ARGS` inherited: not used (exit 5 fail, `pytest args: none`); `--pytest-args` that are not shell words are refused at init and leave no manifest. | FAIL: `init --pytest-args` unknown |

The split was checked in two scratch copies of this tree (spec folder left out), never in a real state dir:

- v30 copy (the three files in `pack/live/`, `gc.patch` applied, `PACK.json` at 30, the three plants added):
  `plants/run_all.sh`, 38 plants PASS, `plants: PASS`. The 35 existing plants are unchanged and pass.
- v29 copy (unmodified, plus the three new plants): each new plant FAILs as in the table.
- With v29's U1 dropped into the v30 copy, `e1_pytest_args` FAILs on the U1 input count (1, not 2). So the plant
  catches U1 not getting the setting, not only E1.

## Going live (K5 steps 3 and 4, on signer yes)

1. Copy `proposals/v30/{C1.py,U1.py,E1.sh}` to `pack/live/`. Change the first docstring or comment line from
   "Proposed for pack v30" to "Live in pack v30".
2. `patch -p1 < proposals/v30/gc.patch`.
3. `pack/live/PACK.json`: `pack_version` 30. The lists do not change.
4. Copy `proposals/v30/plants/*.sh` to `plants/`.
5. PACK.md: version 30; rows E1, C1, U1 "last set in v30" with the exit-5 rule, `REPO_PYTEST_ARGS`, and the name rule
   below 3.11. History line: v30 (2026-10-16), the two fixes, plants `c1_py38_qualname`, `e1_exit5_tests_present`,
   `e1_pytest_args`. KERNEL.md kernel-files note: the `kernel_sha256` change above. README `Use`: `gc init
   --pytest-args`.
6. `gc selftest`.

T2 and T3: v30 is a new frozen pack. CLOSER_PROVING results on v26 or v29 do not carry over. The proving run has to
be done fresh on v30.

## For the signer

- **What changes beyond the two named lines.** C1's RUNNER gains two functions, which U1 now imports along with
  `norm`. U1 loses its short-name fallback. The v29 U1 docstring said only 3.10 lacks `co_qualname`; in fact 3.8,
  3.9 and 3.10 all lack it. C1's `coverage` evidence on 3.8 to 3.10 now counts claims for methods and nested
  functions (v29 counted 0). U1's pytest run takes REPO_PYTEST_ARGS, so on a repo with settings it now records
  inputs from tests it used to skip. E1 now judges a suite it used to report as empty, so a repo that "passed" E1
  with no tests collected can now be struck. That is the point, but it is a change in verdicts.
- **CLOSER_PROVING needs the setting.** prove.py has to pass each bug's BASE_CHECKS `args` column to
  `gc init --pytest-args`. Otherwise every tqdm item (and any other repo with nonstandard test names) is now an E1
  fail at exit 5 instead of a silent pass.
- **The tqdm suite is not green here even with the args.** `tests_main.py::test_main` and `::test_manpath` fail on
  the base tree too (set2 lists them in `_tools/deselect/tqdm/3.txt`). `tests_synchronisation.py::test_monitoring_multi`
  also failed on the base tree in a plain run here, though BASE_CHECKS records the base as 61/0. Those deselects
  have to go into the pytest-args as `--deselect <node>` (with the `#` comments stripped from the deselect file), or
  E1 will strike every tqdm ticket for tests that were already red. `test_monitoring_multi` needs a look before the
  proving run.
- **Known limits of the name lookup.** Code without a def or class (lambdas, comprehensions) keeps `co_name`. That
  is harmless, because the reach rule exempts lambdas and only judges defs. A name-mangled `global __x` inside a
  class is not modelled; it did not occur in the 66,612 code objects checked.
