# Stage 5 — Cross-document harmonisation

Load when two or more documents are in scope.

## Why a corpus behaves differently from a document

Each policy was drafted by a different owner, approved on a different date, and
edited without the others open. The predictable results: the same obligation stated
twice with different words, the same event given two different turnaround times,
the same duty assigned to two different functions, and a chain of references to
documents nobody supplied. None of these are visible while reading one document at
a time, and all of them determine whether the corpus can actually be complied with.

`cross_document_analysis.py` proposes candidates. Your job is the confirmation, and
the discipline is simple: **read both quotes before you call anything a conflict.**

## 1. Relationship taxonomy

| Relationship | Test | Default action |
|---|---|---|
| `DUPLICATE` | Same commitment, same actor, same timing, same threshold — stated in two documents | Keep both records; ask which document is the system of record |
| `OVERLAPPING` | Related subject, partially shared scope, neither subsumes the other | Keep both; map the boundary |
| `DEPENDENT` | One cannot be performed without the other, or one names the other as its mechanism | Link; check the dependency is available |
| `POTENTIALLY_CONFLICTING` | Same subject, incompatible timing, role, threshold or condition | Raise a reviewer question; change nothing |
| `DISTINCT` | Superficial lexical similarity only | Dismiss with a one-line reason |

`POTENTIALLY_CONFLICTING` is a question, never a finding. Two documents can hold
different TATs legitimately — different products, different channels, different
customer segments, a general rule and a specific one. Only the reviewer knows which.

## 2. Deterministic conflict tests

Run these on any pair the similarity search proposes:

**Timing.** Compare `deadline_value`, `deadline_unit` and `deadline_basis`. Note that
30 calendar days and 30 working days differ by about two weeks — a basis mismatch is
a conflict even when the number matches. Where one record says `not_specified`, that
is a gap, not a conflict.

**Role.** Compare `accountable_role`, ignoring case and honorifics. Treat a
difference as a conflict only when both are `role_basis: explicit_source`; an
inferred role differing from a stated one is your inference to correct.

**Threshold and amount.** Compare `numeric_facts` of kind money, percentage,
threshold. Compare the digits, not the formatting — ₹1,00,000 and ₹1 lakh are the
same value written two ways, and flagging it as a conflict wastes reviewer attention.

**Condition and scope.** Compare `applicability` and `exceptions_conditions`. The
most common real conflict is a general obligation in one document and an unqualified
carve-out in another.

**Version and supersession.** Compare the documents' approval/effective dates. A
later document is *not* automatically superseding — say only what the dates show,
and put the supersession question to the reviewer.

## 3. Dependency and missing-reference mapping

Every requirement that names another document creates a dependency. Resolve it
against the corpus; where it does not resolve, it goes in the
missing-referenced-document register and every dependent requirement is marked
source-limited.

This matters more than it looks. A grievance policy that says "compensation shall be
paid as per the Customer Compensation Policy" contains, by itself, no compensation
obligation at all. Extracting it as though it did is a completeness failure that
looks like thoroughness.

Typical dependency shapes in a policy corpus:

```
Customer Rights Policy
  ├─ requires public availability of the Cheque Collection, Grievance Redressal,
  │  Compensation and Collection/Repossession policies
  ├─ links the right to grievance redressal → Grievance Redressal Policy
  └─ links compensation entitlements       → Customer Compensation Policy

Customer Relations Policy
  ├─ links unauthorised electronic banking transaction reporting → grievance intake
  ├─ links customer liability determination → investigation procedure
  └─ links compensation → Customer Compensation Policy

Suitability & Appropriateness Policy
  ├─ references the Record Retention Policy
  ├─ requires a product / process approval framework
  └─ assigns assurance to Compliance and Internal Audit
```

Read that shape as a graph: the leaf documents (Compensation, Record Retention) carry
obligations that several other policies rely on, so an error there propagates. Extract
and validate the leaves first where you can.

## 4. Enterprise views worth building

Once relationships are confirmed:

- **Obligation-to-policy map** — which document is the source of record for each
  subject. The answer to "where is this actually written down".
- **Organisation-wide RACI** — every named role and everything it owns across the
  corpus. Concentrations and orphans both show up immediately.
- **TAT, threshold and liability register** — every timing and value in one table,
  sorted by subject. Inconsistencies that were invisible across seven PDFs become
  obvious in twenty rows.
- **Regulatory obligation register** — every citation as printed. Not verified, not
  interpreted; a Compliance work-list.
- **Missing referenced document register** — the corpus gaps, which is usually the
  first thing to act on.

## 5. Reviewer questions that get answered

A question a reviewer can answer in one sitting names both records, both sources,
the specific difference, and the decision needed. Compare:

> Weak: "There appear to be conflicting timelines between the grievance and
> compensation policies."

> Strong: "`GRV-R-003` (grievanceredressalpolicy.pdf p.7, *Resolution of complaints*)
> requires resolution within 30 working days for fraud and old-record cases.
> `CMP-R-011` (compensationpolicy.pdf p.9, *Timeline for compensation*) requires
> compensation within 10 calendar days of the complaint being upheld. If a fraud
> complaint is upheld on day 30, the compensation clock starts then — is that the
> intended reading, or is compensation expected within the 30-day window? Neither
> document states supersession."

The strong version can be answered yes or no. The weak version generates a meeting.
