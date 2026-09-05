#!/usr/bin/env python3
"""Stage 7 - Publish compliance packs, enterprise views and machine-readable exports.

Rendering is deterministic and refuses to publish anything the validator would
reject as uncited, so a pack cannot quietly acquire an unsourced row. Everything
published while a review gate is open is stamped DRAFT.

Usage:
    python3 build_packs.py --kb ./kb
    python3 build_packs.py --kb ./kb --allow-uncited

Exit codes: 0 = published; 1 = refused (uncited rows present and --allow-uncited not set).
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from assert_live_version import assert_live, read_version
except Exception:  # pragma: no cover
    assert_live = None  # type: ignore
    def read_version(_root=None):
        return "unknown"

DRAFT_BANNER = ("> **DRAFT - NOT APPROVED FOR OPERATIONAL USE.** Review gates are open. "
                "Do not rely on this document for legal, regulatory, audit or operational purposes "
                "until the policy owner, Compliance/Legal (where applicable), Operations and "
                "Internal Audit have signed their gates.")
APPROVED_BANNER = ("> All records in this pack carry signed review gates. Source citations remain "
                   "the authority; proposed controls remain labelled as proposals.")


def load(kb: Path):
    reg_path = kb / "source-register.json"
    req_path = kb / "02-requirements" / "requirements.json"
    if not reg_path.exists():
        raise SystemExit("ERROR: source-register.json missing. Run Stage 0.")
    if not req_path.exists():
        raise SystemExit("ERROR: requirements.json missing. Complete Stage 3.")
    register = json.loads(reg_path.read_text(encoding="utf-8"))
    data = json.loads(req_path.read_text(encoding="utf-8"))
    reqs = data.get("requirements", []) if isinstance(data, dict) else data
    return register, reqs


def cited(r: dict) -> bool:
    return bool(r.get("source_file") and r.get("source_page_start") and (r.get("source_quote") or "").strip() and (r.get("source_section") or "").strip())


def src(r: dict) -> str:
    p0, p1 = r.get("source_page_start"), r.get("source_page_end")
    pages = f"p.{p0}" if p0 == p1 else f"pp.{p0}-{p1}"
    return f"{r.get('source_file')} {pages}, {r.get('source_section')}"


def esc(v) -> str:
    return str(v if v is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def when(r: dict) -> str:
    dv = r.get("deadline_verbatim")
    if dv:
        return esc(dv)
    if r.get("deadline_value") is not None:
        return esc(f"{r['deadline_value']} {r.get('deadline_unit') or ''} ({r.get('deadline_basis')})")
    freq = r.get("frequency")
    return esc(freq) if freq and freq != "not_specified" else "not_specified"


def who(r: dict) -> str:
    basis = r.get("role_basis", "not_specified")
    tag = {"explicit_source": "", "operational_inference": " *(inferred)*", "not_specified": ""}.get(basis, "")
    a, resp = r.get("accountable_role", "not_specified"), r.get("responsible_role", "not_specified")
    return esc(f"A: {a}; R: {resp}") + tag


def evidence_list(r: dict) -> str:
    items = [esc(e) for e in (r.get("mandatory_evidence") or [])]
    for c in r.get("controls") or []:
        for e in c.get("evidence") or []:
            tag = "" if e.get("label") == "SOURCE-EXPLICIT" else " `PROPOSED-EVIDENCE`"
            items.append(esc(e.get("artefact")) + tag)
    return "<br>".join(items) or "not_specified"


def control_summary(r: dict) -> str:
    out = []
    for c in r.get("controls") or []:
        tag = "`SOURCE-EXPLICIT`" if c.get("label") == "SOURCE-EXPLICIT" else "`PROPOSED-CONTROL`"
        out.append(f"{esc(c.get('control_id'))} {tag}: {esc(c.get('objective'))}")
    return "<br>".join(out) or "none recorded"


def status_cell(r: dict) -> str:
    st = r.get("status", "draft")
    rs = r.get("review_status", "unreviewed")
    conf = r.get("extraction_confidence", "medium")
    flag = " \u26a0" if (conf == "low" or r.get("evidence_class") == "REQUIRES-LEGAL-REVIEW") else ""
    return esc(f"{st}/{rs}/{conf}") + flag


def table(headers, rows) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(rows_i) + " |" for rows_i in rows]
    return out


def banner(reqs: list[dict]) -> str:
    return APPROVED_BANNER if reqs and all(r.get("status") == "approved" for r in reqs) else DRAFT_BANNER
