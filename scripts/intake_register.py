#!/usr/bin/env python3
"""Stage 0 - Intake, classification and source preservation.

Creates the immutable baseline the whole pipeline is traced back to: a SHA-256
per original file, a page count, a text-quality triage, a document-type hint and
a processing-path decision.

No semantic work may start until every input file appears in source-register.yaml
with an id, a hash, a page count and a processing path.

Usage:
    python3 intake_register.py --inputs ./policy-pdfs --out-dir ./kb
    python3 intake_register.py --inputs a.pdf b.pdf --out-dir ./kb

Exit codes: 0 = all files registered; 1 = no readable input; 2 = registered with
one or more files needing OCR or manual triage.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

LOW_TEXT_CHARS = 25  # a page with fewer characters than this is treated as scanned

DOC_TYPE_HINTS = [
    ("regulatory_circular", r"\b(circular|master direction|notification|gazette|rbi/\d|sebi/)\b"),
    ("terms_and_conditions", r"\b(terms and conditions|terms & conditions|schedule of charges)\b"),
    ("sop", r"\b(standard operating procedure|s\.o\.p\.|\bsop\b|process manual|work instruction)\b"),
    ("form_or_checklist", r"\b(application form|checklist|annexure\s+[a-z0-9]+\s*[-–:]\s*form)\b"),
    ("policy", r"\bpolicy\b"),
]

SLUG_STOPWORDS = {"the", "of", "on", "and", "for", "a", "an", "policy", "final", "v", "version"}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def words_from(text: str) -> list[str]:
    """Tokenise a title or filename into meaningful lowercase words."""
    raw = re.sub(r"\.pdf$", "", text or "", flags=re.I)
    raw = re.sub(r"^[0-9a-f]{6,}-", "", raw)          # strip upload hash prefixes
    raw = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw)     # split camelCase
    raw = re.sub(r"\d+$", "", raw)
    out: list[str] = []
    for tok in re.findall(r"[A-Za-z]+", raw):
        out.extend(split_concatenated(tok) if len(tok) > 12 and tok.islower() else [tok.lower()])
    return [w for w in out if w not in SLUG_STOPWORDS and len(w) > 1]


def slugify(title: str, file_name: str) -> str:
    words = words_from(title) or words_from(file_name)
    return "-".join(words[:5]) or "document"


def short_code(slug: str, taken: set[str]) -> str:
    parts = [p for p in slug.split("-") if p]
    if len(parts) >= 2:
        code = "".join(p[0] for p in parts[:4]).upper()
    elif parts:
        code = parts[0][:4].upper()
    else:
        code = "DOC"
    code = re.sub(r"[^A-Z0-9]", "", code)[:12] or "DOC"
    ladder = [code]
    for width in (2, 3, 4):
        if parts:
            ladder.append(re.sub(r"[^A-Z0-9]", "",
                                 (parts[0][:width] + "".join(p[0] for p in parts[1:3])).upper())[:12])
    ladder += [f"{code}{n}" for n in range(2, 100)]
    for alt in ladder:
        if alt and alt not in taken:
            taken.add(alt)
            return alt
    taken.add(code)
    return code


def probe_pdf(path: Path) -> dict:
    """Return page count, per-page char counts, table count and first-pages text."""
    info = {"page_count": 0, "page_chars": [], "table_count": 0, "head_text": "", "error": None}
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            info["page_count"] = len(pdf.pages)
            head = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                info["page_chars"].append(len(text))
                try:
                    info["table_count"] += len(page.find_tables())
                except Exception:
                    pass
                if i < 3:
                    head.append(text)
            info["head_text"] = "\n".join(head)
        return info
    except Exception as exc:  # noqa: BLE001 - fall through to pypdf
        info["error"] = f"pdfplumber: {exc}"

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        info["page_count"] = len(reader.pages)
        head = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            info["page_chars"].append(len(text))
            if i < 3:
                head.append(text)
        info["head_text"] = "\n".join(head)
        info["error"] = None
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"{info['error']}; pypdf: {exc}"
    return info


def classify_doc_type(text: str) -> str:
    low = (text or "").lower()
    for label, pattern in DOC_TYPE_HINTS:
        if re.search(pattern, low):
            return label
    return "unclassified"


METADATA_LINE = re.compile(
    r"^\s*(?:approved|adopted|reviewed|version|effective|issued|revised|classification|"
    r"confidential|internal|page\s+\d|document\s+(?:no|id)|last\s+updated|date\b)",
    re.I,
)
TITLE_NOUN = re.compile(
    r"\b(policy|policies|terms\s+and\s+conditions|procedure|sop|standard operating|manual|"
    r"guidelines?|charter|code|framework|circular|direction|schedule|annexure)\b", re.I,
)


def guess_title(text: str, fallback: str) -> str:
    """Pick the document's own title line."""
    lines = [ln.strip() for ln in (text or "").splitlines()]
    candidates = [ln for ln in lines[:15]
                  if 8 <= len(ln) <= 140 and re.search(r"[A-Za-z]", ln) and not METADATA_LINE.match(ln)]
    for ln in candidates:
        if TITLE_NOUN.search(ln) and not ln.rstrip().endswith((".", ";")):
            return ln
    for ln in candidates:
        if not ln.rstrip().endswith((".", ";")) and len(ln.split()) <= 14:
            return ln
    return candidates[0] if candidates else fallback


