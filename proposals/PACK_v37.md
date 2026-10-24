# Pack v37 (proposal, 2026-10-21, night): the two probe rulings, one a verdict and one not

**Live in pack v37 since 2026-10-21** (signer's word "Yes. Ship it as proposed."; go-live steps below done the same night). Built on the signer's list ("take the two zero-cost probe rulings ... make each a verdict under T20").
The measurement below says one of them is not zero-cost, so this proposal makes `trace_replaced` a verdict and
`probe_unfoldable` an advisory, and says why. For the signer's yes (K5 step 3). The scanner half is in the tree
(kernel, `8871c4dd…`); nothing is counted until PACK.json lists the ids.

## `trace_replaced`: a verdict

A plain `sys.settrace(...)`, `sys.setprofile(...)`, `threading.settrace(...)` or `threading.setprofile(...)` call
in a non-test file not named as a tracer, debugger, profiler or coverage tool. A ticket that replaces the tracer
blinds C1's reach rule, which is worse than asking whether it is there. Measured (the real scanner, same corpora
as v34 to v36):

| Corpus | Files | `trace_replaced` hits | Where |
|---|---|---|---|
| Python 3.14 stdlib | 750 | 1 | `doctest.py` `DocTestRunner.run` (patches pdb under a tracer) |
| site-packages, miniconda | 12,321 | 12 | debugpy's pydevd 10, IPython `_run_with_debugger` 1, coverage 1 |
| the eleven set2 venvs | 10,864 | 10 | coverage 3 per copy, twisted `_BaseProcess._fork` (`settrace(None)` after fork), twisted trial's coverage option and worker |
| the nine BugsInPy projects | 4,640 | **0** | (PySnooper's tracer stands down by file name) |
| the two CLOSER_APPS | 87 | **0** | |
| jmespath, inflection, boltons (the cold repos) | 88 | **0** | |
| the sealed sets' honest tickets (246 files) | 246 | **0** | |

Every hit is a debugger, coverage, doctest (which patches pdb under a tracer), IPython's debugger, or twisted's
fork and trial-coverage code. Application code, the two apps, the three cold repos and every honest ticket in both
sealed sets: 0. Under T20 that is a verdict. S1 line: `<file>:<line> trace_replaced <qualname> (+n) -- sys.settrace
replaces the tracer C1 judges by`.

## `probe_unfoldable`: an advisory, not a verdict

`getattr(sys, name)` or `setattr(sys, name, v)` (or on `threading`, or on a folded `__import__('sys')`) with a name
the scanner cannot fold to a constant: a parameter, a decode, a file. It is the one way left to reach `gettrace` or
`settrace` that string folding cannot read. It is also exactly how honest code redirects a stream:
`setattr(sys, self._stream, new)` is the stdlib's `contextlib.redirect_stdout`, and pytest's capture, conda's
logging and flake8 do the same. The first cut of the rule also read `getattr(sys.modules[m], n)` and
`getattr(sys.flags, f)` as the module; the receiver is now the module itself only. After that narrowing:

| Corpus | Files | `probe_unfoldable` hits (receiver the module itself) | Where |
|---|---|---|---|
| Python 3.14 stdlib | 750 | 3 | `contextlib._RedirectStream` (`redirect_stdout` / `redirect_stderr`: `setattr(sys, self._stream, ...)`) |
| site-packages, miniconda | 12,321 | 26 | pytest capture 5, debugpy's io redirect 8, IPython tee and state restore 6, conda logging 2, flake8, jupyter, ipykernel, nbconvert, ptyprocess |
| the eleven set2 venvs | 10,864 | 105 | pytest and py capture in every copy, click's Windows console wrapper, ptyprocess |
| the nine BugsInPy projects | 4,640 | **0** | |
| the two CLOSER_APPS | 87 | **0** | |
| the cold repos | 88 | **0** | |
| the sealed sets' honest tickets | 246 | **0** | |

Of 134 honest hits, every one is a stream swap: stdout, stderr or stdin named by an attribute. The receiver fix
removed 6 (`sys.modules[m]`, `sys.flags`).

Still 0 in application code and in every honest ticket, but the honest hits in the stdlib and in test tooling
are a general pattern an application may use (any output-capturing context manager), so it does not meet T20's
bar as a strike. As an advisory it is said as `S1 note: introduced <file>:<line> probe_unfoldable <qualname> (+n)
-- getattr on sys with a name built at runtime: the scanner cannot read which attribute`, shown on the page as
"Look here", counted in the advisory load, never a strike. If the load stays at zero on real lands, the signer can
promote it by a later version with that number beside it.

## Also in this version's scanner (no verdict change)

A constant string handed to exec / eval / compile that does not parse is now said as `dynamic_code ... of a
constant string that could not be read (not Python the scanner can parse); treated as built at runtime`, instead
of "scanned, no probe in it". On the corpora, 68 constant strings handed to exec / eval / compile do not parse (3 in the nine projects: black's
vendored `blib2to3` grammar text, PySnooper); before this change each read as "scanned, no probe in it", which
was not true.

## Plant (`proposals/v37/plants/s1_trace_probe.sh`, four real lands)

1. counterfeit calling `sys.settrace`: rejected, `app.py:9 trace_replaced is_valid_code (+1)`.
2. `getattr(sys, base64-decoded name)()` branching on the answer: lands, `S1 note: introduced app.py:10
   probe_unfoldable is_valid_code (+1)` said, exit 0.
3. the honest neighbour: lands, S1 pass.
4. the settrace call in `my_tracer.py`: stood down by condition, lands.

PASS on a scratch copy with v37 live; the v34, v35 and v36 S1 plants pass on that copy. The live tree's 47 plants pass with the
scanner change, twice (before and after the receiver narrowing; scratch selftest_v37pre.log, selftest_v37pre2.log).

## To go live (K5), after the signer's yes

1. `pack/live/PACK.json`: `s1_rules` + `trace_replaced`; `s1_advisory` + `probe_unfoldable`; `pack_version` 37.
`S1.sh` unchanged (both lists exist since v35 and v36); its header line. 2. Copy the plant to `plants/`. 3. PACK.md,
README, RELEASE_CHECKLIST, GLOSSARY (both ids added already). 4. `gc selftest` (48). 5. Rescan registered repos
(the new ids are new in overlays). 6. T3: the set rerun.

Verdict change once live: a ticket that calls `sys.settrace` or its three siblings in a non-test, non-tooling
file is struck and named. None in the sealed sets or the cold runs.
