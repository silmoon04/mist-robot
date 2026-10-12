# Dev server for the MIST simulator — plain http.server but with caching disabled,
# so edits to the JS modules always show up on reload.
#   python sim/serve.py            (or run from anywhere; serves the sim/ folder)
import http.server
import os

PORT = int(os.environ.get('PORT', 8123))
# serve the whole repo so the sim can load brain/face_assets/svg/* faces
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send_response(302)
            self.send_header('Location', '/sim/')
            self.end_headers()
            return
        super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


if __name__ == '__main__':
    with http.server.ThreadingHTTPServer(('127.0.0.1', PORT), NoCacheHandler) as httpd:
        print(f'MIST sim at http://localhost:{PORT}/  (serving {ROOT}, cache disabled)')
        httpd.serve_forever()
