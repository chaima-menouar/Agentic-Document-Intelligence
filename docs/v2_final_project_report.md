# Final V2 Project Report — Agentic Document Intelligence

## 1. Objective

V2 extends the stable V1 evidence-grounded document QA system without replacing
working components simply because a newer option exists.

The design goal is:

> broaden document coverage, strengthen grounding checks, and make recovery more
> efficient while keeping every decision inspectable and reproducible.

V1 remains preserved on `main`. V2 is developed on `v2-development`.

## 2. V2 architecture

```text
PDF
  -> embedded-text extraction
  -> local OCR fallback for text-poor/scanned pages
  -> provenance-preserving chunks
  -> BGE-small + FAISS dense retrieval (validated default)
       -> optional BM25 RRF fusion
       -> optional local cross-encoder reranking
  -> answer generation
       -> deterministic extractive baseline
       -> optional guarded local OpenAI-compatible LLM
            -> citation validation
            -> one repair attempt
            -> extractive fallback
  -> claim extraction
  -> verifier
       -> V1 lexical verifier
       -> V2 local semantic NLI verifier (default in V2 UI)
            -> lexical fallback on model failure
  -> correction
  -> agent
       -> V1 fixed bounded policy
       -> V2 adaptive budgeted policy
  -> cited answer / partial answer / safe abstention
```

## 3. Milestone 11 — OCR / scanned PDFs

V2 detects text-poor pages and can run local Tesseract OCR.

Added page-level diagnostics:

- `extraction_method`
- `ocr_applied`
- `ocr_confidence`
- document-level `ocr_pages`

OCR text keeps the original page ID and page number, so later chunks and
citations preserve provenance.

A real image-only PDF OCR GitHub Actions test passed using Tesseract.

## 4. Milestone 12 — guarded local generation

V2 keeps the deterministic extractive baseline and adds
`GroundedLocalGenerator` for Ollama, LM Studio, or another local
OpenAI-compatible endpoint.

Generation contract:

```text
local model output
  -> validate evidence labels and per-sentence citations
  -> repair once when invalid
  -> deterministic extractive fallback if repair still fails
```

In the controlled V1/V2 generation-contract case:

- V1 uncited output citation precision: **0%**
- V2 repaired output citation precision: **100%**

The answer-relevance proxy stayed equal in that controlled case, showing that
the guard repaired grounding without changing the answer topic.

## 5. Milestone 13 — semantic verification

V1 uses transparent lexical token grounding.

V2 adds a local NLI verifier using:

`cross-encoder/nli-MiniLM2-L6-H768`

Default decision thresholds:

- entailment >= 0.70 -> supported
- entailment >= 0.40 -> needs review
- otherwise -> unsupported

Citation mapping is still mandatory before semantic scoring.

### Controlled verifier results

| Case | V1 lexical | V2 semantic |
| --- | --- | --- |
| Direct entailment | supported | supported (~0.994) |
| Semantic paraphrase | needs review (~0.333 lexical) | needs review (~0.606 NLI) |
| Explicit contradiction | incorrectly supported | correctly unsupported (~0.002 NLI) |

Controlled classification accuracy:

- V1: **33.3%**
- V2: **66.7%**

The result demonstrates stronger contradiction handling, but also shows that the
semantic verifier remains conservative on the paraphrase case.

### Latency trade-off

The V1 lexical check is extremely cheap. On the CI CPU runner, the local V2 NLI
verification averaged roughly **1.1 s** per controlled case. V2 therefore pays a
compute cost for stronger semantic checking.

## 6. Milestone 14 — hybrid retrieval and reranking

V2 adds:

- in-memory BM25 sparse ranking;
- Reciprocal Rank Fusion (RRF);
- optional local cross-encoder reranking using
  `cross-encoder/ms-marco-MiniLM-L-6-v2`.

### Full QASPER validation — 888 evaluable questions

| Metric | Dense BGE | Hybrid RRF |
| --- | ---: | ---: |
| Recall@1 | 27.93% | 28.27% |
| Recall@3 | 53.38% | 52.59% |
| Recall@5 | 66.10% | 65.43% |
| Recall@10 | 83.33% | 82.21% |
| Recall@20 | 94.59% | 94.03% |
| MRR@20 | 44.97% | 44.82% |

Because RRF did not improve the primary Recall@5 metric, **dense BGE + FAISS
remains the default**.

### Matched 50-question reranker sample

| Metric | Dense BGE | Hybrid + reranker |
| --- | ---: | ---: |
| Recall@1 | 28% | 30% |
| Recall@3 | 58% | 52% |
| Recall@5 | 70% | 74% |
| MRR@5 | 44.70% | 45.13% |

The reranker improved Recall@5 by four percentage points on this sample but
reduced Recall@3, so it remains an optional experimental mode rather than
replacing the validated dense default.

## 7. Milestone 15 — adaptive agent policy

V1 uses a fixed bounded retrieval policy.

V2 chooses the next retrieval action from the failure reason and enforces a
strict total chunk budget.

Examples:

- missing citation -> recover citation;
- weak evidence -> strengthen evidence;
- citation mismatch -> repair search;
- year/number mismatch -> answer-type-aware search;
- no new evidence -> early stop;
- budget exhausted -> stop.

### Controlled real-index comparison — 20 cases per scenario

