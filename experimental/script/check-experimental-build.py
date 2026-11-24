#!/usr/bin/env python3
"""Check that a staged Jekyll build is self-contained under /experimental/."""

from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit


PREFIX = "/experimental"


class LocalReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.noindex = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        for name in ("href", "src", "poster"):
            if attrs.get(name):
                self.urls.append(attrs[name])
        if attrs.get("srcset"):
            self.urls.extend(part.strip().split()[0] for part in attrs["srcset"].split(","))
        if tag == "meta" and attrs.get("name") == "robots":
            self.noindex = "noindex" in attrs.get("content", "").lower()


def target_for(path, site):
    relative = unquote(path[len(PREFIX):]).lstrip("/")
    if not relative or path.endswith("/"):
        target = site / relative / "index.html"
    else:
        target = site / relative
    if target.is_file():
        candidate = target
    else:
        candidate = site / (relative + ".html")
    return candidate if candidate.resolve().is_relative_to(site.resolve()) else site / "__invalid_path__"


def check(site):
    errors = []
    pages = list(site.rglob("*.html"))
    if not (site / "index.html").is_file():
        errors.append("Missing experimental homepage")
    if (site / "CNAME").exists():
        errors.append("Nested CNAME must not be included")
    for name in ("docs", "script", "test", "_publication_review"):
        if (site / name).exists():
            errors.append(f"Internal directory included: {name}")
    for page in pages:
        parser = LocalReferences()
        parser.feed(page.read_text(encoding="utf-8"))
        if not parser.noindex:
            errors.append(f"Missing noindex tag: {page.relative_to(site)}")
        for url in parser.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                continue
            path = parsed.path
            if not path.startswith("/") or path.startswith("//"):
                continue
            if path != PREFIX and not path.startswith(PREFIX + "/"):
                errors.append(f"Root URL escapes experimental site in {page.relative_to(site)}: {url}")
                continue
            if not target_for(path, site).is_file():
                errors.append(f"Missing target in {page.relative_to(site)}: {url}")
    return pages, errors


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 script/check-experimental-build.py DIRECTORY")
    site = Path(sys.argv[1]).resolve()
    pages, errors = check(site)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(f"Validated {len(pages)} experimental HTML pages under {PREFIX}/")


if __name__ == "__main__":
    main()
