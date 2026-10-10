# V2 Hybrid Retrieval + Reranking

Milestone 14 upgrades retrieval from dense-only search to a fused dense+sparse
pipeline with an optional local cross-encoder reranker.

## Retrieval modes

### V1 dense BGE + FAISS

```text
question -> BGE query embedding -> FAISS cosine search -> top-k
```

### V2 hybrid RRF

```text
                    -> BGE + FAISS dense ranking ----question ----------------------------------------------> reciprocal-rank fusion -> top-k
                    -> BM25 sparse lexical ranking --/
```

Dense retrieval captures semantic similarity. Sparse BM25 retrieval helps with
exact identifiers, rare terms, names, codes, and wording that can be diluted by
embedding similarity.

### V2 hybrid + reranker

```text
dense candidates + sparse candidates
  -> reciprocal-rank fusion
  -> candidate pool
  -> local cross-encoder query/passage scoring
  -> final top-k
```

The default reranker is:

`cross-encoder/ms-marco-MiniLM-L-6-v2`

It is loaded lazily, so the non-reranked hybrid mode does not pay the model-load
cost.

## Fusion

Reciprocal Rank Fusion (RRF) is used instead of directly mixing incompatible
dense cosine and BM25 score scales.

For a candidate with rank `r` in a retrieval list:

```text
RRF contribution = 1 / (k + r)
```

The default constant is `k=60`. Contributions from dense and sparse rankings
are summed.

## Traceability

Each returned hybrid `RetrievalHit` can carry:

- `dense_score`
- `sparse_score`
- `fusion_score`
- `rerank_score` when reranking is enabled
- `retrieval_mode`

These diagnostics are copied into answer citations and shown in the Streamlit
source expander.

## Document-scoped search

Hybrid retrieval preserves V1's document-scoped semantics. Sparse candidates are
filtered to the selected document, and dense scoped search continues to use the
same BGE vectors.

## Evaluation

`scripts/evaluate_qasper_hybrid.py` evaluates document-scoped QASPER retrieval
with Recall@k and MRR.

`.github/workflows/v2-hybrid-retrieval-e2e.yml` validates:

1. hybrid/BM25/reranking unit tests;
2. Classical and Agentic RAG compatibility;
3. dense BGE baseline on the existing QASPER validation index;
4. hybrid RRF on the same full evaluation set;
5. dense-vs-hybrid Recall@5 comparison;
6. a 50-question real local cross-encoder reranking smoke benchmark;
7. Streamlit module compilation.


## Recorded V2 benchmark results

Full QASPER validation (888 evaluable questions):

| Metric | Dense BGE | Hybrid RRF |
| --- | ---: | ---: |
| Recall@1 | 27.93% | 28.27% |
| Recall@3 | 53.38% | 52.59% |
| Recall@5 | 66.10% | 65.43% |
| Recall@10 | 83.33% | 82.21% |
| Recall@20 | 94.59% | 94.03% |
| MRR@20 | 44.97% | 44.82% |

RRF slightly improved Recall@1 but reduced the primary Recall@5 metric, so
dense BGE remains the default retrieval mode.

Matched 50-question reranker sample:

| Metric | Dense BGE | Hybrid + reranker |
| --- | ---: | ---: |
| Recall@1 | 28% | 30% |
| Recall@3 | 58% | 52% |
| Recall@5 | 70% | 74% |
| MRR@5 | 44.70% | 45.13% |

The reranked candidate won on the selected primary metric Recall@5 (+4
percentage points) and Recall@1 (+2 points), but Recall@3 decreased. For that
reason reranking remains an optional V2 mode rather than replacing the validated
dense default.
