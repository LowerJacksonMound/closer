# COUNTERFEITS: what the gate hunts

Written 2026-10-15. Eleven species (T11 added 2026-10-16),
each with its sub-species and one example per biome. A **biome** is where the code lives: pure function, method
with state, I/O (file, db, network), UI handler, worker (thread / async), validator or auth, test.

Every counterfeit is a **gap**: what the function was required to do that it does not do (GLOSSARY.md). The
two kinds differ in where the gap shows. **Shape** species (T1, T2, T3, T8) have a total gap: whatever was
required, the code does none of it, so the gap shows in the code itself. **Claim** species (T4, T5, T6, T7, T9,
T10) have a partial gap: the code does the part its own tests touch, and the gap is the rest. It shows only
against a point of the requirement the writer did not choose.

## T1 hard-coded: returns a constant or near-constant whatever its input

| Sub-species | Example | Biome |
|---|---|---|
| Literal return | `def rating_trend(h): return 0.0` | pure |
| Near-constant: two outputs picked by a trivial feature | `return "↑" if h else "→"` for a trend text | UI |
| Computation theatre: computes, discards, returns fixed | `s = sum(...); return 3.0` | method |
| Constant exception | every input raises the same `ValueError("bad")`, claiming validation | validator |
| Fixed "fresh" value | `new_request_id()` returns the same token each call | I/O |
| Constant status | worker `status()` always `"idle"` while running | worker |
| Constant match | `matches(q, ep)` returns True for every query | pure |

## T2 placeholder: a stub body

| Sub-species | Example | Biome |
|---|---|---|
| `pass` / `...` / `return None` | `def on_key(self, k): pass` for a documented key | UI |
| NotImplemented behind a default | `if fmt == "md": raise NotImplementedError; return ""` | pure |
| TODO with a default | `# TODO real check` then `return True` | validator |
| Factory that makes nothing | `_make_worker()` returns None, poll never runs | worker |
| Empty handler registered | button wired to a handler whose body is `pass` | UI |
| Init that sets nothing | `SettingsScreen.__init__` ignores its arguments | method |
| Stub endpoint | `def post_json(...): return {"ok": True}` without a request | I/O |

## T3 swallowed failure: catches a failure and returns a default, or reports success

| Sub-species | Example | Biome |
|---|---|---|
| Bare except → default | `except: return []` on a parser | pure |
| Log and return success | `except Exception as e: log(e); return True` | I/O |
| Narrow except that hides the real failure | `except OSError: pass` inside `rotate_autosaves`, so a failed move loses a save and reports ok | I/O |
| Failure turned into a value | `change_password` returns `"changed"` when the store raised | method |
| Swallowed on a worker thread | exception in the thread target never reaches the caller | worker |
| Awaited task's error dropped | `asyncio.gather(..., return_exceptions=True)` and the result ignored | worker |
| UI shows nothing | `sign_in` catches `LockedOut` and draws no message | UI |
| `finally` that returns | `finally: return result` masks the raise | pure |

## T4 answer table: right only for the inputs its tests use

| Sub-species | Example | Biome |
|---|---|---|
| Dict keyed on the tests' literals | `{"s01e01": 2, "s02e03": 7}.get(code, 0)` | pure |
| if/elif chain of the tests' inputs | `if gold == 100: return 5 elif gold == 250: return 12 else: return 0` | method |
| Default outside the tested range | computed for 1..10 pages, `0` beyond | pure |
| Golden written by the code | `expected.json` regenerated from the output it checks | test |
| Field changed only when it is the tested one | `Inbox.reformattable` counts only the fixture's note kind | method |
| Lookup by hash of the input | memoized table shipped as "the algorithm" | pure |
| Validator with a whitelist of the tests' values | `is_valid(v): return v in ("a", "b")` | validator |

## T5 pass-through: claims to transform, validate, clean or redact, and hands its input back

| Sub-species | Example | Biome |
|---|---|---|
| Parse that returns the raw string | `parse_query(q)` returns `q` | pure |
| Redact / mask that returns the original | `mask_email(e): return e` | pure |
| Normalize that copies | `normalize(d): return dict(d)` | pure |
| Clean that returns "cleaned" input | validator returns the input as the cleaned value | validator |
| Serializer that returns the object | `to_row(ep): return ep` | I/O |
| Format that drops nothing | `_audit_when(ts)` returns `ts` unformatted | UI |
| Translation that returns the key | `t("menu.start")` returns `"menu.start"` for the second language | UI |

## T6 fake effect: claims to write, save, send or delete, and does not, or does it where nothing reads

| Sub-species | Example | Biome |
|---|---|---|
| Builds the payload, never writes | `save_settings` serializes and returns without `write` | I/O |
| Writes where nothing reads | autosave to a temp dir the loader never opens | I/O |
| Logs "sent" without sending | `post_json` logs `sent` and makes no request | I/O |
| Delete that only marks in memory | `delete_sessions_for(user)` clears a list, not the table | I/O |
| Reads stale state, so the effect is empty | `submit_score` reads `self.recording` after it was set to None, every score refused | method |
| Effect on a copy | mutates `list(items)` and returns ok | pure |
| Enqueue with no worker | `start_wave` queues a boss that nothing spawns | worker |
| Button with no wiring | `seek_next_wave` drawn, handler never bound | UI |
| Mixer that plays nothing | `Mixer.__init__` never opens the music voice | I/O |

## T7 partial: does the slice its tests reach; the rest is silently wrong

