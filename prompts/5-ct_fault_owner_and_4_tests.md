Two jobs in this tree, in order; one session. Repo: this directory (the Cartouche tree, cartouche/). Stdlib only. Nothing in CLOSER changes.

FIRST: finish prompt 4 (ct_release_contracts). Everything else from it has landed: closer_lock in cartouche/build_release.py, closer_state/closer_issues in cartouche/hold.py, the Watch answer's "closer" block in cartouche/mcp_tools.py, the launcher PYTHONPATH, the test_release.py case. Do not re-plan or touch those. What is left is ONE test class that holed (two "did not run" tries, logged as CloserPlanTests in ~/.closer): the test methods used self.contracts without a setUp, so the plan check called them and they raised AttributeError.
- cartouche/tests/test_mcp.py gains class CloserRowTests(unittest.TestCase) in that SAME file (not a new file; not the name CloserPlanTests, which is the holed name). No setUp: each test builds its own data inline. Each test makes a temp target dir and a temp CLOSER_HOME (os.environ patched for the test; judge.state_dir reads CLOSER_HOME) holding the state dir for that target with a plans.jsonl and a holes.jsonl the test writes, then calls closer_issues(release, target) from cartouche.hold with a release whose "closer" block is closer_lock of a two-contract spec. Three tests: an approved plan whose contracts differ gives exactly one row with fault "locked" and detail "CONTRACTS"; a matching plan gives no row; two hole records give two rows with fault "missing" and detail "HOLE(<kind>)". Read judge.state_dir and holes.py for the record shapes before writing; do not guess them.
- Contract: lock CloserRowTests by params only (test methods have no params beyond self; the lock is the names). Run `python3 -m unittest discover -s cartouche/tests` from this folder and say the count (162 before yours).

THEN, prompt 5 as written:

One owner per fault kind: CLOSER keeps what its judge already proves by running the code; Cartouche keeps what only the release can know. Repo: this directory (the Cartouche tree). Stdlib only. Nothing in CLOSER changes.

The ruling (Ian, 2026-11-11, 90/10):
- template (hollow stub, constant return, swallowing bare except): CLOSER's. Its judge runs the function on the checks; a stub that passes the locked checks is not a fault, and one that fails is a strike or a hole. Cartouche stops reporting it.
- missing parameters (MISSING_PARAMS, today reported as missing): CLOSER's. cl_submit refuses a locked name whose parameters differ (judge.py:684). Cartouche stops reporting it.
- missing (the function is not there), skew (a required edge is gone), locked (the request was edited after release), SYNTAX: Cartouche's. CLOSER has no release and no topology.
- holes: CLOSER writes them, CodeRadar repairs them, Cartouche shows them (4-ct_release_contracts).

cartouche/project_symbol.py
- DEFECTS becomes (LOCKED, MISSING, SKEW); TEMPLATE and the two template rows in _WARRANT_DEFECT (CARTOUCHE_COUNTERFEIT_STUB, CARTOUCHE_MALFORMED_GLYPH) go. defect_of answers None for them (let through, like any warrant the scan does not recognise), and the MISSING_PARAMS branch goes with them. The docstring says who owns what, one line.
- The scanner (cartouche/cartouche_scanner.py) keeps emitting its warrants: the CLI's scan report and the live page still show HOLLOW_STUB / DEGENERATE_CONSTANT_RETURN / SWALLOWED_BARE_EXCEPT / MISSING_PARAMS as diagnostics in glyph_diagnostics. Only issues_of (what ct_look hands the agent and what seals a build) drops them. `is_sealed` in _project must therefore not be false on a template-only warrant: is_sealed is computed at cartouche_scanner.py:513 from projection_residual and the bitmask, and a template fault sets fidelity 0.0 (cartouche_scanner.py:423); make a sealed build one with no issue rows from issues_of (a syntax failure still unseals) without changing the diagnostics.

cartouche/mcp_tools.py
- Tool descriptions: "one of four words" becomes three, with the sentence: a hollow or fake-shaped body and wrong parameters are CLOSER's to refuse; Cartouche reports missing, skew and locked.

Docs: README.md and INTENT.md name template (grep "template"; MCP.md has no mention); change each to the three faults and add the one-line ownership sentence. CHANGELOG.md gets a line under a new version (0.3.0: a new version is a new name; do not reuse 0.2.0).

Tests: cartouche/tests/test_gate.py and test_mcp.py assert template rows and MISSING_PARAMS -> missing; change those assertions to "no issue row, build sealed" and keep the diagnostics assertions on the scan report. Run `python3 -m unittest discover -s cartouche/tests` and say the count.

Contracts: lock defect_of (literal: ("CARTOUCHE_MISSING_GLYPH", []) -> "missing"; ("CARTOUCHE_COUNTERFEIT_STUB", []) -> None; ("CARTOUCHE_MALFORMED_GLYPH", ["MISSING_PARAMS(x)"]) -> None; ("CARTOUCHE_TOPOLOGY_BREAK", []) -> "skew"; ("CARTOUCHE_UNPARSED", []) -> "SYNTAX") and issues_of (a report with one COUNTERFEIT_STUB warrant and one MISSING_GLYPH warrant answers one row, the missing one). Anything else you touch is locked by params.
