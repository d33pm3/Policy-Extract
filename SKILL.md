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

See README.md for the public quick start. The full stage contract, G1–G8 guardrails,
run sequence, output tree, honesty rules and maintenance commands live in this file
as shipped in the sanitized 1.2.0 release.

The complete operating text is identical to the enclosed skill package after these
public-release edits:

- Skill root is the clone of this repository.
- Default knowledge-base output is `./policy-kb`.
- Scripts are invoked as `python3 scripts/<script>.py` from the skill root.
- No historical client pack is a gold file.
- Live-version pin is `RELEASE_PIN.json` at this repository root (min 1.2.0).
