"""Serve this design locally for the offline assembly viewer."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class LocalHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".stl": "application/octet-stream"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8139)
    args = parser.parse_args()
    design_root = Path(__file__).resolve().parents[1]
    handler = partial(LocalHandler, directory=str(design_root))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Quadruped viewer: http://127.0.0.1:{args.port}/review/", flush=True)
    print(f"Serving only: {design_root}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
