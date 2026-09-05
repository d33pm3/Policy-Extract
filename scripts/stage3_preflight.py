#!/usr/bin/env python3
"""Stage 3 preflight — recommendation 1.

Refuse Stage 3 until the recall contract and extraction prompt are present
and current. Writes 05-quality-assurance/stage3-preflight.md.

Usage:
    python3 stage3_preflight.py --kb ./kb
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from assert_live_version import assert_live, read_version  # noqa: E402

REQUIRED_TOKENS = {
    "references/atomicity-and-recall.md": [
        "What must become its own record",
        "Clock-start discipline",
        "Page-span quotes",
        "Worked splits",
        "purpose_statement",
    ],
    "prompts/extraction.md": [
        "independently testable verbs",
        "source_page_end",
        "disclosure_requirement",
        "function list",
        "clock starts",
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", required=True)
    args = ap.parse_args()
    root = assert_live()
    missing = []
    for rel, tokens in REQUIRED_TOKENS.items():
        path = root / rel
        if not path.exists():
            missing.append(f"MISSING {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for tok in tokens:
            if tok.lower() not in text.lower():
                missing.append(f"{rel} missing token {tok!r}")
    kb = Path(args.kb)
    qa = kb / "05-quality-assurance"
    qa.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Stage 3 preflight",
        "",
        f"- Skill version: **{read_version(root)}**",
        f"- Skill root: `{root}`",
        f"- atomicity-and-recall.md: loaded",
        f"- prompts/extraction.md: loaded",
        "",
        "Stage 3 must follow those two files. Row count is not a quality metric.",
        "Coverage is the candidate disposition ratio plus C3 recall-surface hits.",
        "",
    ]
    if missing:
        lines += ["**Result: BLOCKED.**", ""] + [f"- {m}" for m in missing]
        (qa / "stage3-preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("PREFLIGHT BLOCKED")
        for m in missing:
            print(" ", m)
        return 1
    lines.append("**Result: PASSED.** Stage 3 may proceed.")
    (qa / "stage3-preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PREFLIGHT PASSED version={read_version(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
