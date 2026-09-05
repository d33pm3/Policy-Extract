# Compliance pack — {DOCUMENT TITLE}

> **DRAFT — NOT APPROVED FOR OPERATIONAL USE.** Review gates are open.

Template for `03-policy-compliance-packs/<slug>.md`. `build_packs.py` renders this
automatically from `requirements.json`; use the template directly only when working
by hand or answering in chat.

## 1. Document identity

- Document ID: `SRC-nnnn`
- Source file: `filename.pdf`
- SHA-256: `...`
- Pages: n | Tables detected: n
- Document type: policy | t&c | sop | circular | mixed
- Approval / effective date as printed: ... | `not_specified`
- Text quality: ... | Processing path: ...
- Requirements extracted: n

## 2. Requirement register

| ID | What | Why | Who (A/R) | Trigger | When | How (steps) | Evidence | Control | Source | Status |
|---|---|---|---|---|---|---|---|---|---|---|

Roles marked *(inferred)* and controls marked `PROPOSED-CONTROL` are proposals, not
policy text. `not_specified` means the document is silent — a gap in the policy, not
in the extraction.

## 3. Verbatim source evidence

**{REQ-ID}** — {file} p.{n}, {section}

> {exact quote}

## 4. TATs, thresholds, amounts and liability values

| Requirement | Kind | Verbatim value | Context | Source | Visual reconciliation |
|---|---|---|---|---|---|

Values are reproduced exactly as printed — not converted, rounded or annualised. A
table-derived value marked **UNCHECKED** has not passed G7 and must not be relied on.

## 5. Exceptions, conditions and carve-outs

| Requirement | Exception / condition | Source |
|---|---|---|

## 6. Cross-references and cited regulations

**Referenced documents:** ... (resolved / **NOT IN CORPUS**)

**Cited regulations (as printed, not interpreted):** ...

## 7. Proposed controls, evidence and audit tests

Everything in this section is an AI proposal for the policy owner, Operations and
Internal Audit to accept, amend or reject. None of it is stated by the document.

### {CTRL-ID} — {objective} `PROPOSED-CONTROL`

- Requirement: `{REQ-ID}` ({source})
- Type: ... | Frequency: ... | Performer: ... | Automation: ...
- Evidence: {artefact} `PROPOSED-EVIDENCE`
- Test procedure:
  1. {step} `PROPOSED-TEST`

## 8. Open questions by reviewer

**Policy owner** — ownership gaps, applicability, exceptions
**Compliance / Legal** — citations and every `REQUIRES-LEGAL-REVIEW` record
**Operations** — feasibility of procedures, evidence and inferred roles
**Internal Audit / Risk** — control design and test adequacy
**Document analyst** — low-confidence records and parser exceptions

## 9. Approval block

| Gate | Reviewer | Decision | Date | Signature |
|---|---|---|---|---|
| Source fidelity (document analyst) |  |  |  |  |
| Policy meaning (policy / business owner) |  |  |  |  |
| Regulatory mapping (Compliance / Legal) |  |  |  |  |
| Operational feasibility (process owner / Operations) |  |  |  |  |
| Assurance design (Internal Audit / Risk) |  |  |  |  |

This pack is not approved for operational use until every applicable row above is
signed.

## 10. Verification statement

**Checked mechanically:** {scripts run and exit codes; candidates dispositioned;
numeric values reconciled}
**Judgement-dependent:** {atomisation calls, applicability reads, proposed controls}
**Open:** {gates, missing referenced documents, OCR-limited pages, low-confidence records}
