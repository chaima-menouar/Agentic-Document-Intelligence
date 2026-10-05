# Agentic Document Intelligence

An evidence-grounded document question-answering system for English PDF corpora.

The project is developed as a 12-week academic project and compares three modes:

- **Mode A — Classical RAG:** retrieval + answer generation.
- **Mode B — Verified RAG:** Mode A + claim-level evidence verification.
- **Mode C — Agentic Verified RAG:** Mode B + bounded additional retrieval when evidence is insufficient.

## Version 1 scope

- English, text-based PDFs
- Multi-document corpus
- Page-level provenance and inspectable citations
- Semantic retrieval over document chunks
- Claim extraction and evidence verification
- Bounded agentic re-retrieval
- No web search in V1
- No OCR/scanned-PDF support in V1

## Current milestone

**Milestone 1 — Reliable PDF ingestion**

```
PDF
 ↓
page-by-page extraction
 ↓
stable document ID + page IDs
 ↓
JSON
 ↓
quality inspection
```

The first milestone intentionally comes before embeddings or LLM integration: if extraction or page mapping is wrong, later citations and verification cannot be trusted.

## Planned project layout

```text
app/
  ingestion/
  retrieval/
  rag/
  verification/
  agent/
  models/
  ui/
data/
  raw/
  processed/
  evaluation/
tests/
scripts/
```

## Development

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Roadmap

1. PDF extraction and provenance
2. Chunking and retrieval
3. Classical RAG with citations
4. Documents + Assistant UI
5. Claim extraction and verification
6. Partial-answer correction
7. Agentic additional retrieval
8. A/B/C evaluation
9. Stabilization, report, and demo
