Build `episodes.py` in this directory: a Seinfeld episode line. Stdlib only. pyproject.toml is already here.

The plan is already approved: Cartouche released it (spec /Users/ian/Desktop/seinfeld-request/spec.json, signed contract
/Users/ian/Desktop/seinfeld-request/build_input.json) and wrote it into CLOSER's state for this repo. Do NOT call cl_plan.
Do the whole job through the three MCP servers, in this order:

1. ct_watch with spec=/Users/ian/Desktop/seinfeld-request/spec.json contract=/Users/ian/Desktop/seinfeld-request/build_input.json
   target=/Users/ian/Desktop/seinfeld-test. Report its closer block (plan hash, holes).
2. cl_submit the five functions one at a time, in this order. The locked contracts are in the spec's "closer" block; your
   checks are those checks verbatim. Module constant GUIDE = {"The Contest": (4, 11), "The Bubble Boy": (4, 7),
   "The Soup Nazi": (7, 6), "The Marine Biologist": (5, 14), "The Puffy Shirt": (5, 2)}. Lookups are case-insensitive on
   the title and the answer uses GUIDE's spelling. A found answer is
   {"status": "found", "title": T, "season": S, "episode": E, "line": f"{T}: season {S}, episode {E}."}; an unknown one is
   {"status": "unknown", "title": T, "line": f"No episode called {T}."}.
   fxnA_answer(line)        line is a dict {caller, said}; no "said" -> ValueError; else fxnB_lookup(said)
   fxnB_lookup(title)       blank -> ValueError; in GUIDE -> fxnC_season({"title": T, "season": S, "episode": E}); else fxnD_unknown(title)
   fxnC_season(episode)     missing keys or season < 1 -> ValueError; else fxnE_readback(episode)
   fxnE_readback(episode)   missing keys -> ValueError; returns the found answer
   fxnD_unknown(title)      blank -> ValueError; returns the unknown answer
   Every function calls the next one directly. Direct Edit/Write/Bash writes to code are refused; cl_submit is the only way in.
3. ct_look. Report sealed/open and any issues.
4. cr_watch with target=/Users/ian/Desktop/seinfeld-test, wait 90 seconds, then cr_look. Report where CodeRadar says its
   intent came from (CLOSER's approved plan and its sha256) and what it found.
End with one table: location, PASS/FAIL/HOLE on which try, and the final ct_look and cr_look lines.
