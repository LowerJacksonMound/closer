Build a stdlib-only Python package `seedbank` in this directory (write a minimal setuptools pyproject.toml; it must install): a community seed-bank ledger with a web UI. Every page and every script the browser receives is a string returned by a Python function. No .html or .js files.

lots.py
- `Lot`: a plain dataclass record, no methods: id (str), species (str), variety (str), year (int, the harvest year), count (int), tested (str, ISO date of the last germination test or ""), germ_pct (int, 0-100, the last test's result, 0 if untested).
- `LotError(ValueError)`: nothing but the base class. Its message names the 1-based data row and the field.
- `load_lots(path)` -> list[Lot] from a CSV file at `path` with header id,species,variety,year,count,tested,germ_pct. A duplicate id, a year before 1900 or after 2100, a negative count, a germ_pct outside 0-100, a tested value that is not an ISO date (empty is allowed), or a missing field raises LotError.
- `parse_lot_line(line)` -> Lot from one CSV data line (the same fields, no header); the same errors, with row 1.

viability.py
- `expected_germ(lot, on)` -> int: the germination percent expected on ISO date `on`. Start from germ_pct if tested, else 85. Subtract 8 for each full year between the harvest year and the year of `on`, using 6 for the first year after a test instead. Never below 0. A date before the harvest year raises ValueError.
- `is_viable(lot, on)` -> bool: expected_germ >= 50.
- `packets_possible(lot, seeds_per_packet)` -> int: count // seeds_per_packet; seeds_per_packet < 1 raises ValueError.

frost.py
- `fetch_frost_dates(url)` -> dict: GET a JSON object {"last_spring": "YYYY-MM-DD", "first_fall": "YYYY-MM-DD"} and return it. A non-200 status, bad JSON, a missing key or a value that is not an ISO date raises ValueError.
- `sowing_window(frost, species)` -> (start, end) ISO dates: tomatoes and peppers start 6 weeks before last_spring and end 2 weeks after it; beans and squash start on last_spring and end 8 weeks before first_fall; anything else starts 2 weeks before last_spring and ends 10 weeks before first_fall.

__init__.py
- `class SeedBank(lots)`: `add(lot)` (duplicate id raises LotError); `get(id)` (unknown raises KeyError); `record_test(id, on, germ_pct)` sets tested and germ_pct on that lot and returns it; `withdraw(id, n)` reduces count, raises ValueError if n > count; `viable(on)` -> lots viable on that date sorted by species then id; `summary(on)` -> {"lots": N, "seeds": total count, "viable": count of viable lots}.
- Expose Lot, LotError, load_lots, fetch_frost_dates, SeedBank.

web.py
- `page_index(bank, on)` -> HTML: the summary line "N lots, S seeds, V viable on <on>" and links to /lots and /sow.
- `page_lots(bank, on)` -> HTML: a table with one row per lot (id, species, variety, year, count, expected germ) sorted by species then id; rows carry data-species attributes; non-viable rows carry class="dead"; includes <script src="/app.js">.
- `page_sow(bank, frost)` -> HTML: one line per species present, "species: start to end".
- `page_error(message, status)` -> HTML for the error.
- `script_filter()` -> the JavaScript for /app.js: an input that filters lot rows by species as you type.
- `label_png(lot)` -> bytes: a 1-bit PNG of the lot id as text, for the printer. Any valid PNG will do.
- `serve(bank, frost, port)` -> runs stdlib http.server on 127.0.0.1 and blocks until interrupted. A port below 1024 raises ValueError before anything starts. GET /, /lots, /sow, /app.js, /label/<id>.png; POST /test with id, on, germ_pct as form fields; errors render through page_error with 400 or 404.

Submit every function and class through CLOSER with contracts drawn from this spec. Use `files` for load_lots and `serve` bodies for fetch_frost_dates. The dates in every check are literal strings you choose. If the spec gives nothing CLOSER can check for a location, say so in its contract rather than inventing a check.
