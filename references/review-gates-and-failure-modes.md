# Stage 6 — Review gates, approval lifecycle and failure modes

Load before declaring anything final, and whenever a validation run fails in a way
you have not seen before.

## 1. The five gates

No output is `approved` until each applicable gate is signed by a named human. You
prepare the queue and state what must be decided; you never sign.

| Gate | Reviewer | Decides | Evidence they need in front of them |
|---|---|---|---|
| Source fidelity | Document analyst | Did we read the document correctly? | Rendered pages, parser exceptions, OCR flags, low-confidence records |
| Policy meaning | Policy / business owner | Do these requirements mean what the policy means? Who owns them? | Requirement register with quotes, `not_specified` owners, open questions |
| Regulatory mapping | Compliance / Legal | Are the citations right, and what do the flagged interpretation questions resolve to? | Regulatory obligation register, every `REQUIRES-LEGAL-REVIEW` record |
| Operational feasibility | Process owner / Operations | Can this actually be executed, with these owners and this evidence? | Procedures, evidence artefacts, proposed RACI, TAT register |
| Assurance design | Internal Audit / Risk | Are the controls and tests adequate and testable? | Control matrix, proposed tests, control-to-requirement coverage |

**Applicability.** Source fidelity and policy meaning always apply. Regulatory
mapping applies when the record cites a regulation or carries
`REQUIRES-LEGAL-REVIEW`. Operational feasibility applies when there are process
steps or controls. Assurance design applies when there are controls. The validator
uses these same rules.

## 2. Approval lifecycle

```
draft ──► in_review ──► approved
  ▲           │
  └──────────────────────  (amended or rejected at any gate returns the record to draft)
```

- `draft` — extracted, automated gates may or may not pass.
- `in_review` — automated gates pass; the record is in front of at least one reviewer.
- `approved` — every applicable gate signed, `review_status` settled, confidence not
  `low`, and no unverified numeric or unresolved interpretation remaining.

A pack containing one unapproved record is a draft pack. Partial approval is normal
and useful; describing a partially approved pack as approved is not.

## 3. What "prepare the queue" means in practice

For each reviewer, produce a list they can work through in order, where each item
states the record, the source, the specific question, and what changes depending on
the answer. Sort by consequence, not by requirement ID — the owner question on a TAT
with a regulatory dimension outranks a formatting query.

Say plainly what you could not determine. A reviewer who receives fifty confident
records and three questions will assume the fifty are settled; a reviewer who
receives forty confident records, seven `not_specified` owners and six flagged
interpretations knows exactly where to spend their hour.

## 4. Automated gates (what `validate_pack.py` actually checks)

| Test | Rule | Level |
|---|---|---|
| `source_traceability` | File in register, page in range, section present, quote found on the cited page | FAIL |
| `candidate_coverage` | No candidate left `pending`; mapped IDs resolve | FAIL for critical/high, WARN otherwise |
| `numeric_integrity` | Every numeric fact and every number in a structured field traceable to the cited page | FAIL |
| `role_integrity` | `role_basis: explicit_source` roles appear on the page; no filler values | FAIL |
| `cross_reference_integrity` | Referenced documents resolve or appear in the missing register | WARN |
| `output_schema` | Validates against the JSON Schema | FAIL |
| `no_silent_inference` | Controls, evidence and tests all labelled | FAIL |
| `legal_interpretation` | Conclusion language routed to `REQUIRES-LEGAL-REVIEW` | FAIL |
| `visual_reconciliation` | Table-derived numerics carry a checked page image | FAIL |
| `approval_gates` | `approved` only with all applicable gates signed by named reviewers | FAIL |
| `atomicity` | Compound-obligation detector | WARN — needs human judgement |

**Repair budget: three cycles.** Fix the specific reported records and re-run. If
the third run still fails, stop and report the failing IDs with what each needs. The
failure mode to avoid is deleting the awkward fields until the validator goes green —
a clean report over a hollowed-out register is worse than an honest red one.

## 5. Failure-mode register

