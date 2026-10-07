# V2 Adaptive Agent Policy

Milestone 15 upgrades the fixed re-retrieval loop into a failure-aware,
budgeted agent while preserving the original V1 agent for reproducibility.

## V1 fixed policy

```text
unsupported claim
  -> round 1: retrieve using claim text
  -> round 2+: retrieve using question + claim
  -> stop at max_rounds
```

This is deterministic and bounded, but it treats every verification failure in
roughly the same way.

## V2 adaptive policy

The V2 policy inspects the verification result before choosing the next action.

| Failure signal | Action |
| --- | --- |
| missing citation | retrieve directly from the claim text |
| citation label mismatch | repair search using question + claim |
| weak / needs-review evidence | strengthen evidence with claim + question |
| unsupported claim | search alternative evidence |
| year/number answer-type mismatch | add answer-type cue to the retrieval query |
| no new evidence | stop early |
| retrieval budget exhausted | stop immediately |

## Strict retrieval budget

`AdaptiveAgenticVerifiedRAG` accepts:

- `max_rounds`
- `additional_top_k`
- `max_total_additional_chunks`

The final bound is therefore not only a number of rounds. The agent cannot
consume more retrieved chunks than the configured total budget.

## Early stopping

The agent tracks whether a retrieval action introduced any new chunk. If the
same evidence is returned again and the claim remains unsupported, V2 stops
instead of repeating another nearly identical retrieval.

The policy also exposes support-score improvement in the trace so later V2
experiments can add stronger stagnation rules without changing the output
schema.

## Trace fields

Each adaptive retrieval step can expose:

- `action`
- `failure_reason`
- `support_score_before`
- `support_score`
- `support_improvement`
- `new_chunks`
- `stopped_early`

The final answer also reports:

- `retrieval_budget`
- `budget_exhausted`
- `early_stop_reason`

These values are visible in the Streamlit Agentic retrieval trace.

## Compatibility

`AgenticVerifiedRAG` remains unchanged as the V1 fixed policy.

`AdaptiveAgenticVerifiedRAG` is a separate V2 class. The UI allows switching
between both policies.

## Evaluation

`scripts/evaluate_agent_policies.py` compares fixed and adaptive policies on
the same real BGE+FAISS QASPER index for:

1. recoverable uncited claims;
2. truly unsupported synthetic claims.

The benchmark reports recovery rate, safe abstention, average rounds, average
additional chunks, early stopping, and budget compliance.