VOCAB = [
    "grievance", "redressal", "customer", "relations", "rights", "compensation", "cheque",
    "collection", "collections", "repossession", "security", "dues", "suitability",
    "appropriateness", "deceased", "depositors", "savings", "account", "terms", "conditions",
    "policy", "procedure", "manual", "charter", "code", "guidelines", "framework", "service",
    "protection", "privacy", "outsourcing", "vendor", "credit", "risk", "fraud", "kyc", "aml",
]


def split_concatenated(token: str) -> list[str]:
    """Split concatenated known words; leave unknown text alone."""
    out, i = [], 0
    low = token.lower()
    while i < len(low):
        match = next((w for w in sorted(VOCAB, key=len, reverse=True) if low.startswith(w, i)), None)
        if match:
            out.append(match)
            i += len(match)
        else:
            j = i
            while j < len(low) and not any(low.startswith(w, j) for w in VOCAB):
                j += 1
            chunk = low[i:j]
            if chunk:
                out.append(chunk)
            i = j if j > i else i + 1
    return [w for w in out if len(w) > 1]


DATE_PAT = re.compile(
    r"\b(?:(?:approved|effective|adopted|reviewed|version|dated)[^\n]{0,40}?)"
    r"((?:\d{1,2}[ /.-])?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[ /.-]?\d{0,2},?[ /.-]?\d{4}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.I,
)


def guess_dates(text: str) -> str:
    m = DATE_PAT.search(text or "")
    return m.group(1).strip() if m else "not_specified"


def text_quality(page_chars: list[int], table_count: int) -> tuple[str, list[int]]:
    low_pages = [i + 1 for i, c in enumerate(page_chars) if c < LOW_TEXT_CHARS]
    if not page_chars:
        return "unreadable", []
    if len(low_pages) == len(page_chars):
        return "scanned_image_only", low_pages
    if low_pages:
        return "hybrid_some_scanned_pages", low_pages
    if table_count:
        return "native_text_with_tables", []
    return "native_digital_text", []


def processing_path(quality: str) -> str:
    return {
        "native_digital_text": "text_primary",
        "native_text_with_tables": "text_primary_with_table_render",
        "hybrid_some_scanned_pages": "text_primary_with_ocr_fallback",
        "scanned_image_only": "ocr_required",
        "unreadable": "manual_triage_required",
    }.get(quality, "manual_triage_required")


