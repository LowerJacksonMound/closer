# Pack v31 (proposal, 2026-10-19; amended the same day, signer's ruling: four items folded in, one bump)

**Live as pack v31 since 2026-10-19 (signer yes). The files under `proposals/v31/` are the record; `pack/live/` is the law.**

Was: nothing under `pack/live/`, `bin/`, `plants/` or the law docs was edited; the proposed file is in
`proposals/v31/`, the plant in `proposals/v31/plants/`.

Four fixes to E1, all in the one script, so the set2 run (CLOSER_PROVING, 3.8 venvs handed to E1 as REPO_PYTHON) is
clean on every pytest the venvs carry (3.0.7, 3.10.1, 4.6.11, 5.4.3, 6.2.5, 7.4.4):

| # | What was wrong (v30) | v31 |
|---|---|---|
| 1 | `--rootdir=.` is always passed; pytest 3.0.7 (httpie-2014-py38, httpie-2016b-py38) has no such option, exits 2 (`unrecognized arguments`) before collecting, so every ticket in those repos got `run_fail (pytest exit 2, no test named)`, honest ones included | the flag is passed only when the repo's pytest lists `--rootdir` in `--help` (added in pytest 3.1); without it node ids are still `tests/...::...` relative to the cwd, the tree root |
| 2 | the short-summary parse reads `FAILED` only; pytest 3.x prints `FAIL`, and a method's node id carries `::()` | reads `FAILED|FAIL|ERROR`, drops `::()` (the first proposal) |
| 3 | the live E1 header still reads "Proposed for pack v30" (v30's go-live step 1 was never applied) | the proposed header reads "Proposed for pack v31 (2026-10-19: ...)" and lists every change back to v23; go-live copies the file as is and changes "Proposed" to "Live" |
| 4 | every `ERROR` line is suffixed `(collection error)`, a fixture error included | `(collection error)` only when the ERROR names a file (no `::`), `(error)` when it names a test |

| File | What |
|---|---|
| `proposals/v31/E1.sh` | the full proposed E1 |
| `proposals/v31/plants/e1_pytest3_names_test.sh` | the plant (extended: two interpreters, three cases), plus a one-line README |

## What each old pytest printed

Probe repos in the scratch dir, run with `python -m pytest -q --tb=no -rfE --color=no -p no:cacheprovider` from each
set2 venv (read only), 2026-10-19. `pfix`: one passing, one failing and one erroring (fixture raises) test, and a red
method on a class. `pcoll`: a test file that imports a module that does not exist.

```
pytest 3.0.7  (httpie-2014-py38, httpie-2016b-py38; the two are the same version):
   with --rootdir=.   usage: pytest.py [options] ... / pytest.py: error: unrecognized arguments: --rootdir=.   exit 2
                      (`--help` does not list --rootdir)
   without, pfix:     FAIL tests/test_probe.py::test_red
                      FAIL tests/test_probe.py::TestBox::()::test_method_red
                      ERROR tests/test_probe.py::test_err                                                     exit 1
   without, pcoll:    ERROR tests/test_coll.py                                                               exit 2
pytest 3.10.1 (httpie-2016-py38, thefuck-old-py38): takes --rootdir; the same five lines with or without it
pytest 4.6.11 (luigi-2018-py38):   FAILED tests/test_probe.py::test_red - assert 1 == 2
                                   FAILED tests/test_probe.py::TestBox::test_method_red - assert 1 == 3
                                   ERROR tests/test_probe.py::test_err - RuntimeError: boom                  exit 1
                                   ERROR tests/test_coll.py                                                  exit 2
pytest 5.4.3  (scrapy-2019-py38):  as 4.6.11 (checked in the first proposal)
pytest 7.4.4  (tqdm-py38):         as 4.6.11
```

So: the `FAILED`/`FAIL` boundary is below 4.6; `::()` is 3.x only; the two `ERROR` forms are the same on every version
(a collection error names the file, a setup error names the node, and 4.6 on appends ` - message` to the node form only).
Node ids are relative to the cwd on every version with or without `--rootdir=.`, also with a `tox.ini [pytest]` in a
parent directory (checked on 3.0.7, 3.10.1, 7.4.4), so dropping the flag on 3.0.7 keeps the file part matching the
write_set paths.

## The change

`diff pack/live/E1.sh proposals/v31/E1.sh` is the header, the notes, and these lines of logic:

```
v30:  cmd = [sys.argv[5] or sys.executable, "-m", "pytest", "-q", "--rootdir=.", "-p", "no:cacheprovider", ...]
v31:  py = sys.argv[5] or sys.executable
      h = subprocess.run([py, "-m", "pytest", "--help"], capture_output=True, text=True, timeout=limit)   # TimeoutExpired: E1 fail, out of time
      rootdir = ["--rootdir=."] if "--rootdir" in h.stdout else []
      cmd = [py, "-m", "pytest", "-q", *rootdir, "-p", "no:cacheprovider", ...]

v30:  m = re.match(r"^(FAILED|ERROR)\s+(\S+)", ln)
      node = m.group(2).rstrip(":")
      fails.append(f"{node} ({...})" + (" (collection error)" if m.group(1) == "ERROR" else ""))
v31:  m = re.match(r"^(FAILED|FAIL|ERROR)\s+(\S+)", ln)
      node = m.group(2).rstrip(":").replace("::()", "")
      label = "" if m.group(1) != "ERROR" else (" (error)" if "::" in node else " (collection error)")
      fails.append(f"{node} ({...})" + label)
```

The `--rootdir` decision is pytest's own answer (`--help`), not a version table. The probe is one more pytest start
(under a second) per E1 run, with the suite's clock as its own timeout; a `--help` that fails outright leaves
`h.stdout` without `--rootdir`, the flag is dropped and the main run reports whatever is wrong. `\S+` already stops
before 4.6's ` - message`; the file part (`split("::", 1)[0]`, matched against the write_set) is unchanged by `::()` or
by the label.

**K-rules.** K5: this proposal. K8: the finding names the test under pytest 3.x as under 4.6 and later, and a fixture
error is no longer called a collection error. K6, K2: no change (same `re`, same pytest run plus `--help`, writes
nothing). T4/T5: no change in what is judged. **One verdict changes**, and it is a correction: an honest ticket in a
pytest 3.0.x repo, which v30 rejected with a strike (`pytest exit 2, no test named`), lands under v31 when its tests are
green. Every other v30 reject stays a reject, every other pass a pass; only the text of the `run_fail` line changes.

**Evidence, before and after** (the probe dirs as SCOPED_ROOT, both test files in the write_set; `pack/live/E1.sh` vs
`proposals/v31/E1.sh` by hand, 2026-10-19):

```
pytest 3.0.7   v30 pfix:  E1 fail: run_fail (pytest exit 2, no test named)
               v30 pcoll: E1 fail: run_fail (pytest exit 2, no test named)
               v31 pfix:  E1 fail: run_fail tests/test_probe.py::test_red (own)
                          E1 fail: run_fail tests/test_probe.py::TestBox::test_method_red (own)
                          E1 fail: run_fail tests/test_probe.py::test_err (own) (error)
               v31 pcoll: E1 fail: run_fail tests/test_coll.py (own) (collection error)
pytest 3.10.1  v30 pfix:  E1 fail: run_fail tests/test_probe.py::test_err (own) (collection error)   (the two red tests unnamed)
               v30 pcoll: E1 fail: run_fail tests/test_coll.py (own) (collection error)
               v31:       the same four lines as v31 on 3.0.7
pytest 4.6.11, 7.4.4
               v30 pfix:  the three tests named; test_err labelled (collection error)
               v30 pcoll: E1 fail: run_fail tests/test_coll.py (own) (collection error)
               v31:       the same four lines as v31 on 3.0.7
```

## Plant

`proposals/v31/plants/e1_pytest3_names_test.sh`, the existing plants' shape: a temp repo, `gc --repo --state` into the
temp dir, `gc init --python <venv python>`, land through the real kernel, read the ledger row, print
`PLANT <name>: PASS`. One plant, extended rather than split: the same three cases run under two interpreters, pytest
3.10.1 (takes `--rootdir`) and pytest 3.0.7 (does not).

| Case | Proves | On v30 |
|---|---|---|
| 1 (struck, named) | the ticket breaks `tests/test_app.py::test_f` and adds `tests/test_g.py` with a red method `TestG::test_g` and a test `test_e` whose fixture raises; the row has decision reject, strike, E1 exit 1, and E1 said exactly `tests/test_app.py::test_f (before-ticket)`, `tests/test_g.py::TestG::test_g (own)`, `tests/test_g.py::test_e (own) (error)`; no `::()`, no `no test named`, no `(collection error)`; repo rolled back | under 3.10.1: `FAIL pytest3-rootdir: before-ticket test not named: E1 fail: run_fail tests/test_g.py::test_e (own) (collection error)`; under 3.0.7 (cases reordered in a scratch copy): `FAIL pytest30-no-rootdir: E1 did not name the failing tests: E1 fail: run_fail (pytest exit 2, no test named)` |
| 2 (clean) | an honest ticket lands under the same interpreter, `E1 pass: 1 test(s) passed on the patched tree`; the test asserts it ran on pytest 3.x | under 3.0.7 v30 rejects it (exit 2): the honest ticket that lands only on v31 |
| 3 (struck, collection error) | the ticket's own `tests/test_bad.py` imports a module that does not exist; reject, strike, E1 exit 1, E1 said exactly `tests/test_bad.py (own) (collection error)` | passes on v30 (v30 already labelled a file-level ERROR so); it pins the label v31 keeps |

Interpreters: `GC_PLANT_PYTEST3`, default `~/Desktop/CLOSER_PROVING/set2/_envs/thefuck-old-py38/bin/python` (3.8.20,
pytest 3.10.1), and `GC_PLANT_PYTEST30`, default `.../httpie-2016b-py38/bin/python` (3.8.20, pytest 3.0.7). The plant
checks each is pytest 3.x, that the first lists `--rootdir` in `--help` and the second does not. **Either absent: the
plant FAILs** (exit 1, `no interpreter at ...; set GC_PLANT_...`), the convention `c1_py38_qualname` follows for its 3.8;
the first proposal's "not run, exit 0" is gone, and the README line says so.

## Proof

Two scratch copies of this tree (spec folder, `proposals/`, `__pycache__` and `.DS_Store` left out), never the real
tree, never a real state dir, 2026-10-19:

- v31 copy (`proposals/v31/E1.sh` as `pack/live/E1.sh`, `PACK.json` at 31, the plant in `plants/`):
  `plants/run_all.sh`: 39 plants PASS, `plants: PASS` (38 existing plus `e1_pytest3_names_test`; the first proposal miscounted 40), 0 FAIL lines; the
  plant alone runs in about 10 s. Log in the scratch directory, not here.
- v30 copy (unmodified, `pack/live/E1.sh` byte-identical to the live one by `diff`, plus the plant): the plant FAILs as
  in the table, under 3.10.1 first (`before-ticket test not named`) and, with the 3.0.7 cases run first in a scratch
  copy of the plant, `(pytest exit 2, no test named)`.
- The proposed and the live E1 were run by hand under pytest 3.0.7, 3.10.1, 4.6.11 and 7.4.4 on the probe dirs
  (evidence above).

## To go live (K5 steps 3 and 4, on signer yes)

1. Copy `proposals/v31/E1.sh` to `pack/live/E1.sh` as is. Change "Proposed for pack v31" on line 2 to "Live in pack
   v31"; the rest of the header (the list of every change) stays.
2. `pack/live/PACK.json`: `pack_version` 31. The lists do not change.
3. Copy `proposals/v31/plants/e1_pytest3_names_test.sh` to `plants/`.
4. PACK.md: live pack version 31; row E1 "last set in v31", add "names the failing test under pytest 3.x (`FAIL`,
   `::()`); `--rootdir=.` only when the pytest takes it (3.0.x does not); `(error)` vs `(collection error)`". History
   line: v31 (2026-10-19), the four fixes, plant `e1_pytest3_names_test`, 39 plants pass. README `Status`: a v31 line,
   "Pack v31 is the live pack".
