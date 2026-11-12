Build `tracks.py` in this directory: a David Cross track line served as a web page. Stdlib only. pyproject.toml and
catalogue.json are already here.

The plan is already approved: Cartouche released it (spec /Users/ian/Desktop/dc-request/spec.json, signed contract
/Users/ian/Desktop/dc-request/build_input.json) and wrote it into CLOSER's state for this repo. Do NOT call cl_plan.
Do the whole job through the three MCP servers, in this order:

1. ct_watch with spec=/Users/ian/Desktop/dc-request/spec.json contract=/Users/ian/Desktop/dc-request/build_input.json
   target=/Users/ian/Desktop/dc-build. Report its closer block (plan hash, holes).
2. cl_submit the six functions one at a time, callees before callers. The locked contracts are in the spec's "closer"
   block; your checks are those checks verbatim. Each submit is import lines (optional) then exactly one def.
   fxnD_not_found(title)                  blank -> ValueError; {"status": "not_found", "title": T, "line": f"No track called {T}."}
   fxnA_load_catalogue(path)              json.load the file; missing file or "tracks" not a list -> ValueError; returns the list
   fxnB_find_track(catalogue, title)      blank title or catalogue not a list -> ValueError; case-insensitive match on
                                          "title" returns that track dict; no match -> fxnD_not_found(title)
   fxnC_log_play(track, log_path)         track without int "id" -> ValueError; append f"{id}\n" to log_path; return how
                                          many lines in the log now equal that id (including this one)
   fxnE_render_page(track, plays)         plays < 0 -> ValueError; returns HTML with <h1>{title}</h1>, the year, "{minutes} min",
                                          "played {plays} time" + ("s" if plays != 1 else "") and a link <a href="/">catalogue</a>
   fxnF_handle(path, catalogue_path, log_path)
                                          "/" -> HTML with <h1>David Cross</h1> and one <a href="/track?title=...">title</a>
                                          per track (urllib.parse.quote_plus); "/track?title=X" -> load, find, and either
                                          fxnE_render_page(track, fxnC_log_play(track, log_path)) or the not_found line in
                                          a <p>; any other path -> ValueError
   Direct Edit/Write/Bash writes to code are refused; cl_submit is the only way in.
3. ct_look. Report sealed/open and any issues.
4. cr_watch with target=/Users/ian/Desktop/dc-build, wait 90 seconds, then cr_intent and cr_status. Report where CodeRadar
   says its intent came from (CLOSER's approved plan and its sha256) and what it found.
End with one table: location, PASS/FAIL/HOLE on which try, and the final ct_look, cr_intent and cr_status lines.
