# Policy-extractor

**Author:** DK Mendiratta

## This is / this is not

**This is** a skill plus deterministic scripts that turn policies and SOPs into an evidence-linked knowledge base.
**This is** a sourced-vs-proposed schema: document text is kept separate from proposed controls.
**This is** a G1–G8 validator built to catch silent omission and silent invention.
**This is not** a legal-research tool, a policy drafter, or a contract redliner.
**This is not** a one-command finished register — Stage 3 is written by an agent or a human.
**This is not** approved policy until G8 human review gates are signed.
**This is not** a substitute for a policy owner, Legal/Compliance, Operations, or Internal Audit.
**This is not** a live-web SEBI research tool or a filled client pack.

Evidence-linked policy and SOP compliance extraction.

This public repository is a self-contained release of the Policy Extractor
skill: a deterministic-first pipeline that turns policies, SOPs, procedures,
terms-and-conditions, circulars and annexures into an auditable knowledge
base. Every requirement carries the file, the page, the section heading and
the verbatim sentence that created it. AI-originated controls, evidence and
tests are labelled separately from what the document actually says.

Canonical source: https://github.com/d33pm3/Policy-Extract

Version: **1.2.0** · License: **Apache-2.0** · Author: **DK Mendiratta**

Under Apache-2.0 you may view, copy, modify, and use this code, including commercially, if you keep the license notice and attribution.

## Why this exists

Two failure modes drive the design.

1. **Silent omission.** A model that reads a 15-page policy finds the headline
   obligations and misses the footnote, annexure cell, or published mailbox.
   Stage 2 therefore finds candidate clauses deterministically first. Every
   candidate must receive a disposition. Recall is a number, not a hope.
2. **Silent invention.** A model asked for "controls and owners" will invent
   plausible ones the policy never mentioned. The schema forces every field
   into sourced or proposed. The validator rejects records that blur them.

This is not a legal-research tool, a policy drafter, or a contract redliner.

## Repository tree

```
Policy-Extract/
├── SKILL.md                          # operating contract, stages, guardrails
├── VERSION                           # 1.2.0
├── RELEASE_PIN.json                  # required-file pin + min version
├── LICENSE                           # Apache-2.0
├── SECURITY.md
├── requirements.txt
├── pyproject.toml
├── assets/                           # pack and record templates
├── prompts/                          # extraction / verification / cross-policy
├── references/                       # stage specs, schema labels, review gates
├── schemas/policy-requirement.schema.json
└── scripts/
    ├── intake_register.py            # Stage 0
    ├── build_source_layer.py         # Stage 1
    ├── find_candidates.py            # Stage 2
    ├── stage3_preflight.py           # gate before Stage 3
    ├── validate_pack.py              # Stage 6
    ├── cross_document_analysis.py    # Stage 5
    ├── build_packs.py                # Stage 7
    ├── assert_live_version.py        # rollback guard
    ├── run_regression_tests.py
    └── smoke_live_skill.py
```

## Quick start

```bash
git clone https://github.com/d33pm3/Policy-Extract.git
cd Policy-Extract
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export SKILL="$PWD"
export KB="$PWD/policy-kb"

python3 scripts/intake_register.py --inputs ./policy-pdfs --out-dir "$KB"
python3 scripts/build_source_layer.py --kb "$KB" --doc-id ALL
python3 scripts/find_candidates.py --kb "$KB" --doc-id ALL
python3 scripts/stage3_preflight.py --kb "$KB"
# Stage 3 is not a script. After PREFLIGHT PASSED, an agent or a human
# writes $KB/02-requirements/requirements.json using
# schemas/policy-requirement.schema.json and assets/requirement-record.template.json.
python3 scripts/cross_document_analysis.py --kb "$KB"
python3 scripts/validate_pack.py --kb "$KB" --report "$KB/05-quality-assurance/validation-report.md"
python3 scripts/build_packs.py --kb "$KB"
```

Optional engines: `pdftoppm` for page renders (G7), `tesseract` for OCR.

## Self-test

```bash
python3 scripts/assert_live_version.py
python3 scripts/run_regression_tests.py
python3 scripts/smoke_live_skill.py
```

All three must pass before a change is treated as ready.

## Guardrails (G1–G8)

| # | Rule |
|---|---|
| G1 | Quote + page + section on every requirement |
| G2 | One independently testable commitment per record |
| G3 | Numbers, timings, units preserved exactly |
| G4 | Silence is `not_specified`, never a guess |
| G5 | Proposed controls / evidence / tests are labelled `PROPOSED-*` |
| G6 | Legal interpretation is flagged, never concluded |
| G7 | Table TATs and slabs need visual reconciliation |
| G8 | `approved` requires signed human review gates |

Coverage is the candidate disposition ratio plus C3 recall-surface hits.
Requirement row count is not a quality metric. No historical client pack
is a gold file. See `references/gold-pack-policy.md`.

## Isolation

This public repository is a new build. It is not a fork, submodule, or
rename of any private repository. Do not mix trees.
