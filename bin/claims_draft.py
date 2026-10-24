#!/usr/bin/env python3
"""claims_draft: draft claims from a task's acceptance criteria, by fixed rules. A signer tool (T5), not a check.

usage: python3 bin/claims_draft.py --repo DIR (--task-file FILE | --backlog FILE --task N) --out DRAFT.json
                                   [--changed FILE:QUALNAME ...]
       python3 bin/claims_draft.py --repo DIR [task args] [--changed FILE:QUALNAME ...] --check CLAIMS.json

Reads the task text, finds its acceptance criteria, and for each clause applies fixed tables (no LLM): the
backticked name it is about, the verb that says what must happen, and the literals it gives. It writes
DRAFT.json in the claim shape `gc ticket --claims` takes, and DRAFT.notes.txt saying which clause each claim came
from and which clauses drafted nothing. Absent, never wrong: a clause the tables do not match drafts no claim.

Every value the tables could not fill is a `<FILL: ...>` placeholder. gc refuses to mint a claims file that still
holds one, so a draft is never a claim until the signer has replaced every placeholder (T5: the signer states the
claims; this tool only saves typing). The signer deletes drafts that are wrong and adds what is missing.

Tables:
  RAISES   rejects | refuses | raises | fails on | errors on    -> {"raises": <CamelCase *Error|*Exception in the clause, or FILL>}
  RESULT   returns | gives | yields | evaluates to | is <literal> -> {"result": <literal after the verb, or FILL>}
  EFFECT   logs | writes | saves | records | stores | sends | emits | appends | deletes | removes | clears
                                                              -> {"true": <FILL: predicate reading the effect>}
  ACCEPT   accepts | handles | supports | allows | keeps | carries -> {"true": <FILL: predicate on the result>}
Names: a backticked identifier (`parse_query`, `Store.upsert_episodes`) resolved against the repo's defs and
classes to a dotted path (src/ stripped); unknown names get `<FILL: module>.name`. Inputs: backticked tokens that
are not identifiers (`prod:1ACX`, `order:production`) become string arguments of the call.

Checklist: for every function the criteria name (Class names excepted) and every `--changed FILE:QUALNAME`, the
notes carry a block of what its claims should cover, from its name words (scanner/lexicon.py checklist_classes)
plus three lines every function gets. `--check CLAIMS.json` judges each line by the claims' shape and prints the
uncovered ones; a claim covers a function when its `name` is the function or its setup/call mentions it.
  negative    a raises claim, a `true` predicate starting `not ` or ending ` is False`, or a result of False
  positive    a claim on it that is not a negative
  differs     a result claim whose expected literal is not in its call, or a `true` predicate with `!=`
  odd         a string in a call or setup that is empty, padded, non-ASCII, mixed case or over 64 characters
  wired       a `true` predicate that calls something other than hasattr/getattr/isinstance/callable/type/id
  two_inputs  two claims with different calls and different expects
  sink        a `true` predicate naming a SINK_WORDS word (file, log, store, screen)
  surfaces    a raises claim with a setup (the setup arranges the other failure)
  set_up      every negative `true` predicate has a setup
  kept        not judged by shape: after a land, C1 evidence `holds_before` lists the claims that guard it
Advice to the signer, exit 0: nothing here refuses a mint (T5: only a `<FILL:` placeholder does).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner import lexicon  # noqa: E402  (claim words of a function name; signer advice only)

RAISES = ("rejects", "refuses", "raises", "fails on", "errors on", "is refused", "is rejected")
RESULT = ("returns", "gives", "yields", "evaluates to", "resolves to")
EFFECT = ("logs", "writes", "saves", "records", "stores", "sends", "emits", "appends", "deletes", "removes", "clears")
ACCEPT = ("accepts", "handles", "supports", "allows", "keeps", "carries")
VERBS = [(v, "raises") for v in RAISES] + [(v, "result") for v in RESULT] + [(v, "true") for v in EFFECT] + \
        [(v, "accept") for v in ACCEPT]
TICK = re.compile(r"`([^`]+)`")
IDENT = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")
EXC = re.compile(r"\b([A-Z]\w*(?:Error|Exception|Exit|Warning))\b")
LITERAL = re.compile(r"""(?:"[^"]*"|'[^']*'|\b-?\d+(?:\.\d+)?\b|\bTrue\b|\bFalse\b|\bNone\b)""")
FILL = "<FILL: "


