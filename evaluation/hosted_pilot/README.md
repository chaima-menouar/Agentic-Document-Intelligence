# Hosted real-PDF pilot — 13 October 2026

This is a small manually reviewed pilot, not a general quality benchmark or an A/B/C comparison.

## Corpus and configuration

Five public English research PDFs: Transformer (1706.03762), BERT (1810.04805), RAG (2005.11401), DPR (2004.04906), and SQuAD (1606.05250). Original URLs and tested-byte SHA256 hashes are in `corpus.json`. PDFs were rewritten with PyMuPDF garbage collection and deflate compression without rasterizing or changing their page content. External PDFs are not redistributed here.

The upload indexed 73 pages and 244 passages, with no ingestion warnings. Twenty questions are in `questions.json`: 15 answerable questions with page-one reference answers and five intentionally unanswerable dated revenue questions. References are PDF page numbers, not printed page labels.

Hosted settings: dense BGE retrieval, offline extractive generator, lexical verifier, top-k 5, recovery budget 10. All questions were scoped to their intended document. This does not validate semantic NLI, reranking, local LLMs, OCR, or multi-document reasoning.

## Baseline observed on commit c1bd6f9

| Check | Result |
|---|---:|
| HTTP success | 20/20 |
| Answerable questions correctly answered, manual relevance review | 6/15 |
| Unanswerable questions safely abstained | 3/5 |
| Median server-reported answer latency | 0.04 seconds |
| Largest observed recovery round count | 2 |

Latency excludes upload, network time and cold-start model downloads. Indexing the combined upload took about 90 seconds. `baseline_results.json` retains statuses, timings, citation page numbers and short answer excerpts. A `verified` label means the claim matched evidence; it does not prove the claim answers the question.

## Failures and changes

- Uploading the original combined corpus was rejected with HTTP 413 before reaching the API. The Vercel image now advertises and enforces a conservative 4 MiB combined request-content limit; local/Render limits remain 25 MiB per PDF and 100 MiB total.
- Geometric line sorting interleaved two-column scientific text. Extraction now preserves the PDF's authored order. This is not a general layout reconstruction engine; arbitrary producer order and complex tables still need inspection.
- Dated revenue questions selected unrelated cited text. The offline generator now requires every explicit question year to occur in the selected sentence.
- Several answers were supported by citations but irrelevant to the question. These are recorded as failures, not counted as correct. Stronger answer relevance remains necessary.

Focused regression tests cover column paragraph order and dated-question abstention. The baseline predates these changes; do not attribute its numbers to the patched release or claim improvement until rerunning.
