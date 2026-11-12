Build a stdlib-only Python package `kiln` in this directory (pyproject.toml is here; it must install): a pottery-studio kiln scheduler with a web UI. Every page and every script the browser receives is a string returned by a Python function. No .html or .js files.

pieces.py
- `Piece`: a plain dataclass record, no methods: id (str), maker (str), clay in {"stoneware","porcelain","earthenware"}, stage in {"bisque","glaze"}, height_cm, width_cm, depth_cm (ints).
- `load_pieces(csv_text)` -> list[Piece] from a CSV with header id,maker,clay,stage,height_cm,width_cm,depth_cm. A duplicate id, unknown clay or stage, missing field, or non-positive dimension raises `PieceError` whose message names the 1-based data row and the field.
- `cone_for(piece)` -> str: bisque is cone "04" for every clay; glaze is "04" earthenware, "6" stoneware, "10" porcelain.

cones.py
- `fetch_cone_chart(url)` -> dict: GET a JSON object like {"04": {"top_c": 1060}, "6": {"top_c": 1222}, "10": {"top_c": 1305}} and return {cone: top_c}. A non-200 status, bad JSON, a missing cone from the three above, or a top_c that is not a positive int raises ValueError (catchable).

packing.py
- `pack_shelves(pieces, shelf_w, shelf_d, kiln_h)` -> list of shelves, each {"height_cm": int, "pieces": [ids]}. Sort pieces by height descending, then id. Place in rows left to right with a 2 cm gap between pieces; start a new row (behind, with a 2 cm gap) when a piece does not fit the width; start a new shelf when a row does not fit the depth. A shelf's height_cm is its tallest piece + 3 (the post and shelf). Raise `PackError` naming the piece id if a piece is wider or deeper than the shelf, and if the shelves' total height exceeds kiln_h.

schedule.py
- `firing_schedule(stage, top_c)` -> list of (rate_c_per_h, target_c, hold_min): [(100, 250, 0), (150, top_c - 100, 0), (60, top_c, hold)] with hold 10 for bisque and 15 for glaze; for a bisque add a first segment (40, 120, 30) in front (water smoking).
- `duration_hours(segments)` -> float rounded to 2 dp: sum over segments of (target - previous target, starting from 20) / rate plus hold / 60.
- `firing_cost(hours, kw, rate_per_kwh)` -> float rounded to 2 dp.

__init__.py
- `Firing`: plain dataclass record, no methods: number, stage, cone, shelves, segments, hours, cost.
- `class Studio(shelf_w, shelf_d, kiln_h, kw, rate_per_kwh, chart)`: `add(piece)` (duplicate id raises PieceError); `queue()` -> list of queued pieces sorted by id; `plan(stage, cone)` -> Firing from the queued pieces of that stage whose cone_for matches (none raises ValueError), numbered from 1; `record(number, results)` with results {piece_id: "ok"|"cracked"} removes those pieces from the queue, keeps cracked ids in `losses`, and raises ValueError for a piece not in that firing or a result not ok/cracked.
- Expose Piece, PieceError, PackError, load_pieces, fetch_cone_chart, Studio.

web.py
- `page_index()` -> HTML with links to /queue and /firing/1.
- `page_queue(studio)` -> HTML: a table with one row per queued piece (id, maker, clay, stage, cone) and a line "N pieces queued"; the table rows carry data-maker attributes; the page includes <script src="/app.js">.
- `page_firing(firing)` -> HTML: shelf-by-shelf lists of piece ids, a segment table, and a line "Total: H h, $C".
- `page_error(message, status)` -> HTML for the error.
- `script_filter()` -> the JavaScript text for /app.js: an input that filters queue rows by maker as you type.
- `serve(studio, port)` -> stdlib http.server with GET /, /queue, /firing/<n>, /app.js; POST /piece with the CSV columns as form fields adds a piece via load_pieces; errors render through page_error with 400 or 404.

Submit every function and class through CLOSER with checks drawn from this spec. Use serve bodies for fetch_cone_chart. Use files for load_pieces.
