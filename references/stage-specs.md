# Stage 0–7 specification

Load this before a first run on a new corpus, or when a stage's stop rule fires and
you need the fallback path.

## Contents

1. Stage 0 — Intake, classification, preservation
2. Stage 1 — Structural ingestion and source reconstruction
3. Stage 2 — Completeness-first candidate clause ledger
4. Stage 3 — Atomic semantic requirement extraction
5. Stage 4 — Control, procedure and evidence design (see also `control-and-evidence-design.md`)
6. Stage 5 — Cross-document harmonisation (see also `cross-document-analysis.md`)
7. Stage 6 — Validation and human sign-off (see also `review-gates-and-failure-modes.md`)
8. Stage 7 — Publication and archive
9. Working with a corpus too large for one pass

---

## 1. Stage 0 — Intake, classification, preservation

**Objective.** Create an immutable, auditable baseline before any conversion or
analysis. If a reviewer six months from now asks "which version of the policy did
this requirement come from", the SHA-256 answers it and nothing else does.

**Actions.** Hash every original; capture filename, title, issuer, version and
approval/effective date **as printed** (never inferred from file timestamps); count
pages; classify document type; triage text quality; store originals read-only.

**Document types.** policy | terms_and_conditions | sop | regulatory_circular |
form_or_checklist | annexure_or_schedule | mixed | unclassified. The intake script
gives a hint from first-page text; correct it by reading the cover page. A wrong
type is not fatal — it only steers the extraction emphasis — but an unclassified
mixed document that is actually a policy-plus-annexure set should be flagged so the
annexure is not skipped.

**Text-quality triage.** native_digital_text | native_text_with_tables |
hybrid_some_scanned_pages | scanned_image_only | unreadable. This decides the
processing path, and the path decides how much you can trust text extraction.

**Stop rule.** No semantic work until every file has an ID, a hash, a page count and
a processing path.

---

## 2. Stage 1 — Structural ingestion and source reconstruction

**Objective.** A faithful, reviewable source layer that preserves hierarchy,
headings, lists, tables and page references — because every downstream citation
resolves against it.

**Decision tree.**

```
Text-native, normal layout?            → default text extraction (pdfplumber)
Poor scan, stamps, broken reading order,
image-based tables?                    → OCR pre-processing (--ocr), then re-extract
A critical table or threshold?         → render the page, Read the image, compare
Still uncertain reading order?         → manual page-level review; log the exception
```

**Quality controls.**
- Preserve heading sequence and physical page numbers. Where the printed page
  number differs from the physical page, record both (`printed_page_label`).
- Preserve lists as lists. A merged list is how a five-item obligation becomes one.
- Preserve each table separately with a table ID, page and cell data.
- Keep explicit page markers in the Markdown: `<!-- source: SRC-0001 p.4 -->`.
- Flag low-confidence OCR blocks; never silently correct them. A corrected block
  that was corrected wrongly is undetectable downstream.

**Stop rule.** A conversion fails if a page, annexure, table or heading is missing,
unreadable, or of uncertain reading order. Route to OCR or manual review and log it.

---

## 3. Stage 2 — Completeness-first candidate clause ledger

**Why this stage exists.** Semantic models group well and enumerate badly. Given a
15-page policy they find the obligations a human would name first and miss the one
in the annexure footnote. A regex sweep has poor precision and near-total recall,
which is the correct trade for a denominator.

**Pattern families.** Binding language; timing and frequency; governance and
approval; process conditions; definitions; published contacts (email, URL, postal
address, portal); forum constitution, chair and membership; page-break sentences
that start on one physical page and finish on the next; and a separate numeric
sweep across prose and table cells for money, percentages, durations and
thresholds, including blank annexure templates.

Stage 2 splits on sentences **and** on list bullets. A coordinated multi-verb
sentence is still one candidate text, but it is flagged so Stage 3 must split it.
Annex and appendix pages are scanned with the same patterns as the body.

**Dispositions.** Every candidate ends as one of:

| Disposition | Meaning | Requires |
|---|---|---|
| `mapped` | Discharged by one or more requirements | `mapped_requirement_ids` populated |
| `non_binding` | Background, recital, definition or duplicate phrasing | `disposition_reason` one line |
| `queued_for_review` | Genuinely ambiguous; a human must decide | Entry in the exception queue |

**Stop rule.** No document is complete while any candidate is `pending`. The
validator escalates pending `critical`/`high` candidates to blocking failures.

---

## 4. Stage 3 — Atomic semantic requirement extraction

**Objective.** Turn candidate clauses plus their local context into small, testable,
source-linked requirements.

**Work order.** Section by section, including every annexure and appendix, not
document by document. Keep that section's candidate slice open beside you and
tick items off; this is the mechanism that makes the coverage number real rather
than reconstructed at the end. Load `atomicity-and-recall.md` before the first
section.

