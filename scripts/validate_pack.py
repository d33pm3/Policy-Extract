#!/usr/bin/env python3
"""Stage 6 - Automated validation of the requirement register.

Checks G1-G8 and C1-C3. Exit 0 clean, 2 warnings only, 1 blocking failures.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from assert_live_version import assert_live, read_version
except Exception:  # pragma: no cover
    assert_live = None  # type: ignore
    def read_version(_root=None):
        return "unknown"

FUZZY_ACCEPT = 0.90
INTERPRETATION_PAT = re.compile(
    r"\b(this (?:is|would be) (?:legally|statutorily) (?:required|mandatory)|"
    r"complies with|is compliant with|non[- ]compliance with .{0,40} (?:attracts|results in)|"
    r"violates|breaches? (?:the )?(?:Act|Regulation|Rule|Section)|"
    r"is mandated by (?:the )?(?:Act|RBI|SEBI|IRDAI|MCA)|"
    r"the (?:Act|Regulation|Rule) requires|as required by law|legally obligated)\b", re.I)
COMPOUND_PAT = re.compile(
    r"\b(and (?:also )?(?:shall|must|will|report|maintain|conduct|submit|ensure|provide|"
    r"resolve|escalate|acknowledge|update|display|publish|refer|record|track|lodge|"
    r"assign|train|review|disclose|facilitate|approach)|as well as)\b", re.I)
CLOCK_START_PAT = re.compile(
    r"\bfrom the (?:date of )?(?:decision date|decision|receipt|lodg(?:ing|ement)|referral|communication|approval)\b", re.I)
ANNEX_HINT = re.compile(r"\b(annexure|appendix|part [ab]|annual report disclosure|template)\b", re.I)
EMAIL_OR_URL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}|https?://[^\s)>\]]+", re.I)
FILLER_VALUES = {"tbd", "n/a", "na", "as applicable", "as prescribed", "as per policy", "periodic", "to be decided", "appropriate", "relevant team", "concerned department", "management", "as required", "various", "-", "--", "?"}
SENTINEL = "not_specified"
TABLE_NUMERIC_KINDS = {"money", "percentage", "duration", "threshold", "rate"}
LABELS_OK = {"SOURCE-EXPLICIT", "SOURCE-INFERRED", "PROPOSED-CONTROL", "PROPOSED-EVIDENCE", "PROPOSED-TEST", "REQUIRES-LEGAL-REVIEW"}


def norm(s: str) -> str:
    s = (s or "").replace("\u00ad", "").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def squash(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", norm(s))


def digits(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")


def best_ratio(needle: str, haystack: str) -> float:
    if not needle or not haystack:
        return 0.0
    sm = SequenceMatcher(None, needle, haystack, autojunk=False)
    m = sm.find_longest_match(0, len(needle), 0, len(haystack))
    return m.size / len(needle)


class Corpus:
    def __init__(self, kb: Path):
        self.kb = kb
        reg_path = kb / "source-register.json"
        if not reg_path.exists():
            raise SystemExit("ERROR: source-register.json missing. Run Stage 0.")
        self.register = {d["document_id"]: d for d in json.loads(reg_path.read_text(encoding="utf-8"))}
        self.pages: dict[str, dict[int, str]] = {}
        for doc_id in self.register:
            pj = kb / "01-source-layer" / doc_id / "pages.json"
            if pj.exists():
                self.pages[doc_id] = {int(k): v for k, v in json.loads(pj.read_text(encoding="utf-8")).items()}

    def page_text(self, doc_id: str, pno: int) -> str:
        return self.pages.get(doc_id, {}).get(pno, "")

    def span_text(self, doc_id: str, p0: int, p1: int, pad: int = 0) -> str:
        lo, hi = min(p0, p1) - pad, max(p0, p1) + pad
        return "\n".join(self.page_text(doc_id, p) for p in range(max(1, lo), hi + 1))


def load_requirements(kb: Path) -> list[dict]:
    path = kb / "02-requirements" / "requirements.json"
    if not path.exists():
        raise SystemExit(f"ERROR: {path} missing. Complete Stage 3 first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("requirements", [])
    if not isinstance(data, list):
        raise SystemExit("ERROR: requirements.json must be a list or an object with a requirements list.")
    return data


def load_candidates(kb: Path) -> list[dict]:
    out = []
    for fp in sorted((kb / "02-candidates").glob("*-candidates.json")):
        led = json.loads(fp.read_text(encoding="utf-8"))
        out.extend(led.get("candidates", []))
    return out


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []
    def add(self, check: str, level: str, rid: str, message: str) -> None:
        self.items.append({"check": check, "level": level, "id": rid, "message": message})
    def fail(self, check, rid, msg):
        self.add(check, "FAIL", rid, msg)
    def warn(self, check, rid, msg):
        self.add(check, "WARN", rid, msg)
    @property
    def failures(self):
        return [i for i in self.items if i["level"] == "FAIL"]
    @property
    def warnings(self):
        return [i for i in self.items if i["level"] == "WARN"]
