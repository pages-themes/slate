#!/usr/bin/env python3
"""Serve the root site at / and experimental/ source at /experimental/."""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import subprocess
from tempfile import TemporaryDirectory
from threading import Event, Thread
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def handler_for(site):
    class LocalSiteHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site), **kwargs)

        def send_head(self):
            parsed = urlsplit(self.path)
            path = unquote(parsed.path)
            if path != "/" and not path.endswith("/"):
                page = (site / (path.lstrip("/") + ".html")).resolve()
                if page.is_relative_to(site) and page.is_file():
                    self.path = parsed.path + ".html"
                    if parsed.query:
                        self.path += "?" + parsed.query
            return super().send_head()

    return LocalSiteHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", args.port))
        except OSError as error:
            parser.error(f"port {args.port} is unavailable ({error}); stop the existing server or run make serve LOCAL_PORT=4002")

    with TemporaryDirectory(prefix="autodial-local-composite-") as temporary:
        temp = Path(temporary)
        combined = temp / "site"
        run("bundle", "exec", "jekyll", "build", "--source", str(ROOT),
            "--config", str(ROOT / "_config.yml"), "--destination", str(combined), "--quiet")

        config = temp / "experimental-config.yml"
        config.write_text(f"url: http://127.0.0.1:{args.port}\nbaseurl: /experimental\n", encoding="utf-8")
        draft_command = (
            "bundle", "exec", "jekyll", "build", "--source", str(ROOT / "experimental"),
            "--config", f"{ROOT / 'experimental/_config.yml'},{config}",
            "--destination", str(combined / "experimental"),
        )
        run(*draft_command, "--quiet")
        if not (combined / "index.html").is_file() or not (combined / "experimental/index.html").is_file():
            raise RuntimeError("The master or experimental homepage was not generated")

        with ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(combined)) as server:
            print(f"Original site: http://127.0.0.1:{args.port}/", flush=True)
            print(f"Experimental draft: http://127.0.0.1:{args.port}/experimental/", flush=True)
            print("Ctrl-C to stop. Draft changes rebuild automatically.", flush=True)
            watcher = subprocess.Popen((*draft_command, "--watch"), cwd=ROOT)
            stopping = Event()

            def monitor_watcher():
                status = watcher.wait()
                if not stopping.is_set():
                    print(f"Draft rebuild process exited with status {status}", flush=True)
                    server.shutdown()

            monitor = Thread(target=monitor_watcher, daemon=True)
            monitor.start()
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                stopping.set()
                if watcher.poll() is None:
                    watcher.terminate()
                try:
                    watcher.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    watcher.kill()
                    watcher.wait()


if __name__ == "__main__":
    main()
