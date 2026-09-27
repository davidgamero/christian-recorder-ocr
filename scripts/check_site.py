"""Check corpus/page counts, local links, and the GitHub Pages artifact budget."""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from build import BASE, OUT


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src", "data-url"} and value:
                self.paths.append(value)


def main():
    catalog = json.loads((OUT / "catalog.json").read_text())
    pages = list((OUT / "scans").glob("*/index.html"))
    assert len(pages) == catalog["scans"] == 2376
    broken = []
    for path in OUT.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text())
        for value in parser.paths:
            link = urlsplit(value)
            if link.scheme or link.netloc or not link.path or "{{" in value:
                continue
            target = unquote(link.path)
            if target.startswith(BASE):
                target = OUT / target[len(BASE):]
            elif target.startswith("/"):
                broken.append((str(path), value))
                continue
            else:
                target = path.parent / target
            if target.is_dir():
                target /= "index.html"
            if not target.exists():
                broken.append((str(path), value))
    assert not broken, broken[:20]
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    index = sum(p.stat().st_size for p in (OUT / "pagefind").rglob("*") if p.is_file())
    assert total < 950_000_000, f"Site too close to Pages' 1GB limit: {total}"
    print(f"Verified {len(pages)} scans and local links. Site: {total/1e6:.1f} MB; search: {index/1e6:.1f} MB")


if __name__ == "__main__":
    main()