5. Hashes (bin/ledger.py): `kernel_sha256` does not change (`KERNEL_FILES` is `bin/*`, the adapters and `scanner/`; E1.sh
   is none of them; live `d468b580e7ec9da870d7e82c41f957929a9559d88e9532d149b2c8d33c4bedaa`). `pack_sha256` is
   `tree_hash` over every file in `pack/live/`, so it changes: live
   `c16541060cde8dbbdc2d488db35657674627283266694013699c3110fb0ff31f`; with the proposed E1 headed "Live in pack v31"
   (line 2 only changed) and PACK.json at 31 it is `0abf96e200efd9aa94deced2fc27f1cedb57013ebe920a138ad52df7c74c5678`
   (recompute after step 1 if the header is worded differently). Rows from then on carry the new value.
6. `gc selftest`. A version bump rejects every outstanding ticket.

T2/T3: v31 is a new frozen pack; CLOSER_PROVING results on v30 do not carry over. The CLOSER_PROVING note "E1 under
pytest below 5 names no failing test" closes with this ("below 5" is "below 4.6" by the venvs here), and so does the
set2 exit-2 note for httpie-2014 and httpie-2016b.

## For the signer

- **One verdict changes, by correction**: honest tickets in pytest 3.0.x repos (httpie-2014, httpie-2016b) land under
  v31; v30 rejected and struck them without running a test. Everything else keeps its verdict; the `run_fail` text
  gains names and the right ERROR label.
- **`--help` as the probe.** E1 asks the repo's pytest what it takes rather than reading a version table. If the signer
  would rather the version (`pytest.__version__ >= 3.1`), it is a two-line swap in the same place.
- **The plant needs two venvs** from CLOSER_PROVING and FAILs without them, as `c1_py38_qualname` does. On a machine
  without CLOSER_PROVING `plants/run_all.sh` fails on those two plants; that was already so for `c1_py38_qualname`.
- Nothing in this amendment needed more than the brief allowed; no item is left undone.
