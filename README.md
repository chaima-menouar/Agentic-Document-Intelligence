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

**Milestone 2 — Canonical corpus normalization + provenance-preserving chunking**

Completed foundation:

```text
PDF / QASPER / SciFact / HotpotQA
 ↓
canonical CorpusDocument
 ↓
source segments with provenance
 ↓
overlapping word chunks
 ↓
stable chunk IDs + source IDs
 ↓
ready for embeddings and semantic retrieval
```

The chunker never crosses a provenance boundary. A retrieval chunk can therefore
be traced back to one source page, section/paragraph, or evidence sentence.

Default experiment configuration:

- chunk size: **220 words**
- overlap: **40 words**
- QASPER: primary scientific document-QA corpus
- SciFact: scientific claim verification corpus
- HotpotQA: 10,000-example agentic/multi-hop stress-test subset

Large public datasets stay out of Git history. GitHub Actions reproducibly
collects them, normalizes them, chunks them, and uploads both raw and processed
artifacts.

## Project layout

```text
app/
  ingestion/
    pdf_extractor.py
    dataset_normalizer.py
    chunker.py
  retrieval/
  rag/
  verification/
  agent/
  models/
  ui/
data/
  raw/
  external/
  processed/
  evaluation/
tests/
scripts/
  prepare_datasets.py
  build_corpus.py
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

To reproduce the benchmark corpus locally:

```bash
pip install -r requirements.txt -r requirements-data.txt
python scripts/prepare_datasets.py --output data/external --hotpot-size 10000 --seed 42
python scripts/build_corpus.py --input data/external --output data/processed/benchmark
python scripts/build_vector_index.py --chunks data/processed/benchmark/chunks.jsonl --output data/indexes/qasper --dataset qasper
python scripts/evaluate_qasper_retrieval.py --qasper data/external/qasper/validation.parquet --index data/indexes/qasper --output data/evaluation/qasper_retrieval.json --top-k 1,3,5,10,20
python scripts/search_index.py "What evidence supports the claim?" --index data/indexes/qasper --top-k 5
```

## Roadmap

1. ✅ PDF extraction and provenance
2. ✅ Corpus normalization + chunking
3. 🚧 Semantic embeddings + retrieval and Recall@k
4. Classical RAG with citations
5. Documents + Assistant UI
6. Claim extraction and verification
7. Partial-answer correction
8. Agentic additional retrieval
9. A/B/C evaluation
10. Stabilization, report, and demo