| Metric | V1 fixed | V2 adaptive |
| --- | ---: | ---: |
| Recoverable recovery | 90% | 90% |
| Recoverable average rounds | 1.2 | 1.1 |
| Recoverable average chunks | 3.6 | 3.3 |
| Unsupported safe abstention | 100% | 100% |
| Unsupported average rounds | 3.0 | 2.0 |
| Unsupported average chunks | 9.0 | 6.0 |

V2 preserved recovery and safe abstention while reducing unnecessary retrieval.
Budget compliance and early-stop/budget-stop behavior were both **100%** on the
unsupported controlled cases.

## 8. Milestone 16 — consolidated V1 vs V2 evaluation

The final controlled scorecard reports:

| Metric | V1 | V2 |
| --- | ---: | ---: |
| Generation citation precision | 0% | 100% |
| Answer relevance proxy | 100% | 100% |
| Verification classification accuracy | 33.3% | 66.7% |
| Recoverable claim recovery | 90% | 90% |
| Unsupported safe abstention | 100% | 100% |
| Unsupported average agent rounds | 3.0 | 2.0 |
| Unsupported average additional chunks | 9.0 | 6.0 |
| Paid external API cost | 0 | 0 |

These are controlled grounding/safety measurements, not a claim of general LLM
quality.

## 9. Regression cases

Two failures observed during the interactive V1 demo are now explicit
regression checks:

1. main-idea extraction must not collapse to the fragment `important.`;
2. an unsupported year question must return `INSUFFICIENT_EVIDENCE` rather
   than inventing a date.

Both passed in the consolidated V1/V2 CI benchmark.

## 10. V2 Streamlit UI

The final V2 interface uses a dark navy / blue / cyan document-intelligence
visual system with rounded evidence panels, status pills, and restrained scan,
flow, pulse, and fade animations. The design keeps citations and verification
status visually dominant instead of using decorative motion for its own sake.

The application is organized into six spaces:

- **Overview** — architecture flow, capability cards, release/workspace status;
- **Documents** — PDF upload, OCR/index metrics, document status, and a
  side-by-side original-page vs extracted/OCR-text inspector;
- **Assistant** — a three-zone layout for **Sources**, **Question + Answer**, and
  **Evidence**, plus expandable citations and agent traces;
- **Evaluation** — live session metrics, response latency, local-LLM call count,
  claim/citation support, benchmark snapshots, action log, and human review;
- **V1 vs V2** — controlled side-by-side behavior comparison;
- **Configuration** — active generator, retrieval, verifier, chunking, top-k,
  agent policy/budget, OCR, embedding, and corpus settings.

The V2 UI exposes:

- OCR controls and OCR-page count;
- generator selection;
- dense / hybrid / reranked retrieval selection;
- lexical / semantic verifier selection;
- fixed / adaptive agent policy selection;
- adaptive retrieval budget;
- semantic and lexical verification diagnostics;
- dense/sparse/fusion/rerank retrieval scores;
- adaptive failure reason, action, new chunks, support delta, and early-stop
  reason;
- live evaluation and human-review controls;
- a **V1 vs V2** side-by-side demo tab.

The side-by-side tab intentionally uses the same dense retriever and extractive
generator on both sides to isolate verification and agent-policy differences.

## 11. Default V2 configuration

The current recommended V2 configuration is:

- OCR: enabled for text-poor pages;
- retrieval: **dense BGE + FAISS**;
- generator: offline extractive for reproducible demos, guarded local LLM when a
  local endpoint is available;
- verifier: **V2 semantic NLI**;
- agent: **V2 adaptive budgeted**;
- hybrid/reranker: optional experiment, not default.

## 12. Limitations

V2 still has deliberate limits:

- English OCR language is the configured default.
- OCR quality depends on scan quality and Tesseract.
- The semantic NLI verifier is stronger than lexical overlap but not infallible;
  the controlled paraphrase example remained `needs_review`.
- Local NLI and reranking require more CPU/RAM and first-use model downloads.
- Reranker improvement was measured on a 50-question matched sample, not the
  entire QASPER validation set.
- No web search is used.
- The controlled benchmarks focus on grounding, retrieval, recovery, and safety;
  they do not replace human evaluation of open-ended answer quality.

## 13. Reproducibility

Install the full local stack:

```bash
python -m pip install -r requirements-all.txt
```

For OCR, the machine also needs Tesseract. The Codespaces configuration installs
it automatically.

Run tests:

```bash
pytest -q
```

Run the consolidated comparison:

```bash
python scripts/evaluate_v1_v2.py \
  --index data/indexes/qasper-bge-small \
  --output data/evaluation/v1_vs_v2.json \
  --agent-cases 20
```

Run the UI:

```bash
python -m streamlit run app/ui/streamlit_app.py
```

## 14. Conclusion

V2 does not simply add more components. It adds measured safeguards and keeps
the older baseline whenever the benchmark does not justify replacement.

The strongest demonstrated V2 gains are:

- scanned-document coverage through local OCR;
- citation-contract enforcement around local generative models;
- better contradiction detection from semantic verification;
- the same 90% controlled recovery with less agent retrieval;
- preserved 100% safe abstention on unsupported controlled claims;
- an inspectable side-by-side V1/V2 interface.

This keeps the project local-first, evidence-grounded, and reproducible while
making the V2 behavior broader and more efficient than the stable V1 baseline.
