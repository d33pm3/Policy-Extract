---
name: policy-extractor
description: Evidence-linked policy and SOP compliance extraction pipeline. Turns policies, SOPs, procedures, terms-and-conditions, circulars and annexures into an auditable knowledge base including source register, page-aware source layer, candidate-clause ledger, atomic requirement register, What/Why/Who/When/How/Evidence compliance pack, control/RACI/evidence matrix, cross-document conflict and dependency registers, and a human review-gate log. Use it whenever a policy or SOP must become requirements, obligations, controls, a RACM or control matrix, a RACI, an evidence or TAT/threshold register, a compliance pack, or an audit-ready traceability trail — or when two or more governance documents must be reconciled for duplicates, conflicting timelines, inconsistent roles or missing referenced policies. Trigger on casual phrasings too — break this policy into requirements, what controls do we need for this SOP, do these policies contradict each other. Not for legal research, drafting policy text, or contract redlining.
license: Apache-2.0
metadata:
  type: workflow
  version: "1.2.0"
  source_architecture: policy-extraction
  output_format: policy-kb-v1
---

# Policy Extractor — Source-Grounded Compliance Pipeline

## 0. What this skill is for, and why it is built this way

Policy documents get read once, summarised badly, and then argued about. This skill
replaces that with a pipeline whose output can survive an audit: every requirement
carries the file, the page, the section heading and the verbatim sentence that
created it, and every AI-originated idea is visibly separated from what the document
actually says.

Two failure modes drive the whole design:

1. **Silent omission.** A model that reads a 15-page policy will reliably find the
   headline obligations and reliably miss the one buried in a table footnote or an
   annexure. So the pipeline finds candidate clauses *deterministically first*
   (Stage 2), then requires every candidate to receive a disposition. Recall becomes
   a measurable number instead of a hope.
2. **Silent invention.** A model asked for "controls and owners" will happily supply
   plausible ones the policy never mentioned. So the schema forces every field into
   one of two classes — sourced or proposed — and the validator mechanically rejects
   records that blur them.

Everything else in this file exists to serve those two properties.

## 1. Skill architecture (progressive disclosure)

- **This file** — the operating contract, the stage sequence, the guardrails, and
  the run commands. Always in effect.
- **`scripts/`** — deterministic executables. Anything mechanically checkable lives
  here rather than in prose, because prose instructions degrade and scripts do not:
  - `intake_register.py` — Stage 0: SHA-256, page count, text-quality triage, manifest
  - `build_source_layer.py` — Stage 1: page-aware Markdown, table objects, page renders
  - `find_candidates.py` — Stage 2: candidate-clause ledger + numeric/table-cell ledger
  - `validate_pack.py` — Stage 6: all automated gates, including quote and numeric reconciliation
  - `cross_document_analysis.py` — Stage 5: duplicate / conflict / dependency / missing-reference detection
  - `build_packs.py` — Stage 7: renders Markdown packs, registers, CSV and SQLite
  - `run_regression_tests.py` — self-test after any edit to this skill
- **`references/`** — load on demand:
  - `stage-specs.md` — the full Stage 0–7 specification. Load before a first run on a new corpus.
  - `atomicity-and-recall.md` — Stage 2–3 split and recall contract. Load before writing requirement records. Stage 3 is blocked until `stage3_preflight.py` passes.
  - `gold-pack-policy.md` — no historical client pack is a gold file. Do not regress against it.
  - `schema-and-labels.md` — field-by-field schema semantics, the label taxonomy, controlled vocabularies. Load before writing requirement records.
  - `control-and-evidence-design.md` — Stage 4 patterns for proposing controls, evidence and audit tests without overreaching. Load when the user wants a control matrix or RACM input.
  - `cross-document-analysis.md` — Stage 5 comparison rules and reviewer-question formats. Load when two or more documents are in scope.
  - `review-gates-and-failure-modes.md` — the five review gates, the approval lifecycle, and the failure-mode register FM-1..FM-14. Load before declaring anything final.
