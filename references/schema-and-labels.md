# Requirement schema, labels and controlled vocabularies

Load before writing requirement records. The authoritative machine contract is
`schemas/policy-requirement.schema.json`; this file explains what each field means
and, more usefully, how each one is commonly got wrong.

## Contents

1. Identity and source fields
2. Classification fields
3. Substance: what / why
4. Roles
5. Timing
6. Procedure, evidence, exceptions, references
7. Numeric facts
8. Controls, evidence and tests
9. Visual reconciliation
10. Confidence, review status, gates, status
11. Label taxonomy
12. Worked example

---

## 1. Identity and source fields

| Field | Rule |
|---|---|
| `requirement_id` | `<SHORTCODE>-R-<nnn>`, e.g. `GRV-R-001`. The short code comes from the source register. Stable forever — never renumber after publication, because reviewers cite these IDs in emails. |
| `policy_name` | The document's own title as printed, not your paraphrase. |
| `policy_approval_or_effective_date` | As printed. `not_specified` if the document does not say. Never take it from file metadata — a re-saved PDF has a misleading date. |
| `source_document_id` | `SRC-nnnn` from the register. |
| `source_file` | Must match the register's `file_name` exactly; the validator compares them. |
| `source_page_start` / `source_page_end` | **Physical PDF pages**, from `pages.json`. If the printed page number differs, put that in `printed_page_label`. When a quote spans a page break, cite both pages. |
| `source_section` | The heading or clause reference as printed. `not_specified` only when the passage genuinely sits under no heading. |
| `source_quote` | Verbatim. Copy from `pages.json` or `document.md`, do not retype. The validator re-reads the page and fails a quote it cannot find. |

The single most common failure is a quote that is *almost* right — a word modernised,
a comma moved, an ellipsis introduced. It reads as a citation and functions as a
paraphrase. Copy, don't compose.

## 2. Classification fields

`requirement_type`: policy_obligation, process_step, customer_obligation,
approval_requirement, monitoring_requirement, reporting_requirement,
record_retention_requirement, disclosure_requirement, prohibition, exception,
definition, regulatory_reference.

`normative_strength`: the document's own modal verb — must, shall, will, should,
may, must_not, shall_not, not_specified. Never upgrade `should` to `shall`. The
strength is evidence about enforceability; overwriting it destroys that evidence.

`obligation_bearer`: organisation, customer, third_party, regulator, both,
not_specified. When one sentence creates duties for two parties, write two records.

## 3. Substance: what / why

`what` — one testable commitment, stated actively, in the document's own vocabulary.
Prefer the policy's terms ("Internal Ombudsman", "UEBT", "TAT") over generic
equivalents; a reviewer searching the PDF for your wording should find it.

`why` + `why_basis` — the purpose. `explicit_source` when the document gives the
rationale; `operational_inference` when you supply a plausible purpose;
`not_specified` when neither. A `why` that is really your own reasoning, tagged
`explicit_source`, is a small lie that survives into a control design.

## 4. Roles

`accountable_role`, `responsible_role`, `consulted_roles`, `assurance_roles`, plus
`role_basis` for the whole set.

- `explicit_source` — the named role appears in the cited passage. The validator
  checks this: if the role string is not on the page, the record fails.
- `operational_inference` — you assigned it. Legitimate and useful, but it must say so.
- `not_specified` — the document is silent and you are not proposing anyone.

Policies are frequently silent on ownership. `not_specified` is the honest and
actionable answer: it tells the policy owner exactly which gap to close. An invented
"Compliance Department" tells them nothing and quietly becomes fact.

## 5. Timing

`trigger` — the event that starts the clock, **in the document's words**. If the
source gives a duration ("within 30 days") and does not name the start event,
`trigger` is `not_specified`. Never write "from the decision date" or "from
receipt" unless those words are in the quote.

`frequency` — recurring cadence, or `not_specified`.
`deadline_value` / `deadline_unit` — numeric decomposition, for sorting and calendars.
Set these only for operational clocks in the policy body. A number that exists
only as a column header in a blank annexure or appendix disclosure template is
**not** a `deadline_value`.
`deadline_basis` — calendar_day | working_day | business_day | immediate | not_specified.
`deadline_verbatim` — **required whenever `deadline_value` is set.** The timing
expression exactly as printed, e.g. `"within 30 working days from the date of receipt"`.

