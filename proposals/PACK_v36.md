# Pack v36 (proposal, 2026-10-21): the answer's path, and a pack-level stand-down list

**Live in pack v36 since 2026-10-21** (signer's word "Lets run 'em"; go-live steps below done the same day). Built on the signer's word ("keep going unless necessary to pause"; the review's third step, with the
signer's two rulings: data-flow is evidence and never a condition on the strike, and the evidence line names both the
probe's line and the line it reaches). For the signer's yes (K5 step 3). The scanner change is in the tree already
(kernel, `70040d7a…`); it changes no verdict. `proposals/v36/S1.sh` is the pack half and is not live.

## 1. Data-flow evidence on every probe (scanner; no verdict change)

A `judge_detection` finding now carries, in its `why`, where the answer to the probe goes, found by a parent map and
a conservative use search inside the scope (and across functions for a module-level answer):

| The code | S1's line (after ` -- `) |
|---|---|
| `if sys.gettrace() is not None:` | `asks at line 3; the answer reaches the branch at line 3` |
| `judged = sys.gettrace() is not None` ... `if judged:` | `asks at line 10; the answer is stored in judged at line 10, which reaches the branch at line 11` |
| `JUDGED = sys.gettrace()` at module level, read in `check` | `asks at line 2; the answer is stored in JUDGED at line 2, which reaches the branch at line 6 in check` |
| `return sys.gettrace() is not None` | `asks at line 5; the answer is returned at line 5` |
| `x if sys.gettrace() else -x` | `the answer picks a value at line N` |
| `logging.info('%r', sys.gettrace())` | `the answer is passed to a call at line N` |
| `sys.gettrace()` as a bare statement | `the answer is discarded at line N` |
| `w = sys.gettrace()` never read | `the answer is stored in w at line N and not read in this scope` |

The strike line is self-contained: file and probe line in the prefix, the branch (or return, or store and reads) in
the reason, so the writer's transcript and the signer's page both show why it fired and where it bites. The verdict
is unchanged: a probe is a verdict on presence (T20). Why not a condition, measured: of the 65 honest hits in
29,000 files of tooling (the stdlib's warnings and doctest, coverage, debuggers, pytest, conda, mypyc, dotenv), 35
store the answer and read it, 6 branch on it directly, 1 returns it (dotenv), 11 discard it, 11 use it otherwise.
Honest tooling branches on the answer by trade, so "reaches a branch" does not separate honest from counterfeit;
and a condition could only remove strikes, which a counterfeit can earn by laundering the answer through a
container or a call. Application code: 0 hits before and after, as in v34 and v35.

The inner-string strike (v35) keeps its own reason (`exec at line 7 runs code whose line 2 asks: ...`).

## 2. A pack-level stand-down list (`proposals/v36/S1.sh`, `PACK.json s1_stand_down`)

The scanner's file-name condition (a module named debugger / tracer / profiler / coverage) stays. Beside it, the
pack gains `s1_stand_down`: a list of relpath patterns (fnmatch, whole path, e.g. `vendor/dotenv/*`,
`tools/pysnooper/tracer.py`). For a file matching one, S1 drops `judge_detection` and `dynamic_code` findings
before counting, on both sides of the comparison, and says each as `S1 note: stood down <file> <rule> <qualname>
(s1_stand_down '<pattern>')`, so the page shows "Look here" for every allowance and nothing is stood down in silence.
The list is in the pack, so it is audited and changed only by version (K5), which is the point of a list over a
heuristic once it grows. Default: `[]`. The shape rules are not stood down: a vendored package in a write set is
still judged for stubs and swallows.

## Plants (`proposals/v36/plants/s1_probe_flow.sh`, three real lands)

1. counterfeit: the answer stored, then branched on. Rejected with a strike; S1's line is
   `app.py:10 judge_detection is_valid_code (+1) -- asks at line 10; the answer is stored in judged at line 10, which reaches the branch at line 11`.
2. the same probe under `vendor/` with `s1_stand_down: ["vendor/*"]`: lands, S1 exit 0,
   `S1 note: stood down vendor/dbg.py judge_detection watched (s1_stand_down 'vendor/*')` in the row. (The claim
   checks only the answer's type: under C1's tracer the probe answers True, which is the mechanism the rule exists for.)
3. the same file outside the list: struck, `dbg.py:5 judge_detection watched (+1) -- asks at line 5; the answer is returned at line 5`.

PASS on a scratch copy with v36 live (2026-10-21), with the v34, v35 and v26 S1 plants passing on that copy. The
regression set (35 snippets, planted and honest) matches exactly on the new scanner. The live tree's 46 plants pass with the
new scanner (2026-10-21 17:1x, scratch selftest_v36pre.log).

## Files

| File | What |
|---|---|
| `scanner/substance.py` | `_parents`, `_target_names`, `_name_uses`, `_scope_name_at`, `_flow`; hits carry their nodes; every judge_detection finding gets `asks at line N; ...`. Kernel; in the tree; `kernel_sha256` `5cfa4632…` to `70040d7a…` (KERNEL.md). |
| `proposals/v36/S1.sh` | `s1_stand_down` read (75 if malformed), `stood_down(rel)`, the drop on both sides, the `S1 note: stood down` lines. Not live. |
| `proposals/v36/plants/s1_probe_flow.sh` | the plant above. |

## To go live (K5), after the signer's yes

1. Copy `proposals/v36/S1.sh` to `pack/live/S1.sh`. 2. `pack/live/PACK.json`: `s1_stand_down: []`, `pack_version` 36
(a repo that needs an entry gets it by a later version, with the file named). 3. Copy the plant to `plants/` (its
stand-down case runs on a private copy of the kernel dirs with `vendor/*` set, so the live list stays empty). 4. PACK.md, README, RELEASE_CHECKLIST. 5. `gc selftest` (47). 6. Rescan registered repos (the
`why` is new in overlays; comparison ignores it, so this is for the page's words only). 7. T3: the set rerun.

Verdict change once live: none. Every S1 strike on a probe reads with both lines; every stand-down is said.
