# Stage 4 — Designing controls, evidence and audit tests without overreaching

Load when the user wants a control matrix, RACM input, evidence checklist or audit
programme from a policy.

## The line you are walking

A policy says what must happen. A control is a mechanism that makes it likely to
happen and detectable when it does not. Most policies name obligations and very few
name controls, so nearly everything in this stage is your design work — which is
genuinely valuable, and dangerous in exactly one way: a proposal that loses its
label becomes, to the next reader, something the policy required.

So the rule is not "be conservative". It is "be clearly attributed". Propose freely
and label ruthlessly.

## 1. When a control is SOURCE-EXPLICIT

Only when the document names the mechanism, not merely the outcome.

| Document says | Control label |
|---|---|
| "The Bank shall conduct a monthly quality audit of complaint classification and resolution." | `SOURCE-EXPLICIT` — the audit *is* the control |
| "Complaints shall be resolved within 30 working days." | Any monitoring you design is `PROPOSED-CONTROL` |
| "All waivers above ₹1 lakh require approval of the Committee." | `SOURCE-EXPLICIT` — the approval gate is named |
| "The Bank shall maintain adequate records." | `PROPOSED-CONTROL` — "adequate" names no mechanism |

When in doubt, ask whether an auditor could test the control using only the
document's own words. If not, it is yours.

## 2. Control design pattern

For each requirement, work through five questions in order. Each answer that the
document does not supply is a `not_specified` or a proposal, never a silent default.

1. **What failure are we preventing or detecting?** State it as an observable
   outcome, not a restatement of the requirement. Weak: "ensure complaints are
   resolved in 30 days". Strong: "no fraud or old-record complaint closes beyond the
   stated TAT without a recorded exception". The second one can fail a test.
   Do not add a clock-start event the quote does not contain. If the policy says
   "communicate within 30 days" and is silent on when the 30 days begin, the
   control objective must not say "within 30 days from the decision date". Put
   the missing start event in `open_questions`.
2. **Preventive or detective?** Preventive stops the outcome (system block, mandatory
   field, approval gate). Detective finds it afterwards (exception report, reconciliation,
   sample review). Most policy obligations need both; say which you are proposing.
3. **Who performs it?** If the policy names an owner, use it. If not, `not_specified`
   with an open question for the policy owner beats a plausible-sounding function.
4. **How often?** Tie the frequency to the obligation's trigger — per event, daily,
   monthly, per reporting cycle. A monthly control over a same-day obligation leaves
   a 30-day exposure window; say so rather than letting the mismatch pass silently.
5. **What would prove it ran?** See §3.

## 3. Evidence that is actually evidence

An evidence artefact has to be a thing that exists, in a system, with a date and an
actor. "Complaint records" is not evidence; "CRM case ID with receipt timestamp,
assigned group and closure communication" is.

Test each artefact against four properties:

| Property | Question |
|---|---|
| Existence | Does this artefact exist today, or is it something the organisation would have to start producing? Say which. |
| Attribution | Does it show *who* performed the activity? |
| Timing | Does it show *when*, precisely enough to test the TAT? |
| Completeness | Can you get the whole population from it, or only samples? A control tested on a sample of an incomplete population proves very little. |

Where the policy names a record ("acknowledgement to the customer", "register of
complaints"), that artefact is `SOURCE-EXPLICIT`. Everything else is
`PROPOSED-EVIDENCE`, and the system of record and retention period are
`not_specified` unless the policy states them.

## 4. Audit test procedures

A test procedure has a population, a selection basis, a procedure and a conclusion
criterion. Steps that lack these read as activity rather than assurance.

Pattern:

```
1. Obtain the population of <events> for <period> from <system / register>.
   [state how completeness of that population will be established]
2. Select <basis: risk-based / statistical / full population> of <n>.
3. For each item: trace <source event> to <system record>; recompute <elapsed time /
   amount / threshold>; inspect <approval / communication / evidence artefact>.
4. Conclude: the control operates effectively if <criterion>, e.g. every sampled item
   was closed within the stated TAT or carries a documented, approved exception.
```

Where full-population testing is feasible — TATs, amounts, thresholds usually are,
because they are computable from a data extract — propose it rather than sampling.
It is cheaper and it is stronger evidence. Say plainly when the population's
completeness cannot itself be evidenced; that is the weak point of most such tests
and reviewers should see it.

Every step you wrote carries `PROPOSED-TEST`.

## 5. RACI without invention

- **Accountable** — one role, answerable for the outcome. If the policy does not name
  one, `not_specified` plus an open question. Do not distribute accountability across
  a committee unless the document does.
- **Responsible** — performs the work. Often the same as accountable in a policy that
  names only one party; say so rather than manufacturing a split.
- **Consulted** — named in the document as being involved (Legal, Compliance, a
  committee). Only if named.
- **Assurance** — Internal Audit, Risk, Compliance monitoring. Almost always your
  proposal; label it.

A RACI where every row is populated is a warning sign, not an achievement. Real
policies are silent on ownership more often than not, and the gaps are the most
actionable output of the whole exercise.

## 6. Gaps worth reporting

While designing controls you will notice things the reviewer needs to know. Record
them as open questions rather than fixing them silently:

- An obligation with no stated owner, no stated deadline, or no stated evidence.
- A deadline with no consequence for breach — nothing makes the TAT bite.
- A control the policy names but no evidence artefact that would demonstrate it ran.
- A threshold with no stated approval path above it.
- Two obligations whose timings cannot both be met (an escalation due before the
  investigation it depends on).
- An obligation that depends on a system, register or committee the policy never
  establishes.

These are the findings a policy owner actually acts on. They come free with careful
extraction and are lost entirely by a summary.

## 7. Worked transformation

```yaml
source_explicit_requirement:
  requirement_id: GRV-R-001
  what: "Record complaints in the CRM and assign them to the respective group for resolution."
  source: "grievanceredressalpolicy.pdf pp.4-5, Complaint intake"
  label: SOURCE-EXPLICIT

proposed_control:
  control_id: CTRL-GRV-001
  label: PROPOSED-CONTROL
  objective: "No customer complaint is resolved without a traceable intake, assignment and closure record."
  control_type: preventive_and_detective
  automation: it_dependent_manual
  frequency: per_complaint, with monthly exception review
  performer: not_specified          # policy names no owner - open question raised
  evidence:
    - artefact: "CRM case ID with channel receipt timestamp"
      label: PROPOSED-EVIDENCE
    - artefact: "Assigned group and status history"
      label: PROPOSED-EVIDENCE
    - artefact: "Closure communication to the customer"
      label: PROPOSED-EVIDENCE
  test_procedure:
    - step: "Obtain the full population of complaints received in the period across all intake channels; reconcile channel-level counts to the CRM to establish completeness."
      label: PROPOSED-TEST
    - step: "Trace a risk-based sample from original receipt (email, branch register, call log) to CRM case creation."
      label: PROPOSED-TEST
    - step: "Verify assignment to a group and inspect resolution and closure evidence."
      label: PROPOSED-TEST
    - step: "Recompute elapsed time from receipt to closure and compare with the applicable TAT."
      label: PROPOSED-TEST
  open_questions:
    - "Policy does not name an owner for complaint intake and assignment. Who is accountable?"
    - "Are all intake channels captured in the CRM, or do some (branch walk-in, post) rely on manual entry? Completeness of the tested population depends on this."
```

Notice the second open question. It came from designing the test, not from reading
the policy — that is the point of doing Stage 4 properly rather than pasting a
generic control library over the requirement register.
