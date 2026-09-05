# Atomic requirement extraction prompt

Use this verbatim when delegating Stage 3 to a subagent, or as your own working
contract when extracting directly. Supply with it: the section's source text from
`pages.json` (with page numbers), that section's candidate slice, and
`schemas/policy-requirement.schema.json`.

---

You will receive a source policy excerpt with its source file, page numbers and
section heading, plus a list of candidate clauses already identified in that
excerpt, plus a JSON Schema.

Extract every independently testable policy, process, reporting, monitoring,
disclosure, record-retention, approval, prohibition, customer or regulatory
requirement in the excerpt. Also extract, as typed records, every institutional
definition of a named office or forum, every published contact (email, URL,
postal address, portal), every display or notice-board duty, every forum
constitution / chair / membership sentence, every bullet in a function or
oversight list, every mechanism exclusion, every named alternative dispute
forum, and every annex or appendix taxonomy or disclosure-format note.

Do not absorb those classes into a neighbouring row. Do not mark them
`non_binding` because they look like background. Purpose statements that use
no binding verb may be left unmapped with reason `purpose_statement`.
Applicability lists are coverage, not a separate control test, unless a
distinct duty is stated for that segment.

For each requirement:

- Use only the supplied source. Do not use outside knowledge of law, regulation or
  industry practice, and do not use another document unless it was supplied.
- Quote the exact sentence or sentences that support it, copied character for
  character from the supplied text. Do not retype, tidy, modernise or abbreviate.
- Record the physical page number and the section heading as printed.
- Preserve every date, money value, threshold, percentage, timing expression, unit,
  condition, exception and defined term exactly as written. Record each numeric value
  in `numeric_facts` with its verbatim form.
- Split compound statements into atomic requirements. Split whenever the actor,
  action, object, trigger, timing, applicability, channel or consequence differs.
  One record must be independently testable: a reviewer should be able to pass or
  fail it on its own.
- A coordinated sentence with two or more independently testable verbs is that
  many records. Same quote may be reused; `what` names one verb. If only one
  verb in the sentence carries a TAT, only that record receives the TAT.
- A function list under "carries out the following" / "the following reports
  shall be submitted" is one record per bullet, not one mega-row.
- If the quote would end mid-sentence, extend `source_page_end` and the quote
  onto the next page up to the first terminal punctuation. Never leave a
  truncated quote.
- `trigger` and any control objective that states when a clock starts may use
  only words present in the quote. If the source says "within 30 days" and does
  not name the start event, `trigger` is `not_specified`.
- A number that appears only as a column header in a blank annexure or appendix
  template is a `disclosure_requirement` format fact. Do not set `deadline_value`
  and do not treat it as an operational TAT.
- Separate the organisation's obligation from the customer's obligation, even when a
  single sentence creates both.
- Use `not_specified` for any field the source does not answer — role, deadline,
  frequency, evidence, procedure. Never supply a plausible value. A `not_specified`
  is a finding; a guess is a defect.
- Set `role_basis` honestly: `explicit_source` only when the role appears in the
  cited passage; `operational_inference` when you assigned it; otherwise
  `not_specified`.
- Do not state any legal conclusion — what a law requires, whether something
  complies, what a breach attracts. Where the passage raises such a question, set
  `evidence_class` to `REQUIRES-LEGAL-REVIEW` and put the question in
  `open_questions`.
- Label every control, evidence artefact and test step you design as
  `PROPOSED-CONTROL`, `PROPOSED-EVIDENCE` or `PROPOSED-TEST`. Only a mechanism the
  document itself names is `SOURCE-EXPLICIT`.
- Where the requirement derives from a table containing money, percentages,
  durations or thresholds, set `source_table_id` and populate
  `visual_reconciliation` only after actually looking at the rendered page image.
- List in `candidate_ids` every candidate clause this requirement discharges, so
  coverage can be measured.
- Set `extraction_confidence` to `low` whenever reading order, OCR quality, table
  structure or ambiguous drafting leaves real doubt, and say why in `reviewer_notes`.
- Leave `status` as `draft` and all review gates `open`. You do not sign gates.

Return a JSON array that validates against the supplied schema, and nothing else.

Before you finish, check your output against the candidate list you were given: name
any candidate you did not map to a requirement and say whether it is non-binding
(with a one-line reason) or needs human review. An unmentioned candidate is treated
as an omission.
