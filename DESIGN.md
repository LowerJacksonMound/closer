# DESIGN

How a World is produced and what the scanner guarantees. Regenerated 2026-10-11 from
`CLOSER_SPEC_2026-10-10/` and the code in `scanner/` and `bin/`. WORLD.md is the shape; this file is how the
shape gets filled. Names are as GLOSSARY.md defines them.

## Scanner handoff

`gc scan` runs `bin/emit_world.py` on the manifest, then the S1 before overlay, then publishes the World as
latest. Inside the scan (`scanner/scan.py`):

1. **Snapshot.** Record inode, size, mtime and ctime of every file under every root.
2. **Walk.** Each manifest root is walked (`os.walk`; directory symlinks are not followed). Fixed skips and
   the root's excludes are applied (below). Every regular file is kept, hidden names included; a symlink
   to a file is read as that file. The World sorts units and edges afterwards, so walk order does not
   matter.
3. **Read.** Every kept file is read by the textual reader, which always runs and never drops a file: it
   records size and lines and harvests path-like string literals. If a language reader is registered for
   the file's language (today: Python, `scanner/readers/python_ast.py`, stdlib `ast` only), it adds `defs`
   and `refs`. A reader that fails or raises leaves the unit as text only, with `reader_error` set.
4. **Resolve edges.** Each ref and string path becomes an edge to the unit it names. A string path is tried
   as `<root_id>/<relpath>` (another root), then as written, then relative to the referencing file. An
   import is resolved as a module or package `__init__`, relative imports by their dots. A target that does
   not resolve is kept as `unresolved:<literal>`, never dropped.
5. **Record unreadable.** Anything the walk or a read could not open goes in `unreadable` with its error.
   `emit_world` prints each one as `NOT SCANNED` on stderr.
6. **Check no source writes.** Re-snapshot and compare. Any change refuses the scan: no World.
7. **Emit.** Write-once (K1): the World is linked into `<state>/worlds/scan_<id>.json` and made read-only.

Then gc writes the S1 before overlay (`<id>.substance.json`, from `scanner/substance.py`) and only then
moves `LATEST` to the new World. A failed overlay leaves the World unpublished.

## Guarantees

- **No source writes.** The scanner reads the repo and nothing else; the before/after snapshot proves it on
  every scan. A file rewritten in place with its size and mtime restored is still caught by ctime.
- **Nothing silently skipped.** Every walked file is a unit (R6-4), including files with no defs. What
  cannot be read is listed in `unreadable`. The only skips are:
  - fixed directories: VCS stores (`.git`, `.hg`, `.svn`, `.jj`), installed dependencies (`node_modules`,
    `.venv`, `venv`), tool caches (`__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.tox`,
    `.nox`) and `DerivedData`;
  - the file `.DS_Store`;
  - anything that is not a regular file: FIFOs, sockets, devices and dangling links (reading one can hang
    or fail). These are not listed in `unreadable`;
  - the manifest's `exclude` patterns: an exact path, a path prefix, or a bare name at any depth.
- **One path rule** (`scanner/pathrule.py`), shared with `bin/safepath.py`:
  - `lexical`: backslash to `/`, drop empty and `.` segments; keeps `..`, case and Unicode form. Used for
    unit ids and string-path literals.
  - `canon`: `lexical`, then refuse absolute or drive paths, any `..`, an empty result, and control,
    format or separator characters. Used for every write_set path.
  - `fold`: NFC plus casefold of `canon`. A comparison key for case-insensitive filesystems; never opened.
- **Relative paths only** in a World. Absolute root paths stay in the manifest.

## Who consumes a World

- **Pack `world` checks** run on every scan (PACK.md): W1 (K1 holds), R6-1 (consumers read the World, they
  do not parse the tree), R6-2 (string-path edges count for reachability), R6-4 (every file is a unit).
- **Tickets** bind to one World by `world_id`. `gc ticket` and land both load it through
  `world_v1.load_world_v1`, which refuses anything outside the WORLD.md contract.
- **The governor** reroutes a ticket whose World is not the latest.
- **S1** reads the before overlay beside the World to tell introduced findings from pre-existing ones.
- **The writer** reads Worlds through the gc `read` tool only (`bin/read_world.py`).

## Limits

- World v1 records a byte count per unit, not a content hash. A same-size edit between emit and the before
  overlay is not caught; `gc scan` runs the two seconds apart.
- Python is the only language reader. Other files are units with string paths, no defs or refs.
- Nested defs are not listed (module-level only).
