#!/usr/bin/env python3
"""Self-test harness for the policy-extractor skill.

Builds a synthetic knowledge base in a temporary directory, seeds it with one
correct requirement and one deliberate violation of each guardrail, then asserts
that validate_pack.py catches exactly the guardrails it should - and that the
correct record produces no failures.

A guardrail that cannot be demonstrated to fire is not a guardrail. Run this after
any edit to the skill:

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
        "source_quote": "Complaints relating to fraud cases or old records shall be "
                        "resolved within 30 working days of receipt.",
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
        "numeric_facts": [
            {"kind": "duration", "verbatim": "30 working days", "value": 30,
             "unit": "working_day", "context": "resolution TAT"}
        ],
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
    for sub in ["01-source-layer/SRC-0001", "02-candidates", "02-requirements",
                "04-cross-policy-analysis", "05-quality-assurance"]:
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
    (kb / "01-source-layer/SRC-0001/pages.json").write_text(
        json.dumps({"1": PAGE_1, "2": PAGE_2}, indent=2), encoding="utf-8")
    (kb / "02-candidates/SRC-0001-candidates.json").write_text(json.dumps({
        "source_document_id": "SRC-0001", "short_code": "GRV", "source_file": "grievance.pdf",
        "page_count": 2, "candidate_count": 2,
        "by_priority": {"critical": 1, "high": 1, "medium": 0, "low": 0},
        "table_cell_candidates": 0,
        "candidates": [
            {"candidate_id": "GRV-CAN-00001", "source_document_id": "SRC-0001",
             "source_file": "grievance.pdf", "source_page": 2,
             "source_section": "Resolution of complaints", "origin": "sentence",
             "source_table_id": None,
             "exact_text": "Complaints relating to fraud cases or old records shall be resolved "
                           "within 30 working days of receipt.",
             "trigger_terms": ["shall", "within"], "numeric_facts": [], "cited_regulations": [],
             "candidate_type": "deadline_and_escalation", "extraction_priority": "critical",
             "disposition": "pending", "mapped_requirement_ids": [], "disposition_reason": None},
            {"candidate_id": "GRV-CAN-00002", "source_document_id": "SRC-0001",
             "source_file": "grievance.pdf", "source_page": 1,
             "source_section": "Complaint intake", "origin": "sentence", "source_table_id": None,
             "exact_text": "The Nodal Officer shall monitor complaint ageing on a monthly basis.",
             "trigger_terms": ["shall", "monitor"], "numeric_facts": [], "cited_regulations": [],
             "candidate_type": "governance_or_reporting", "extraction_priority": "high",
             "disposition": "pending", "mapped_requirement_ids": [], "disposition_reason": None},
        ],
    }, indent=2), encoding="utf-8")


CASES: list[tuple[str, dict, set[str], str]] = [
    ("clean record passes", base_record("GRV-R-001", candidate_ids=["GRV-CAN-00001"]), set(),
     "A correctly cited, atomic, sourced record must produce no failures."),
    ("G1 fabricated quote", base_record("GRV-R-002", candidate_ids=["GRV-CAN-00001"],
        source_quote="The Bank shall appoint an Internal Ombudsman for all complaints rejected in full or in part."),
     {"G1-source"}, "A quote that is not on the cited page must fail traceability."),
    ("G1 page out of range", base_record("GRV-R-003", candidate_ids=["GRV-CAN-00001"],
        source_page_start=9, source_page_end=9), {"G1-source"}, "A page beyond the document page count must fail."),
    ("G3 numeric drift", base_record("GRV-R-004", candidate_ids=["GRV-CAN-00001"],
        numeric_facts=[{"kind": "duration", "verbatim": "45 working days", "value": 45, "unit": "working_day", "context": "TAT"}]),
     {"G3-numeric"}, "A numeric value not present in the source must fail reconciliation."),
    ("G3 money restated", base_record("GRV-R-005", candidate_ids=["GRV-CAN-00001"],
        what="Cap compensation for delayed resolution at 5000 rupees per complaint.",
        numeric_facts=[{"kind": "money", "verbatim": "Rs. 6,000", "value": 6000, "unit": None, "currency": "INR", "context": "cap"}]),
     {"G3-numeric"}, "A money value the page does not carry must fail even when it looks plausible."),
    ("G4 invented owner claimed as sourced", base_record("GRV-R-006", candidate_ids=["GRV-CAN-00001"],
        accountable_role="Chief Compliance Officer", responsible_role="Grievance Redressal Cell",
        role_basis="explicit_source"), {"G4-not_specified"}, "A role claimed as explicit but absent from the page must fail."),
    ("G4 filler value", base_record("GRV-R-007", candidate_ids=["GRV-CAN-00001"],
        accountable_role="TBD", role_basis="operational_inference"), {"G4-not_specified"},
     "Filler values like TBD must fail; not_specified is the required sentinel."),
    ("G5 unlabelled control", base_record("GRV-R-008", candidate_ids=["GRV-CAN-00001"], controls=[{
        "control_id": "CTRL-GRV-001", "label": "SOURCE-EXPLICIT",
        "objective": "Monitor complaint ageing against the stated TAT.",
        "control_type": "detective", "frequency": "monthly", "performer": "not_specified",
        "evidence": [{"artefact": "Ageing report", "label": "SOURCE-EXPLICIT"}],
        "test_procedure": []}]), set(),
     "A SOURCE-EXPLICIT control with no test procedure warns but does not block."),
    ("G5 invalid label", base_record("GRV-R-009", candidate_ids=["GRV-CAN-00001"], controls=[{
        "control_id": "CTRL-GRV-002", "label": "PROPOSED-CONTROL",
        "objective": "Detect breaches of the resolution turnaround time.",
        "control_type": "detective", "frequency": "monthly", "performer": "not_specified",
        "evidence": [{"artefact": "Ageing report", "label": "SUGGESTED"}],
        "test_procedure": [{"step": "Recompute elapsed working days.", "label": "PROPOSED-TEST"}]}]),
     {"C2-schema", "G5-labels"}, "An evidence artefact with a non-permitted label must fail."),
    ("G6 legal conclusion", base_record("GRV-R-010", candidate_ids=["GRV-CAN-00001"],
        what="Resolve fraud complaints within 30 working days; this complies with the applicable regulatory turnaround requirement."),
     {"G6-legal"}, "Interpretation language must be routed to legal review, not asserted."),
    ("G7 table numerics without visual check", base_record("GRV-R-011", candidate_ids=["GRV-CAN-00001"], source_table_id="T002-1",
        numeric_facts=[{"kind": "money", "verbatim": "Rs. 5,000", "value": 5000, "unit": None, "currency": "INR", "context": "compensation cap"}]),
     {"G7-visual"}, "A table-derived money value without a checked page image must fail."),
    ("G8 approved without gates", base_record("GRV-R-012", candidate_ids=["GRV-CAN-00001"], status="approved"),
     {"G8-gates"}, "status=approved with open gates and review_status=unreviewed must fail."),
    ("G2 compound obligation", base_record("GRV-R-013", candidate_ids=["GRV-CAN-00001"],
        what="Resolve fraud complaints within the stated TAT and report the results to the Committee and maintain an ageing register."),
     set(), "A compound obligation warns rather than blocks, because splitting is a judgement call."),
]