**Extraction rules.**
1. Extract only what the supplied passage supports.
2. Quote the exact supporting sentence(s); record page and heading. If the
   sentence crosses a page break, cite both pages and do not truncate.
3. Split compound obligations so each record is independently testable. Split
   multi-verb sentences, function-list bullets, and TAT-bearing verbs from
   verbs in the same sentence that carry no TAT.
4. Never infer a deadline, clock-start event, statutory obligation, role,
   authority, system or control where the source is silent.
5. Use `not_specified` rather than guessing.
6. Separate the organisation's obligation from the customer's obligation.
7. Capture conditions, exceptions, thresholds, dependencies and escalation
   separately. A named-mechanism exclusion is its own `exception` record.
8. Label every rationale `explicit_source` or `operational_inference`.
9. Never turn policy text into a legal conclusion; flag ambiguity for legal review.
10. Do not mark named offices, published contacts, display duties, forum
    constitution/chair/membership, annex taxonomies or alternative dispute
    forums as `non_binding` background.
11. Do not promote a blank annexure template column into an operational TAT.
12. Return JSON that validates against `schemas/policy-requirement.schema.json`.

**Atomicity test.** Split when any of these differ: actor, action, object, trigger,
timing, applicability, channel, consequence. Merge only when the same actor performs
the same action on the same object under the same trigger and timing, and completing
one automatically completes the other.

**Confidence.** `high` = quote directly states the requirement and every field.
`medium` = the requirement is clear but one or more fields are `not_specified` or
normalised. `low` = reading order, OCR quality, table structure or ambiguous drafting
leaves real doubt. Low-confidence records go in the exception queue and can never be
approved without a documented reviewer decision.

---

## 5. Stage 4 — Control, procedure and evidence design

Full patterns in `control-and-evidence-design.md`. Summary of the labelling
contract:

| Layer | Label |
|---|---|
| Policy requirement | `SOURCE-EXPLICIT` |
| Process step | `SOURCE-EXPLICIT` if the document sets it out; otherwise `SOURCE-INFERRED` |
| Control activity | `PROPOSED-CONTROL` unless the document names the control |
| Evidence artefact | `SOURCE-EXPLICIT` if named; otherwise `PROPOSED-EVIDENCE` |
| Audit test | `PROPOSED-TEST` |

**Stop rule.** Never present an AI-designed control or test as an approved policy
requirement. The label stays until a human removes it.

---

## 6. Stage 5 — Cross-document harmonisation

Methods, comparison rules and reviewer-question formats: `cross-document-analysis.md`.

Detect: duplicate and near-duplicate obligations; conflicting timeframes; different
role assignments for the same duty; referenced-but-unavailable documents;
supersession and version-date inconsistencies; and implementation dependencies that
live in another document.

Similarity **proposes**; a reviewer confirms. Never conclude supersession unless a
document states it.

---

## 7. Stage 6 — Validation and human sign-off

Automated gates are in `validate_pack.py`; the human gates, the approval lifecycle
and the failure-mode register are in `review-gates-and-failure-modes.md`.

**Repair budget.** Three cycles. After the third failing run, stop and report the
failing record IDs and what each needs. Iterating a validator to green by weakening
records is worse than an honest partial result.

**Stop rule.** No pack is `approved` while it contains unresolved low-confidence
extraction, unverified numeric data, unreviewed legal interpretation or missing
referenced policies.

---

## 8. Stage 7 — Publication and archive

Publish human-readable Markdown without losing machine-readable records or source
traceability: per-document compliance packs, enterprise views, and
`requirements.{json,csv,md,sqlite}`. Keep the whole tree in Git if the user has a
repository — the diff between two runs of the same policy version is the review
artefact for a policy amendment.

`build_packs.py` refuses to publish an uncited row unless `--allow-uncited` is
passed, and then stamps each one. Prefer fixing the row.

---

## 9. Working with a corpus too large for one pass

For a corpus over roughly 150 pages, or more than four documents:

1. Run Stages 0–2 across the whole corpus first. They are deterministic and cheap,
   and the candidate counts tell you where the density actually is.
2. Extract document by document, and within a document section by section. Write
   `requirements.json` incrementally rather than holding everything in context.
3. Run `validate_pack.py` after each document rather than at the end — a citation
   convention error caught on document one saves re-doing all six.
4. Run Stage 5 only once every document has passed Stage 6's automated gates;
   cross-document comparison on unvalidated records generates noise.
5. If delegating to subagents, give each one the prompts in `prompts/` verbatim plus
   one document's source layer and candidate slice. Do not let a subagent invent its
   own schema — hand it `schemas/policy-requirement.schema.json`.