def collect_inputs(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        p = Path(item).expanduser()
        if p.is_dir():
            files.extend(sorted(q for q in p.rglob("*.pdf") if q.is_file()))
        elif p.is_file():
            files.append(p)
    seen, unique = set(), []
    for f in files:
        key = f.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def yaml_dump(records: list[dict]) -> str:
    """Minimal deterministic YAML writer (no external dependency required)."""
    def scalar(v) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v)
        if s == "" or re.search(r'[:#\-\[\]{}&*!|>%@`"\']|^\s|\s$', s):
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
        return s

    lines = ["# Stage 0 source register - immutable intake baseline", "source_documents:"]
    for rec in records:
        first = True
        for k, v in rec.items():
            prefix = "  - " if first else "    "
            first = False
            if isinstance(v, list):
                if not v:
                    lines.append(f"{prefix}{k}: []")
                else:
                    lines.append(f"{prefix}{k}:")
                    for item in v:
                        lines.append(f"      - {scalar(item)}")
            else:
                lines.append(f"{prefix}{k}: {scalar(v)}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 0 intake register")
    ap.add_argument("--inputs", nargs="+", required=True, help="PDF files and/or directories")
    ap.add_argument("--out-dir", required=True, help="Knowledge-base root to create")
    ap.add_argument("--copy-originals", action="store_true",
                    help="Copy originals read-only into 01-source-layer/<DOC_ID>/original.pdf")
    args = ap.parse_args()

    files = collect_inputs(args.inputs)
    if not files:
        print("ERROR: no PDF inputs found", file=sys.stderr)
        return 1

    kb = Path(args.out_dir)
    for sub in ["01-source-layer", "02-candidates", "02-requirements",
                "03-policy-compliance-packs", "04-cross-policy-analysis",
                "04-enterprise-views", "05-quality-assurance"]:
        (kb / sub).mkdir(parents=True, exist_ok=True)

    records, needs_attention = [], 0
    taken_codes: set[str] = set()
    for idx, path in enumerate(files, start=1):
        doc_id = f"SRC-{idx:04d}"
        probe = probe_pdf(path)
        quality, low_pages = text_quality(probe["page_chars"], probe["table_count"])
        title = guess_title(probe["head_text"], path.stem)
        slug = slugify(title, path.name)
        rec = {
            "document_id": doc_id,
            "short_code": short_code(slug, taken_codes),
            "slug": slug,
            "file_name": path.name,
            "original_path": str(path.resolve()),
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
            "title": title,
            "document_type_hint": classify_doc_type(probe["head_text"]),
            "approval_or_effective_date_hint": guess_dates(probe["head_text"]),
            "page_count": probe["page_count"],
            "detected_table_count": probe["table_count"],
            "text_quality": quality,
            "low_text_pages": low_pages,
            "processing_path": processing_path(quality),
            "parse_error": probe["error"],
            "original_file_retained": True,
            "registered_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if quality in ("scanned_image_only", "unreadable", "hybrid_some_scanned_pages") or probe["error"]:
            needs_attention += 1
        records.append(rec)

        doc_dir = kb / "01-source-layer" / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        if args.copy_originals:
            import shutil

            dest = doc_dir / "original.pdf"
            shutil.copy2(path, dest)
            os.chmod(dest, 0o444)

    (kb / "source-register.yaml").write_text(yaml_dump(records), encoding="utf-8")
    (kb / "source-register.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    with (kb / "source-register.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
        w.writeheader()
        for rec in records:
            w.writerow({k: (";".join(map(str, v)) if isinstance(v, list) else v) for k, v in rec.items()})

    print(f"Registered {len(records)} document(s) into {kb}")
    for r in records:
        print(f"  {r['document_id']}  {r['short_code']:<8} p{r['page_count']:<4} "
              f"tables={r['detected_table_count']:<3} {r['text_quality']:<28} {r['file_name']}")
    if needs_attention:
        print(f"\nWARNING: {needs_attention} document(s) need OCR or manual triage before Stage 1.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