| # | Failure | Likely cause | Detection | Action |
|---|---|---|---|---|
| FM-1 | Omitted clause | Buried in an annexure, footnote or table | Candidate left `pending` | Re-extract that section with surrounding context |
| FM-2 | Wrong TAT or amount | Merged-cell table, transposed column, OCR digit error | Numeric reconciliation FAIL, or G7 visual check | Read the rendered page; correct with a reviewer note |
| FM-3 | Invented owner or control | Semantic overreach | `role_basis` check, unlabelled control | Change to `not_specified` or `PROPOSED-*`; raise an open question |
| FM-4 | Wrong reading order | Multi-column layout or table-heavy page | Quote not found on cited page; Markdown vs image mismatch | Re-extract with OCR; manual page check |
| FM-5 | False duplicate or conflict | Lexical similarity overstates equivalence | Reviewer comparison of both quotes | Keep both; mark `DISTINCT` with a reason |
| FM-6 | Obsolete regulatory reference | The policy itself has not been updated | Citation register shows an old reference | Flag it; do not update the interpretation without Legal |
| FM-7 | Paraphrased quote | Retyped rather than copied | Fuzzy match WARN at 90–99% | Re-copy verbatim from `pages.json` |
| FM-8 | Page drift | Printed page number cited instead of physical | Quote found on an adjacent page | Cite the physical page; record the printed label separately |
| FM-9 | Compound requirement | Atomicity not applied | Atomicity WARN; the record cannot be tested as one thing | Split by actor / action / object / trigger / timing |
| FM-10 | Lost condition | Proviso dropped from an otherwise correct record | Reviewer reads the full quote; conditional candidate unmapped | Add to `exceptions_conditions`; re-check siblings |
| FM-11 | Cross-reference treated as content | An obligation that lives in an unsupplied document | Missing-reference register | Mark source-limited; obtain the document |
| FM-12 | Silent conflict resolution | Two positions merged into one comfortable statement | Cross-document review | Restore both positions with citations; raise the question |
| FM-13 | Approved-by-default | Status set to approved without gates | G8 FAIL | Reset to draft; the pipeline does not sign for humans |
| FM-14 | Confident completeness claim | Coverage asserted without the candidate ledger | Coverage WARN: no ledger found | Run Stage 2; state coverage as a ratio, not an adjective |
| FM-15 | List / multi-verb collapse | Function bullets or coordinated verbs folded into one `what` | G2 WARN + C3-recall | Split per `atomicity-and-recall.md`; reuse the quote |
| FM-16 | Forum / contact treated as background | Named office, email, URL, constitution or chair marked `non_binding` | C3-recall WARN | Map as `definition`, `process_step` or `disclosure_requirement` |
| FM-17 | Truncated page-span quote | Quote cut at a physical page break mid-sentence | G1 WARN on next-page continuation | Extend `source_page_end` and the quote |
| FM-18 | Invented clock start or template TAT | Control says "from the decision date" or annexure column becomes a TAT | G4 / G3 WARN | `trigger=not_specified`; annexure numbers stay disclosure format |

## 6. Closing statement

Every substantive output ends with what was checked, what is judgement, and what is
open:

> **Verification.** Ran `intake_register.py` (exit 0), `build_source_layer.py`
> (exit 2 — three OCR exceptions logged), `find_candidates.py` (412 candidates),
> `validate_pack.py` (exit 2 — 0 failures, 9 warnings). 412/412 candidates
> dispositioned; 63 numeric values reconciled against rendered pages; 4 records
> flagged `REQUIRES-LEGAL-REVIEW`.
> **Judgement-dependent:** atomisation of 7 compound clauses, applicability of the
> annexure to non-retail customers, all 21 proposed controls.
> **Open:** all five review gates; 2 referenced documents not supplied
> (Record Retention Policy, Product Approval Framework); 3 pages OCR-limited.
> **Status: DRAFT — not approved for operational use.**

That paragraph is the difference between a deliverable a reviewer can rely on and
one they have to re-verify from scratch.
