#!/usr/bin/env python3
"""Self-test harness for the policy-extractor skill.

Builds a synthetic knowledge base in a temporary directory, seeds it with one
correct requirement and one deliberate violation of each guardrail, then asserts
that validate_pack.py catches exactly the guardrails it should.

    python3 scripts/run_regression_tests.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent

PAGE_1 = (
    "CUSTOMER GRIEVANCE REDRESSAL POLICY\n"
    "1. Complaint intake\n"
    "The Bank shall record every complaint received in the CRM and assign it to the "
    "respective group for resolution.\n"
    "The Nodal Officer shall monitor complaint ageing on a monthly basis.\n"
)
PAGE_2 = (
    "2. Resolution of complaints\n"
    "Complaints relating to fraud cases or old records shall be resolved within 30 "
    "working days of receipt.\n"
    "Compensation for delayed resolution shall not exceed Rs. 5,000 per complaint.\n"
    "3. Reporting\n"
    "A quarterly report shall be placed before the Customer Service Committee of the Board.\n"
)


def base_record(rid: str, **over) -> dict:
    rec = {
        "requirement_id": rid,
        "policy_name": "Customer Grievance Redressal Policy",
        "policy_approval_or_effective_date": "not_specified",
        "source_document_id": "SRC-0001",
        "source_file": "grievance.pdf",
        "source_page_start": 2,
        "source_page_end": 2,
        "source_section": "Resolution of complaints",
        "source_quote": "Complaints relating to fraud cases or old records shall be resolved within 30 working days of receipt.",
        "requirement_type": "policy_obligation",
        "normative_strength": "shall",
        "obligation_bearer": "organisation",
        "what": "Resolve fraud and old-record complaints within the stated turnaround time.",
        "why": None,
        "why_basis": "not_specified",
        "accountable_role": "not_specified",
        "responsible_role": "not_specified",
        "consulted_roles": [],
        "assurance_roles": [],
        "role_basis": "not_specified",
        "trigger": "Receipt of a fraud or old-record complaint",
        "frequency": "per complaint",
        "deadline_value": 30,
        "deadline_unit": "day",
        "deadline_basis": "working_day",
        "deadline_verbatim": "within 30 working days of receipt",
        "process_steps": [],
        "mandatory_evidence": [],
        "exceptions_conditions": [],
        "cited_regulations": [],
        "cross_policy_references": [],
        "numeric_facts": [{"kind": "duration", "verbatim": "30 working days", "value": 30, "unit": "working_day", "context": "resolution TAT"}],
        "evidence_class": "SOURCE-EXPLICIT",
        "controls": [],
        "visual_reconciliation": None,
        "candidate_ids": [],
        "extraction_confidence": "high",
        "review_status": "unreviewed",
        "reviewer_notes": None,
        "open_questions": [],
        "review_gates": {"source_fidelity": {"state": "open"}, "policy_meaning": {"state": "open"}},
        "status": "draft",
    }
    rec.update(over)
    return rec


def build_kb(kb: Path) -> None:
    for sub in ["01-source-layer/SRC-0001", "02-candidates", "02-requirements", "04-cross-policy-analysis", "05-quality-assurance"]:
        (kb / sub).mkdir(parents=True, exist_ok=True)
    (kb / "source-register.json").write_text(json.dumps([{
        "document_id": "SRC-0001", "short_code": "GRV", "slug": "grievance-redressal",
        "file_name": "grievance.pdf", "original_path": str(kb / "grievance.pdf"),
        "sha256": "0" * 64, "bytes": 1, "title": "Customer Grievance Redressal Policy",
        "document_type_hint": "policy", "approval_or_effective_date_hint": "not_specified",
        "page_count": 2, "detected_table_count": 1, "text_quality": "native_text_with_tables",
        "low_text_pages": [], "processing_path": "text_primary_with_table_render",
        "parse_error": None, "original_file_retained": True, "registered_at_utc": "2026-01-01T00:00:00+00:00",
    }], indent=2), encoding="utf-8")
    (kb / "01-source-layer/SRC-0001/pages.json").write_text(json.dumps({"1": PAGE_1, "2": PAGE_2}, indent=2), encoding="utf-8")
    (kb / "02-candidates/SRC-0001-candidates.json").write_text(json.dumps({
        "source_document_id": "SRC-0001", "short_code": "GRV", "source_file": "grievance.pdf",
        "page_count": 2, "candidate_count": 2,
        "by_priority": {"critical": 1, "high": 1, "medium": 0, "low": 0},
        "table_cell_candidates": 0,
        "candidates": [
            {"candidate_id": "GRV-CAN-00001", "source_document_id": "SRC-0001", "source_file": "grievance.pdf",
             "source_page": 2, "source_section": "Resolution of complaints", "origin": "sentence", "source_table_id": None,
             "exact_text": "Complaints relating to fraud cases or old records shall be resolved within 30 working days of receipt.",
             "trigger_terms": ["shall", "within"], "numeric_facts": [], "cited_regulations": [],
             "candidate_type": "deadline_and_escalation", "extraction_priority": "critical",
             "disposition": "pending", "mapped_requirement_ids": [], "disposition_reason": None},
            {"candidate_id": "GRV-CAN-00002", "source_document_id": "SRC-0001", "source_file": "grievance.pdf",
             "source_page": 1, "source_section": "Complaint intake", "origin": "sentence", "source_table_id": None,
             "exact_text": "The Nodal Officer shall monitor complaint ageing on a monthly basis.",
             "trigger_terms": ["shall", "monitor"], "numeric_facts": [], "cited_regulations": [],
             "candidate_type": "governance_or_reporting", "extraction_priority": "high",
             "disposition": "pending", "mapped_requirement_ids": [], "disposition_reason": None},
        ],
    }, indent=2), encoding="utf-8")


CASES: list[tuple[str, dict, set[str], str]] = [
    ("clean record passes", base_record("GRV-R-001", candidate_ids=["GRV-CAN-00001"]), set(), "clean sourced record"),
    ("G1 fabricated quote", base_record("GRV-R-002", candidate_ids=["GRV-CAN-00001"], source_quote="The Bank shall appoint an Internal Ombudsman for all complaints rejected in full or in part."), {"G1-source"}, "fabricated quote"),
    ("G1 page out of range", base_record("GRV-R-003", candidate_ids=["GRV-CAN-00001"], source_page_start=9, source_page_end=9), {"G1-source"}, "page out of range"),
    ("G3 numeric drift", base_record("GRV-R-004", candidate_ids=["GRV-CAN-00001"], numeric_facts=[{"kind": "duration", "verbatim": "45 working days", "value": 45, "unit": "working_day", "context": "TAT"}]), {"G3-numeric"}, "numeric drift"),
    ("G3 money restated", base_record("GRV-R-005", candidate_ids=["GRV-CAN-00001"], what="Cap compensation at 5000 rupees.", numeric_facts=[{"kind": "money", "verbatim": "Rs. 6,000", "value": 6000, "unit": None, "currency": "INR", "context": "cap"}]), {"G3-numeric"}, "money restated"),
    ("G4 invented owner", base_record("GRV-R-006", candidate_ids=["GRV-CAN-00001"], accountable_role="Chief Compliance Officer", responsible_role="Grievance Redressal Cell", role_basis="explicit_source"), {"G4-not_specified"}, "invented owner"),
    ("G4 filler value", base_record("GRV-R-007", candidate_ids=["GRV-CAN-00001"], accountable_role="TBD", role_basis="operational_inference"), {"G4-not_specified"}, "TBD filler"),
    ("G5 unlabelled control", base_record("GRV-R-008", candidate_ids=["GRV-CAN-00001"], controls=[{"control_id": "CTRL-GRV-001", "label": "SOURCE-EXPLICIT", "objective": "Monitor ageing.", "control_type": "detective", "frequency": "monthly", "performer": "not_specified", "evidence": [{"artefact": "Ageing report", "label": "SOURCE-EXPLICIT"}], "test_procedure": []}]), set(), "valid labels warn only"),
    ("G5 invalid label", base_record("GRV-R-009", candidate_ids=["GRV-CAN-00001"], controls=[{"control_id": "CTRL-GRV-002", "label": "PROPOSED-CONTROL", "objective": "Detect TAT breaches.", "control_type": "detective", "frequency": "monthly", "performer": "not_specified", "evidence": [{"artefact": "Ageing report", "label": "SUGGESTED"}], "test_procedure": [{"step": "Recompute elapsed working days.", "label": "PROPOSED-TEST"}]}]), {"C2-schema", "G5-labels"}, "bad evidence label"),
    ("G6 legal conclusion", base_record("GRV-R-010", candidate_ids=["GRV-CAN-00001"], what="Resolve fraud complaints within 30 working days; this complies with the applicable regulatory turnaround requirement."), {"G6-legal"}, "legal interpretation"),
    ("G7 table numerics", base_record("GRV-R-011", candidate_ids=["GRV-CAN-00001"], source_table_id="T002-1", numeric_facts=[{"kind": "money", "verbatim": "Rs. 5,000", "value": 5000, "unit": None, "currency": "INR", "context": "cap"}]), {"G7-visual"}, "unchecked table money"),
    ("G8 approved without gates", base_record("GRV-R-012", candidate_ids=["GRV-CAN-00001"], status="approved"), {"G8-gates"}, "approved with open gates"),
    ("G2 compound obligation", base_record("GRV-R-013", candidate_ids=["GRV-CAN-00001"], what="Resolve fraud complaints within the stated TAT and report the results to the Committee and maintain an ageing register."), set(), "compound warns"),
]


def run_validator(kb: Path) -> tuple[int, list[dict]]:
    proc = subprocess.run([sys.executable, str(HERE / "validate_pack.py"), "--kb", str(kb), "--quiet"], capture_output=True, text=True)
    report = (kb / "05-quality-assurance" / "validation-report.md")
    findings = []
    if report.exists():
        for line in report.read_text(encoding="utf-8").splitlines():
            if line.startswith("- **FAIL** `") or line.startswith("- **WARN** `"):
                level = "FAIL" if "**FAIL**" in line else "WARN"
                rid = line.split("`")[1]
                findings.append({"level": level, "id": rid, "line": line})
    return proc.returncode, findings


def case_checks(kb: Path, rid: str) -> tuple[set[str], set[str]]:
    report = (kb / "05-quality-assurance" / "validation-report.md").read_text(encoding="utf-8")
    fails, warns, current = set(), set(), None
    heading_to_key = {
        "G1 Source traceability": "G1-source", "G2 Atomicity": "G2-atomicity",
        "G3 Numeric integrity": "G3-numeric", "G4 not_specified discipline": "G4-not_specified",
        "G5 Proposal labelling": "G5-labels", "G6 Legal interpretation routing": "G6-legal",
        "G7 Visual source reconciliation": "G7-visual", "G8 Approval gates": "G8-gates",
        "C1 Candidate coverage": "C1-coverage", "C2 Schema validity": "C2-schema",
        "C2 ID uniqueness": "C2-ids", "C2 Cross-reference integrity": "C2-xref",
        "C3 Recall surfaces": "C3-recall",
    }
    for line in report.splitlines():
        if line.startswith("## "):
            current = heading_to_key.get(line[3:].strip())
        elif current and line.startswith("- **") and f"`{rid}`" in line:
            (fails if "**FAIL**" in line else warns).add(current)
    return fails, warns


def structural_checks(results: list[tuple[bool, str]]) -> None:
    required = {
        "SKILL.md": SKILL / "SKILL.md",
        "schema": SKILL / "schemas" / "policy-requirement.schema.json",
        "extraction prompt": SKILL / "prompts" / "extraction.md",
        "verification prompt": SKILL / "prompts" / "verification.md",
        "cross-policy prompt": SKILL / "prompts" / "cross-policy-analysis.md",
        "stage specs": SKILL / "references" / "stage-specs.md",
        "schema reference": SKILL / "references" / "schema-and-labels.md",
        "control design reference": SKILL / "references" / "control-and-evidence-design.md",
        "cross-doc reference": SKILL / "references" / "cross-document-analysis.md",
        "review gates reference": SKILL / "references" / "review-gates-and-failure-modes.md",
        "atomicity and recall reference": SKILL / "references" / "atomicity-and-recall.md",
        "gold pack policy": SKILL / "references" / "gold-pack-policy.md",
        "VERSION pin": SKILL / "VERSION",
        "RELEASE_PIN": SKILL / "RELEASE_PIN.json",
        "pack template": SKILL / "assets" / "compliance-pack.md",
        "record template": SKILL / "assets" / "requirement-record.template.json",
    }
    for name, p in required.items():
        results.append((p.exists(), f"structure: {name} present"))
    for script in ["intake_register.py", "build_source_layer.py", "find_candidates.py", "validate_pack.py", "cross_document_analysis.py", "build_packs.py", "assert_live_version.py", "stage3_preflight.py", "smoke_live_skill.py"]:
        p = HERE / script
        ok = p.exists()
        if ok:
            r = subprocess.run([sys.executable, "-c", f"import ast,sys;ast.parse(open({str(p)!r}).read())"], capture_output=True, text=True)
            ok = r.returncode == 0
        results.append((ok, f"structure: {script} parses"))
    body = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    fm = body.split("---")[1] if body.startswith("---") else ""
    results.append(("name: policy-extractor" in fm, "frontmatter: name present"))
    results.append(("1.2.0" in fm or 'version: "1.2.0"' in body, "frontmatter: version is 1.2.0"))
    results.append(((SKILL / "VERSION").read_text(encoding="utf-8").strip() == "1.2.0", "VERSION file pins 1.2.0"))
    results.append(("description:" in fm, "frontmatter: description present"))
    results.append((len(fm) > 400, "frontmatter: description is substantive"))
    results.append((len(body.splitlines()) < 520, "SKILL.md under ~500 lines"))
    for g in ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]:
        results.append((f"| {g} |" in body, f"SKILL.md documents guardrail {g}"))
    results.append(("atomicity-and-recall.md" in body, "SKILL.md points at atomicity-and-recall.md"))
    extract = (SKILL / "prompts" / "extraction.md").read_text(encoding="utf-8")
    for token in ["independently testable verbs", "clock start", "source_page_end", "disclosure_requirement", "function list"]:
        results.append((token.lower() in extract.lower(), f"extraction prompt encodes {token}"))


def candidate_sweep_check(results: list[tuple[bool, str]]) -> None:
    sys.path.insert(0, str(HERE))
    try:
        import find_candidates as fc
    except Exception as exc:  # noqa: BLE001
        results.append((False, f"candidate sweep importable ({exc})"))
        return
    probes = [
        ("The Bank shall resolve the complaint within 30 working days.", "binding"),
        ("The Bank shall resolve the complaint within 30 working days.", "timing"),
        ("Compensation shall not exceed Rs. 5,000 per instance.", "numeric"),
        ("A quarterly report shall be placed before the Board committee.", "governance"),
        ("Provided that this clause shall not apply to corporate customers.", "conditional"),
        ("Escalate to pno@example.com or https://cms.rbi.org.in.", "contact"),
        ("The Bank has constituted the Branch Level Customer Service Committee.", "forum"),
    ]
    for text, flag in probes:
        info = fc.classify(text)
        results.append((info["flags"][flag], f"candidate sweep detects {flag} language"))
    nums = fc.numeric_hits("Rs. 5,000 within 30 working days at 2% per annum")
    kinds = {n["kind"] for n in nums}
    results.append(({"money", "duration", "percentage"} <= kinds, "candidate sweep extracts money, duration and percentage"))
    multi = fc.classify("The branches shall acknowledge the complaints, update the customers and display the escalation matrix on the notice board.")
    results.append((multi["flags"]["multi_verb"], "candidate sweep flags coordinated multi-verb sentences"))
    pages = {8: "Salient features of RBIO scheme are being displayed in prominent locations in", 9: "9\nbranches and websites\n3. Forums to review customer grievances"}
    units = fc.stitch_page_units(pages)
    joined = [u for u in units if u["origin"] == "page_span_sentence"]
    results.append((any("branches and websites" in u["text"] and u["page_start"] == 8 and u["page_end"] == 9 for u in joined), "candidate sweep stitches page-break sentences"))


def main() -> int:
    results: list[tuple[bool, str]] = []
    structural_checks(results)
    candidate_sweep_check(results)
    with tempfile.TemporaryDirectory() as tmp:
        kb = Path(tmp) / "kb"
        build_kb(kb)
        for name, record, expected_fails, rationale in CASES:
            (kb / "02-requirements" / "requirements.json").write_text(json.dumps([record], indent=2), encoding="utf-8")
            run_validator(kb)
            fails, _warns = case_checks(kb, record["requirement_id"])
            if expected_fails:
                missing = expected_fails - fails
                results.append((not missing, f"{name}: fires {sorted(expected_fails)}" + (f" (missing {sorted(missing)})" if missing else "")))
            else:
                results.append((not fails, f"{name}: no blocking failures" + (f" (got {sorted(fails)})" if fails else "")))
        clock = base_record("GRV-R-020", candidate_ids=["GRV-CAN-00001"], what="Communicate the final decision within 30 days from the decision date.", controls=[{"control_id": "CTRL-GRV-020", "label": "PROPOSED-CONTROL", "objective": "No IO decision is communicated beyond 30 days from the decision date.", "control_type": "detective", "frequency": "monthly", "performer": "not_specified", "automation": "it_dependent_manual"}])
        (kb / "02-requirements" / "requirements.json").write_text(json.dumps([clock], indent=2), encoding="utf-8")
        run_validator(kb)
        _fails, warns = case_checks(kb, "GRV-R-020")
        results.append(("G4-not_specified" in warns, "clock-start invention in a control objective warns G4"))
        tmpl = base_record("GRV-R-021", candidate_ids=["GRV-CAN-00001"], source_section="Annexure 1, Part B - disclosure template", requirement_type="policy_obligation", deadline_value=30, what="Disclose complaints pending beyond 30 days in Annexure 1 Part B.")
        (kb / "02-requirements" / "requirements.json").write_text(json.dumps([tmpl], indent=2), encoding="utf-8")
        run_validator(kb)
        _fails, warns = case_checks(kb, "GRV-R-021")
        results.append(("G3-numeric" in warns, "annexure template deadline_value warns it is not an operational TAT"))
        (kb / "02-requirements" / "requirements.json").write_text(json.dumps([base_record("GRV-R-001")], indent=2), encoding="utf-8")
        code, _ = run_validator(kb)
        report = (kb / "05-quality-assurance" / "validation-report.md").read_text(encoding="utf-8")
        results.append(("GRV-CAN-00001" in report and code == 1, "C1: an undispositioned critical candidate blocks the run"))
        led_path = kb / "02-candidates" / "SRC-0001-candidates.json"
        led = json.loads(led_path.read_text(encoding="utf-8"))
        led["candidates"][0].update({"disposition": "mapped", "mapped_requirement_ids": ["GRV-R-001"]})
        led["candidates"][1].update({"disposition": "non_binding", "disposition_reason": "Monitoring duty captured by GRV-R-001."})
        led_path.write_text(json.dumps(led, indent=2), encoding="utf-8")
        (kb / "02-requirements" / "requirements.json").write_text(json.dumps([base_record("GRV-R-001", candidate_ids=["GRV-CAN-00001"])], indent=2), encoding="utf-8")
        code, findings = run_validator(kb)
        results.append((code in (0, 2) and not [f for f in findings if f["level"] == "FAIL"], f"end-to-end: fully dispositioned clean register passes (exit {code})"))
        bad = base_record("GRV-R-014", candidate_ids=["GRV-CAN-00001"], source_quote="")
        bad["source_section"] = ""
        (kb / "02-requirements" / "requirements.json").write_text(json.dumps([bad], indent=2), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(HERE / "build_packs.py"), "--kb", str(kb)], capture_output=True, text=True)
        results.append((proc.returncode == 1 and "REFUSED" in proc.stdout, "publisher refuses to publish an uncited requirement"))
        (kb / "02-requirements" / "requirements.json").write_text(json.dumps([base_record("GRV-R-001", candidate_ids=["GRV-CAN-00001"])], indent=2), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(HERE / "build_packs.py"), "--kb", str(kb)], capture_output=True, text=True)
        pack = kb / "03-policy-compliance-packs" / "grievance-redressal.md"
        ok = proc.returncode == 0 and pack.exists() and "DRAFT - NOT APPROVED" in pack.read_text(encoding="utf-8")
        results.append((ok, "publisher emits a DRAFT-stamped compliance pack"))
        proc = subprocess.run([sys.executable, str(HERE / "cross_document_analysis.py"), "--kb", str(kb)], capture_output=True, text=True)
        results.append((proc.returncode == 0, "cross-document analysis runs on a single-document corpus"))
    passed = sum(1 for ok, _ in results if ok)
    for ok, label in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