| Sub-species | Example | Biome |
|---|---|---|
| First page / first item only | export marks the first watched episode only | I/O |
| One format of several | markdown export works, CSV returns markdown | I/O |
| Happy path only | `place_tower` handles an empty cell; occupied cells silently succeed | method |
| Test-sized only | no pagination; correct under 50 rows | pure |
| One language of N | German strings for the title screen only | UI |
| Drawn but not interactive | settings buttons placed under other buttons, unclickable | UI |
| One event of the set | `App.poll` handles refresh, drops the notify event | worker |
| Load path without the buttons | `_load_game_buttons` lists saves, none loads | UI |

## T8 hollow test: a test that cannot fail

| Sub-species | Example | Biome |
|---|---|---|
| Asserts nothing | calls the function, no `assert` | test |
| Tautology | `assert result == result`, `assert True` | test |
| Asserts the mock's own return | `mock.return_value = 3; assert f() == 3` | test |
| No-exception only | `f(x)  # should not raise` | test |
| Asserts on the fixture, not the result | checks the input list is sorted | test |
| Checks part of what its name claims | `test_air_order_is_unchanged` asserts `order == "air"`, never the order | test |
| Vacuous setup | `assert all(x.ok for x in [])` | test |
| Quietly skipped | `pytest.skip` inside the body on the real path | test |
| Loops seamlessly, asserts length | `test_music_buffer_loops_seamlessly` checks only `len(buf) > 0` | test |

## T9 fake check: a validator, permission or auth check that always passes

| Sub-species | Example | Biome |
|---|---|---|
| Validator always True | `is_valid_code(s): return True` | validator |
| Permission ignores the user | `can_edit(user, ep): return True` | validator |
| Auth compares nothing | `check_password(p, h): return True` | validator |
| Lockout that never locks | `_locked_until()` returns None after any count | method |
| Rate limiter that never limits | `allow(key)` always True | worker |
| Signature verify on mismatch | `verify(sig, body)` returns True when `sig` is empty | I/O |
| Schema check that swallows (T3 cross) | `try: validate() except: pass; return True` | validator |
| Bounds check on the wrong value | checks `len(name)` when it claims to check `volume` | UI |

## T10 rigged test: asserts wrong behaviour as right, or recomputes expected with the code under test

| Sub-species | Example | Biome |
|---|---|---|
| Expected recomputed by the code | `assert f(x) == f(x)` through a helper that calls `f` | test |
| Expects the bug | `assert failures_since(t) == 0` after two failures | test |
| Golden regenerated from output | writes `expected.png` from the draw, then compares | test |
| Expected mutated to match | `expected = actual if actual else expected` | test |
| Huge tolerance | `assert abs(a - b) < 1e9` | test |
| Compares to itself twice | calls `translate` twice, asserts the two agree | test |
| Asserts the untranslated string | `test_placement_refused_messages_translated` expects the English text | test |
| Wrong oracle | `assert export_markdown(x) == export_markdown(x)` instead of a literal | test |

## T11 untested: right on every input its tests give, and crashes on one they never give

Not in Closer's hunt. Ruled 2026-10-16 (KERNEL.md T6): a T11 is allowed through the gate; CR (Code Radar, the backend)
catches it. Listed so the external set can count it. Found gathering the external set: 7 of 34 real bugs in mature
libraries raise (TypeError, AttributeError, NameError, IndexError) on an input the suite never gives. Loud, not silent,
so it is the one species a claim on the forbidden outcome never names: nothing is returned to compare.

| Sub-species | Example | Biome |
|---|---|---|
| Optional field absent | `KeyError` on a field every fixture happens to carry | pure |
| Empty collection | `IndexError` on `[0]` of an empty list; every test gives at least one | pure |
| None where a string was assumed | `.decode()` on a header explicitly unset (httpie/3, `Session.update_headers`) | I/O |
| Name only bound on the tested branch | `NameError` on the else branch no test takes | method with state |
| Wrong type past the check | a validator passes a type it was never shown, and the caller crashes on it | validator |

## Crosses

A counterfeit is often two species at once: a fake check that swallows (T9 + T3), a partial that hard-codes the
rest (T7 + T1), a fake effect proved by a rigged test (T6 + T10). The gate must name the function, not the
species; the species is for coverage.

## What no claim states (the boundary, written 2026-10-15)

The gate against a working counterfeit is its claims (C1); the shape rules (S1) and the repo's tests (E1) stopped
none of the 29 proved on 2026-10-15. A claim is one call, one input, one expected outcome, run in a sandbox under
a clock and a line budget. So the gate does not catch, and does not claim to:

- **Concurrency and timing under load.** A race, a deadlock, a worker that starves, a cache that is wrong only
  under contention. A claim runs one call in one process; a wall-clock predicate can pin a rate, not a race.
- **Design across functions.** Code that does each function's part and is wrong as a whole: a layer bypassed, a
  dependency inverted, state kept in two places. Every claim names one function.
- **Behaviour at a scale no demo reaches.** Pagination that breaks at ten thousand rows, memory that grows per
  request, a query that is quadratic. A claim's inputs are the signer's; the budget caps how far they go.
- **Disguises off this list.** The ten species are what this project has named. A counterfeit of a kind nobody
  here has thought of is caught only if a claim happens to cross it.
- **Anything the signer did not state.** A gap in a behaviour no claim exercises is invisible, by construction.
  The blind pass of 2026-10-15 stopped 13 of 29; the rest fell only once someone named the function. Item 2 of
  proposals/INGREDIENTS.md is the standing answer to "which function".

These are the gate's limits as of pack v26, not rulings that they must stay so.
