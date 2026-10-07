# V1 vs V2 Evaluation

Milestone 16 consolidates the V2 work into one reproducible comparison against
the stable V1 behavior.

## Scope

This benchmark measures grounding, verification, abstention, agent efficiency,
and regression behavior. It is not a general open-ended LLM quality benchmark.

The comparison uses:

- the real BGE + FAISS QASPER validation index for retrieval/agent cases;
- deterministic generator-contract cases for citation repair;
- a real local NLI model for semantic verification;
- the same controlled recoverable and unsupported agent scenarios for V1/V2;
- regression cases derived from the interactive demo failures.

No paid external API is required.

## Metrics

### Citation precision

Fraction of source labels written in the answer that map to structured retrieved
evidence.

### Answer relevance proxy

A transparent lexical proxy: the fraction of non-stopword question content
tokens covered by the answer. It is reported explicitly as a proxy rather than
as an LLM-judge score.

### Verification classification accuracy

Accuracy on controlled supported/paraphrased/contradictory claim-evidence pairs.

### Recovery rate

Fraction of recoverable initially unsupported claims successfully grounded after
agentic retrieval.

### Safe abstention rate

Fraction of truly unsupported cases where the system refuses to present an
unsupported final answer.

### Retrieval cost

Average additional retrieval rounds and chunks consumed by the agent.

## Regression cases

The consolidated evaluator includes two real demo regressions:

1. a main-idea question must not collapse to the fragment `important.`;
2. an unsupported year question must abstain rather than invent a year.

## Reproduction

```bash
python scripts/evaluate_v1_v2.py \
  --index data/indexes/qasper-bge-small \
  --output data/evaluation/v1_vs_v2.json \
  --agent-cases 20
```

The GitHub Actions workflow is
`.github/workflows/v2-v1-vs-v2-evaluation.yml`.
