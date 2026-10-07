# V2 Roadmap

V2 builds on the stable V1 while preserving the same evidence-grounded philosophy.

## Goals

1. **OCR + scanned PDF support**
   - Detect text-poor/scanned pages.
   - Run a local OCR fallback.
   - Preserve page-level provenance for OCR text.
   - Expose OCR warnings and confidence metadata in the UI.

2. **Stronger local answer generation**
   - Keep the deterministic extractive baseline.
   - Add a better local generative option with a clean adapter.
   - Preserve strict evidence-only prompting and citation mapping.
   - Keep paid external API cost optional rather than required.

3. **Semantic claim verification**
   - Add a local semantic/NLI verifier behind the existing verifier interface.
   - Keep the transparent lexical verifier as fallback.
   - Compare lexical vs semantic verification on controlled cases.

4. **Hybrid retrieval + reranking**
   - Combine dense semantic retrieval with sparse lexical retrieval.
   - Add a local reranking stage.
   - Evaluate Recall@k / MRR and answer-grounding impact.

5. **Smarter agent policy**
   - Use failure reason to choose the next action.
   - Distinguish missing evidence, weak evidence, citation mismatch, and answer-type mismatch.
   - Stop early when recovery probability is low.
   - Keep a strict maximum tool/retrieval budget.

6. **Richer evaluation**
   - Add answer relevance, citation precision, support rate, abstention quality, and latency/cost metrics.
   - Add regression cases from real demo failures.
   - Compare V1 vs V2.

7. **UI improvements**
   - Surface OCR status, retrieval path, verification reason, and agent trace more clearly.
   - Add an evaluation/demo panel for side-by-side mode comparison.

## V2 milestones

11. ✅ OCR/scanned PDF ingestion
12. ✅ Local generative answer upgrade
13. ⏳ Semantic verifier
14. ⬜ Hybrid retrieval + reranking
15. ⬜ Adaptive agent policy
16. ⬜ V1 vs V2 evaluation
17. ⬜ UI polish + final V2 report/demo

## Compatibility rule

V1 behavior must remain available and reproducible. V2 changes are developed on
`v2-development` until regression tests and V1-vs-V2 evaluation pass.
