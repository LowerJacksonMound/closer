Build `vets.py` in this directory: Riverside Vets' after-hours phone line. Stdlib only. pyproject.toml is already here.

The plan is already approved: Cartouche released it (spec ~/Desktop/vets-request/spec.json, signed contract
~/Desktop/vets-request/build_input.json) and wrote it into CLOSER's state for this repo. Do NOT call cl_plan.
Do the whole job through the three MCP servers, in this order:

1. ct_watch with spec=/Users/ian/Desktop/vets-request/spec.json contract=/Users/ian/Desktop/vets-request/build_input.json
   target=/Users/ian/Desktop/vets-test. Report its closer block (plan hash, holes).
2. cl_submit the five functions one at a time, in the order the conversation runs. The locked contracts are in the
   spec's "closer" block; your checks are those checks, verbatim, plus any you add. The five:
   fxnA_answer(line)            line is a dict {caller, said}; no "said" -> ValueError; otherwise fxnB_triage(said)
   fxnB_triage(symptom_text)    blank -> ValueError; an emergency word (collapsed, not breathing, seizure, bleeding,
                                poisoned, lilies) -> fxnD_emergency_route(symptom_text); else fxnC_book_visit(symptom_text)
   fxnC_book_visit(request)     blank -> ValueError; a HH:MM in the text is the asked slot, else "08:00"; a slot
                                outside 08:00-17:59 -> ValueError; then fxnE_confirm_visit(slot)
   fxnE_confirm_visit(slot)     blank -> ValueError; returns {"status": "booked", "slot": slot,
                                "message": f"Booked for tomorrow at {slot}. Bring a carrier."}
   fxnD_emergency_route(payload) blank -> ValueError; returns {"status": "emergency", "hospital": "Oak Street Emergency",
                                "called_ahead": True, "reason": payload}
   Every function calls the next one directly (no dispatch table, no lambdas). No direct Edit/Write/Bash writes to
   code: they are refused; cl_submit is the only way in.
3. ct_look. Report sealed/open and any issues.
4. cr_watch with target=/Users/ian/Desktop/vets-test, then cr_look after a minute. Report where CodeRadar says its
   intent came from (it should name CLOSER's approved plan and its sha256) and what it found.
End with one table: location, PASS/FAIL/HOLE on which try, and the final ct_look and cr_look lines.
