Read /Users/ian/Desktop/setlist-request/PROMPT.md and build exactly that, here, in this directory.

The plan is already approved: Cartouche released it (spec /Users/ian/Desktop/setlist-request/spec.json, signed contract
/Users/ian/Desktop/setlist-request/build_input.json) and wrote it into CLOSER's state for this repo. Do NOT call cl_plan.
Work only through the three MCP servers, in this order:

1. ct_watch with spec=/Users/ian/Desktop/setlist-request/spec.json contract=/Users/ian/Desktop/setlist-request/build_input.json
   target=/Users/ian/Desktop/setlist-stack. Report its closer block.
2. cl_submit every function in the plan, one def per submit (import lines first, then exactly one def), callees before
   callers across the four files. The checks for each are the locked ones in the spec's "closer" block, verbatim. Also
   submit main() in app.py with a check that it is a function (e.g. {"call": "callable(main)", "expect": true}).
   Direct Edit/Write/Bash writes to code are refused; cl_submit is the only way in. If a submit FAILs, read the verdict
   and fix the function, do not change the checks.
3. ct_look. Report sealed/open and issues.
4. cr_watch with target=/Users/ian/Desktop/setlist-stack, wait 90 seconds, then cr_intent and cr_status.
End with one table: location, PASS/FAIL/HOLE on which try, then the final ct_look, cr_intent and cr_status lines.
