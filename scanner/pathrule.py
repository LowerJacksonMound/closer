"""The one path rule. Stdlib only. Imported by scanner.model and bin/safepath; nothing else defines one.

  lexical(p)   backslash -> "/", drop "" and "." segments. Keeps "..", case and Unicode form as given.
               Used for World unit ids and string-path literals, where "../b.py" is a real reference.
  canon(p)     lexical(p), then refuse what a write_set must never hold: absolute or drive paths,
               any "..", an empty result, control/format/separator characters. Raises UnsafePath.
  fold(p)      NFC + casefold of canon form. A comparison key only (case-insensitive filesystems);
               never a path to open or write.

Case and NFC are preserved by lexical and canon on purpose: World unit ids are the names on disk, and a
write_set entry must name the same unit. Equality that has to survive case or form goes through fold.
"""

from __future__ import annotations

import unicodedata


class UnsafePath(ValueError):
    pass


def lexical(p: str) -> str:
    parts = [s for s in str(p).replace("\\", "/").split("/") if s not in ("", ".")]
    return "/".join(parts)


def bad_chars(rel: str) -> bool:
    """Control, format and line/paragraph-separator characters have no business in a path."""
    return any(unicodedata.category(c) in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp") for c in rel)


def canon(p: str) -> str:
    raw = str(p)
    slashed = raw.replace("\\", "/")
    if slashed.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        raise UnsafePath(f"absolute path refused: {raw}")
    rel = lexical(raw)
    if not rel:
        raise UnsafePath(f"empty path: {raw}")
    if ".." in rel.split("/"):
        raise UnsafePath(f"path escapes root via ..: {raw}")
    if bad_chars(rel):
        raise UnsafePath(f"control or separator character in path {raw!r}")
    return rel


def fold(rel: str) -> str:
    return unicodedata.normalize("NFC", rel).casefold()
