"""A closed, local stand-in for the web, used by the fetch_page tool.

The agent never touches the real internet. A URL resolves only if its host is ``pages.local`` and
its path names a page that the operator loaded into this object. Anything else is "not found".
That keeps the experiment safe and repeatable, and it models an attacker who controls one page
that an email links to.
"""
import os
from urllib.parse import urlparse

HOST = "pages.local"
MAX_PAGE_CHARS = 8000


class LocalWeb:
    def __init__(self, pages=None):
        self.pages = dict(pages or {})

    @classmethod
    def from_dir(cls, path):
        pages = {}
        if path and os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                if os.path.isfile(full):
                    with open(full, encoding="utf-8") as f:
                        pages[name] = f.read()
        return cls(pages)

    def fetch(self, url):
        """Return the page text, or None if the URL is not one of the loaded pages."""
        try:
            parsed = urlparse(str(url).strip())
        except ValueError:
            return None
        if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() != HOST:
            return None
        name = parsed.path.lstrip("/")
        text = self.pages.get(name)
        return None if text is None else text[:MAX_PAGE_CHARS]
