"""Open the finished dashboard in a local browser. Python standard library only.

Run after extracting the project: python preview.py
This is a local preview on your computer, not public hosting.
"""
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import shutil
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent

class DashboardHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.serve_dashboard(head_only=True)

    def do_GET(self):
        self.serve_dashboard(head_only=False)

    def serve_dashboard(self, head_only):
        if urlsplit(self.path).path not in ('/', '/index.html'):
            self.send_error(404)
            return
        path = ROOT / 'index.html'
        if not path.is_file():
            self.send_error(503, 'index.html is missing; extract the complete project first')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Disposition', 'inline; filename="index.html"')
        self.send_header('Content-Length', str(path.stat().st_size))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if not head_only:
            with path.open('rb') as f:
                shutil.copyfileobj(f, self.wfile)

    def log_message(self, format, *args):
        pass

def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), DashboardHandler)
    except OSError as error:
        parser.exit(1, f'Cannot start preview: {error}. Try python preview.py --port 8001\n')
    url = f'http://127.0.0.1:{server.server_port}/'
    print(f'Local dashboard preview: {url}', flush=True)
    print('Keep this terminal open. Press Ctrl+C to stop. This is not a public URL.', flush=True)
    if not args.no_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
