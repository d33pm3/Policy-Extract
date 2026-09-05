# Atomicity and recall contract (Stage 2–3)

Load this with `prompts/extraction.md` before writing any requirement record.
This file exists because a complete-looking register can still lose independently
testable commitments that sit inside lists, multi-verb sentences, forums,
published contacts, annex notes and page-break sentences.

## Contents

1. Why recall collapses
2. What must become its own record
3. What must not become an operational TAT
4. Page-span quotes
5. Clock-start discipline
6. Disposition rules that caused silent drops
7. Worked splits (normative)

---

## 1. Why recall collapses

Stage 2 finds sentences. Stage 3 is where recall is lost: the extractor treats a
paragraph as one idea, files committee composition under "background", and folds
"acknowledge, update and display" into a single `what`. Those are design failures,
not judgement calls.

A record is too coarse when a reviewer cannot pass or fail one action without
also judging a different action, a different owner, a different channel, or a
different clock.

## 2. What must become its own record

Create a separate requirement (or a `definition` / `exception` / `disclosure_requirement`
typed record) whenever the source contains any of the following. Do not absorb
them into a neighbouring row.

| Class | Extract when the source | Type | Do not classify as |
|---|---|---|---|
| Multi-verb process | One sentence gives two or more independently testable verbs (acknowledge / update / display / publish / refer / resolve / report / record / track / lodge / assign / facilitate / disclose / train / review / submit) | `process_step` or `policy_obligation` | One compound `what` |
| Timing attached to one verb only | Same sentence: verb A with no TAT and verb B with a TAT | two records | One row that applies the TAT to both verbs |
| Named office / apex role | Principal Nodal Officer, Internal Ombudsman, Nodal Officer, competent authority, named committee chair | `definition` plus any duty the same passage imposes | Footnote on a generic escalation row |
| Published contact | Email, URL, postal address, phone, named portal | `process_step` or `disclosure_requirement` | Dropped as "details" |
| Display / publish duty | "display", "made available", "published at branches / website / notice board" | `policy_obligation` | Folded into the customer's right to approach a forum |
| Forum constitution | "has constituted", "functions as", "is chaired by", membership | `definition` or `governance` obligation | Background |
| Forum function list | "carries out the following functions" plus bullets or numbered items | one record per function | One mega-row of all functions |
| Board / standing-committee oversight list | Separate review, oversee, report duties | one record per duty | One "reporting" row |
| Alternative dispute forum | Named arbitration scheme, ombudsman scheme, court carve-out | own record | Buried in a residual disputes paragraph |
| Institutional definition | "X is an independent apex authority and is not an employee" | `definition` | `non_binding` |
| Mechanism exclusion | "would not be examined by", "shall not apply", "excluding" a named mechanism | `exception` as its own record when it changes who may act | Only an `exceptions_conditions` field on the parent |
| Second mechanism after "in addition / also / additionally" | A further channel, survey, meeting or report | own record | Absorbed into the first mechanism |
| Annex / appendix taxonomy | Master list of grounds, "maintainable complaints" notes, prescribed disclosure formats | `definition` or `disclosure_requirement` | Skipped because it is an annex |
| End-to-end recording duty | "all complaints are recorded and tracked" | own `process_step` | Absorbed into a system-specific CRM row |
| Channel inventory item | A specifically named intake channel (branch, CRM, demat email, iMobile, social) | own record when the source names the channel | Generic "multiple channels" only |

Purpose / objective sentences ("the objective of the policy is to ensure that
customers are treated fairly") stay out of the live obligation register unless
they use binding language (`shall` / `must` / `will`) that a tester can fail.
Record them as `non_binding` candidates with reason `purpose_statement`.

Applicability lists (who the policy covers) are coverage, not a separate control
test, unless the source imposes a distinct duty for that segment.

## 3. What must not become an operational TAT

A number in an annexure or appendix table is an operational deadline only when
the policy *body* uses that number as a turnaround, referral or communication
clock.

| Source shape | Correct handling |
|---|---|
| Annexure / Annual Report disclosure template column "pending beyond 30 days" | `disclosure_requirement`. Do not set `deadline_value`. Do not mark G7 visual reconciliation as if it were a TAT. |
| Blank template with column headers only | Extract the duty to *publish in that format*. Do not invent populated figures. |
| Body prose "within 30 working days" | Operational TAT. Preserve unit and basis. |
| Template 30 days and body 30 working days in the same document | Two different facts. Do not merge them. |

`visual_reconciliation` = checked is allowed on a template only to confirm the
*column structure*, never to treat a header number as a tested TAT.

## 4. Page-span quotes

Physical PDF pages insert a page number into running text. A sentence that
starts on page N and finishes on page N+1 is one sentence.

Rules:

1. If the quote does not end in `. ? ! :` and the next page continues the
   sentence, extend `source_page_end` and extend the quote to the first
   terminal punctuation on the next page.
2. Never cut a quote mid-phrase ("in prominent locations in").
3. Copy the quote from `pages.json` after joining the two pages and
   stripping the inserted page-number token if it sits inside the sentence.
4. Cite every physical page the quote occupies.

Stage 2 emits `origin: page_span_sentence` candidates for these joins. Stage 3
must map them, not ignore them.

## 5. Clock-start discipline

`trigger` and any control objective that names when the clock starts must use
only words present in the quote.

- Source: "The final decision will be communicated to the customer within 30 days."
- Legal `trigger`: `not_specified` (the source does not name the start event).
- Illegal: "within 30 days from the IO decision date" in `what` or in a control
  objective. That start event is an invention.

If you need a working assumption for a proposed control, write it as
`PROPOSED-CONTROL` and put "clock start is not specified in the policy" in
`open_questions`. Do not smuggle the assumption into `deadline_verbatim`.

## 6. Disposition rules that caused silent drops

Do **not** mark as `non_binding` solely because the sentence is:

- a definition of a named office, forum or scheme
- committee constitution, chair or membership
- a published email, URL, postal address or portal
- a display / notice-board / website duty
- an annex note or appendix master list
- an exclusion from a named mechanism
- a second mechanism introduced by "in addition"

Those are mapped records. `non_binding` is for purpose statements, recitals,
pure duplication of a sentence already mapped, and decorative headings.

## 7. Worked splits (normative)

**Source (overseas branches):** "The branches shall acknowledge the complaints,
update the customers on the status of the complaint and display the escalation
matrix on the branch notice board/website."

Three records: acknowledge; update status; display matrix. Same quote is
allowed; `what` must name one verb.

**Source (insurance):** "…will acknowledge the complaint and facilitate
redressal of the same within 14 days of receipt…"

Two records: acknowledge (no TAT in source for this verb); facilitate
redressal within 14 days.

**Source (forums):** "The CSC carries out the following specific functions:"
plus five bullets.

Five records, one per bullet, plus separate records for chair/membership and
meeting cadence if those are stated in other sentences.

**Source (IO):** independence sentence; referral-before-communication sentence;
20-day referral sentence; 30-day communication sentence; binding-decision
sentence; exclusion sentence.

Six records. The exclusion is type `exception`, not a parenthetical on referral.
