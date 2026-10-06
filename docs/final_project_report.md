# Final Project Report — Agentic Document Intelligence

## 1. Objective

Agentic Document Intelligence is an evidence-grounded question-answering system for English document corpora. The project compares three progressively safer architectures:

- **Mode A — Classical RAG:** retrieve evidence and generate a cited answer.
- **Mode B — Verified RAG:** verify answer claims against cited evidence and conservatively remove unsupported content.
- **Mode C — Agentic Verified RAG:** when evidence is insufficient, perform bounded claim-focused retrieval, re-verify, and stop when claims are supported or the retrieval budget is exhausted.

The implementation is designed to remain inspectable, reproducible, and usable without paid external APIs.

## 2. Implemented pipeline

The final V1 pipeline is:

```text
PDF / benchmark documents
  -> extraction + normalization
  -> provenance-preserving chunking
  -> BAAI/bge-small-en-v1.5 embeddings
  -> FAISS semantic retrieval
  -> Mode A cited answer
  -> Mode B claim extraction + verification + correction
  -> Mode C bounded claim-focused re-retrieval + re-verification
  -> final cited answer or safe abstention
```

Every retrieval chunk keeps source provenance so citations can be traced back to the originating document and page/segment.

## 3. Retriever choice

The selected retriever is **BAAI/bge-small-en-v1.5**. On document-scoped QASPER validation it outperformed the MiniLM alternative used during model comparison.

Recorded validation metrics:

| Metric | Result |
| --- | ---: |
| Recall@1 | 27.9% |
| Recall@3 | 53.4% |
| Recall@5 | 66.1% |
| Recall@10 | 83.3% |
| Recall@20 | 94.6% |
| MRR@20 | 45.0% |

## 4. A/B/C controlled evaluation

The reproducible benchmark uses the real QASPER BGE + FAISS index and deterministic local generation/verification components. It is a controlled stress evaluation of grounding and recovery behavior, not a general LLM quality benchmark.

Configuration:

- 20 cases per scenario
- max agentic retrieval rounds: 2
- additional chunks per round: 3
- paid external API cost: 0

### Normal grounded scenario

| Metric | Result |
| --- | ---: |
| Mode A cited answer rate | 100% |
| Mode B verified rate | 95% |
| Mode C no-extra-round rate | 95% |

### Recoverable uncited scenario

| Metric | Result |
| --- | ---: |
| Mode A uncited output rate | 100% |
| Mode B detection rate | 100% |
| Mode B safe abstention rate | 100% |
| Mode C recovery rate | 90% |
| Mode C average rounds | 1.1 |
| Mode C average additional chunks | 3.3 |

### Unsupported-claim scenario

| Metric | Result |
| --- | ---: |
| Mode B detection rate | 100% |
| Mode B safe abstention rate | 100% |
| Mode C safe abstention rate | 100% |
| Mode C retrieval-bound respected rate | 100% |
| Mode C average rounds | 2.0 |

### Mean benchmark latency

| Mode | Mean latency |
| --- | ---: |
| Mode A | 0.0223 s |
| Mode B | 0.0223 s |
| Mode C | 0.0509 s |

Mode C is slower because it may perform additional retrieval and verification, but the benchmark shows the intended trade-off: extra computation is used only when evidence is insufficient.

## 5. Main findings

The evaluation supports three project conclusions.

First, citation-only RAG is not enough. Mode A can produce an answer but does not independently detect unsupported or uncited claims.

Second, deterministic verification improves safety. Mode B detected all controlled unsupported/uncited stress cases and safely abstained rather than presenting unsupported content.

Third, bounded agentic retrieval adds useful recovery behavior. Mode C recovered 90% of deliberately recoverable uncited cases while preserving safe abstention for truly unsupported claims and respecting the configured retrieval budget in every tested case.

## 6. Limitations

The current V1 has intentionally narrow scope:

- English text-based PDFs only.
- No OCR for scanned documents.
- The offline verifier is conservative and primarily validates citation mapping and lexical grounding; it is not a full semantic entailment model.
- The controlled A/B/C benchmark evaluates grounding and recovery behavior, not open-ended answer quality or human preference.
- No web search is used in V1.
- The bundled offline generator is intentionally extractive, but it is question-aware and selects the most relevant supported sentence across retrieved sources. A stronger local generative model or NLI verifier can still be plugged into the architecture later without changing the overall pipeline.

## 7. Reproducibility

Run tests:

```bash
pytest
```

Run the A/B/C benchmark:

```bash
python scripts/evaluate_abc_modes.py \
  --index data/indexes/qasper-bge-small \
  --output data/evaluation/abc_evaluation.json \
  --cases 20 \
  --max-rounds 2 \
  --additional-top-k 3
```

Run the local UI:

```bash
python -m pip install -r requirements-all.txt
python -m streamlit run app/ui/streamlit_app.py
```

## 8. Final conclusion

The project demonstrates a complete progression from Classical RAG to evidence verification and then to bounded agentic recovery. The final system does not merely retrieve and answer: it checks whether its claims are grounded, removes unsupported content, searches again only when necessary, and safely abstains when evidence remains insufficient.

For an academic V1, the result is a reproducible and inspectable document-intelligence pipeline that clearly exposes the value added by verification and agentic retrieval.


## 9. Final stabilization status

The final repository includes a one-command dependency set
(`requirements-all.txt`), a Codespaces devcontainer that installs the full
local stack automatically, and a `final-smoke` GitHub Actions workflow. The
workflow runs the complete test suite, validates the Streamlit module, and
checks the local retrieval/UI dependencies before the final manual demo.
