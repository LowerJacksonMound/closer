Build a stdlib-only Python package `lido` in this directory (write a minimal setuptools pyproject.toml; it must install): an outdoor swimming pool's lane booking and water-quality log with a web UI. Every page and every script the browser receives is a string returned by a Python function. No .html or .js files.

swimmers.py
- `Swimmer`: a plain dataclass record, no methods: id (str), name (str), level in {"beginner","improver","fast"}, member (bool).
- `BookingError(ValueError)`: nothing but the base class. Its message names the swimmer id and the problem.
- `load_swimmers(path)` -> list[Swimmer] from a CSV file at `path` with header id,name,level,member (member is "yes" or "no"). A duplicate id, unknown level, a member value other than yes/no, or a missing field raises BookingError naming the 1-based data row and the field.
- `lane_for(swimmer)` -> int: beginner 1, improver 2, fast 3.

sessions.py
- `slots(open_at, close_at, minutes)` -> list of "HH:MM" start times from open_at (ISO "HH:MM") while a full slot fits before close_at; minutes < 15 raises ValueError.
- `book(bookings, swimmer, slot, per_lane)` -> the new bookings dict {slot: {lane: [swimmer ids]}}. The swimmer goes in lane_for(swimmer); a lane already holding per_lane swimmers raises BookingError "lane full"; the same id twice in one slot raises BookingError "already booked". The input dict is not changed.
- `occupancy(bookings, slot)` -> {lane: count} for lanes 1..3, zeros included.

water.py
- `fetch_readings(url)` -> list of (ISO datetime, ph, chlorine_ppm): GET a JSON list of {"t": ..., "ph": number, "cl": number} and return tuples. A non-200 status, bad JSON, a non-list, a missing key, or a non-number raises ValueError.
- `water_ok(reading)` -> bool: ph in 7.2-7.8 inclusive and chlorine 1.0-3.0 inclusive.
- `last_safe(readings)` -> the ISO datetime of the latest reading that is water_ok, or None.

pricing.py
- `price(swimmer, slot)` -> int pence: 650, members 450; before "09:00" 100 off; beginners never pay less than 300.
- `till_lines(swimmers, slot)` -> list of str "NAME £X.XX" in the given order then "TOTAL £X.XX".

__init__.py
- `class Lido(open_at, close_at, minutes, per_lane)`: `add(swimmer)` (duplicate id raises BookingError); `book(id, slot)` (unknown id raises KeyError; unknown slot raises ValueError; otherwise sessions.book); `cancel(id, slot)` (not booked raises KeyError); `lanes(slot)` -> occupancy; `takings(slot)` -> pence; `day()` -> {slot: total swimmers} for every slot.
- Expose Swimmer, BookingError, load_swimmers, fetch_readings, Lido.

web.py
- `page_index(lido, readings)` -> HTML: the line "Open OPEN_AT to CLOSE_AT, N slots" and the line "Water last safe: T" (or "Water: no safe reading"), and links to /slots and /water.
- `page_slots(lido)` -> HTML: a table with one row per slot (time, lane 1, lane 2, lane 3 counts, takings); rows carry data-slot attributes; a full slot's row carries class="full"; includes <script src="/app.js">.
- `page_water(readings)` -> HTML: one row per reading with class="ok" or class="bad".
- `page_error(message, status)` -> HTML for the error.
- `script_filter()` -> the JavaScript for /app.js: a checkbox that hides full slots.
- `timetable_ics(lido)` -> bytes: an iCalendar file with one VEVENT per slot that has at least one swimmer, UTF-8.
- `serve(lido, readings, port)` -> runs stdlib http.server on 127.0.0.1 and blocks until interrupted. A port below 1024 raises ValueError before anything starts. GET /, /slots, /water, /app.js, /timetable.ics; POST /book with id and slot as form fields; errors render through page_error with 400 or 404.

Submit every function and class through CLOSER with contracts drawn from this spec. Use `files` for load_swimmers and `serve` bodies for fetch_readings. Every number and time in a check is a literal you choose from the spec's rules. If the spec gives nothing CLOSER can check for a location, say so in its contract rather than inventing a check.