def criteria(text: str) -> list[str]:
    """The bullet lines under the task's acceptance-criteria heading (the whole text if there is none)."""
    lines = text.splitlines()
    start = next((i + 1 for i, ln in enumerate(lines) if "acceptance criteria" in ln.lower()), 0)
    out, cur = [], ""
    for ln in lines[start:]:
        if ln.startswith("## "):
            break
        if re.match(r"^\s*[-*]\s+", ln):
            if cur:
                out.append(cur)
            cur = re.sub(r"^\s*[-*]\s+", "", ln).strip()
        elif cur and ln.strip():
            cur += " " + ln.strip()
    if cur:
        out.append(cur)
    return out


def clauses(bullet: str) -> list[str]:
    return [c.strip(" ,") for c in re.split(r";|\bthen\b|\band\b(?=\s+`|\s+[a-z]+\s+`)", bullet) if c.strip(" ,")]


def task_from_backlog(text: str, n: int) -> str:
    m = re.search(rf"^## {n}\.\s.*?(?=^## \d+\.|\Z)", text, re.M | re.S)
    if not m:
        sys.exit(f"claims_draft: no task {n} in the backlog")
    return m.group(0)


def repo_names(repo: Path) -> dict[str, str]:
    """name -> dotted module path for every top-level def and class; Class.method -> the class's module."""
    out: dict[str, str] = {}
    for p in sorted(repo.rglob("*.py")):
        rel = p.relative_to(repo)
        parts = list(rel.with_suffix("").parts)
        if any(d in ("test", "tests", "testing", ".venv", "venv", "build", "demos") for d in parts[:-1]) or \
                parts[-1].startswith("test_"):
            continue
        if parts and parts[0] == "src":
            parts = parts[1:]
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        mod = ".".join(parts)
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.setdefault(node.name, mod)
            elif isinstance(node, ast.ClassDef):
                out.setdefault(node.name, mod)
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out.setdefault(f"{node.name}.{sub.name}", mod)
    return out


def resolve(name: str, names: dict[str, str], hint: str | None) -> str:
    if name in names:
        return f"{names[name]}.{name}"
    head = name.split(".")[0]
    if head in names:
        return f"{names[head]}.{name}"
    return f"{hint}.{name}" if hint else f"{FILL}module>.{name}"


COND = re.compile(r"==|!=|<=|>=|<|>|%|\+|\*|/| or | and |\bwhen\b")


def literal(t: str):
    """A backticked Python literal (`11`, `True`, `"x"`) -> its value; anything else -> None."""
    try:
        v = ast.literal_eval(t)
    except (ValueError, SyntaxError):
        return None
    return v if isinstance(v, (bool, int, float, str)) or v is None else None


def is_subject(t: str, names: dict[str, str]) -> bool:
    """A backticked name that is a function or Class.method: in the repo, dotted, or an identifier with an
    underscore or a capital. A single lowercase word the repo does not know (`air`, `boss`) is a value."""
    if not IDENT.match(t) or t.isupper() or EXC.fullmatch(t) or t in ("True", "False", "None"):
        return False
    return t in names or "." in t or "_" in t or t[0].isupper()


