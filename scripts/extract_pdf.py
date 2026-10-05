"""Command-line entry point for Milestone 1 PDF extraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.ingestion import PdfExtractionError, extract_pdf, save_extraction_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract a text-based PDF page by page with stable provenance."
    )
    parser.add_argument("pdf", type=Path, help="Path to the input PDF.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to data/processed/<document_id>.json.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        extraction = extract_pdf(args.pdf)
    except PdfExtractionError as exc:
        print(f"Extraction failed: {exc}")
        return 1

    output = args.output or Path("data/processed") / f"{extraction.document_id}.json"
    save_extraction_json(extraction, output)

    print(f"Document: {extraction.filename}")
    print(f"Document ID: {extraction.document_id}")
    print(f"Pages: {extraction.page_count}")
    print(f"Empty pages: {extraction.quality.empty_pages or 'none'}")
    print(f"Saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
