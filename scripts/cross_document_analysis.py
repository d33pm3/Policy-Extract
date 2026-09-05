#!/usr/bin/env python3
"""Stage 5 - Cross-document duplicate, conflict and dependency analysis.

Policies are written one at a time and read one at a time, which is how an
organisation ends up with a 30-day TAT in one document and 21 days in another for
the same event. This script proposes relationships between requirements across
documents; it never concludes one.

Similarity proposes. A human confirms by reading both quotes. In particular the
script will not decide that one policy supersedes another - only a document can
say that.

Detections
  duplicate / overlapping     high lexical similarity across documents
  timing conflict             similar obligation, different deadline value/unit/basis
  role conflict               similar obligation, different accountable role
  threshold conflict          similar obligation, different money/percentage value
  dependency                  requirement whose text points at another document
  missing reference           a referenced document absent from the corpus

Usage:
    python3 cross_document_analysis.py --kb ./kb [--threshold 0.62]

Exit codes: 0 = registers written; 1 = inputs missing.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

STOP = set("""a an the and or of to in for on at by with from as is are be been shall must will
may not no any all such that this these those which who whom whose it its their his her our your
if where unless provided case event subject except per each other than into upon within also
bank customer policy shall_not""".split())

REF_PAT = re.compile(
    r"\b((?:[A-Z][A-Za-z&/'\-]+\s+){0,5}"
    r"(?:Policy|Procedure|SOP|Manual|Guidelines?|Charter|Code|Framework|Circular|"
    r"Master Direction|Annexure|Schedule|Standard))\b"
)

TITLE_NOISE = re.compile(r"\b(this|the|our|said|above|following|such|a|an)\b", re.I)


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(w) > 2 and w not in STOP]


def tfidf_vectors(docs: list[str]) -> list[dict[str, float]]:
    toks = [tokens(d) for d in docs]
    df: Counter = Counter()
    for t in toks:
        df.update(set(t))
    n = len(docs) or 1
    vecs = []
    for t in toks:
        tf = Counter(t)
        v = {w: (c / len(t)) * math.log((n + 1) / (df[w] + 1)) + 1e-9 for w, c in tf.items()} if t else {}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


def load_requirements(kb: Path) -> list[dict]:
    p = kb / "02-requirements" / "requirements.json"
    if not p.exists():
        raise SystemExit(f"ERROR: {p} missing. Complete Stage 3 first.")
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("requirements", []) if isinstance(data, dict) else data


def load_register(kb: Path) -> list[dict]:
    p = kb / "source-register.json"
    if not p.exists():
        raise SystemExit("ERROR: source-register.json missing. Run Stage 0.")
    return json.loads(p.read_text(encoding="utf-8"))


def deadline_signature(r: dict) -> tuple | None:
    if r.get("deadline_value") is None:
        return None
    return (float(r["deadline_value"]), r.get("deadline_unit"), r.get("deadline_basis"))


def money_signature(r: dict) -> set[str]:
    return {re.sub(r"[^0-9.]", "", nf.get("verbatim", ""))
            for nf in (r.get("numeric_facts") or [])
            if nf.get("kind") in ("money", "percentage", "threshold") and nf.get("verbatim")}


def role_signature(r: dict) -> str:
    v = (r.get("accountable_role") or "").strip().lower()
    return "" if v in ("", "not_specified") else re.sub(r"\s+", " ", v)


def cite(r: dict) -> str:
    return f"{r.get('source_file')} p.{r.get('source_page_start')} / {r.get('source_section')}"


def classify_pair(a: dict, b: dict, sim: float) -> tuple[str, list[str]]:
    reasons = []
    da, db = deadline_signature(a), deadline_signature(b)
    if da and db and da != db:
        reasons.append(f"timing differs: {a.get('deadline_verbatim') or da} vs {b.get('deadline_verbatim') or db}")
    ra, rb = role_signature(a), role_signature(b)
    if ra and rb and ra != rb:
        reasons.append(f"accountable role differs: {a['accountable_role']} vs {b['accountable_role']}")
    ma, mb = money_signature(a), money_signature(b)
    if ma and mb and ma != mb:
        reasons.append(f"values differ: {sorted(ma)} vs {sorted(mb)}")
    if reasons:
        return "POTENTIALLY_CONFLICTING", reasons
    if sim >= 0.85:
        return "DUPLICATE", [f"lexical similarity {sim:.2f} with no differing timing, role or value"]
    return "OVERLAPPING", [f"lexical similarity {sim:.2f}"]


def reviewer_question(kind: str, a: dict, b: dict, reasons: list[str]) -> str:
    if kind == "POTENTIALLY_CONFLICTING":
        return (f"Which position governs where both apply - {a['requirement_id']} ({cite(a)}) or "
                f"{b['requirement_id']} ({cite(b)})? Difference: {'; '.join(reasons)}. "
                "Neither document has been read as superseding the other.")
    if kind == "DUPLICATE":
        return (f"Are {a['requirement_id']} and {b['requirement_id']} the same commitment stated twice? "
                "If so, which document is the system of record, and should the other cross-refer to it?")
    return (f"Do {a['requirement_id']} and {b['requirement_id']} need to be executed as one process, "
            "or are they genuinely distinct commitments?")


def find_references(reqs: list[dict], register: list[dict]) -> tuple[list[dict], list[dict]]:
    known = []
    for d in register:
        known.append(("title", (d.get("title") or "").lower()))
        known.append(("slug", (d.get("slug") or "").replace("-", " ").lower()))
        known.append(("file", (d.get("file_name") or "").lower()))

    deps, missing = [], []
    seen_missing: set[str] = set()
    for r in reqs:
        texts = [r.get("source_quote") or ""] + list(r.get("cross_policy_references") or [])
        hits: set[str] = set()
        for t in texts:
            for m in REF_PAT.finditer(t):
                name = TITLE_NOISE.sub(" ", m.group(1))
                name = re.sub(r"\s+", " ", name).strip()
                if len(name) > 6:
                    hits.add(name)
        for name in sorted(hits):
            low = name.lower()
            match = next((v for _, v in known if v and (low in v or v in low)), None)
            row = {"requirement_id": r["requirement_id"], "source": cite(r), "referenced": name}
            if match:
                row["resolved_to"] = match
                deps.append(row)
            else:
                deps.append({**row, "resolved_to": None})
                key = low
                if key not in seen_missing:
                    seen_missing.add(key)
                    missing.append({"referenced": name, "first_seen_in": r["requirement_id"],
                                    "source": cite(r)})
    return deps, missing


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in row) + " |")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 5 cross-document analysis")
    ap.add_argument("--kb", required=True)
    ap.add_argument("--threshold", type=float, default=0.62,
                    help="Lexical similarity floor for proposing a relationship (default 0.62)")
    ap.add_argument("--max-pairs", type=int, default=400)
    args = ap.parse_args()

    kb = Path(args.kb)
    reqs = load_requirements(kb)
    register = load_register(kb)
    out = kb / "04-cross-policy-analysis"
    out.mkdir(parents=True, exist_ok=True)

    corpus = [" ".join(filter(None, [r.get("what"), r.get("trigger"), r.get("source_section"),
                                     r.get("source_quote")])) for r in reqs]
    vecs = tfidf_vectors(corpus)

    pairs = []
    for i in range(len(reqs)):
        for j in range(i + 1, len(reqs)):
            if reqs[i].get("source_document_id") == reqs[j].get("source_document_id"):
                continue
            sim = cosine(vecs[i], vecs[j])
            if sim >= args.threshold:
                pairs.append((sim, i, j))
    pairs.sort(reverse=True)
    pairs = pairs[: args.max_pairs]

    buckets: dict[str, list] = defaultdict(list)
    for sim, i, j in pairs:
        kind, reasons = classify_pair(reqs[i], reqs[j], sim)
        buckets[kind].append((sim, reqs[i], reqs[j], reasons))

    rows = [[f"{a['requirement_id']}", cite(a), f"{b['requirement_id']}", cite(b),
             f"{sim:.2f}", reviewer_question("DUPLICATE", a, b, rs)]
            for sim, a, b, rs in buckets.get("DUPLICATE", [])]
    body = ["# Duplicate / near-duplicate requirement register", "",
            "Proposed by lexical similarity across documents. **Confirm by reading both quotes.** "
            "Keeping both records is the safe default; merging is a reviewer decision.", ""]
    body += md_table(["Req A", "Source A", "Req B", "Source B", "Sim", "Reviewer question"], rows) if rows \
        else ["_No duplicate candidates above threshold._"]
    (out / "duplicate-requirement-register.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    rows = [[a["requirement_id"], cite(a), b["requirement_id"], cite(b), "; ".join(rs),
             reviewer_question("POTENTIALLY_CONFLICTING", a, b, rs)]
            for sim, a, b, rs in buckets.get("POTENTIALLY_CONFLICTING", [])]
    body = ["# Conflict and ambiguity register", "",
            "Requirements that address a similar subject but differ on timing, role or value. "
            "**POTENTIALLY_CONFLICTING is a question, not a finding.** No supersession has been "
            "inferred; only a document can establish that.", ""]
    body += md_table(["Req A", "Source A", "Req B", "Source B", "Difference", "Reviewer question"], rows) if rows \
        else ["_No conflict candidates detected._"]
    (out / "conflict-and-ambiguity-register.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    rows = [[a["requirement_id"], cite(a), b["requirement_id"], cite(b), f"{sim:.2f}"]
            for sim, a, b, rs in buckets.get("OVERLAPPING", [])]
    body = ["# Overlapping requirement candidates", ""]
    body += md_table(["Req A", "Source A", "Req B", "Source B", "Sim"], rows) if rows \
        else ["_No overlaps above threshold._"]
    (out / "overlapping-requirement-register.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    deps, missing = find_references(reqs, register)
    rows = [[d["requirement_id"], d["source"], d["referenced"],
             d["resolved_to"] or "**NOT IN CORPUS**"] for d in deps]
    body = ["# Cross-policy dependency register", "",
            "Documents each requirement points at. A cross-reference is not evidence: an unresolved "
            "reference means the obligation cannot be fully assessed from this corpus.", ""]
    body += md_table(["Requirement", "Source", "Referenced document", "Resolved to"], rows) if rows \
        else ["_No cross-document references detected._"]
    (out / "cross-policy-dependency-register.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    rows = [[m["referenced"], m["first_seen_in"], m["source"]] for m in missing]
    body = ["# Missing referenced document register", "",
            "Referenced by a requirement in this corpus but not supplied. Obtain these before any "
            "completeness claim; until then, every dependent requirement is source-limited.", ""]
    body += md_table(["Referenced document", "First seen in", "Source"], rows) if rows \
        else ["_All detected references resolve within the corpus._"]
    (out / "missing-referenced-document-register.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    bydoc: dict[str, list[dict]] = defaultdict(list)
    for r in reqs:
        bydoc[r.get("source_document_id", "?")].append(r)
    body = ["# Obligation-to-policy map", ""]
    for doc in register:
        rs = bydoc.get(doc["document_id"], [])
        body += [f"## {doc['document_id']} - {doc.get('title') or doc['file_name']}", "",
                 f"- Requirements: {len(rs)}",
                 f"- Types: " + (", ".join(f"{k}={v}" for k, v in
                                           Counter(x.get('requirement_type') for x in rs).most_common()) or "none"),
                 ""]
    (out / "obligation-to-policy-map.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    print(f"Cross-document analysis complete over {len(reqs)} requirements from {len(register)} documents.")
    print(f"  duplicates: {len(buckets.get('DUPLICATE', []))}  "
          f"potential conflicts: {len(buckets.get('POTENTIALLY_CONFLICTING', []))}  "
          f"overlaps: {len(buckets.get('OVERLAPPING', []))}")
    print(f"  dependencies: {len(deps)}  missing referenced documents: {len(missing)}")
    print(f"Registers written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
