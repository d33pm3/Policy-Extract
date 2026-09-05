#!/usr/bin/env python3
"""Stage 1 - Structural ingestion and source reconstruction.

Produces the page-aware source layer every later citation resolves against:

    01-source-layer/<DOC_ID>/document.md    page-marked Markdown
    01-source-layer/<DOC_ID>/pages.json     {page -> raw text} citation backbone
    01-source-layer/<DOC_ID>/tables.json    per-table page, bbox, header and rows
    01-source-layer/<DOC_ID>/pages/p###.png rendered images for table/numeric pages
    01-source-layer/<DOC_ID>/conversion-exceptions.md

Usage:
    python3 build_source_layer.py --kb ./kb --doc-id ALL
    python3 build_source_layer.py --kb ./kb --doc-id SRC-0003 --ocr --render-all

Exit codes: 0 = clean; 2 = completed with exceptions logged; 1 = fatal.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

LOW_TEXT_CHARS = 25
RENDER_DPI = 150

NUMERIC_PAGE_PAT = re.compile(
    r"(₹|rs\.?\s*\d|inr\s*\d|\d+\s*%|per\s*cent|\bTAT\b|turn\s*around\s*time|"
    r"within\s+\d+\s+(?:working|calendar|business)?\s*days?|slab|threshold|"
    r"liability|compensation|penalty|charges?)",
    re.I,
)

HEADING_PAT = re.compile(
    r"^(?:\s*)("
    r"(?:\d+(?:\.\d+)*\.?\s+[A-Z][^\n]{2,90})"
    r"|(?:[A-Z][A-Z0-9 &/,'()\-\.]{5,80})"
    r"|(?:(?:Annexure|Schedule|Appendix|Chapter|Part|Section)\s+[-–:]?\s*[A-Z0-9IVX]+[^\n]{0,70})"
    r")\s*$"
)


def load_register(kb: Path) -> list[dict]:
    reg = kb / "source-register.json"
    if not reg.exists():
        raise SystemExit(f"ERROR: {reg} not found. Run intake_register.py (Stage 0) first.")
    return json.loads(reg.read_text(encoding="utf-8"))


def extract_pages(pdf_path: Path) -> tuple[dict[int, str], list[dict], list[str]]:
    pages: dict[int, str] = {}
    tables: list[dict] = []
    exceptions: list[str] = []
    try:
        import pdfplumber

        with pdfplumber.open(str(pdf_path)) as pdf:
            for pno, page in enumerate(pdf.pages, start=1):
                try:
                    pages[pno] = page.extract_text() or ""
                except Exception as exc:  # noqa: BLE001
                    pages[pno] = ""
                    exceptions.append(f"p.{pno}: text extraction failed ({exc})")
                try:
                    for tno, tbl in enumerate(page.find_tables(), start=1):
                        rows = tbl.extract()
                        rows = [[(c or "").strip().replace("\n", " ") for c in row] for row in rows or []]
                        if not rows or all(not any(r) for r in rows):
                            continue
                        tables.append({
                            "table_id": f"T{pno:03d}-{tno}",
                            "page": pno,
                            "bbox": [round(v, 2) for v in tbl.bbox],
                            "n_rows": len(rows),
                            "n_cols": max(len(r) for r in rows),
                            "header": rows[0],
                            "rows": rows[1:],
                        })
                except Exception as exc:  # noqa: BLE001
                    exceptions.append(f"p.{pno}: table detection failed ({exc})")
        return pages, tables, exceptions
    except Exception as exc:  # noqa: BLE001
        exceptions.append(f"pdfplumber unavailable/failed ({exc}); falling back to pypdf")

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        for pno, page in enumerate(reader.pages, start=1):
            pages[pno] = page.extract_text() or ""
        exceptions.append("Tables NOT extracted: pypdf fallback has no table model. "
                          "Reconcile every table value against the rendered page image.")
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"FATAL: cannot read {pdf_path}: {exc}")
    return pages, tables, exceptions


def ocr_page(pdf_path: Path, pno: int, workdir: Path) -> str:
    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        return ""
    workdir.mkdir(parents=True, exist_ok=True)
    stem = workdir / f"ocr-p{pno:03d}"
    try:
        subprocess.run(
            ["pdftoppm", "-f", str(pno), "-l", str(pno), "-r", "300", "-png",
             str(pdf_path), str(stem)],
            check=True, capture_output=True, timeout=120,
        )
        img = next(iter(sorted(workdir.glob(f"ocr-p{pno:03d}*.png"))), None)
        if img is None:
            return ""
        out = subprocess.run(["tesseract", str(img), "stdout", "--psm", "3"],
                             check=True, capture_output=True, timeout=180)
        return out.stdout.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def render_page(pdf_path: Path, pno: int, out_dir: Path) -> str | None:
    if not shutil.which("pdftoppm"):
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / f"p{pno:03d}"
    if any(out_dir.glob(f"p{pno:03d}*.png")):
        return str(next(iter(sorted(out_dir.glob(f"p{pno:03d}*.png")))))
    try:
        subprocess.run(
            ["pdftoppm", "-f", str(pno), "-l", str(pno), "-r", str(RENDER_DPI),
             "-png", "-singlefile", str(pdf_path), str(stem)],
            check=True, capture_output=True, timeout=120,
        )
    except Exception:  # noqa: BLE001
        return None
    hit = next(iter(sorted(out_dir.glob(f"p{pno:03d}*.png"))), None)
    return str(hit) if hit else None


def to_markdown(doc: dict, pages: dict[int, str], tables: list[dict]) -> str:
    by_page: dict[int, list[dict]] = {}
    for t in tables:
        by_page.setdefault(t["page"], []).append(t)

    out = [
        f"# {doc['title']}",
        "",
        f"- Document ID: `{doc['document_id']}`  ",
        f"- Source file: `{doc['file_name']}`  ",
        f"- SHA-256: `{doc['sha256']}`  ",
        f"- Pages: {doc['page_count']}  ",
        f"- Text quality: {doc['text_quality']}",
        "",
        "> Source layer. Page markers below are physical PDF pages and are the",
        "> anchor for every citation in this knowledge base. Do not edit this file.",
        "",
    ]
    for pno in sorted(pages):
        out.append(f"<!-- source: {doc['document_id']} p.{pno} -->")
        text = pages[pno] or ""
        if len(text.strip()) < LOW_TEXT_CHARS:
            out.append(f"<!-- LOW-TEXT PAGE: {len(text.strip())} chars. "
                       f"Verify against pages/p{pno:03d}.png -->")
        for line in text.splitlines():
            stripped = line.rstrip()
            if not stripped:
                out.append("")
            elif HEADING_PAT.match(stripped):
                out.append(f"### {stripped.strip()}")
            else:
                out.append(stripped)
        for t in by_page.get(pno, []):
            out += ["", f"<!-- table: {t['table_id']} page {t['page']} "
                        f"({t['n_rows']}x{t['n_cols']}) - RECONCILE AGAINST pages/p{pno:03d}.png -->"]
            hdr = t["header"] or []
            if hdr:
                out.append("| " + " | ".join(c or " " for c in hdr) + " |")
                out.append("|" + "---|" * len(hdr))
            for row in t["rows"]:
                padded = list(row) + [""] * (len(hdr) - len(row)) if hdr else row
                out.append("| " + " | ".join(c or " " for c in padded) + " |")
            out.append("")
        out.append("")
    return "\n".join(out)


def process_doc(kb: Path, doc: dict, do_ocr: bool, render_all: bool) -> tuple[int, list[str]]:
    src = Path(doc["original_path"])
    doc_dir = kb / "01-source-layer" / doc["document_id"]
    doc_dir.mkdir(parents=True, exist_ok=True)
    local = doc_dir / "original.pdf"
    pdf_path = local if local.exists() else src
    if not pdf_path.exists():
        return 1, [f"{doc['document_id']}: original PDF not found at {pdf_path}"]

    pages, tables, exceptions = extract_pages(pdf_path)

    if do_ocr:
        for pno, text in list(pages.items()):
            if len(text.strip()) < LOW_TEXT_CHARS:
                got = ocr_page(pdf_path, pno, doc_dir / ".ocr-tmp")
                if got.strip():
                    pages[pno] = got
                    exceptions.append(f"p.{pno}: OCR applied (low native text). "
                                      f"Treat as low-confidence until visually verified.")
                else:
                    exceptions.append(f"p.{pno}: low text and OCR unavailable/empty. MANUAL REVIEW REQUIRED.")
        shutil.rmtree(doc_dir / ".ocr-tmp", ignore_errors=True)

    table_pages = {t["page"] for t in tables}
    numeric_pages = {p for p, t in pages.items() if NUMERIC_PAGE_PAT.search(t or "")}
    low_pages = {p for p, t in pages.items() if len((t or "").strip()) < LOW_TEXT_CHARS}
    to_render = set(pages) if render_all else (table_pages | numeric_pages | low_pages)

    rendered = {}
    for pno in sorted(to_render):
        got = render_page(pdf_path, pno, doc_dir / "pages")
        if got:
            rendered[pno] = got
    if to_render and not rendered:
        exceptions.append("Page rendering unavailable (pdftoppm missing). "
                          "G7 visual reconciliation must be done manually against the original PDF.")

    (doc_dir / "pages.json").write_text(
        json.dumps({str(k): v for k, v in sorted(pages.items())}, indent=2), encoding="utf-8")
    (doc_dir / "tables.json").write_text(json.dumps(tables, indent=2), encoding="utf-8")
    (doc_dir / "document.md").write_text(to_markdown(doc, pages, tables), encoding="utf-8")

    ex_lines = [f"# Conversion exceptions - {doc['document_id']} ({doc['file_name']})", ""]
    if exceptions:
        ex_lines += [f"- {e}" for e in exceptions]
    else:
        ex_lines.append("- None. All pages extracted with native text.")
    ex_lines += ["", f"Pages rendered for visual reconciliation: "
                     f"{', '.join(str(p) for p in sorted(rendered)) or 'none'}"]
    (doc_dir / "conversion-exceptions.md").write_text("\n".join(ex_lines) + "\n", encoding="utf-8")

    print(f"  {doc['document_id']}: {len(pages)} pages, {len(tables)} tables, "
          f"{len(rendered)} rendered, {len(exceptions)} exception(s)")
    return (2 if exceptions else 0), exceptions


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 1 source layer builder")
    ap.add_argument("--kb", required=True)
    ap.add_argument("--doc-id", default="ALL")
    ap.add_argument("--ocr", action="store_true", help="OCR low-text pages where tesseract is available")
    ap.add_argument("--render-all", action="store_true", help="Render every page, not just table/numeric pages")
    args = ap.parse_args()

    kb = Path(args.kb)
    register = load_register(kb)
    targets = register if args.doc_id.upper() == "ALL" else [d for d in register if d["document_id"] == args.doc_id]
    if not targets:
        print(f"ERROR: no document matched {args.doc_id}", file=sys.stderr)
        return 1

    print(f"Building source layer for {len(targets)} document(s)")
    worst, all_ex = 0, []
    for doc in targets:
        code, ex = process_doc(kb, doc, args.ocr, args.render_all)
        worst = max(worst, code)
        all_ex += [f"{doc['document_id']}: {e}" for e in ex]

    qa = kb / "05-quality-assurance" / "parser-exceptions.md"
    qa.parent.mkdir(parents=True, exist_ok=True)
    body = ["# Parser exceptions (Stage 1)", ""]
    body += [f"- {e}" for e in all_ex] if all_ex else ["- None."]
    qa.write_text("\n".join(body) + "\n", encoding="utf-8")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