- **`prompts/`** — `extraction.md`, `verification.md`, `cross-policy-analysis.md`.
  Use these verbatim when delegating a stage to a subagent, so a delegated run is
  held to the same contract as a direct one.
- **`schemas/policy-requirement.schema.json`** — the canonical JSON Schema the
  validator enforces.
- **`assets/`** — output templates (compliance pack and requirement record). Packs,
  control matrix, RACI, TAT/threshold register, conflict register and approval log
  are rendered by `build_packs.py` into the same output tree as the source skill.

**Runtime.** Skill root is the clone of this repository (the directory that
contains `SKILL.md`, `VERSION` and `scripts/`). Prefer invoking scripts from
that root. Default knowledge-base output is `./policy-kb` unless the caller
sets another `--out-dir` / `--kb`. Verified engines are `pdfplumber` (primary)
and `pypdf` (fallback); page renders use `pdftoppm`; OCR uses `tesseract`.
PyMuPDF (`fitz`) is not assumed. `jsonschema` is optional — if missing,
`validate_pack.py` still runs G1–G8 and C1, and warns on C2 schema validation.
Always invoke scripts as `python3 scripts/<script>.py` from the skill root.

## 2. Mandatory compliance guardrails

These are the non-negotiables. The validator enforces G1–G7 mechanically; G8 is a
process gate you must not declare passed on your own authority.

| # | Guardrail | Enforcement |
|---|---|---|
| G1 | Every requirement carries source file, source page, section heading, and a verbatim supporting quote | `validate_pack.py` re-reads the cited page and fails any record whose quote is not found there |
| G2 | One requirement record = one independently testable commitment | Compound-obligation detector flags multi-verb, multi-actor and conjunctive records for split |
| G3 | Money, percentages, timings, units, trigger events, exceptions and conditions are preserved exactly | Numeric reconciliation: every number in a structured field must appear in the quote or on the cited page |
| G4 | Where the policy does not specify a role, deadline or procedure, output `not_specified` — never a guess | Sentinel-value check; unsourced free text in role/deadline fields fails |
| G5 | Any AI-proposed control, evidence artefact or audit test is labelled `PROPOSED-CONTROL`, `PROPOSED-EVIDENCE` or `PROPOSED-TEST` | Label check on every control/evidence/test object |
| G6 | Legal or regulatory interpretation is routed to Legal/Compliance review, never stated as a conclusion | Interpretation-language detector sets `REQUIRES-LEGAL-REVIEW` and blocks approval |
| G7 | Tables carrying TATs, liability slabs, amounts, thresholds and eligibility rules require visual source reconciliation | Table-derived records must carry `visual_reconciliation` with a rendered page image path and a reviewer initial |
| G8 | Nothing is `final`/`approved` until policy owner, Compliance/Legal (where applicable), Operations and Internal Audit have completed their review gates | `validate_pack.py` refuses `status: approved` unless every applicable gate object is signed; you never sign a gate yourself |

**The boundary that makes this work.** Sort every statement you produce into exactly
one of four classes, and label it:

| Class | You may generate it? | Label | Who signs it off |
|---|---|---|---|
| Source fact — the policy's own words, numbers, roles, deadlines | Yes, with quote + page + section | `SOURCE-EXPLICIT` | Document analyst |
| Structured extraction — normalised representation of a source fact | Yes | `SOURCE-EXPLICIT` | Document analyst + policy owner |
| Operational inference — a step, RACI slot, control, evidence or test the policy did not state | Yes, but never silently | `SOURCE-INFERRED`, `PROPOSED-CONTROL`, `PROPOSED-EVIDENCE`, `PROPOSED-TEST` | Policy owner / Operations / Internal Audit |
| Legal interpretation — what a law or regulation means or requires | Flag only, never conclude | `REQUIRES-LEGAL-REVIEW` | Legal / Compliance |

