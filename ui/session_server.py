#!/usr/bin/env python3
"""One local page for one writer session: http://localhost:<port>/ shows the active ticket of one state dir, live.

A plain http.server on loopback only (I2: the machine talking to itself). Every request re-reads the state dir
and renders through bin/session.py; nothing is written to disk and nothing is kept: when the session's state dir
goes, the history goes with it. Lives outside bin/ because K6's plant forbids network modules in the gate.

    python3 ui/session_server.py --state ~/.getting-close/<repo> [--port 8765] [--every 2]

Stop it with ctrl-c (or kill its pid); it holds no lock and leaves nothing behind.
"""
import argparse, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
import session  # the renderer (no network module in it)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, help="the one gate state dir to show")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--every", type=int, default=2, help="seconds between the page's polls")
    a = ap.parse_args()
    st = Path(a.state).expanduser().resolve()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/fragment":
                body = session.fragment(st)
            elif path == "/":
                body = session.page(st, a.every)
            else:
                self.send_response(404); self.end_headers(); return
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):  # quiet
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"serving {st} at http://localhost:{a.port}/  (ctrl-c to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