The distinction between calendar and working days is where TAT registers go wrong,
and it is almost never a rounding matter — 30 working days is six weeks. If the
document does not say, `not_specified` is the answer, not an assumption.

`requirement_type` = `definition` for institutional identity ("X is not an employee",
"maintainable complaints means…", committee constitution). `exception` for a
carve-out that changes who may act. `disclosure_requirement` for annexure formats
and appendix master lists used in public reporting.

## 6. Procedure, evidence, exceptions, references

`process_steps` — only steps the document sets out. If the document says "resolve
the complaint" and nothing more, that is one step, not five you designed. Steps you
design belong in a control's `test_procedure` or an explicitly `SOURCE-INFERRED`
process note.

`mandatory_evidence` — records the document itself requires.
`exceptions_conditions` — provisos, carve-outs, non-applicability, thresholds that
gate the obligation. Losing these turns a conditional duty into an absolute one.
`cited_regulations` — citations **as printed**. Do not expand, correct or verify them.
`cross_policy_references` — other documents this requirement depends on.

## 7. Numeric facts

Every money value, percentage, duration, count, threshold or rate the requirement
asserts gets an entry: `kind`, `verbatim` (exactly as printed, including the currency
symbol and any "lakh"/"crore"), and optionally `value`, `unit`, `currency`, `context`.

The validator checks each `verbatim` against the quote and the cited page, and also
checks that any number appearing in `what`, `trigger`, `frequency` or
`deadline_verbatim` exists on that page. Converting ₹1 lakh to 100,000 fails, and
should — the reviewer needs to see what the policy printed.

## 8. Controls, evidence and tests

Each control: `control_id` (`CTRL-<SHORTCODE>-<nnn>`), `label`, `objective`,
`control_type`, `automation`, `frequency`, `performer`, `evidence[]`,
`test_procedure[]`.

`label` is `SOURCE-EXPLICIT` only when the document names the control mechanism
itself. "The Bank shall conduct a monthly quality audit of complaint classification"
names a control. "The Bank shall resolve complaints within 30 days" does not — any
control you design around it is `PROPOSED-CONTROL`.

Evidence items carry their own `SOURCE-EXPLICIT` / `PROPOSED-EVIDENCE` label; test
steps carry `PROPOSED-TEST` unless the document specifies the test.

## 9. Visual reconciliation

Required (G7) whenever `source_table_id` is set and the record carries money,
percentage, duration, threshold or rate facts. Populate `visual_reconciliation` with
`page_image` (the rendered PNG path), `checked: true`, `checked_by`, `checked_on`,
and any note about what the image showed that the text extraction did not.

Set `checked: true` only after actually looking at the image. Merged cells and
multi-row headers are the specific hazard: text extraction can attach a value to the
wrong row label and produce a perfectly formatted, entirely wrong liability slab.

## 10. Confidence, review status, gates, status

`extraction_confidence`: high | medium | low (definitions in `stage-specs.md` §4).
`review_status`: unreviewed | validated | amended | rejected | requires_policy_owner |
requires_legal_review.
`review_gates`: five gate objects, each `state` = open | not_applicable | signed,
with `reviewer`, `signed_on`, `decision`, `notes`.
`status`: draft | in_review | approved.

`approved` is refused by the validator unless every applicable gate is signed by a
named human, `review_status` is settled, and confidence is not `low`. You never sign
a gate. Preparing the queue and stating what each reviewer must decide is your part.

## 11. Label taxonomy

| Label | Applies to | Meaning |
|---|---|---|
| `SOURCE-EXPLICIT` | requirement, process step, control, evidence | The document states it |
| `SOURCE-INFERRED` | requirement, process step | Normalised or structured from the document, not stated verbatim |
| `PROPOSED-CONTROL` | control | Designed by AI; unapproved |
| `PROPOSED-EVIDENCE` | evidence artefact | Suggested record; unapproved |
| `PROPOSED-TEST` | audit test step | Suggested test; unapproved |
| `REQUIRES-LEGAL-REVIEW` | requirement | Interpretation question for Compliance/Legal |
| `not_specified` | any field | The document is silent — a gap in the policy, not in the extraction |

## 12. Worked example

See `assets/requirement-record.template.json` for the machine-readable skeleton.
A complete worked record is in the enclosed skill package under this same filename.
The record must not invent an owner the policy never named, must not assert that a
TAT satisfies a regulation the policy did not cite, and must label every control
and test as a proposal. Gaps shown on the record are gaps in the policy.
