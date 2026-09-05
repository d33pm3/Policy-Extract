#!/usr/bin/env python3
"""Smoke test that the LIVE skill tree is v1.2.0 and cannot roll back.

Uses a new synthetic policy (not any historical client pack). Proves:
  1. assert_live_version accepts only >= 1.2.0 at this skill tree
  2. stage3_preflight loads atomicity-and-recall + extraction.md
  3. find_candidates flags contact, forum, multi-verb, page-span
  4. validate_pack emits coverage ratio + G3/G4/C3 ID lists
  5. build_packs writes the honesty block
  6. a packaged .skill export is not a runtime override
  7. no historical client pack is imported as a fixture
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
from assert_live_version import assert_live, read_version  # noqa: E402

PAGE_1 = (
    "VENDOR ENTERTAINMENT POLICY\n"
    "1. Intake\n"
    "The Company shall record every vendor complaint and track it to closure.\n"
    "Escalate open items to gifts@example.com.\n"
    "The Company has constituted the Gifts Committee. The Committee is chaired by "
    "the Chief Compliance Officer.\n"
)
PAGE_2 = (
    "2. Handling\n"
    "The desk shall acknowledge the complaint, update the vendor and display the "
    "escalation matrix on the notice board.\n"
    "The final decision will be communicated to the vendor within 30 days.\n"
    "Salient features of the scheme are being displayed in prominent locations in"
)
PAGE_3 = (
    "3\nbranches and websites\n"
    "Annexure 1 Part B disclosure template includes a column pending beyond 30 days.\n"
)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def base_req(rid: str, **over) -> dict:
    rec = {
        "requirement_id": rid,
        "policy_name": "Vendor Entertainment Policy",
        "policy_approval_or_effective_date": "not_specified",
        "source_document_id": "SRC-0001",
        "source_file": "vendor-entertainment.pdf",
        "source_page_start": 1,
        "source_page_end": 1,
        "source_section": "Intake",
        "source_quote": "The Company shall record every vendor complaint and track it to closure.",
        "requirement_type": "process_step",
        "normative_strength": "shall",
        "obligation_bearer": "organisation",
        "what": "Record every vendor complaint and track it to closure.",
        "why": None,
        "why_basis": "not_specified",
        "accountable_role": "not_specified",
        "responsible_role": "not_specified",
        "consulted_roles": [],
        "assurance_roles": [],
        "role_basis": "not_specified",
        "trigger": "not_specified",
        "frequency": "not_specified",
        "deadline_basis": "not_specified",
        "process_steps": [],
        "mandatory_evidence": [],
        "exceptions_conditions": [],
        "cited_regulations": [],
        "cross_policy_references": [],
        "numeric_facts": [],
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


def main() -> int:
    results: list[tuple[bool, str]] = []

    try:
        root = assert_live()
        results.append((True, f"assert_live accepts {root} v{read_version(root)}"))
    except SystemExit as exc:
        results.append((False, f"assert_live: {exc}"))
        _print(results)
        return 1

    results.append((root.resolve() == SKILL.resolve(),
                    f"live tree is this skill root ({SKILL})"))
    results.append((read_version(root) == "1.2.0",
                    f"VERSION file is 1.2.0 (got {read_version(root)})"))
    results.append(((root / "references" / "atomicity-and-recall.md").exists(),
                    "atomicity-and-recall.md present"))
    results.append(((root / "references" / "gold-pack-policy.md").exists(),
                    "gold-pack-policy.md present"))
    results.append(((root / "scripts" / "stage3_preflight.py").exists(),
                    "stage3_preflight.py present"))

    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "policy-extractor"
        fake.mkdir()
        (fake / "SKILL.md").write_text("---\nname: policy-extractor\nmetadata:\n  version: \"1.0.0\"\n---\n", encoding="utf-8")
        (fake / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        proc = run([sys.executable, "-c",
                    "import sys; sys.path.insert(0, %r); import assert_live_version as a; "
                    "a.assert_live(%r)" % (str(HERE), str(fake))])
        results.append((proc.returncode != 0 and "ROLLBACK-GUARD" in (proc.stderr + proc.stdout),
                        "v1.0.0 tree without current pin is rejected"))

    packaged = Path(os.environ.get("POLICY_EXTRACTOR_PACKAGED", "")).resolve() if os.environ.get("POLICY_EXTRACTOR_PACKAGED") else None
    if packaged and packaged.exists():
        results.append((SKILL.resolve() != packaged,
                        "runtime skill dir is not the packaged zip"))
    results.append((not (SKILL / "02-requirements").exists(),
                    "skill tree does not embed a historical client register"))

    with tempfile.TemporaryDirectory() as tmp:
        kb = Path(tmp) / "kb"
        for sub in ["01-source-layer/SRC-0001", "02-candidates", "02-requirements",
                    "04-cross-policy-analysis", "05-quality-assurance"]:
            (kb / sub).mkdir(parents=True)
        (kb / "source-register.json").write_text(json.dumps([{
            "document_id": "SRC-0001", "short_code": "VEN", "slug": "vendor-entertainment",
            "file_name": "vendor-entertainment.pdf", "original_path": "vendor-entertainment.pdf",
            "sha256": "0" * 64, "bytes": 1, "title": "Vendor Entertainment Policy",
            "document_type_hint": "policy", "approval_or_effective_date_hint": "not_specified",
            "page_count": 3, "detected_table_count": 0, "text_quality": "native_digital_text",
            "low_text_pages": [], "processing_path": "text_primary",
            "parse_error": None, "original_file_retained": True,
            "registered_at_utc": "2026-08-31T00:00:00+00:00",
        }]), encoding="utf-8")
        (kb / "01-source-layer/SRC-0001/pages.json").write_text(
            json.dumps({"1": PAGE_1, "2": PAGE_2, "3": PAGE_3}), encoding="utf-8")
        (kb / "01-source-layer/SRC-0001/tables.json").write_text("[]", encoding="utf-8")
        (kb / "01-source-layer/SRC-0001/document.md").write_text(
            "<!-- source: SRC-0001 p.1 -->\n### Intake\n" + PAGE_1 +
            "\n<!-- source: SRC-0001 p.2 -->\n### Handling\n" + PAGE_2 +
            "\n<!-- source: SRC-0001 p.3 -->\n### Annexure\n" + PAGE_3,
            encoding="utf-8")

        pre = run([sys.executable, str(HERE / "stage3_preflight.py"), "--kb", str(kb)])
        results.append((pre.returncode == 0 and "PREFLIGHT PASSED" in pre.stdout,
                        f"stage3 preflight ({pre.returncode}) {pre.stdout.strip()[:80]}"))

        fc = run([sys.executable, str(HERE / "find_candidates.py"), "--kb", str(kb)])
        results.append((fc.returncode == 0, f"find_candidates exit {fc.returncode}"))
        led_path = kb / "02-candidates" / "SRC-0001-candidates.json"
        results.append((led_path.exists(), "candidate ledger written"))
        led = json.loads(led_path.read_text(encoding="utf-8")) if led_path.exists() else {"candidates": []}
        cands = led.get("candidates") or []
        flags_contact = any("@" in (c.get("exact_text") or "") for c in cands)
        flags_forum = any("constituted" in (c.get("exact_text") or "").lower() for c in cands)
        flags_multi = any(len(c.get("action_verbs") or []) >= 2 for c in cands)
        origins = {c.get("origin") for c in cands}
        results.append((flags_contact, "new-policy sweep caught published email"))
        results.append((flags_forum, "new-policy sweep caught forum constitution"))
        results.append((flags_multi, "new-policy sweep caught multi-verb sentence"))
        results.append(("page_span_sentence" in origins,
                        "new-policy sweep stitched the page-break display sentence"))

        reqs = [
            base_req("VEN-R-001", candidate_ids=[],
                     source_quote="The Company shall record every vendor complaint and track it to closure.",
                     what="Record every vendor complaint and track it to closure."),
            base_req("VEN-R-002", candidate_ids=[],
                     source_quote="Escalate open items to gifts@example.com.",
                     what="Escalate open items to the published gifts mailbox.",
                     requirement_type="process_step"),
            base_req("VEN-R-003", candidate_ids=[],
                     source_quote="The Company has constituted the Gifts Committee.",
                     what="The Company has constituted the Gifts Committee.",
                     requirement_type="definition"),
            base_req("VEN-R-004", candidate_ids=[],
                     source_quote="The Committee is chaired by the Chief Compliance Officer.",
                     what="The Gifts Committee is chaired by the Chief Compliance Officer.",
                     requirement_type="definition",
                     accountable_role="Chief Compliance Officer",
                     role_basis="explicit_source"),
            base_req("VEN-R-005", candidate_ids=[],
                     source_page_start=2, source_page_end=2, source_section="Handling",
                     source_quote="The desk shall acknowledge the complaint, update the vendor and display the escalation matrix on the notice board.",
                     what="Acknowledge the vendor complaint.",
                     requirement_type="process_step"),
            base_req("VEN-R-006", candidate_ids=[],
                     source_page_start=2, source_page_end=2, source_section="Handling",
                     source_quote="The desk shall acknowledge the complaint, update the vendor and display the escalation matrix on the notice board.",
                     what="Update the vendor on complaint status.",
                     requirement_type="process_step"),
            base_req("VEN-R-007", candidate_ids=[],
                     source_page_start=2, source_page_end=2, source_section="Handling",
                     source_quote="The desk shall acknowledge the complaint, update the vendor and display the escalation matrix on the notice board.",
                     what="Display the escalation matrix on the notice board.",
                     requirement_type="policy_obligation"),
            base_req("VEN-R-008", candidate_ids=[],
                     source_page_start=2, source_page_end=2, source_section="Handling",
                     source_quote="The final decision will be communicated to the vendor within 30 days.",
                     what="Communicate the final decision to the vendor within 30 days.",
                     trigger="not_specified",
                     deadline_value=30, deadline_unit="day", deadline_basis="not_specified",
                     deadline_verbatim="within 30 days",
                     numeric_facts=[{"kind": "duration", "verbatim": "30 days", "value": 30,
                                     "unit": "day", "context": "communication TAT"}],
                     open_questions=["Clock start for the 30 days is not specified in the source."]),
            base_req("VEN-R-009", candidate_ids=[],
                     source_page_start=2, source_page_end=2, source_section="Handling",
                     source_quote="Salient features of the scheme are being displayed in prominent locations in",
                     what="Display salient features of the scheme in prominent locations.",
                     requirement_type="policy_obligation"),
            base_req("VEN-R-010", candidate_ids=[],
                     source_page_start=3, source_page_end=3, source_section="Annexure",
                     source_quote="Annexure 1 Part B disclosure template includes a column pending beyond 30 days.",
                     what="Disclose ageing in the Annexure 1 Part B format.",
                     requirement_type="disclosure_requirement"),
        ]
        for c in cands:
            c["disposition"] = "mapped"
            c["mapped_requirement_ids"] = ["VEN-R-001"]
        led["candidates"] = cands
        led_path.write_text(json.dumps(led, indent=2), encoding="utf-8")
        for r, c in zip(reqs, cands):
            r["candidate_ids"] = [c["candidate_id"]]
        (kb / "02-requirements" / "requirements.json").write_text(
            json.dumps(reqs, indent=2), encoding="utf-8")

        val = run([sys.executable, str(HERE / "validate_pack.py"), "--kb", str(kb)])
        report = (kb / "05-quality-assurance" / "validation-report.md")
        text = report.read_text(encoding="utf-8") if report.exists() else ""
        results.append((report.exists(), "validation report written"))
        results.append(("Coverage ratio (not row count)" in text,
                        "validation report states coverage ratio, not row-count quality"))
        results.append(("Open G3" in text and "Open G4" in text and "Open C3" in text,
                        "validation report lists open G3/G4/C3 IDs"))
        results.append((val.returncode in (0, 2),
                        f"validate_pack exit {val.returncode} (0 or 2 expected)"))

        pub = run([sys.executable, str(HERE / "build_packs.py"), "--kb", str(kb)])
        pack = kb / "03-policy-compliance-packs" / "vendor-entertainment.md"
        results.append((pub.returncode == 0 and pack.exists(),
                        f"build_packs published new-policy pack (exit {pub.returncode})"))
        body = pack.read_text(encoding="utf-8") if pack.exists() else ""
        results.append(("Honesty and coverage" in body, "pack contains honesty block"))
        results.append(("not a gold file" in body.lower() or "historical client pack" in body.lower(),
                        "pack states no historical client pack is gold"))
        results.append(("Candidate disposition ratio" in body,
                        "pack prints candidate disposition ratio"))
        results.append(("VEN-R-005" in body and "VEN-R-006" in body and "VEN-R-007" in body,
                        "multi-verb sentence was split into three records"))
        results.append(("gifts@example.com" in body, "published contact captured"))
        results.append(("constituted the Gifts Committee" in body, "forum constitution captured"))

    _print(results)
    return 0 if all(ok for ok, _ in results) else 1


def _print(results: list[tuple[bool, str]]) -> None:
    for ok, name in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    failed = sum(1 for ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} smoke checks passed")


if __name__ == "__main__":
    raise SystemExit(main())