def draft_clause(clause: str, names: dict[str, str], hint: str | None,
                 carried: str | None = None) -> tuple[list[dict], str, str | None]:
    ticks = TICK.findall(clause)
    subjects = [t for t in ticks if is_subject(t, names)]
    conds = [t for t in ticks if not IDENT.match(t) and COND.search(t)]
    inputs = [t for t in ticks if t not in subjects and t not in conds and not EXC.fullmatch(t)]
    if not subjects and carried:
        subjects = [carried]
    low = clause.lower()
    hits = sorted(((low.find(v), v, kind) for v, kind in VERBS if re.search(r"\b" + re.escape(v) + r"\b", low)),
                  key=lambda x: x[0])
    if not subjects:
        return [], "no backticked name", carried
    if not hits:
        return [], "no verb from the tables", subjects[0]
    subject = subjects[0]
    full = resolve(subject, names, hint)
    callee = subject.split(".")[-1] if "." not in subject or subject[0].isupper() else subject
    def render(xs: list[str]) -> str:
        return ", ".join(x if literal(x) is not None and not isinstance(literal(x), str)
                         else json.dumps(literal(x) if literal(x) is not None else x) for x in xs) if xs else f"{FILL}arguments>"
    setup = [f"# {FILL}arrange so that {c}>" for c in conds]
    if "." in subject and subject[0].isupper():
        cls = subject.split(".")[0]
        setup.append(f"obj = {cls}({FILL}constructor arguments>)")
        callee = f"obj.{subject.split('.', 1)[1]}"
    out = []
    for pos, verb, kind in hits[:2]:
        after = clause[pos + len(verb):]
        expected_lit = None
        if kind == "result":
            m = LITERAL.search(after.split(" for ")[0].split(" when ")[0].split(" on ")[0])
            expected_lit = m.group(0) if m else None
        own = [x for x in inputs if x != expected_lit]
        c: dict = {"name": full, "call": f"{callee}({render(own)})"}
        if setup:
            c["setup"] = setup
        if kind == "raises":
            m = EXC.search(after) or EXC.search(clause)
            c["expect"] = {"raises": m.group(1) if m else f"{FILL}exception class>"}
        elif kind == "result":
            lit = expected_lit
            try:
                c["expect"] = {"result": ast.literal_eval(lit)} if lit else {"result": f"{FILL}expected value>"}
            except (ValueError, SyntaxError):
                c["expect"] = {"result": f"{FILL}expected value>"}
        elif kind == "true":
            c["expect"] = {"true": f"{FILL}predicate: {verb} {after.strip()[:60]}>"}
        else:
            c["expect"] = {"true": f"{FILL}predicate on result: {after.strip()[:60]}>"}
        out.append(c)
    return out, f"{len(out)} claim(s)", subject


CHECKLIST = {  # class -> (key, species it guards against, line). Species are notes for the signer (K8 is findings).
    "check": [("negative", "T9", "a negative case: the refusal raises or the predicate is false"),
              ("positive", "T1", "the positive case passes")],
    "transform": [("differs", "T5", "the result differs from the input in the required way"),
                  ("odd", "T7", "odd inputs: empty, mixed case, surrounding whitespace, non-ASCII, longer than a demo")],
    "factory": [("wired", "T2/T6", "every collaborator is wired, observed by its effect, not by attribute")],
    "compute": [("two_inputs", "T4", "at least two inputs with hand-derived expected values that differ")],
    "effect": [("sink", "T6", "the effect read at its sink (the file, the store row, the log line, the screen)")],
}
ALWAYS = [("kept", "T7", "what it did before this task is kept (compare the base file)"),
          ("surfaces", "T3", "a failure of another kind surfaces, not swallowed"),
          ("set_up", "T8", "every negative is set up so the forbidden outcome could occur (a guest who has watched "
                           "something, a user who is locked, a file that exists)")]
SINK_WORDS = frozenset({  # file, log, store, screen
    "open", "read", "read_text", "read_bytes", "exists", "is_file", "listdir", "glob", "path", "file",
    "log", "logs", "caplog", "logging", "records", "getvalue",
    "store", "db", "row", "rows", "select", "execute", "fetchone", "fetchall", "table",
    "screen", "render", "draw", "label", "widget", "capsys", "readouterr", "stdout"})
NOT_EFFECT_CALLS = frozenset({"hasattr", "getattr", "isinstance", "callable", "type", "id"})


def checklist(qual: str) -> list[tuple[str, str, str]]:
    return [x for k in lexicon.checklist_classes(qual.split(".")[-1]) for x in CHECKLIST[k]] + ALWAYS


