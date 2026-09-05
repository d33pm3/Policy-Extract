#!/usr/bin/env python3
"""Refuse to run pipeline scripts against a stale or foreign skill tree.

Canonical live skill: the repository / skill root that contains this script
(parent of ``scripts/``). Override with POLICY_EXTRACTOR_ROOT when needed.

Minimum version: 1.2.0 (atomicity-and-recall + C3 + clock/template warnings).

Any copy missing VERSION / RELEASE_PIN.json, or reporting a lower version,
is treated as the pre-1.2.0 skill and is rejected. There is no automatic
fallback to a packaged .skill export or to a sibling directory.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _default_canonical() -> Path:
    env = (os.environ.get("POLICY_EXTRACTOR_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


CANONICAL = _default_canonical()
MIN = tuple(int(x) for x in "1.2.0".split("."))


def _parse(v: str) -> tuple[int, ...]:
    parts = []
    for token in (v or "").strip().split("."):
        digits = "".join(c for c in token if c.isdigit())
        parts.append(int(digits or 0))
    return tuple((parts + [0, 0, 0])[:3])


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_version(root: Path) -> str:
    vf = root / "VERSION"
    if vf.exists():
        return vf.read_text(encoding="utf-8").strip()
    md = (root / "SKILL.md").read_text(encoding="utf-8") if (root / "SKILL.md").exists() else ""
    for line in md.splitlines():
        if "version:" in line.lower() and any(ch.isdigit() for ch in line):
            raw = line.split(":", 1)[-1].strip().strip("\"'")
            if raw:
                return raw
    return "0.0.0"


def assert_live(root: Path | None = None) -> Path:
    root = Path(root) if root is not None else skill_root()
    version = read_version(root)
    pin_path = root / "RELEASE_PIN.json"
    if not pin_path.exists():
        raise SystemExit(
            f"ROLLBACK-GUARD: {root} has no RELEASE_PIN.json. "
            "This is not policy-extractor >= 1.2.0. Refusing to run."
        )
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    if _parse(version) < MIN or _parse(str(pin.get("version", "0"))) < MIN:
        raise SystemExit(
            f"ROLLBACK-GUARD: live skill version {version} is older than required 1.2.0. "
            "Refusing to run the pre-recall-contract skill."
        )
    for rel in pin.get("required_files") or []:
        if not (root / rel).exists():
            raise SystemExit(f"ROLLBACK-GUARD: required file missing: {rel}")
    recall = (root / "references" / "atomicity-and-recall.md").read_text(encoding="utf-8")
    if "Clock-start discipline" not in recall or "What must become its own record" not in recall:
        raise SystemExit("ROLLBACK-GUARD: atomicity-and-recall.md is not the 1.2.0 contract.")
    return root


def main() -> int:
    root = assert_live()
    print(f"LIVE {root} version={read_version(root)}")
    print(f"CANONICAL {CANONICAL} match={root.resolve() == CANONICAL.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
