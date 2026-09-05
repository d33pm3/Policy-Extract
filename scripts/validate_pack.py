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
INTERPRETATION_PAT = re.compile(r"\b(complies with|is compliant with|violates|as required by law|legally obligated)\b", re.I)
COMPOUND_PAT = re.compile(r"\b(and (?:also )?(?:shall|must|will|report|maintain|conduct|submit|ensure|provide|resolve|escalate|acknowledge|update|display|publish|refer|record|track)|as well as)\b", re.I)
CLOCK_START_PAT = re.compile(r"\bfrom the (?:date of )?(?:decision date|decision|receipt|lodg(?:ing|ement)|referral|communication|approval)\b", re.I)
ANNEX_HINT = re.compile(r"\b(annexure|appendix|part [ab]|annual report disclosure|template)\b", re.I)
FILLER_VALUES = {"tbd", "n/a", "na", "as applicable", "as prescribed", "as per policy", "periodic", "to be decided", "appropriate", "relevant team", "concerned department", "management", "as required", "various", "-", "--", "?"}
SENTINEL = "not_specified"
EVIDENCE_LABELS = {"SOURCE-EXPLICIT", "SOURCE-INFERRED", "PROPOSED-EVIDENCE", "REQUIRES-LEGAL-REVIEW"}
CONTROL_LABELS = {"SOURCE-EXPLICIT", "SOURCE-INFERRED", "PROPOSED-CONTROL", "REQUIRES-LEGAL-REVIEW"}
TEST_LABELS = {"SOURCE-EXPLICIT", "SOURCE-INFERRED", "PROPOSED-TEST", "REQUIRES-LEGAL-REVIEW"}


def norm(s: str) -> str:
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u2013", "-").replace("\u2014", "-")
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
        self.pages = {}
        for doc_id in self.register:
            pj = kb / "01-source-layer" / doc_id / "pages.json"
            if pj.exists():
                self.pages[doc_id] = {int(k): v for k, v in json.loads(pj.read_text(encoding="utf-8")).items()}
    def page_text(self, doc_id, pno):
        return self.pages.get(doc_id, {}).get(pno, "")
    def span_text(self, doc_id, p0, p1, pad=0):
        lo, hi = min(p0, p1) - pad, max(p0, p1) + pad
        return "\n".join(self.page_text(doc_id, p) for p in range(max(1, lo), hi + 1))