def criteria_functions(bullets: list[str], names: dict[str, str], hint: str | None) -> list[tuple[str, str]]:
    """(full dotted name, qualname) for every backticked function the criteria name; class names are skipped."""
    out: list[tuple[str, str]] = []
    for b in bullets:
        if b.lower().startswith("tests"):
            continue
        for t in TICK.findall(b):
            if is_subject(t, names) and not t.split(".")[-1][0].isupper():
                fn = (resolve(t, names, hint), t)
                if fn not in out:
                    out.append(fn)
    return out


def changed_function(spec: str, repo: Path) -> tuple[str, str]:
    """FILE:QUALNAME -> (full dotted name, qualname); FILE relative to the repo, src/ stripped."""
    path, _, qual = spec.rpartition(":")
    if not path or not IDENT.match(qual):
        sys.exit(f"claims_draft: --changed wants FILE:QUALNAME, got {spec!r}")
    rel = Path(path)
    if rel.is_absolute():
        rel = rel.resolve().relative_to(repo.resolve())
    parts = [x for x in rel.with_suffix("").parts]
    parts = parts[1:] if parts and parts[0] == "src" else parts
    parts = parts[:-1] if parts and parts[-1] == "__init__" else parts
    return ".".join(parts + [qual]), qual


def checklist_notes(fns: list[tuple[str, str, str]]) -> list[str]:
    out = ["", "# checklist: what each function's claims should cover (name words via scanner/lexicon.py; advice, "
               "never a refusal; `--check CLAIMS.json` says which lines no claim covers)"]
    for full, qual, why in fns:
        short = qual.split(".")[-1]
        classes = lexicon.checklist_classes(short)
        out.append(f"## {full} ({why}; {', '.join(classes) or 'no claim words'})")
        out += [f"- {short} [{key}, {sp}]: {text}" for key, sp, text in checklist(qual)]
    return out


def _expect(c: dict) -> tuple[str, object]:
    e = c.get("expect") or {}
    k = next(iter(e), "")
    return k, e.get(k)


def negative(c: dict) -> bool:
    k, v = _expect(c)
    if k == "true" and isinstance(v, str):
        w = v.strip()
        return w.startswith("not ") or w.endswith(" is False")
    return k == "raises" or (k == "result" and v is False)


def _strings(c: dict) -> list[str]:
    out = []
    for src in [c.get("call", "")] + list(c.get("setup") or []):
        try:
            out += [n.value for n in ast.walk(ast.parse(str(src))) if isinstance(n, ast.Constant)
                    and isinstance(n.value, str)]
        except (SyntaxError, ValueError):
            pass
    return out


def _odd(s: str) -> bool:
    return s == "" or s != s.strip() or not s.isascii() or len(s) > 64 or (s.lower() != s and s.upper() != s)


def _words(text: str) -> set[str]:
    toks = set(re.findall(r"\w+", text.lower()))
    return toks | {p for t in toks for p in t.split("_")}


def covered(key: str, hits: list[dict]) -> bool | None:
    """Whether the claims reaching a function cover one checklist line, by shape. None: not judged by shape."""
    trues = [str(_expect(c)[1]) for c in hits if _expect(c)[0] == "true"]
    if key == "negative":
        return any(negative(c) for c in hits)
    if key == "positive":
        return any(not negative(c) for c in hits)
    if key == "differs":
        return any(_expect(c)[0] == "result" and json.dumps(_expect(c)[1]) not in c.get("call", "")
                   and repr(_expect(c)[1]) not in c.get("call", "") for c in hits) or any("!=" in t for t in trues)
    if key == "odd":
        return any(_odd(s) for c in hits for s in _strings(c))
    if key == "wired":
        return any(set(x.split(".")[-1] for x in re.findall(r"([A-Za-z_][\w.]*)\s*\(", t)) - NOT_EFFECT_CALLS
                   for t in trues)
    if key == "two_inputs":
        return len({c.get("call") for c in hits}) >= 2 and len({json.dumps(c.get("expect"), sort_keys=True)
                                                                 for c in hits}) >= 2
    if key == "sink":
        return any(_words(t) & SINK_WORDS for t in trues)
    if key == "surfaces":
        return any(_expect(c)[0] == "raises" and c.get("setup") for c in hits)
    if key == "set_up":
        return all(c.get("setup") for c in hits if negative(c) and _expect(c)[0] == "true")
    return None


