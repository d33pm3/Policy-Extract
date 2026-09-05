# Cross-policy relationship prompt

Use for Stage 5 confirmation of the relationships `cross_document_analysis.py`
proposes. Supply the candidate pairs with both full records and both source quotes.

---

You will receive two or more source-linked requirement records from different
documents.

Determine the relationship between them, choosing exactly one:

- `DUPLICATE` — the same commitment, same actor, same timing, same threshold.
- `OVERLAPPING` — a related subject with partially shared scope; neither subsumes the
  other.
- `DEPENDENT` — one cannot be performed without the other, or one names the other as
  its mechanism.
- `POTENTIALLY_CONFLICTING` — the same subject with incompatible timing, role,
  threshold or condition.
- `DISTINCT` — superficial similarity only.

Rules:

- Read both quotes before deciding. Lexical similarity is a prompt to look, not
  evidence of equivalence.
- Do not decide that one document supersedes another unless a document says so.
  Different approval dates are a fact you may report; supersession is a conclusion you
  may not draw.
- Different timings are not automatically a conflict. Different products, channels,
  customer segments, or a general rule and a specific one can each justify a genuine
  difference. Say what the difference is and let the reviewer decide whether it is
  intended.
- Compare values by magnitude, not formatting: ₹1,00,000 and ₹1 lakh are the same
  value.
- Treat a calendar-day versus working-day difference as a real difference even when
  the number matches.
- Where one record says `not_specified` and the other names a value, that is a gap in
  the first document, not a conflict between the two.

For every finding, output:

1. Both requirement IDs and both full source citations (file, page, section).
2. The specific difference — the exact wording, threshold, timing or role that
   diverges, quoted from each.
3. A reviewer question that can be answered yes or no, or by choosing one of two
   named options. Name what changes depending on the answer.
4. What you did **not** determine, so nobody mistakes an open question for a
   resolution.
