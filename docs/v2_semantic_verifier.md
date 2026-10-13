# V2 Semantic / NLI Verification

Milestone 13 upgrades claim grounding beyond lexical token overlap.

## Verification path

```text
generated claim + cited retrieved passages
  -> validate citation labels
  -> local NLI entailment scorer
  -> supported / needs_review / unsupported
  -> lexical score kept as a diagnostic
  -> lexical verifier fallback if the semantic model is unavailable
```

## Default local model

The default scorer is `cross-encoder/nli-MiniLM2-L6-H768`. The model is loaded
lazily and used locally through Transformers.

## Decision thresholds

- semantic entailment >= 0.70 -> supported
- semantic entailment >= 0.40 -> needs_review
- otherwise -> unsupported

The thresholds are configurable when constructing
`SemanticCitationGroundingVerifier`.

## Diagnostics

Each `ClaimVerification` can expose:

- `verifier_method`
- `lexical_support_score`
- `semantic_entailment_score`

The Streamlit UI shows these values inside each claim-verification expander.

## Safety / robustness

Semantic verification never bypasses citation mapping. A claim with no citation,
or with a citation label that does not map to retrieved evidence, is unsupported
without invoking the NLI model.

If the NLI model cannot load or score, the system falls back to the V1 lexical
verifier instead of failing the entire RAG request.

## Validation

`.github/workflows/v2-semantic-verifier-e2e.yml` runs semantic verifier unit
tests and a real local NLI inference smoke test.