When you catch yourself about to write a role, a deadline, a control or a regulatory
consequence that you cannot point to in the text, that is exactly the moment G4 and
G5 exist for. Write `not_specified`, or write it as a `PROPOSED-*` object. Both are
useful to a reviewer; a confident guess is worse than useless because it is
indistinguishable from a fact.

## 3. Run sequence

Work stage by stage. Each stage has a stop rule; do not carry an unresolved stop
rule forward, because every downstream artefact inherits the defect.

```
Stage 0  Intake, classify, preserve        → source-register.yaml / .csv
Stage 1  Structural ingestion              → 01-source-layer/<DOC_ID>/{document.md,tables.json,pages/}
Stage 2  Candidate clause ledger           → 02-candidates/<DOC_ID>-candidates.json
Stage 3  Atomic requirement extraction     → 02-requirements/requirements.json
Stage 4  Control, evidence, RACI design    → controls embedded in requirements.json
Stage 5  Cross-document harmonisation      → 04-cross-policy-analysis/*.md
Stage 6  Validation + human review gates   → 05-quality-assurance/*.md
Stage 7  Publish + archive                 → 03-policy-compliance-packs/, 04-enterprise-views/
```

Set `SKILL` to this repository root and `KB` to `./policy-kb`
unless the user names another output directory.

### Stage 0 — Intake

```bash
python3 $SKILL/scripts/intake_register.py --inputs <dir-or-files> --out-dir $KB
```

Produces `source-register.yaml`, hashes every original, records page count, detects
scanned/low-text pages, and assigns a `DOC_ID` and a processing path. **Stop rule:**
no semantic work until every file has an ID, a hash, a page count and a path.

### Stage 1 — Source layer

```bash
python3 $SKILL/scripts/build_source_layer.py --kb $KB --doc-id ALL
```

Emits page-marked Markdown (`<!-- source: DOC_ID p.4 -->`), a separate `tables.json`
with per-table page and cell data, and — for any page carrying a table of TATs,
amounts, slabs or thresholds — a rendered PNG under `pages/`. Add `--ocr` for
low-text pages; OCR blocks are flagged, never silently corrected.

**Read the rendered PNG with `read_file`** for every table page before you record
a numeric requirement from it. That is what G7 means by visual reconciliation: a
human-legible image, looked at, compared to the extracted cell. Text extraction
transposes columns in merged-cell tables often enough that this step earns its cost.

**Stop rule:** a conversion fails if a page, annexure, table or heading is missing or
its reading order is uncertain. Route it to OCR or manual review and log it in
`05-quality-assurance/parser-exceptions.md`.

### Stage 2 — Candidate clause ledger

```bash
python3 $SKILL/scripts/find_candidates.py --kb $KB --doc-id ALL
```

Deterministic pattern sweep for binding language, timing, governance, conditional
constructions, definitions, published contacts (email / URL / postal), forum
constitution and membership, and page-break sentences, plus a table-cell ledger
for every money value, percentage, duration and threshold, including annexure
templates. This is your recall denominator. Map annex and appendix candidates
with the same seriousness as body-text candidates.

**Stop rule:** no document is complete while a candidate carries
`disposition: pending`. Every candidate ends as `mapped` (to one or more requirement
IDs), `non_binding` (with a one-line reason), or `queued_for_review`.

### Stage 3 — Atomic requirement extraction

```bash
python3 $SKILL/scripts/stage3_preflight.py --kb $KB
```

**Stop rule:** do not write a requirement record until preflight prints
`PREFLIGHT PASSED`. That command confirms `atomicity-and-recall.md` and
`prompts/extraction.md` are the live 1.2.0 files. There is no fallback to an
older packaged `.skill`.

Read `references/schema-and-labels.md` and `references/atomicity-and-recall.md`,
then work **section by section, including every annexure and appendix**, not
document by document — carry the candidate ledger for that section beside you
and tick items off. Use `prompts/extraction.md` verbatim if delegating.

