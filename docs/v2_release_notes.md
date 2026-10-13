# V2 Release Notes

Agentic Document Intelligence V2 extends the stable V1 baseline while preserving
its evidence-grounded design and local-first execution model.

## What changed

### Document ingestion
- Added local OCR fallback for scanned and text-poor PDF pages.
- Preserved page provenance for OCR-derived text.
- Added OCR method/confidence metadata and UI visibility.

### Generation
- Added a guarded local OpenAI-compatible LLM path.
- Added citation-contract validation for every factual sentence.
- Added one repair attempt for missing/invalid citations.
- Added deterministic extractive fallback if repair still fails.

### Verification
- Added a local semantic/NLI verifier.
- Kept lexical verification as a fallback and diagnostic.
- Exposed lexical and semantic support scores in the UI.

### Retrieval
- Added BM25 sparse retrieval.
- Added dense + sparse reciprocal-rank fusion.
- Added optional local cross-encoder reranking.
- Kept dense BGE + FAISS as the validated default where benchmark results did
  not justify replacing it globally.

### Agentic recovery
- Added a failure-aware adaptive retrieval policy.
- Added a strict additional-chunk budget.
- Added early stopping when no useful new evidence is found.
- Added richer agent trace metadata.

### Evaluation and UI
- Added V1 vs V2 controlled evaluation.
- Added a side-by-side V1 vs V2 demo tab.
- Added OCR, retrieval, verifier, and agent-policy diagnostics.
- Rebuilt the Streamlit visual layer with a Mantine-inspired product identity: charcoal/neutral surfaces, white/gray typography, a single warm-yellow accent, clean brand bar, layered document/evidence hero cards, subtle motion, compact cards, verification gauges, and themed native controls.
- Added exactly two switchable appearance modes: **Dark** and **Light**.
- Added reduced-motion support for accessibility.
- Added V2-specific E2E workflows and a final full-stack smoke workflow.

## Compatibility

V1 behavior remains reproducible:
- deterministic extractive generator remains available;
- lexical verifier remains available;
- dense BGE + FAISS remains available;
- fixed bounded agent remains available.

## Final automated validation

The release candidate passed:
- OCR scanned-PDF E2E;
- guarded local generator E2E;
- semantic verifier E2E;
- hybrid retrieval + reranking E2E;
- adaptive-agent E2E;
- Streamlit UI smoke;
- full V2 regression/import/local-tool smoke.

## Merge policy

V2 remains on `v2-development` until one final manual Streamlit demo is
completed successfully. After that single manual test, the draft PR can be
marked ready and merged into `main`.
