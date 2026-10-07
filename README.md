# Agentic Document Intelligence

An evidence-grounded document question-answering system for English PDF corpora.

The project is developed as a 12-week academic project and compares three modes:

- **Mode A — Classical RAG:** retrieval + answer generation.
- **Mode B — Verified RAG:** Mode A + claim-level evidence verification.
- **Mode C — Agentic Verified RAG:** Mode B + bounded additional retrieval when evidence is insufficient.

## V2 development

V2 is developed on the `v2-development` branch while `main` preserves the
stable V1.

Current V2 progress:

- ✅ Milestone 11 — local OCR fallback for scanned/text-poor PDF pages
- ✅ Milestone 12 — guarded local LLM generation with citation repair/fallback
- ✅ Milestone 13 — local semantic/NLI claim verification with lexical fallback
- ⏳ Milestone 14 — hybrid dense+BM25 retrieval and local cross-encoder reranking
- ⬜ Milestone 15 — adaptive agent policy
- ⬜ Milestone 16 — V1 vs V2 evaluation
- ⬜ Milestone 17 — final V2 UI/report/demo polish

Detailed V2 design notes are in:

- `docs/v2_roadmap.md`
- `docs/v2_local_generator.md`
- `docs/v2_semantic_verifier.md`
- `docs/v2_hybrid_retrieval.md`

## Version 1 scope

- English, text-based PDFs
- Multi-document corpus
- Page-level provenance and inspectable citations
- Semantic retrieval over document chunks
- Claim extraction and evidence verification
- Bounded agentic re-retrieval
- No web search in V1
- No OCR/scanned-PDF support in V1

## Project status

**V1 complete — implementation, evaluation, stabilization, report, and demo are finished.**

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
python -m pip install -r requirements-all.txt
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
6. ✅ Claim extraction and verification
7. ✅ Partial-answer correction
8. ✅ Agentic additional retrieval
9. ✅ A/B/C evaluation
10. ✅ Stabilization, report, and demo


## A/B/C evaluation

Milestone 9 includes a reproducible, fully local comparison harness for the
three system modes. It reports answer/citation rates for Mode A, claim
grounding metrics for Mode B, and recovery/round-efficiency metrics for Mode C.

Build a deterministic QASPER evaluation set:

```bash
python scripts/build_qasper_eval_questions.py \
  --qasper data/external/qasper/validation.parquet \
  --output data/evaluation/abc/questions.jsonl \
  --limit 50
```

Then compare all three modes on the same questions:

```bash
python scripts/evaluate_abc_modes.py \
  --index data/indexes/qasper-bge-small \
  --output data/evaluation/abc_evaluation.json \
  --cases 20 \
  --max-rounds 2 \
  --additional-top-k 3
```

The controlled evaluator runs deterministically on the real BGE + FAISS index and
writes the full scenario records plus aggregate metrics to
`data/evaluation/abc_evaluation.json`. No paid API is required.

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
python -m pip install -r requirements-all.txt
python -m streamlit run app/ui/streamlit_app.py
```

The default generator is a free, deterministic, question-aware extractive baseline that ranks sentences across retrieved evidence and preserves exact source labels. A local
OpenAI-compatible server such as Ollama or LM Studio can also be selected from
the sidebar without changing the RAG architecture.


## Verified RAG (Mode B)

Mode B wraps Classical RAG with deterministic sentence-level claim extraction
and a transparent offline citation-grounding verifier. Each claim is labeled as
`supported`, `needs_review`, or `unsupported`, with a support score and
the exact cited evidence labels used for the decision.

The current offline verifier is intentionally conservative: it validates
citation mapping and lexical grounding, but it does not claim to be a full
natural-language entailment model. The architecture remains pluggable for a
stronger local verifier later.

The `.github/workflows/verified-rag-e2e.yml` workflow validates the real
BGE-small retrieval -> Classical RAG -> claim extraction -> verification path.


## Partial-answer correction

After claim verification, claims marked `needs_review` or `unsupported` are
removed from the user-facing answer. If some supported claims remain, the
system returns a `partial_answer`; if none remain, it abstains with
`insufficient_evidence`. This conservative correction step is fully local and
keeps only citations used by the retained claims.

The `.github/workflows/corrected-rag-e2e.yml` workflow applies the correction
layer to a real Mode B smoke-test artifact.


## Agentic Verified RAG (Mode C)

Mode C starts from Mode B and targets only unresolved claims. Each unresolved
claim becomes a focused retrieval query; newly retrieved passages are attached
as evidence and the verifier runs again. The process stops early when all
claims are supported and is hard-bounded by a configurable maximum number of
rounds.

The real-index smoke test recovered an initially uncited QASPER claim in one
additional round using BGE-small + FAISS, then returned the recovered claim with
new evidence labels. The workflow is
`.github/workflows/agentic-rag-e2e.yml`.


## Final deliverables

The final academic delivery package is available in:

- `docs/final_project_report.md` — architecture, retriever results, A/B/C benchmark, findings, limitations, and reproducibility.
- `docs/demo_guide.md` — step-by-step demo flow explaining the difference between Classical, Verified, and Agentic RAG.

Key controlled A/B/C results: Mode B detected unsupported/uncited stress cases at 100% with 100% safe abstention; Mode C recovered 90% of recoverable uncited cases, safely abstained on unsupported claims at 100%, and respected its retrieval bound at 100%.


## Final validation

The repository includes a full-stack smoke workflow at
`.github/workflows/final-smoke.yml`. It installs the complete local dependency
set, runs the test suite, compiles the Streamlit UI, and checks that Streamlit,
sentence-transformers, FAISS, and the local generator import successfully.

GitHub Codespaces is configured through `.devcontainer/devcontainer.json` to
install `requirements-all.txt` automatically and forward Streamlit port 8501.
