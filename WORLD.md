# WORLD

The World v1 contract. Regenerated 2026-10-11 from `CLOSER_SPEC_2026-10-10/` and the code that builds and
enforces it: `scanner/model.py` (shape), `scanner/emit.py` (write-once), `bin/world_v1.py` (the loader
every consumer uses), `bin/gc` (ids, manifests). Names are as GLOSSARY.md defines them.

A World is a frozen snapshot of one scan. Consumers read the World; they do not parse the target tree
(R6-1). The shape does not change without a pack bump.

## Shape

A World is one JSON object. All nine top-level keys are required:

| Key | Type | Holds |
|---|---|---|
| `kind` | string | Always `"world"`. |
| `version` | int | Always `1`. |
| `world_id` | string | This World's id (below). |
| `manifest_id` | string | The scan manifest it was built from (below). |
| `roots` | list | One entry per manifest root: `root_id`, `role` (`primary`, `dep`, `vendor`, `generated`), `walk`. No paths. |
| `units` | list | Every file the walk kept, sorted by `unit_id`. |
| `edges` | list | Every reference between units, sorted by `edge_id`. |
| `unreadable` | list | What the walk could not read. |
| `stats` | object | Counts over the above. |

### units

Every scanned file is a unit, files with no defs included (R6-4). Each unit:

| Field | Holds |
|---|---|
| `unit_id` | `<root_id>:<relpath>`. |
| `root_id` | The root it was found under. |
| `relpath` | Path under that root: forward slashes, no `.` or empty segments. Never absolute. |
| `lang`, `reader` | Detected language and the reader that read it (`textual` when no language reader applies). |
| `reader_error` | `null`, or why the language reader failed. The unit is kept, read as text only. |
| `bytes`, `lines` | Size. `bytes` is the only per-unit content fact World v1 records; there is no content hash. |
| `defs`, `refs`, `string_paths` | What the reader found. Empty lists when nothing. |

### edges

| Field | Holds |
|---|---|
| `edge_id` | `sp:<from>:<line>:<lit>` for a string path, `ref:<from>:<line>:<lit>` for a reader ref. |
| `kind` | `string_path` or `import`. (`include` has an id prefix reserved, but no reader emits it yet.) |
| `from` | The `unit_id` the reference is in. |
| `to` | The `unit_id` it resolves to, or `unresolved:<literal>`. |
| `lit`, `line` | The literal as written, and its line. |
| `confidence` | How sure the resolution is (`high` for reader refs, `low` for string paths). |

String-path edges count for reachability, not imports alone (R6-2).

### unreadable

One entry per thing the walk could not read: `root_id`, `relpath` (absent when the whole root is missing),
`error`. Unreadable files are recorded here, never silently dropped. `emit_world` also prints each one as
`NOT SCANNED`, so a partial scan is not mistaken for a full one.

### stats

`units` (count), `defs` (total across units), `string_path_edges`, `unresolved` (edges whose `to` starts
with `unresolved:`).

## world_id

`scan_<UTC timestamp>_<4 hex>`, e.g. `scan_20261010T120000_a1b2`, minted by `gc scan`: opaque, unique per
scan. The file is `<state>/worlds/scan_<id>.json`. Tools accept the id with or without the `scan_` prefix and
treat the two as the same World.

Freshness is a World's path identity, not a timestamp (R2). A World is current when it is the latest one
gc published; its timestamp means nothing to any check.

## Frozen and write-once (K1)

- A World is written once. A second write to the same id fails, even when two emitters race: the file is
  hard-linked into place, which never replaces an existing name.
- On write the World is made read-only (`chmod a-w`). If that does not stick, the emit refuses to call it
  frozen.
- A World is never edited in place. A changed repo gets a new scan and a new World.
- Every consumer loads it through `world_v1.load_world_v1` with `require_frozen=True`: a World whose owner
  write bit is set is refused. The check is the frozen file itself; its owner can always make it writable
  again, so the World's id binds only what it names.
- W1 checks K1 on every scan.

## No absolute paths

Absolute root paths live in the manifest only. A unit whose `relpath` is absolute (POSIX `/…` or a Windows
drive) is a contract break and the World is refused.

## Binding to the manifest

- `gc init` writes `<state>/manifest.json`: kind `scan_manifest`, version 1, the repo, and its roots, each
  with `root_id`, `role`, `path` and `exclude`.
- Every `gc scan` writes the exact manifest it used, with its new `world_id`, to
  `<state>/manifests/<world_id>.json`. `manifest_id` in the World names that manifest.
- The scan never writes the source: every walked file's inode, size, mtime and ctime are compared before and
  after, and any change means no World is emitted.
- `<id>.substance.json` beside a World is S1's before overlay, bound to that World by `world_id`. It is not a
  World field. A World whose overlay fails is never published as latest.

## Refused

`load_world_v1` refuses, naming the reason:

| What | Message names |
|---|---|
| No file, or a file not named `scan_*.json` | missing World id / non-World path |
| Not JSON, or not a JSON object | cannot load / not a JSON object |
| `kind` not `"world"` or `version` not `1` | not a world v1; lists any retired sketch keys present |
| Any of the nine keys missing | the missing keys |
| `roots`, `units` or `edges` not a list; `stats` not an object | the key |
| A unit with an absolute `relpath` | the path |
| Writable | not frozen |
| `world_id` not the one the ticket names | wrong world_id, with both ids |

### Retired sketch fields

The pre-cutover sketch carried `scan_id`, `started_at`, `sha256` and `files_scanned`. A file with them is not
a World: it is refused, never mapped. GLOSSARY.md records what each name now reads as (`scan_id` →
`world_id`, `started_at` → path identity, `files_scanned` → units) so old docs can still be read (G1).

A ticket is checked against its World twice: when it is minted (`gc ticket` refuses a World that does not
load) and again at land (`apply_ticket` and `verify_ticket`).
