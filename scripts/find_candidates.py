#!/usr/bin/env python3
"""Stage 2 - Completeness-first candidate clause ledger.

This stage exists because of one specific, reproducible failure: a language model
reading a policy end to end finds the headline obligations and misses the clause
in the annexure, the proviso in a footnote, and the TAT hiding in a table cell.
Deterministic pattern matching has poor precision and excellent recall, which is
exactly the right trade here - it produces the denominator against which Stage 3
completeness is measured.

Two ledgers are produced:
  * sentence candidates - any sentence carrying binding, timing, governance or
    conditional language
  * numeric candidates  - every money value, percentage, duration, count and
    threshold anywhere in the document, including table cells

Every candidate must later carry a disposition: mapped / non_binding /
queued_for_review. `validate_pack.py` fails the run while any stay `pending`.

Usage:
    python3 find_candidates.py --kb ./kb --doc-id ALL

Exit codes: 0 = ledger written; 1 = source layer missing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from assert_live_version import assert_live
except Exception:  # pragma: no cover
    assert_live = None  # type: ignore

# --- pattern families -------------------------------------------------------

BINDING = re.compile(
    r"\b(shall not|shall|must not|must|will not|will|required to|is obliged|obligated to|"
    r"has to|have to|need to|needs to|responsible for|accountable for|ensure that|ensures|ensure|"
    r"prohibited|not permitted|shall be entitled|is entitled|may not|no .{0,20}shall)\b",
    re.I,
)
TIMING = re.compile(
    r"\b(within|before|after|not later than|no later than|latest by|immediately|forthwith|"
    r"same day|t\+\d|monthly|quarterly|bi-?quarterly|half-?yearly|annually|annual|yearly|periodically|"
    r"every\s+\d+|working days?|calendar days?|business days?|\d+\s*(?:days?|hours?|months?|years?|weeks?)|"
    r"on a (?:daily|weekly|monthly|quarterly|annual) basis)\b",
    re.I,
)
GOVERNANCE = re.compile(
    r"\b(board[- ]approved|board of directors|approval|approved by|authoris|authoriz|competent authority|"
    r"committee|delegat|review|reviewed|monitor|oversight|audit|report to|reporting|escalat|disclose|"
    r"disclosure|publish|display|record|retain|retention|maintain|register|log|"
    r"constituted|functions as|chaired by|standing committee|nodal officer|"
    r"internal ombudsman|principal nodal|notice board)\b",
    re.I,
)
CONDITIONAL = re.compile(
    r"\b(if\b|where\b|unless|provided that|provided further|in case|in the event|subject to|"
    r"except|exception|exempt|deviation|notwithstanding|only if|only after|prior to|"
    r"shall not apply|not applicable|carve[- ]out|waiver)\b",
    re.I,
)
DEFINITION = re.compile(r'\b(means|shall mean|is defined as|refers to|for the purpose of this)\b', re.I)

MONEY = re.compile(r"(?:₹|Rs\.?|INR|USD|\$|EUR|£)\s?[\d,]+(?:\.\d+)?(?:\s?(?:lakh|lakhs|crore|crores|million|billion|mn|bn))?", re.I)
PERCENT = re.compile(r"\d+(?:\.\d+)?\s?(?:%|per\s?cent)", re.I)
DURATION = re.compile(r"\b(?:T\+\d+|\d+(?:\.\d+)?)\s*(?:working|calendar|business)?\s*(?:day|days|hour|hours|minute|minutes|week|weeks|month|months|year|years)\b", re.I)
THRESHOLD = re.compile(r"\b(?:not exceeding|exceeding|more than|less than|up to|upto|minimum of|maximum of|at least|at most|greater than|below|above)\s+[₹$]?\s?[\d,]+(?:\.\d+)?", re.I)
CITATION = re.compile(r"\b(?:RBI|SEBI|IRDAI|MCA|NHB|NPCI|BCSBI)\b[^.,;\n]{0,60}|\b(?:Section|Sec\.|Rule|Regulation|Clause|Circular|Notification|Master Direction|Act)\s+[A-Z0-9][\w./()\-]*", re.I)
CONTACT = re.compile(
    r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}|https?://[^\s)>\]]+|"
    r"\b(?:postal address|notice board|phone banking|toll[- ]free|"
    r"pincode|pin code|www\.[^\s)>\]]+)\b",
    re.I,
)
FORUM = re.compile(
    r"\b(?:has constituted|have constituted|functions as|is chaired by|chaired by|"
    r"members of the (?:council|committee|board)|standing committee|"
    r"customer service council|internal ombudsman|principal nodal officer|"
    r"branch level customer service|carries out the following)\b",
    re.I,
)
ACTION_VERBS = re.compile(
    r"\b(acknowledge|acknowledged|update|display|publish|published|refer|referred|"
    r"escalate|escalated|resolve|resolved|record|recorded|track|tracked|lodge|lodged|"
    r"assign|assigned|train|trained|review|reviewed|submit|submitted|disclose|"
    r"disclosed|constitute|constituted|facilitate|facilitated|approach|approached|"
    r"report|reported)\b",
    re.I,
)
BULLET_SPLIT = re.compile(r"(?:\n\s*)(?:[•●▪►⁃]|\d+[.)]|[a-z][.)]|[-\u2013\u2014])\s+")
PAGE_NUM_TOKEN = re.compile(r"^\d{1,3}$")

PRIORITY_RULES = [
    ("critical", lambda f: f["binding"] and (f["timing"] or f["numeric"])),
    ("high", lambda f: f["binding"] and (f["governance"] or f["conditional"])),
    ("high", lambda f: f["numeric"] and f["timing"]),
    ("medium", lambda f: f["binding"] or f["numeric"]),
    ("low", lambda f: True),
]

TYPE_RULES = [
    ("deadline_and_escalation", lambda f: f["timing"] and (f["binding"] or f["governance"])),
    ("monetary_or_threshold", lambda f: f["numeric"]),
    ("published_contact", lambda f: f["contact"]),
    ("forum_or_constitution", lambda f: f["forum"]),
    ("governance_or_reporting", lambda f: f["governance"] and f["binding"]),
    ("exception_or_condition", lambda f: f["conditional"]),
    ("definition", lambda f: f["definition"]),
    ("binding_obligation", lambda f: f["binding"]),
    ("informational", lambda f: True),
]

SENT_SPLIT = re.compile(r"(?<=[.;:])\s+(?=[A-Z(•\-\d])|\n{2,}")
PAGE_MARK = re.compile(r"^<!-- source: (SRC-\d{4}) p\.(\d+) -->")


def squash_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def load_register(kb: Path) -> list[dict]:
    reg = kb / "source-register.json"
    if not reg.exists():
        raise SystemExit("ERROR: source-register.json not found. Run Stage 0 first.")
    return json.loads(reg.read_text(encoding="utf-8"))


def nearest_heading(md_lines: list[str], idx: int) -> str:
    for j in range(idx, -1, -1):
        line = md_lines[j].strip()
        if line.startswith("### "):
            return line[4:].strip()
        if PAGE_MARK.match(line) and j < idx - 200:
            break
    return "not_specified"
