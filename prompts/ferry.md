Build a stdlib-only Python package `ferry` in this directory (write a minimal setuptools pyproject.toml; it must install): a one-boat island ferry with sailings, a vehicle deck, fares and a web UI. Every page and every script the browser receives is a string returned by a Python function. No .html or .js files.

vehicles.py
- `Vehicle`: a plain dataclass record, no methods: plate (str), kind in {"car","van","truck","bike"}, length_m (float), height_m (float), passengers (int).
- `BookingError(ValueError)`: nothing but the base class. Its message names the plate and the problem.
- `load_bookings(path)` -> list[Vehicle] from a CSV file at `path` with header plate,kind,length_m,height_m,passengers. A duplicate plate, unknown kind, non-positive length or height, negative passengers, or a missing field raises BookingError naming the 1-based data row and the field.
- `lane_metres(vehicle)` -> float: length_m + 1.0 gap, rounded to 1 dp; a bike takes 0.5 flat.

deck.py
- `pack_deck(vehicles, lanes, lane_length_m, max_height_m)` -> list of lanes, each a list of plates. Vehicles taller than max_height_m raise BookingError naming the plate. Trucks first, then vans, cars, bikes; ties by plate. Each vehicle goes in the lane with the most room left that still fits its lane_metres; if none fits, raise BookingError naming the plate and "no room".
- `deck_report(lanes_packed, lane_length_m)` -> {"vehicles": N, "used_m": total lane metres used rounded to 1 dp, "free_m": remaining rounded to 1 dp}.

tides.py
- `fetch_tides(url)` -> list of (ISO datetime, height_m): GET a JSON list of {"t": "YYYY-MM-DDTHH:MM", "h": number} and return it as tuples. A non-200 status, bad JSON, a non-list, a missing key or a height that is not a number raises ValueError.
- `sailable(tides, at, min_height_m)` -> bool: the height at ISO datetime `at`, linearly interpolated between the two surrounding tide points, is >= min_height_m. `at` outside the tide range raises ValueError.

fares.py
- `fare(vehicle)` -> int pence: car 1850, van 2600, truck 4200 plus 300 per metre of length over 8, bike 250; plus 450 per passenger beyond the driver (a bike's rider is its driver).
- `receipt_lines(vehicles)` -> list of str "PLATE kind £X.XX" in the given order, then "TOTAL £X.XX".

__init__.py
- `class Crossing(departs, lanes, lane_length_m, max_height_m)`: `book(vehicle)` (duplicate plate raises BookingError); `cancel(plate)` (unknown raises KeyError); `manifest()` -> vehicles sorted by plate; `pack()` -> pack_deck of the manifest; `revenue()` -> sum of fares in pence; `summary()` -> {"departs": departs, "vehicles": N, "passengers": total passengers, "revenue": pence}.
- Expose Vehicle, BookingError, load_bookings, fetch_tides, Crossing.

web.py
- `page_index(crossing)` -> HTML: the line "Sailing DEPARTS: N vehicles, P passengers" and links to /manifest and /deck.
- `page_manifest(crossing)` -> HTML: a table with one row per booked vehicle (plate, kind, length, passengers, fare); rows carry data-kind attributes; includes <script src="/app.js">.
- `page_deck(crossing)` -> HTML: one list per lane of plates, and the deck_report line "Used U m, free F m".
- `page_error(message, status)` -> HTML for the error.
- `script_filter()` -> the JavaScript for /app.js: buttons that show only rows of one kind, and one that shows all.
- `manifest_csv(crossing)` -> bytes: the manifest as CSV with the booking header, UTF-8.
- `serve(crossing, tides, port)` -> runs stdlib http.server on 127.0.0.1 and blocks until interrupted. A port below 1024 raises ValueError before anything starts. GET /, /manifest, /deck, /app.js, /manifest.csv, /sailable?at=<ISO>; POST /book with the CSV columns as form fields; errors render through page_error with 400 or 404.

Submit every function and class through CLOSER with contracts drawn from this spec. Use `files` for load_bookings and `serve` bodies for fetch_tides. Every number and date in a check is a literal you choose from the spec's rules. If the spec gives nothing CLOSER can check for a location, say so in its contract rather than inventing a check.