Coverage is the candidate disposition ratio plus C3 recall-surface hits.
Never treat requirement row count as quality.

**Recall classes that must not be absorbed into a neighbour.** Each of these is
its own record (or a typed `definition` / `exception` / `disclosure_requirement`):
named office or apex role; published email / URL / postal / portal; display or
notice-board duty; forum constitution, chair, membership; each bullet in a
function or oversight list; each independently testable verb in a coordinated
sentence; a TAT attached to only one verb in that sentence; a named alternative
dispute forum; a mechanism exclusion; a second mechanism after "in addition";
annex notes and appendix taxonomies; an end-to-end "record and track" duty;
each specifically named intake channel.

Purpose statements without binding language stay `non_binding`. Blank annexure
column headers are disclosure-format duties, not operational TATs. Clock start
in `trigger` or a control objective must be words from the quote — never
"from the decision date" when the source only says "within 30 days".

If a quote ends mid-sentence, extend `source_page_end` onto the next page and
finish the sentence. Do not publish a truncated quote.

Atomicity test — split when any of these differ: actor, action, object, trigger,
timing, applicability, channel, or consequence. A worked example:

> **Source:** "The Bank shall capture complaints, acknowledge them, resolve them
> within the applicable timelines, conduct a monthly audit and report results to the
> Committee."

> **Wrong:** one record saying all of that. Nothing in it can be tested on its own —
> a tester cannot pass or fail "capture, acknowledge, resolve, audit and report".

> **Right:** five records — capture-and-assign; acknowledge; resolve within TAT;
> monthly quality audit; report to Committee. Each has its own owner, trigger,
> deadline, evidence and test. Each can independently pass or fail.

Separate the organisation's obligation from the customer's obligation into different
records even when one sentence creates both — they have different owners and
different consequences.

Write records to `$KB/02-requirements/requirements.json` using
`assets/requirement-record.template.json` and
`schemas/policy-requirement.schema.json`.

### Stage 4 — Control, evidence and audit-test design

Load `references/control-and-evidence-design.md`. Attach to each requirement, clearly
labelled, a control objective, control type and frequency, the evidence artefacts
that would demonstrate performance, and a test procedure. Where the policy itself
names the control or the record, that part is `SOURCE-EXPLICIT`; everything you add
is `PROPOSED-*`. Never let a proposed control appear in the same unlabelled column
as a source requirement — that single formatting shortcut is how an AI suggestion
ends up in a board pack as policy.

### Stage 5 — Cross-document harmonisation

```bash
python3 $SKILL/scripts/cross_document_analysis.py --kb $KB
```

Load `references/cross-document-analysis.md`. The script proposes candidate
relationships (duplicate, overlapping, dependent, potentially conflicting, distinct)
using lexical similarity plus deterministic rules on timings, roles and thresholds.
Similarity **proposes**; you confirm by reading both quotes. Never conclude that one
policy supersedes another unless a document says so. Every referenced-but-absent
document goes into the missing-referenced-document register — a cross-reference is
not evidence.

### Stage 6 — Validation and human review gates

```bash
python3 $SKILL/scripts/validate_pack.py --kb $KB --report $KB/05-quality-assurance/validation-report.md
```

Exit 0 = all automated gates pass. Exit 2 = warnings only (record them). Exit 1 =
blocking failures; fix and re-run, maximum three repair cycles, then stop and report
the failing record IDs rather than forcing a pass.

Then the human gates. Load `references/review-gates-and-failure-modes.md`. Your job
is to *prepare* the review queue and state plainly what each reviewer must decide —
not to mark gates complete.

| Gate | Reviewer | Covers |
|---|---|---|
| Source fidelity | Document analyst | Pages, tables, headings, annexures, OCR exceptions |
| Policy meaning | Policy / business owner | Requirement meaning, applicability, ownership, exceptions |
| Regulatory mapping | Compliance / Legal | Citations and any interpretation flagged `REQUIRES-LEGAL-REVIEW` |
| Operational feasibility | Process owner / Operations | Procedures, evidence, RACI, implementation load |
| Assurance design | Internal Audit / Risk | Control design and audit-test procedures |

