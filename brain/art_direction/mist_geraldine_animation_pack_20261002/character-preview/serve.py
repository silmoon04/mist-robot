"""Serve the isolated character preview and selected pack assets on loopback."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
PACK = ROOT.parent
PREVIEW = "/character-preview/preview/"


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "application/javascript",
                      ".js": "application/javascript", ".json": "application/json", ".wav": "audio/wav"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404, "Choose the preview entry page.")
        return None

    def serve_request(self, head_only=False):
        path = unquote(urlsplit(self.path).path)
        if path == "/":
            self.send_response(302)
            self.send_header("Location", PREVIEW)
            self.end_headers()
            return
        if path == "/__health":
            body = json.dumps({"status": "ok", "version": "1.0.0", "preview": PREVIEW}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        allowed = (path.startswith("/character-preview/") or path.startswith("/site/assets/")
                   or path.startswith("/site/audio/") or path in {
                       "/site/asset-manifest.json", "/site/speech-clips.json", "/site/face-tool.json",
                       "/site/state.mjs", "/site/player.mjs"})
        resolved = Path(self.translate_path(self.path)).resolve()
        roots = (ROOT.resolve(), (PACK / "site").resolve())
        if not allowed or not any(resolved.is_relative_to(root) for root in roots):
            self.send_error(404, "This server exposes only the character preview and selected pack assets.")
            return
        if head_only:
            super().do_HEAD()
        else:
            super().do_GET()

    def do_GET(self):
        self.serve_request()

    def do_HEAD(self):
        self.serve_request(head_only=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9064)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be from 1 to 65535")
    handler = partial(Handler, directory=str(PACK))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"MIST character preview: http://127.0.0.1:{args.port}/", flush=True)
        print("Local synthetic scenes only. Ctrl+C stops this preview server.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
