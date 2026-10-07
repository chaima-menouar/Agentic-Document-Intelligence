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


## Recorded scorecard

The consolidated CI benchmark produced:

| Metric | V1 | V2 |
| --- | ---: | ---: |
| Generation citation precision (controlled contract case) | 0% | 100% |
| Answer relevance proxy | 100% | 100% |
| Verification classification accuracy (3 controlled cases) | 33.3% | 66.7% |
| Recoverable-claim recovery | 90% | 90% |
| Unsupported safe abstention | 100% | 100% |
| Unsupported average agent rounds | 3.0 | 2.0 |
| Unsupported average additional chunks | 9.0 | 6.0 |
| Paid external API cost | 0 | 0 |

### Semantic-verifier detail

- Direct entailment: V1 supported; V2 supported with semantic score ~0.994.
- Semantic paraphrase: both remained conservative (`needs_review`); V2 semantic
  score was ~0.606 versus V1 lexical overlap ~0.333.
- Explicit contradiction: V1 lexical verification incorrectly marked it
  supported, while V2 NLI correctly marked it unsupported with entailment
  score ~0.002.

The semantic verifier therefore improved the controlled classification score,
especially by detecting contradiction, but the paraphrase case shows that V2
remains intentionally conservative rather than treating every related sentence
as fully entailed.

### Latency trade-off

The lexical verifier is effectively negligible in these tiny controlled cases,
while local NLI inference averaged about 1.1 seconds per verification case on
the CI CPU runner. V2 therefore spends more compute for stronger semantic
checking.

### Regression status

Both demo regressions passed:

- the main-idea question no longer collapses to the fragment `important.`;
- the unsupported year question returns `INSUFFICIENT_EVIDENCE`.
