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

## Patched hosted rerun — commit 7d9df07

The same compressed PDFs and questions were rerun after deployment. Indexing took about 90 seconds. Twenty requests were issued: 19 returned HTTP 200 and one returned HTTP 409 immediately after upload, confirming that process-local sessions are unreliable across Vercel instances.

| Check | Baseline | Patched rerun |
|---|---:|---:|
| Correct answerable questions, all 15 including HTTP failures | 6/15 | 4/15 |
| Safe abstention on the five dated revenue questions | 3/5 | 5/5 |
| HTTP success | 20/20 | 19/20 |

The final abstention is preserved from the completed runner stdout; its final raw JSON checkpoint was unavailable, so no timing or verification metadata is invented for that record. Patched results are in `patched_results.json`.

Column order became readable and dated abstention improved, but answer relevance regressed on this small pilot. This release must not be described as generally more accurate or production-ready. The offline selector still confuses similar numerical questions, ranks tables/headings highly, and sometimes truncates a useful answer. Stable external workspace storage and stronger question-answer relevance are remaining work.

The deployed 4 MiB API guard was checked separately: a PDF payload one byte above the limit returned HTTP 413 with the application's explicit 4.0 MB explanation. React build and 30 focused extraction/generator/API tests passed.

## Reproduce

Install the project's runtime dependencies, then run:

```bash
python scripts/run_hosted_pilot.py --output /tmp/adi-pilot
```

The command downloads the five public PDFs when absent, compresses their byte representation, opens its own temporary workspace, uploads the full corpus and checkpoints raw responses. Raw outputs are for local review and are not redistributed here. Manually judge relevance against `questions.json`; do not treat citation verification or keyword matching as answer accuracy.
