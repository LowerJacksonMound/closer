CodeRadar's intent comes from CLOSER's approved plan, never from its own hunt. Repo: this directory (the CodeRadar tree). Stdlib only. Do 1-cr_holes_read first (it adds the gearbox tick that reads CLOSER's state dir).

The ruling (Ian, 2026-11-11): with Cartouche, the release's intent and contracts went to cl_plan hashed, so the approved plan IS the person's signed intent and expectation. Without Cartouche, cl_plan went yes/no until the person approved, so the approved plan is a very close version of it. Either way CodeRadar already has the intent and does not look for one.

Facts (read them):
- system_scripts/intent_file.py: the statement is AUTHORED (set_statement / submit_statement, source "developer"), set once at launch from the setup page's purpose box (launch_setup.py:528 submit_purpose, launch.sh:720); facts are extracted from it by fixed keyword tables (extract_statement_facts). cr_intent (coderadar_mcp/read_tools.py:1503) answers that file.
- plans.jsonl in CLOSER's state dir (judge.state_dir(target)): the last record with "approved": true carries "intent", "expectation", "sha256" (holes.approved_plan after cr_holes_land; else read the lines yourself, last approved wins).

system_scripts/gearbox.py
- On the same tick that reads the holes (1-cr_holes_read), read the approved plan. When its sha256 differs from the last one applied (keep it in the same closer_holes_<repo id>.json file as "plan_sha256"), call intent_file.submit_statement(target, plan["intent"] + "\n" + plan["expectation"]) with source "closer" (submit_statement gains a `source` parameter, default "developer", passed through to set_statement). No approved plan yet: nothing changes, the launch purpose stands.

system_scripts/intent_file.py
- submit_statement(target, text, source="developer"). Nothing else.

coderadar_mcp/read_tools.py
- cr_intent answers two more keys: "plan_sha256" (the applied plan's sha or null) and "source" (the statement's source, "closer" when the plan wrote it). The contract text in tool_interface.py says: the statement is CLOSER's approved plan when one exists (Cartouche's signed intent when Cartouche was used), the launch purpose otherwise; the facts are the fixed-rule facts of that statement; do not go looking for intent elsewhere.

launch_setup.py / the setup page
- The purpose box stays (it is the no-CLOSER fallback). Its label says: "optional; a CLOSER plan replaces it".

Not changed this round: the whitelist stage's intent-source scan (artifact scanner facts) keeps running; under this ruling it is redundant and is a deletion of its own later, recorded in HANDOFF.md as an open item.

Contracts: lock submit_statement with a literal check (a scratch target dir, text "A ferry timetable; entry point python -m ferry.cli", source "closer": the returned data["statement"]["source"] == "closer" and at least one fact). cr_intent and the gearbox tick are locked by params; cr_intent's check is the no-file answer this tree gives today (read it first: error set, statement None). Run `.venv_new/bin/python -m coderadar_mcp.read_tools_proof` from the tree root and say what it printed.
