#!/usr/bin/env python3
"""Stage 7 - Publish compliance packs, enterprise views and machine-readable exports.

Rendering is deterministic and refuses to publish anything the validator would
reject as uncited. Everything published while a review gate is open is stamped DRAFT.

Usage:
    python3 build_packs.py --kb ./kb
    python3 build_packs.py --kb ./kb --allow-uncited
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
    flag = " !" if (conf == "low" or r.get("evidence_class") == "REQUIRES-LEGAL-REVIEW") else ""
    return esc(f"{st}/{rs}/{conf}") + flag


def table(headers, rows) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(rows_i) + " |" for rows_i in rows]
    return out


def banner(reqs: list[dict]) -> str:
    return APPROVED_BANNER if reqs and all(r.get("status") == "approved" for r in reqs) else DRAFT_BANNER


def honesty_block(kb: Path, reqs: list[dict]) -> list[str]:
    report = kb / "05-quality-assurance" / "validation-report.md"
    g3, g4, c3 = [], [], []
    ratio = "not_run"
    if report.exists():
        text = report.read_text(encoding="utf-8")
        m = re.search(r"Candidate disposition ratio: \*\*([^*]+)\*\*", text)
        if m:
            ratio = m.group(1).strip()
        section = None
        for line in text.splitlines():
            if line.startswith("## "):
                section = line[3:].strip()
            elif line.startswith("- **") and "`" in line:
                rid = line.split("`")[1]
                if section and "G3" in section:
                    g3.append(rid)
                elif section and "G4" in section:
                    g4.append(rid)
                elif section and "C3" in section:
                    c3.append(rid)
            elif "Candidate disposition ratio:" in line and "**" in line:
                ratio = line.split("**")[1]
    cand_files = list((kb / "02-candidates").glob("*-candidates.json"))
    cand_n = mapped_n = 0
    if cand_files:
        for fp in cand_files:
            led = json.loads(fp.read_text(encoding="utf-8"))
            for c in led.get("candidates") or []:
                cand_n += 1
                if c.get("disposition") == "mapped":
                    mapped_n += 1
        if ratio == "not_run" and cand_n:
            ratio = f"{mapped_n}/{cand_n}"
    version = read_version(HERE.parent)
    return [
        "## 8b. Honesty and coverage", "",
        f"- Skill version on this run: **{version}**",
        f"- Candidate disposition ratio: **{ratio}**. Requirement row count ({len(reqs)}) is not a quality metric.",
        f"- Open G3 (numeric / template-TAT) IDs: {', '.join(f'`{x}`' for x in dict.fromkeys(g3)) or 'none'}",
        f"- Open G4 (not_specified / clock-start) IDs: {', '.join(f'`{x}`' for x in dict.fromkeys(g4)) or 'none'}",
        f"- Open C3 (recall surface) IDs: {', '.join(f'`{x}`' for x in dict.fromkeys(c3)) or 'none'}",
        "- This pack is `DRAFT` while any review gate is open. Do not describe it as complete or audit-ready.",
        "- No historical client pack is a gold file for this skill. See `references/gold-pack-policy.md`.",
        "",
    ]


def build_pack(kb: Path, doc: dict, reqs: list[dict]) -> Path:
    slug = doc.get("slug") or doc["document_id"].lower()
    out = kb / "03-policy-compliance-packs" / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    L = [f"# Compliance pack - {doc.get('title') or doc['file_name']}", "", banner(reqs), "",
         "## 1. Document identity", "",
         f"- Document ID: `{doc['document_id']}`",
         f"- Source file: `{doc['file_name']}`",
         f"- SHA-256: `{doc['sha256']}`",
         f"- Pages: {doc['page_count']} | Tables detected: {doc.get('detected_table_count', 0)}",
         f"- Requirements extracted: **{len(reqs)}**", "",
         "## 2. Requirement register", "",
         "Every row is traceable to the page and sentence named in the Source column.", ""]
    rows = [[esc(r.get("requirement_id")), esc(r.get("what")), who(r), when(r), esc(src(r)), status_cell(r)] for r in reqs]
    L += table(["ID", "What", "Who (A/R)", "When", "Source", "Status"], rows) if rows else ["_No requirements extracted._"]
    L += ["", "## 3. Verbatim source evidence", ""]
    for r in reqs:
        L += [f"**{r.get('requirement_id')}** \u2014 {esc(src(r))}", "", f"> {(r.get('source_quote') or '').strip()}", ""]
    L += honesty_block(kb, reqs)
    L += ["## 9. Approval block", "",
          "| Gate | Reviewer | Decision | Date | Signature |", "|---|---|---|---|---|",
          "| Source fidelity (document analyst) |  |  |  |  |",
          "| Policy meaning (policy / business owner) |  |  |  |  |",
          "This pack is not approved for operational use until every applicable row above is signed.", ""]
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def build_enterprise_views(kb: Path, register: list[dict], reqs: list[dict]) -> None:
    ev = kb / "04-enterprise-views"
    ev.mkdir(parents=True, exist_ok=True)
    doc_by_id = {d["document_id"]: d for d in register}
    rows = [[esc(r.get("requirement_id")), esc((doc_by_id.get(r.get("source_document_id"), {})).get("title") or r.get("policy_name")), esc(r.get("what")), who(r), when(r), esc(src(r)), status_cell(r)] for r in reqs]
    body = ["# Master compliance requirement register", "", banner(reqs), "", f"{len(reqs)} requirements across {len(register)} documents.", ""]
    body += table(["ID", "Policy", "What", "Who (A/R)", "When", "Source", "Status"], rows)
    (ev / "master-compliance-requirement-register.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    rows = []
    for r in reqs:
        for c in r.get("controls") or []:
            rows.append([esc(c.get("control_id")), "`" + str(c.get("label")) + "`", esc(r.get("requirement_id")), esc(c.get("objective")), esc(src(r))])
    body = ["# Master control matrix", "", banner(reqs), ""]
    body += table(["Control", "Label", "Requirement", "Objective", "Source"], rows) if rows else ["_No controls recorded._"]
    (ev / "master-control-matrix.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    (ev / "RACI.md").write_text("# Organisation-wide RACI\n\n" + banner(reqs) + "\n", encoding="utf-8")
    (ev / "deadlines-thresholds-and-liability-register.md").write_text("# Deadlines, thresholds and liability register\n\n" + banner(reqs) + "\n", encoding="utf-8")
    (ev / "regulatory-obligation-register.md").write_text("# Regulatory obligation register\n\n" + banner(reqs) + "\n", encoding="utf-8")
    (ev / "source-evidence-register.md").write_text("# Source evidence register\n\n" + banner(reqs) + "\n", encoding="utf-8")


def export_machine_readable(kb: Path, reqs: list[dict]) -> None:
    out = kb / "02-requirements"
    out.mkdir(parents=True, exist_ok=True)
    if not reqs:
        return
    flat = []
    for r in reqs:
        row = {k: v for k, v in r.items() if not isinstance(v, (list, dict))}
        row["candidate_ids"] = " || ".join(r.get("candidate_ids") or [])
        flat.append(row)
    fields = sorted({k for row in flat for k in row})
    with (out / "requirements.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in flat:
            w.writerow(row)
    md = ["# Requirement register (all documents)", "", banner(reqs), ""]
    md += table(["ID", "What", "Who (A/R)", "When", "Source", "Status"], [[esc(r.get("requirement_id")), esc(r.get("what")), who(r), when(r), esc(src(r)), status_cell(r)] for r in reqs])
    (out / "requirements.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def write_readme(kb: Path, register: list[dict], reqs: list[dict]) -> None:
    L = ["# Policy compliance knowledge base", "", banner(reqs), "", f"Built {date.today().isoformat()} with the `policy-extractor` skill.", ""]
    (kb / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    ch = kb / "CHANGELOG.md"
    entry = f"- {date.today().isoformat()}: published {len(reqs)} requirements from {len(register)} documents.\n"
    ch.write_text((ch.read_text(encoding="utf-8") if ch.exists() else "# Changelog\n\n") + entry, encoding="utf-8")


def write_approval_log(kb: Path, reqs: list[dict]) -> None:
    qa = kb / "05-quality-assurance"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "review-and-approval-log.md").write_text("# Review and approval log\n\n" + banner(reqs) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 7 publisher")
    ap.add_argument("--kb", required=True)
    ap.add_argument("--allow-uncited", action="store_true")
    args = ap.parse_args()
    if assert_live is not None:
        assert_live()
    kb = Path(args.kb)
    register, reqs = load(kb)
    uncited = [r.get("requirement_id", "<no id>") for r in reqs if not cited(r)]
    if uncited and not args.allow_uncited:
        print("REFUSED: the following requirements lack a complete citation (file, page, section, verbatim quote):")
        for rid in uncited[:40]:
            print(f"  - {rid}")
        print("\nFix them, or re-run with --allow-uncited to publish a stamped emergency draft.")
        return 1
    if uncited:
        for r in reqs:
            if not cited(r):
                r["what"] = "UNCITED - DO NOT RELY: " + str(r.get("what", ""))
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for r in reqs:
        by_doc[r.get("source_document_id", "?")].append(r)
    for doc in register:
        p = build_pack(kb, doc, by_doc.get(doc["document_id"], []))
        print(f"  pack: {p.relative_to(kb)} ({len(by_doc.get(doc['document_id'], []))} requirements)")
    build_enterprise_views(kb, register, reqs)
    export_machine_readable(kb, reqs)
    write_approval_log(kb, reqs)
    write_readme(kb, register, reqs)
    print(f"\nPublished {len(reqs)} requirements from {len(register)} documents into {kb}")
    if any(r.get("status") != "approved" for r in reqs):
        print("Everything is stamped DRAFT - review gates are open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
