"""Textual reader. Always runs. Harvests path-like strings. Never drops a file."""

from __future__ import annotations

import re
from pathlib import Path

from scanner.model import make_unit

# A string that looks like a relative file path, not a URL and not a sentence.
# Deliberately strict: slash, no spaces, a suffix or a dotted module-ish tail.
_PATH = re.compile(
    r"""(?x)
    (?P<q>['\"])
    (?P<lit>
        (?:\.\.?/|[\w.-]+/)
        [\w./-]+
        \.[\w]+
    )
    (?P=q)
    """
)

_EXT_LANG = {
    ".py": "python",
    ".pyi": "python",
}


def lang_of(relpath: str) -> str:
    return _EXT_LANG.get(Path(relpath).suffix.lower(), "unknown")


def harvest_string_paths(text: str) -> list[dict]:
    found = []
    for i, line in enumerate(text.splitlines(), start=1):
        if "://" in line:
            continue
        for m in _PATH.finditer(line):
            lit = m.group("lit")
            if lit.startswith(("http", "//")):
                continue
            found.append({"lit": lit, "line": i})
    return found


def is_env_file(relpath: str) -> bool:
    """I1 addendum: a `.env*` file is in the World for its existence only."""
    return relpath.rsplit("/", 1)[-1].startswith(".env")


def read_textual(root_id: str, relpath: str, abs_path: Path) -> dict:
    raw = abs_path.read_bytes()
    if is_env_file(relpath):
        # Existence only: relpath, size, lang. No string from the file is kept (no quoted path, no value),
        # and lang stays unknown so no language reader parses it. `lines` is a count, not a string.
        return make_unit(root_id=root_id, relpath=relpath, lang="unknown", reader="textual", nbytes=len(raw),
                         lines=raw.count(b"\n") + (0 if raw.endswith(b"\n") or not raw else 1),
                         string_paths=[], reader_error=None)
    try:
        text = raw.decode("utf-8")
        error = None
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
        error = "utf-8 decode replaced"
    strings = harvest_string_paths(text) if error is None else []
    return make_unit(
        root_id=root_id,
        relpath=relpath,
        lang=lang_of(relpath),
        reader="textual",
        nbytes=len(raw),
        lines=text.count("\n") + (0 if text.endswith("\n") or text == "" else 1),
        string_paths=strings,
        reader_error=error,
    )
