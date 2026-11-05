"""SCRUM-61 — measure encrypt/decrypt time per level and payload size, print a Markdown table.

    python tools/perf_report.py            # prints table
    python tools/perf_report.py --write    # also updates docs/testing/PERFORMANCE.md (table section)

Uses the in-memory FakeKM from tests/conftest.py so only the crypto pipeline is timed.
"""
from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from qumail.crypto import envelope, pipeline  # noqa: E402
from tests.conftest import FakeKM  # noqa: E402

envelope.load_levels()
MB = 1024 * 1024
SIZES = [("1 KB", 1024), ("100 KB", 100 * 1024), ("1 MB", MB), ("5 MB", 5 * MB), ("15 MB", 15 * MB)]
LEVELS = [(2, "Level 2 AES-256-GCM", False), (4, "Level 4 double layer", False), (3, "Level 3 hybrid", True)]


class _Att:
    def __init__(self, n, d):
        self.filename, self.data, self.content_type = n, d, "application/octet-stream"


class _Mail:
    def __init__(self, prepared, blobs, level):
        self.level, self.key_id, self.body = level, prepared.key_id, prepared.body
        self.attachments = [_Att(n, d) for n, d in blobs]


def measure(level, hybrid, path, repeat=3):
    enc, dec = [], []
    for _ in range(repeat):
        km = FakeKM(keys=200)
        t0 = time.perf_counter()
        prepared, blobs = pipeline.prepare(level, "perf", [path], km, hybrid)
        t1 = time.perf_counter()
        pipeline.open_message(_Mail(prepared, blobs, level), km)
        t2 = time.perf_counter()
        enc.append(t1 - t0)
        dec.append(t2 - t1)
    return statistics.median(enc), statistics.median(dec), km.status()["reserved"]


def otp_exhaustion():
    km = FakeKM(keys=100)
    t0 = time.perf_counter()
    n = 0
    while pipeline.check_capacity(3, "A" * 900, [], km) is None:
        pipeline.prepare(3, "A" * 900, [], km)
        n += 1
    return n, time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rows = ["| Payload | Level | Encrypt | Decrypt | Keys used |", "|---|---|---|---|---|"]
    with tempfile.TemporaryDirectory() as td:
        for label, size in SIZES:
            p = Path(td) / "blob.bin"
            p.write_bytes(os.urandom(size))
            for level, name, hybrid in LEVELS:
                e, d, keys = measure(level, hybrid, str(p))
                rows.append(f"| {label} | {name} | {e*1000:.0f} ms | {d*1000:.0f} ms | {keys} |")
    n, secs = otp_exhaustion()
    rows.append("")
    rows.append(f"OTP exhaustion: {n} Level-3 mails (900 B each) drained a 100 × 1 KB bank in {secs*1000:.0f} ms; "
                "the 101st was blocked by check_capacity before any key was requested.")
    rows.append("")
    rows.append(f"Machine: {platform.platform()} · Python {platform.python_version()} · "
                f"{time.strftime('%d %b %Y %H:%M')}")
    table = "\n".join(rows)
    print(table)

    if args.write:
        doc = ROOT / "docs" / "testing" / "PERFORMANCE.md"
        text = doc.read_text(encoding="utf-8")
        start, end = "<!-- perf-table-start -->", "<!-- perf-table-end -->"
        a, b = text.index(start) + len(start), text.index(end)
        doc.write_text(text[:a] + "\n" + table + "\n" + text[b:], encoding="utf-8")
        print(f"\nupdated {doc.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
