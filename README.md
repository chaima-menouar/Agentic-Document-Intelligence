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

**Milestone 6 — Claim extraction and verification**

Current pipeline:

```text
PDF / benchmark documents
 ↓
normalization + provenance-preserving chunks
 ↓
BGE-small semantic retrieval + FAISS
 ↓
Top-k evidence
 ↓
Mode A Classical RAG
 ↓
answer + inspectable [S1], [S2] citations
```

The retriever comparison selected **BAAI/bge-small-en-v1.5** over MiniLM on
document-scoped QASPER validation. Mode A now retrieves evidence, builds a
grounded prompt, abstains when evidence is insufficient, and maps generated
source labels back to the exact retrieved chunks.

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
3. ✅ Semantic embeddings + retrieval and Recall@k
4. ✅ Classical RAG with citations
5. ✅ Documents + Assistant UI
6. 🚧 Claim extraction and verification
7. Partial-answer correction
8. Agentic additional retrieval
9. A/B/C evaluation
10. Stabilization, report, and demo


## Classical RAG CLI

Mode A uses a pluggable generator. The included client targets a
`/chat/completions`-compatible endpoint and keeps credentials out of Git.

```bash
# configure your inference endpoint locally
export RAG_LLM_BASE_URL="http://localhost:8000/v1"
export RAG_LLM_MODEL="your-model-name"
export RAG_LLM_API_KEY="optional-secret"

python scripts/run_classical_rag.py \
  "What evidence supports the main finding?" \
  --index data/indexes/qasper-bge-small \
  --top-k 5
```

For a question already associated with one document, pass
`--document-id <document_id>` to use document-scoped retrieval.


## Streamlit UI

The local UI is free and runs on your machine. It supports multi-PDF upload,
local BGE-small embeddings, FAISS retrieval, document-scoped or global search,
answer history, and inspectable page/chunk citations.

```bash
pip install -r requirements.txt -r requirements-retrieval.txt -r requirements-ui.txt
streamlit run app/ui/streamlit_app.py
```

The default generator is the free offline extractive baseline. A local
OpenAI-compatible server such as Ollama or LM Studio can also be selected from
the sidebar without changing the RAG architecture.
