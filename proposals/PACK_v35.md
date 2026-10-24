# Pack v35 (proposal, 2026-10-21): `dynamic_code`, an advisory that looks inside the string

**Live in pack v35 since 2026-10-21** (signer's word "let's move forward"; go-live steps below done the same day). Built on
the signer's word ("let's proceed", the second step under T20's category), with plants and a measurement, for the
signer's yes (K5 step 3).

## What it is

Code that builds or runs code at runtime is where a counterfeit hides the four `judge_detection` probes (v34).
It is also what honest code does about once in ninety application files (plugin loading, a parser generator, a
CLI evaluating option values), so it is not a verdict (T20) and never a strike (T16). It is a **signal the signer
sees in the normal path**: the gate says it, the page and `closer inspect` show it by default, `closer go` repeats
it on an accepted land. And where the string is a constant, the scanner **looks inside**: the four probes run over
the string's own code, and a probe found there is the verdict it would be outside.

| Form | What the scanner does | Said as |
|---|---|---|
| `exec(s)`, `eval(s)`, `compile(s, ...)` with `s` a string built at runtime | advisory `dynamic_code` at the call's line | `S1 note: introduced <file>:<line> dynamic_code <qualname> (+n) -- exec of a string built at runtime` |
| the same with `s` a constant (folded as in v34: concatenation, f-strings, join, bytes.decode, once-bound names) | the string is parsed (as a module, else an expression) and `judge_detection` runs over it. No probe: advisory. A probe: **a `judge_detection` strike at the outer line, citing the probe's line and text** | `S1 fail: introduced app.py:7 judge_detection is_valid_code (+1) -- exec at line 7 runs code whose line 2 asks: watched = sys.gettrace() is not None` |
| `types.FunctionType(...)`, `types.CodeType(...)` | advisory | `... -- builds a FunctionType by hand` |
| `__import__('sys').gettrace()`, `importlib.import_module('sys')...` (name folded) | read as `sys` by every v34 form; a strike where the plain spelling is one | the v34 line |

Not judged: test trees and tooling-named modules, as in v34. Dynamic imports with a runtime name (`__import__(x)`)
are not flagged: they are the commonest honest form (168 in site-packages, 24 in the nine projects, luigi's plugin
loading) and reveal nothing about probes; left for a word.

## Where the signer sees it (the two conditions the signer set)

1. **Visible without a flag.** The note is on stdout, so it is in the ledger row's check lines. `bin/session.py`
   renders every `S1 note:` line as an amber **Look here** paragraph under the land's checks table, in words
   ("builds or runs code at runtime in `app.py:6 calc` eval of a string built at runtime"), on every land, no mode.
   `closer inspect` prints `LOOK HERE: ...` beside the checks. `closer go` prints `LOOK HERE (accepted, but read this
   before you trust it): ...` right after `CORRECT VERSION ACCEPTED`. Verified on a real land of an honest `eval`
   ticket (scratch, 2026-10-21): the three outputs above, word for word.
2. **Both lines cited.** A finding carries a `why`; S1 says it after ` -- `. For a probe inside a constant string the
   why names the outer call and line, the probe's line inside the string, and the probe's text, so the writer's
   transcript and the signer's page both show what fired and where. The existing plants still match (they grep the
   line's prefix).

## Measured on 2026-10-21 (the real scanner, 29,169 files)

| Corpus | Files | `dynamic_code` findings | files with it | probes found inside constant strings |
|---|---|---|---|---|
| the sealed internal set's honest tickets (the real write sets) | 173 | 0 | 0 | 0 |
| the external set's honest tickets | 73 | 2 | 1 (tqdm's CLI, `eval` of option values) | 0 |
| the internal set's counterfeit tickets | 375 | 0 | 0 | 0 |
| the nine BugsInPy projects | 4,640 | 51 | 36 (1 in 129; eval 39, exec 8, compile 4) | 0 |
| the two CLOSER_APPS | 87 | 0 | 0 | 0 |
| jmespath, inflection | 23 | 0 | 0 | 0 |
| boltons (cold run 5) | 65 | 5 | 2 (`namedutils`, `funcutils`: builds classes and functions with exec) | 0 |
| stdlib 3.14 | 750 | 75 | 38 | 0 |
| site-packages, miniconda | 12,321 | 229 | 127 | 0 |
| the eleven set2 venvs | 10,864 | 648 | 415 | 0 |

Reading: on the work the gate has judged, the note would have appeared on 1 honest ticket in 67 and on no
counterfeit; in application code it appears on about one file in a hundred, always honestly. No constant string
handed to exec, eval or compile anywhere in 29,169 files holds a probe, so the inner scan strikes nothing honest and
the only way through it is a string built at runtime, which is exactly what the note points the signer at. The v34
`judge_detection` numbers are unchanged by the folded-import form (0 in application code).

## Plants (`proposals/v35/plants/s1_dynamic_code.sh`, three real lands)

1. honest: a function evaluating a user's arithmetic with `eval`, with a claim reaching it. Lands; `S1 pass ... notes=1`;
   the note `app.py:10 dynamic_code calc (+1) -- eval of a string built at runtime` on stdout and in the row's said lines.
2. counterfeit: the tracer question inside a constant string handed to `exec`. Rejected with a strike; S1 names the
   exec line and the probe's line and text (the full line above).
3. counterfeit: `__import__("sys").gettrace()`. Rejected, named.

PASS on a scratch copy of this tree with `proposals/v35/S1.sh` live and `s1_advisory` set (2026-10-21); the v34 and
v26 S1 plants pass on that copy too. The live tree's 45 plants pass with the scanner change. The scanner's smoke:
twelve new snippets (six planted, six honest, one in a test file) and the v34 regression set, all as expected.

## Files

| File | What |
|---|---|
| `scanner/substance.py` | `RULES` gains `dynamic_code`; `_DYNAMIC_CALLS`, `_CODE_OBJECTS`; `add(..., why)`; `_judge_root` (folded imports); `_inner_probes`. In the tree; not counted (K5). `kernel_sha256` `59e670a8…` to `5cfa4632…` (KERNEL.md). |
| `proposals/v35/S1.sh` | reads PACK.json `s1_advisory` (default empty), says `S1 note:` lines on stdout, never a strike; a finding's `why` after ` -- ` on notes and fails; `S1 pass ... notes=N`; 75 if the scanner lacks a named rule. |
| `bin/session.py`, `ui/go.py` | the words (`dynamic_code`); the Look-here paragraph, `LOOK HERE` in inspect and in go's accept line; S1's plain words carry the why. Not kernel. |
| `GLOSSARY.md` | `dynamic_code` through `gc glossary add` (73 terms). |

## To go live (K5 steps 3 and 4), after the signer's yes

1. Copy `proposals/v35/S1.sh` to `pack/live/S1.sh`. 2. `pack/live/PACK.json`: `s1_advisory: ["dynamic_code"]`,
`pack_version` 35. 3. Copy the plant to `plants/`. 4. PACK.md: version 35, S1 row, History; README Status;
RELEASE_CHECKLIST pass. 5. `gc selftest` (46). 6. Rescan every registered repo (a World frozen before v35 has no
`dynamic_code` findings in its overlay, so a pre-existing `eval` would otherwise read as introduced and be noted on
the first ticket touching its file; a note, not a strike, but a wrong note). 7. T3: a bump reruns the set (lands only).

Verdict change once live: none by the advisory. One by the inner scan: a probe spelled inside a constant string
handed to exec, eval or compile is struck as the v34 forms are. The substance overlay's findings may carry a `why`
key (optional; S1 reads it only to say it; overlays frozen before v35 lack it and compare as before).