def load_requirements(kb: Path):
    path = kb / "02-requirements" / "requirements.json"
    if not path.exists():
        raise SystemExit(f"ERROR: {path} missing. Complete Stage 3 first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("requirements", [])
    return data


def load_candidates(kb: Path):
    out = []
    for fp in sorted((kb / "02-candidates").glob("*-candidates.json")):
        out.extend(json.loads(fp.read_text(encoding="utf-8")).get("candidates", []))
    return out


class Findings:
    def __init__(self):
        self.items = []
    def add(self, check, level, rid, message):
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


def check_schema(reqs, f):
    schema_path = HERE.parent / "schemas" / "policy-requirement.schema.json"
    if not schema_path.exists():
        f.warn("C2-schema", "-", "Schema file not found; structural validation skipped.")
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(schema)
        for r in reqs:
            rid = r.get("requirement_id", "<no id>")
            for err in validator.iter_errors(r):
                loc = ".".join(str(p) for p in err.path) or "(root)"
                f.fail("C2-schema", rid, f"{loc}: {err.message}")
    except ImportError:
        for r in reqs:
            for c in r.get("controls") or []:
                for e in c.get("evidence") or []:
                    if e.get("label") not in EVIDENCE_LABELS:
                        f.fail("C2-schema", r.get("requirement_id", "<no id>"), f"evidence.label {e.get('label')!r} is not permitted")


def check_ids(reqs, f):
    seen = defaultdict(int)
    for r in reqs:
        seen[r.get("requirement_id", "<no id>")] += 1
    for rid, n in seen.items():
        if n > 1:
            f.fail("C2-ids", rid, f"Duplicate requirement_id used {n} times.")


def check_traceability(r, corpus, f):
    rid = r.get("requirement_id", "<no id>")
    doc_id = r.get("source_document_id")
    doc = corpus.register.get(doc_id)
    if not doc:
        f.fail("G1-source", rid, f"source_document_id {doc_id!r} not in source register.")
        return
    p0, p1 = r.get("source_page_start"), r.get("source_page_end")
    npages = doc.get("page_count") or 0
    if not isinstance(p0, int) or not isinstance(p1, int) or p0 < 1 or p1 < p0:
        f.fail("G1-source", rid, f"Invalid page span {p0}-{p1}.")
        return
    if npages and p1 > npages:
        f.fail("G1-source", rid, f"Cited page {p1} exceeds document page count {npages}.")
        return
    if not (r.get("source_section") or "").strip():
        f.fail("G1-source", rid, "source_section is empty.")
    quote = r.get("source_quote") or ""
    if len(quote.strip()) < 15:
        f.fail("G1-source", rid, "source_quote is missing or too short to be evidence.")
        return
    span = corpus.span_text(doc_id, p0, p1)
    if not span.strip():
        f.warn("G1-source", rid, "No extracted text for cited pages.")
        return
    if norm(quote) in norm(span) or squash(quote) in squash(span):
        return
    ratio = best_ratio(squash(quote), squash(span))
    if ratio >= FUZZY_ACCEPT:
        f.warn("G1-source", rid, f"Quote is a near match ({ratio:.0%}) but not verbatim.")
    else:
        f.fail("G1-source", rid, f"Quote NOT found on cited page(s) {p0}-{p1} (best match {ratio:.0%}).")


def check_atomicity(r, f):
    rid = r.get("requirement_id", "<no id>")
    what = r.get("what") or ""
    if COMPOUND_PAT.search(what):
        f.warn("G2-atomicity", rid, "'what' reads as a compound obligation.")


def check_numeric_integrity(r, corpus, f):
    rid = r.get("requirement_id", "<no id>")
    quote = r.get("source_quote") or ""
    page = corpus.span_text(r.get("source_document_id"), r.get("source_page_start") or 1, r.get("source_page_end") or r.get("source_page_start") or 1)
    hay = quote + "\n" + page
    for nf in r.get("numeric_facts") or []:
        ver = nf.get("verbatim") or ""
        if ver and squash(ver) not in squash(hay) and digits(ver) not in digits(hay):
            f.fail("G3-numeric", rid, f"Numeric fact {ver!r} is not on the cited page or quote.")
        elif ver and squash(ver) not in squash(quote) and squash(ver) not in squash(page):
            f.fail("G3-numeric", rid, f"Numeric fact {ver!r} is not reconcilable to source.")


def check_clock_start(r, f):
    rid = r.get("requirement_id", "<no id>")
    qn = re.sub(r"\s+", " ", r.get("source_quote") or "").lower()
    surfaces = [r.get("what") or "", r.get("trigger") or ""]
    for ctrl in r.get("controls") or []:
        surfaces.append(ctrl.get("objective") or "")
    for text in surfaces:
        for m in CLOCK_START_PAT.finditer(text or ""):
            if m.group(0).lower() not in qn:
                f.warn("G4-not_specified", rid, f"Clock-start phrase {m.group(0)!r} is not in the source quote.")


def check_template_not_tat(r, f):
    rid = r.get("requirement_id", "<no id>")
    section = r.get("source_section") or ""
    if ANNEX_HINT.search(section) and r.get("deadline_value") is not None and r.get("requirement_type") != "disclosure_requirement":
        f.warn("G3-numeric", rid, "deadline_value on an annexure/template section is not an operational TAT.")


def check_not_specified_discipline(r, corpus, f):
    rid = r.get("requirement_id", "<no id>")
    page = corpus.span_text(r.get("source_document_id"), r.get("source_page_start") or 1, r.get("source_page_end") or r.get("source_page_start") or 1)
    quote = r.get("source_quote") or ""
    hay = norm(quote + " " + page)
    for field in ("accountable_role", "responsible_role"):
        val = (r.get(field) or "").strip()
        if val.lower() in FILLER_VALUES:
            f.fail("G4-not_specified", rid, f"{field}={val!r} is a filler; use not_specified.")
        if r.get("role_basis") == "explicit_source" and val and val != SENTINEL and norm(val) not in hay:
            f.fail("G4-not_specified", rid, f"{field} {val!r} claimed as explicit_source but absent from the page.")


def check_proposal_labelling(r, f):
    rid = r.get("requirement_id", "<no id>")
    for c in r.get("controls") or []:
        if c.get("label") not in CONTROL_LABELS:
            f.fail("G5-labels", rid, f"control {c.get('control_id')} has invalid label {c.get('label')!r}.")
        for e in c.get("evidence") or []:
            if e.get("label") not in EVIDENCE_LABELS:
                f.fail("G5-labels", rid, f"evidence {e.get('artefact')!r} has invalid label {e.get('label')!r}.")
        for t in c.get("test_procedure") or []:
            if t.get("label") not in TEST_LABELS:
                f.fail("G5-labels", rid, f"test step has invalid label {t.get('label')!r}.")


def check_legal_interpretation(r, f):
    rid = r.get("requirement_id", "<no id>")
    blob = " ".join(filter(None, [r.get("what"), r.get("why"), r.get("source_quote")]))
    if INTERPRETATION_PAT.search(blob or "") and r.get("evidence_class") != "REQUIRES-LEGAL-REVIEW":
        f.fail("G6-legal", rid, "Interpretation language must be routed to REQUIRES-LEGAL-REVIEW.")


def check_visual_reconciliation(r, corpus, f):
    rid = r.get("requirement_id", "<no id>")
    if not r.get("source_table_id"):
        return
    nums = [nf for nf in (r.get("numeric_facts") or []) if nf.get("kind") in ("money", "percentage", "duration", "threshold")]
    if not nums:
        return
    vr = r.get("visual_reconciliation") or {}
    if not vr.get("checked"):
        f.fail("G7-visual", rid, "Table-derived numeric fact without a checked page image.")


def check_approval_gates(r, f):
    rid = r.get("requirement_id", "<no id>")
    if r.get("status") != "approved":
        return
    gates = r.get("review_gates") or {}
    open_gates = [g for g, v in gates.items() if (v or {}).get("state", "open") == "open"]
    if open_gates or r.get("review_status") == "unreviewed":
        f.fail("G8-gates", rid, "status=approved with open gates or unreviewed status.")


def check_candidate_coverage(reqs, cands, f):
    cov = {"total": len(cands), "mapped": 0, "non_binding": 0, "queued": 0, "pending": 0}
    req_ids = {r.get("requirement_id") for r in reqs}
    for c in cands:
        disp = c.get("disposition") or "pending"
        cov[disp] = cov.get(disp, 0) + (1 if disp in cov else 0)
        if disp == "pending":
            cov["pending"] += 0 if "pending" in (c.get("disposition"),) else 1
        if disp == "pending":
            level = "FAIL" if c.get("extraction_priority") in ("critical", "high") else "WARN"
            (f.fail if level == "FAIL" else f.warn)("C1-coverage", c.get("candidate_id", "?"), f"Candidate left pending ({c.get('extraction_priority')}).")
        if disp == "mapped":
            for mid in c.get("mapped_requirement_ids") or []:
                if mid not in req_ids:
                    f.fail("C1-coverage", c.get("candidate_id", "?"), f"mapped to unknown {mid}")
    # recount properly
    cov = {"total": len(cands), "mapped": 0, "non_binding": 0, "queued": 0, "pending": 0}
    for c in cands:
        d = c.get("disposition") or "pending"
        if d == "mapped":
            cov["mapped"] += 1
        elif d == "non_binding":
            cov["non_binding"] += 1
        elif d == "queued_for_review":
            cov["queued"] += 1
        else:
            cov["pending"] += 1
    return cov


def check_recall_surfaces(reqs, corpus, f):
    quoted = " ".join((r.get("source_quote") or "") for r in reqs).lower()
    for doc_id, pages in corpus.pages.items():
        text = "\n".join(pages.values())
        for m in re.finditer(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", text, re.I):
            token = m.group(0)
            if token.lower() not in quoted:
                f.warn("C3-recall", doc_id, f"Published contact {token} appears in the source layer but in no requirement quote.")


def write_report(path, reqs, f, cov, corpus):
    by_check = defaultdict(list)
    for i in f.items:
        by_check[i["check"]].append(i)
    order = ["G1-source", "G2-atomicity", "G3-numeric", "G4-not_specified", "G5-labels", "G6-legal", "G7-visual", "G8-gates", "C1-coverage", "C2-schema", "C2-ids", "C2-xref", "C3-recall"]
    names = {
        "G1-source": "G1 Source traceability", "G2-atomicity": "G2 Atomicity",
        "G3-numeric": "G3 Numeric integrity", "G4-not_specified": "G4 not_specified discipline",
        "G5-labels": "G5 Proposal labelling", "G6-legal": "G6 Legal interpretation routing",
        "G7-visual": "G7 Visual source reconciliation", "G8-gates": "G8 Approval gates",
        "C1-coverage": "C1 Candidate coverage", "C2-schema": "C2 Schema validity",
        "C2-ids": "C2 ID uniqueness", "C2-xref": "C2 Cross-reference integrity",
        "C3-recall": "C3 Recall surfaces",
    }
    lines = ["# Stage 6 validation report", "", f"- Requirements checked: **{len(reqs)}**", f"- Blocking failures: **{len(f.failures)}**   Warnings: **{len(f.warnings)}**", "", "| Check | Failures | Warnings |", "|---|---:|---:|"]
    for key in order:
        items = by_check.get(key, [])
        fa = sum(1 for i in items if i["level"] == "FAIL")
        lines.append(f"| {names[key]} | {fa} | {len(items)-fa} |")
    for key in order:
        items = by_check.get(key, [])
        if not items:
            continue
        lines += ["", f"## {names[key]}", ""]
        for i in items:
            lines.append(f"- **{i['level']}** `{i['id']}` - {i['message']}")
    ratio = f"{cov.get('mapped',0)}/{cov.get('total',0)}" if cov.get("total") else "n/a"
    g3 = [i["id"] for i in f.items if i["check"] == "G3-numeric"]
    g4 = [i["id"] for i in f.items if i["check"] == "G4-not_specified"]
    c3 = [i["id"] for i in f.items if i["check"] == "C3-recall"]
    lines += ["", "---", "", "## Coverage ratio (not row count)", "", f"- Candidate disposition ratio: **{ratio}** mapped", f"- Requirement rows: {len(reqs)} \u2014 this number is **not** a quality metric.", f"- Open G3 (numeric / template-TAT) IDs: {', '.join(f'`{x}`' for x in g3) or 'none'}", f"- Open G4 (not_specified / clock-start) IDs: {', '.join(f'`{x}`' for x in g4) or 'none'}", f"- Open C3 (recall surface) IDs: {', '.join(f'`{x}`' for x in c3) or 'none'}", ""]
    if f.failures:
        lines.append("**Result: BLOCKED.**")
    elif f.warnings:
        lines.append("**Result: PASSED WITH WARNINGS.**")
    else:
        lines.append("**Result: PASSED.**")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 6 validator")
    ap.add_argument("--kb", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if assert_live is not None:
        assert_live()
    kb = Path(args.kb)
    corpus = Corpus(kb)
    reqs = load_requirements(kb)
    cands = load_candidates(kb)
    f = Findings()
    check_schema(reqs, f)
    check_ids(reqs, f)
    for r in reqs:
        check_traceability(r, corpus, f)
        check_atomicity(r, f)
        check_numeric_integrity(r, corpus, f)
        check_clock_start(r, f)
        check_template_not_tat(r, f)
        check_not_specified_discipline(r, corpus, f)
        check_proposal_labelling(r, f)
        check_legal_interpretation(r, f)
        check_visual_reconciliation(r, corpus, f)
        check_approval_gates(r, f)
    cov = check_candidate_coverage(reqs, cands, f)
    check_recall_surfaces(reqs, corpus, f)
    report = Path(args.report) if args.report else kb / "05-quality-assurance" / "validation-report.md"
    write_report(report, reqs, f, cov, corpus)
    if not args.quiet:
        for i in f.failures[:60]:
            print(f"FAIL [{i['check']}] {i['id']}: {i['message']}")
        print(f"\n{len(reqs)} requirements | {cov['total']} candidates ({cov['pending']} pending) | {len(f.failures)} failures | {len(f.warnings)} warnings")
        print(f"Report: {report}")
    if f.failures:
        return 1
    return 2 if f.warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
