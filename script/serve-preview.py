#!/usr/bin/env python3
"""Serve an extracted review bundle on localhost with Jekyll-style page URLs."""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


SITE = Path(__file__).resolve().parent / "site"


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def send_head(self):
        # GitHub Pages resolves /software to software.html. Python's basic
        # server does not, and /news would otherwise open the news/ directory.
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        if path != "/" and not path.endswith("/"):
            page = (SITE / (path.lstrip("/") + ".html")).resolve()
            if page.is_relative_to(SITE) and page.is_file():
                self.path = parsed.path + ".html"
                if parsed.query:
                    self.path += "?" + parsed.query
        return super().send_head()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not (SITE / "index.html").is_file():
        parser.error("site/index.html is missing; extract the full preview ZIP first")
    with ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler) as server:
        print(f"Open http://127.0.0.1:{server.server_port}/ (Ctrl-C to stop)", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
