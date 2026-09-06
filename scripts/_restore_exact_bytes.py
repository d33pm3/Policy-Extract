#!/usr/bin/env python3
"""Assemble files from .exact-src base64 chunks and verify SHA-256."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".exact-src"
MANIFEST = SRC / "MANIFEST.json"


def main() -> int:
    if not MANIFEST.exists():
        print("no .exact-src/MANIFEST.json; nothing to restore")
        return 0
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failed = 0
    for item in items:
        dest = ROOT / item["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        pieces: list[str] = []
        broken = False
        for part in item["parts"]:
            path = SRC / part["name"]
            text = path.read_text(encoding="ascii")
            got = hashlib.sha256(text.encode("ascii")).hexdigest()
            if got != part["sha256"] or len(text) != part["chars"]:
                print(f"FAIL part {part['name']}: sha/size mismatch")
                failed += 1
                broken = True
                break
            pieces.append(text)
        if broken:
            continue
        raw = base64.b64decode("".join(pieces))
        digest = hashlib.sha256(raw).hexdigest()
        if digest != item["sha256"] or len(raw) != item["bytes"]:
            print(f"FAIL {item['path']}: assembled {len(raw)} {digest}")
            failed += 1
            continue
        dest.write_bytes(raw)
        print(f"OK   {item['path']} {len(raw)} {digest}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