### Stage 7 — Publish

```bash
python3 $SKILL/scripts/build_packs.py --kb $KB
```

Renders per-policy compliance packs, the enterprise views (master requirement
register, control matrix, RACI, deadlines/thresholds/liability register, regulatory
obligation register, cross-policy dependencies), and machine-readable
`requirements.{json,csv,sqlite}`. Everything published while gates are open is
stamped `DRAFT — NOT APPROVED FOR OPERATIONAL USE`.

## 4. Output repository shape

Same output format as the source `policy-extraction` architecture:

```
<kb>/
├── README.md
├── source-register.yaml / .csv / .json
├── 01-source-layer/<DOC_ID>/{original.pdf,document.md,pages.json,tables.json,pages/,conversion-exceptions.md}
├── 02-candidates/<DOC_ID>-candidates.json
├── 02-requirements/requirements.{json,csv,md,sqlite}
├── 03-policy-compliance-packs/<policy-slug>.md
├── 04-enterprise-views/{master-compliance-requirement-register,master-control-matrix,RACI,
│                        deadlines-thresholds-and-liability-register,regulatory-obligation-register,
│                        cross-policy-dependencies,source-evidence-register}.md
├── 04-cross-policy-analysis/{obligation-to-policy-map,cross-policy-dependency-register,
│                             duplicate-requirement-register,conflict-and-ambiguity-register,
│                             missing-referenced-document-register}.md
├── 05-quality-assurance/{validation-report,source-coverage-report,parser-exceptions,
│                         numeric-table-reconciliation,review-and-approval-log}.md
└── CHANGELOG.md
```

## 5. Compliance pack structure

Each pack in `03-policy-compliance-packs/` follows `assets/compliance-pack.md`:
document identity and hash; scope and applicability; the requirement table
(`What / Why / Who / When / How / Evidence / Control / Source / Status`); TATs,
thresholds and liability values with their reconciliation status; exceptions and
carve-outs; cross-references (resolved and missing); proposed controls and tests in
their own clearly labelled section; open questions for each reviewer; and the
approval block, unsigned.

## 6. Answering in chat rather than building a repository

Users often ask a narrower question — "what are the TATs in this policy", "who owns
grievance escalation". Answer it directly, but keep the guardrails: cite file, page,
section and quote for every value; use `not_specified` where the policy is silent;
label any control or owner you propose. Skip the repository scaffolding for a
single-question ask, and offer the full pipeline as a next step rather than imposing
it. The guardrails are the point; the directory tree is just where they live when the
job is large.

## 7. Honesty at the end of a run

Close every substantive output by stating what was mechanically checked (which
scripts ran, their exit codes, the candidate disposition ratio, how many
numbers reconciled), what is judgement-dependent (atomisation, applicability,
proposed controls), and what remains open (unreviewed gates, missing referenced
documents, OCR-limited pages, low-confidence records, **every open G3 / G4 / C3
ID from the validation report**). Never describe output as compliant,
audit-ready, complete, approved or final while any review gate is open —
say `DRAFT — pending <gate name>` instead. Do not use any historical client pack as
an expected-output fixture. A reviewer who knows exactly where the soft spots
are can work with a draft; a reviewer who was told it was final cannot.

## 8. Maintenance

After any edit to this skill, run
`python3 scripts/assert_live_version.py`
then
`python3 scripts/run_regression_tests.py`
then
`python3 scripts/smoke_live_skill.py`.
All three must pass before the skill is treated as ready. Live path is this
repository root. A packaged `.skill` archive is an export, not a runtime fallback.
Pipeline scripts abort if `VERSION` is below 1.2.0 or `RELEASE_PIN.json` is
missing — there is no automatic rollback to v1.0.0 / v1.1.0.