def reaches(c: dict, full: str, qual: str) -> bool:
    name = str(c.get("name", ""))
    if name == full or name == qual or name.endswith("." + qual):
        return True
    said = " ".join([str(c.get("call", ""))] + [str(x) for x in c.get("setup") or []])
    return re.search(r"\b" + re.escape(qual.split(".")[-1]) + r"\b", said) is not None


def check(claims: list[dict], fns: list[tuple[str, str, str]]) -> int:
    uncovered = unjudged = 0
    for full, qual, _ in fns:
        hits = [c for c in claims if isinstance(c, dict) and reaches(c, full, qual)]
        for key, sp, text in checklist(qual):
            ok = covered(key, hits)
            if ok is None:
                unjudged += 1
                print(f"not judged {full} [{key}, {sp}]: {text} (after a land: C1 evidence holds_before)")
            elif not ok:
                uncovered += 1
                print(f"uncovered {full} [{key}, {sp}]: {text}")
    print(f"claims_draft --check: {uncovered} uncovered line(s), {unjudged} not judged by shape, "
          f"across {len(fns)} function(s); advice only, nothing refuses a mint")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--task-file")
    ap.add_argument("--backlog")
    ap.add_argument("--task", type=int)
    ap.add_argument("--out")
    ap.add_argument("--changed", action="append", default=[], metavar="FILE:QUALNAME",
                    help="a function changed by a land, for the checklist (repeatable)")
    ap.add_argument("--check", metavar="CLAIMS.json", help="report checklist lines no claim covers; writes nothing")
    a = ap.parse_args()
    text = None
    if a.task_file:
        text = Path(a.task_file).read_text(encoding="utf-8")
    elif a.backlog and a.task:
        text = task_from_backlog(Path(a.backlog).read_text(encoding="utf-8"), a.task)
    elif not (a.check and a.changed):
        ap.error("give --task-file, or --backlog and --task N (--check may take --changed alone)")
    if not a.check and not a.out:
        ap.error("give --out DRAFT.json, or --check CLAIMS.json")
    names = repo_names(Path(a.repo))
    bullets = criteria(text) if text is not None else []
    # the module most backticked names in this task resolve to, for new names
    mods = [names[t] for b in bullets for t in TICK.findall(b) if t in names]
    hint = max(set(mods), key=mods.count) if mods else None
    fns = [(f, q, "criteria") for f, q in criteria_functions(bullets, names, hint)]
    for spec in a.changed:
        f, q = changed_function(spec, Path(a.repo))
        if f not in [x[0] for x in fns]:
            fns.append((f, q, "changed"))
    if a.check:
        try:
            claims = json.loads(Path(a.check).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            sys.exit(f"claims_draft --check: cannot read {a.check}: {e}")
        return check(claims if isinstance(claims, list) else [], fns)
    claims, notes = [], []
    for b in bullets:
        if b.lower().startswith("tests"):
            notes.append(f"skipped (tests are E1's): {b[:90]}")
            continue
        carried = None
        for cl in clauses(b):
            drafted, why, carried = draft_clause(cl, names, hint, carried)
            for d in drafted:
                claims.append(d)
                notes.append(f"claim {len(claims)} <- {cl[:120]}")
            if not drafted:
                notes.append(f"nothing drafted ({why}): {cl[:120]}")
    out = Path(a.out)
    out.write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")
    fills = sum(json.dumps(c).count(FILL) for c in claims)
    out.with_suffix(".notes.txt").write_text(
        f"# claims_draft: {len(claims)} draft claim(s) from {len(bullets)} criteria; {fills} placeholder(s) to fill\n"
        + "\n".join(notes + checklist_notes(fns)) + "\n", encoding="utf-8")
    print(f"claims_draft: {len(claims)} draft claim(s), {fills} placeholder(s) to fill -> {out}; notes in "
          f"{out.with_suffix('.notes.txt')} (checklist for {len(fns)} function(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
