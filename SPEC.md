# CLOSER spec. Ian, 2026-11-11. This replaces the 2026-11-09 restart spec and every ruling before it.

Plan: the agent sends its intent and the person's expectation, with one contract per function the spec names
(file, name, params, checks). The person accepts or declines. A decline means changes: the agent asks in chat,
adds them, sends the plan again. Agent and person are in alignment only when a plan is accepted. Nothing is
written before that. (This accept/decline is the one pause. The 2026-11-09 "no yes" ruling is withdrawn; it was
about a chat yes mid-run, and that stays gone.)

Then: every function is tested in the sandbox. It runs. What came back is compared to the intent and expectation
(the plan's checks, plus the agent's). It matches: CLOSER writes it. It does not run, or it is counterfeit: back to
the author for a second try. Two tries and out: the location is a hole, nothing is written there, CodeRadar takes it.

That's it. Anything not in those two paragraphs is not CLOSER's and is not added. The old CLOSER was rewritten for
severe overcomplication; it is most effective at its simplest.

Where today's pieces sit in it: the accept/decline elicitation and the plan page are the plan paragraph; the
contract lock and tighten-only revision are "plan accepted, then"; the stance line on cl_submit is "compared to
intent"; the strike/hole files and the repair flag are "two tries and out". Pytest is never a check.
