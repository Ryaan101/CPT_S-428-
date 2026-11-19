"""Find and load test emails ("payloads") for the harness.

Two layouts are supported, and can be mixed in one directory:

  flat file      attacks/payloads/01_plain_text.txt
                 One email: a "Subject: ..." line, a blank line, then the body.

  bundle folder  attacks/d3/v2_web_page/
                   trigger.txt       the email the agent is asked to process (same format as above)
                   earlier/*.txt     optional; delivered first, in filename order, then marked processed
                   pages/<file>      optional; served to the fetch_page tool at http://pages.local/<file>

Anything whose name starts with 00_ is a control (no attack in it). A control for an attack named
X is conventionally the bundle 00_X_control, which the report script uses to pair them.
"""
import hashlib
import os
from dataclasses import dataclass, field


@dataclass
class Payload:
    name: str
    subject: str
    body: str
    earlier: list = field(default_factory=list)   # [(subject, body)]
    pages: dict = field(default_factory=dict)     # {filename: text}
    sha256: str = ""

    @property
    def control(self):
        return self.name.startswith("00_")


def parse_email(text):
    header, _, body = text.partition("\n\n")
    return header.replace("Subject:", "", 1).strip(), body


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


def _hash(parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def load_flat(path):
    text = _read(path)
    subject, body = parse_email(text)
    return Payload(os.path.basename(path), subject, body, sha256=_hash([text]))


def load_bundle(path):
    trigger = _read(os.path.join(path, "trigger.txt"))
    subject, body = parse_email(trigger)
    parts = [trigger]
    earlier = []
    edir = os.path.join(path, "earlier")
    if os.path.isdir(edir):
        for name in sorted(os.listdir(edir)):
            if name.endswith(".txt"):
                text = _read(os.path.join(edir, name))
                earlier.append(parse_email(text))
                parts.append(name + text)
    pages = {}
    pdir = os.path.join(path, "pages")
    if os.path.isdir(pdir):
        for name in sorted(os.listdir(pdir)):
            if os.path.isfile(os.path.join(pdir, name)):
                pages[name] = _read(os.path.join(pdir, name))
                parts.append(name + pages[name])
    return Payload(os.path.basename(os.path.normpath(path)), subject, body, earlier, pages, _hash(parts))


def discover(path):
    """Return the payloads under ``path`` (a file, or a directory of files and bundle folders)."""
    if os.path.isfile(path):
        return [load_flat(path)]
    if os.path.isfile(os.path.join(path, "trigger.txt")):
        return [load_bundle(path)]
    found = []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if os.path.isfile(full) and name.endswith(".txt"):
            found.append(load_flat(full))
        elif os.path.isdir(full) and os.path.isfile(os.path.join(full, "trigger.txt")):
            found.append(load_bundle(full))
    return found
