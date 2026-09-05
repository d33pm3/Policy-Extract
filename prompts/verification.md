# Source-fidelity verifier prompt

Use this for an independent second pass over extracted records — ideally by a
subagent that did not do the extraction, since the value here is in not sharing the
first pass's assumptions. Supply the requirement records and the source pages they
cite.

---

Compare each proposed requirement record against the supplied policy source.

Return, for each record, exactly one verdict:

- `VERIFIED` — the quote supports the record and every field is source-accurate.
- `PARTIALLY_VERIFIED` — the core requirement holds but at least one field is wrong,
  missing or over-stated.
- `NOT_VERIFIED` — the quote does not support the record, or the citation is wrong.
- `REQUIRES_LEGAL_REVIEW` — the record turns on what a law or regulation means.

Check, in this order:

1. Does the quote appear on the cited page, character for character? A near-match is
   not a match — report the difference.
2. Are the page number and section heading correct?
3. Does the quote actually support the `what` statement, or does it support something
   adjacent to it?
4. Is every timing, threshold, money value, percentage, frequency and condition
   reproduced exactly? Check units and the calendar/working/business-day basis
   specifically — this is where errors concentrate.
5. Is each assigned role either present in the cited passage or correctly marked as
   an inference?
6. Has the record introduced a control, deadline, exception, owner or legal
   conclusion the source does not contain?
7. Has the record dropped a material condition, proviso, exception or threshold that
   appears in the same passage? Omission is the more common defect and the harder one
   to see.
8. Is the record atomic — could a reviewer pass or fail it as a single commitment?
9. Are all proposed controls, evidence artefacts and test steps labelled?
10. Has a multi-verb sentence, function-list bullet, named office, published
    contact, display duty, forum constitution/chair/membership, mechanism
    exclusion, annex note or appendix taxonomy been absorbed into a neighbour
    or marked `non_binding` as "background"?
11. Does every quote end at a sentence boundary? If the cited page ends mid-
    sentence, has `source_page_end` been extended onto the next page?
12. Does `trigger` or any control objective invent a clock start ("from the
    decision date", "from receipt") that the quote does not contain?
13. Has a blank annexure template column been promoted into an operational TAT?

Report discrepancies only. Do not rewrite the policy, do not improve the phrasing,
and do not fix records — name the field, quote what the source says, and state what
the record says instead. For each `NOT_VERIFIED`, say whether the correct action is
re-citation, correction, splitting, or deletion of the record.
