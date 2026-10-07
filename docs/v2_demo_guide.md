# V2 Demo Guide

## Goal

Demonstrate how V2 improves document coverage, grounding, verification, and
agent efficiency while keeping V1 behavior available for comparison.

## 1. Introduce V1 vs V2

V1 established the core architecture:

```text
PDF -> chunks -> BGE + FAISS -> answer -> claim verification -> bounded recovery
```

V2 adds four upgrades around that stable core:

```text
OCR ingestion
+ guarded local generation
+ semantic NLI verification
+ adaptive budgeted agent
```

Hybrid retrieval/reranking is available as an experimental optional retrieval
mode; dense BGE remains the validated default.

## 2. Show scanned-PDF support

Upload an image-only or text-poor English PDF.

Point out:

- OCR is enabled locally with Tesseract;
- the workspace reports the number of OCR pages;
- OCR text retains its page provenance;
- no paid OCR service is required.

## 3. Ask a normal answerable question

Use:

- Retrieval: **V1 dense BGE + FAISS**
- Verifier: **V2 semantic NLI**
- Agent policy: **V2 adaptive budgeted**

Explain that dense BGE stays the default because the full QASPER benchmark did
not show a Recall@5 improvement from RRF alone.

## 4. Show semantic verification

Open a verification expander.

Point out:

- semantic entailment score;
- lexical score retained as a diagnostic;
- verifier method;
- exact evidence labels.

Explain that V2 can recognize semantic entailment beyond simple token overlap,
while still requiring valid citations.

## 5. Show adaptive agent behavior

Ask an unsupported or evidence-poor question.

Point out:

- failure reason;
- chosen action;
- retrieval query;
- number of new chunks;
- support-score change;
- early-stop reason;
- retrieval budget.

The controlled benchmark preserved 100% safe abstention while reducing
unsupported-case average retrieval from 3 rounds / 9 chunks in the fixed V1
policy to 2 rounds / 6 chunks in the adaptive V2 policy.

## 6. Show V1 vs V2 side-by-side

Open the **V1 vs V2** tab and ask one question.

The comparison intentionally uses:

- the same uploaded corpus;
- the same dense BGE retriever;
- the same deterministic extractive generator.

This isolates the architectural difference:

- V1: lexical verifier + fixed bounded agent;
- V2: semantic NLI verifier + adaptive budgeted agent.

Compare:

- final answer;
- verification status;
- additional rounds;
- additional chunks;
- V2 adaptive trace.

## 7. Optional: show guarded local LLM generation

If a local Ollama/LM Studio OpenAI-compatible endpoint is available, select
**V2 grounded local LLM**.

Explain the contract:

```text
local LLM answer
 -> validate citations
 -> repair once if invalid
 -> deterministic extractive fallback if still invalid
```

This means fluent local generation does not bypass the grounding contract.

## 8. Optional: compare retrieval modes

The UI exposes:

- V1 dense BGE + FAISS;
- V2 hybrid RRF;
- V2 hybrid + reranker.

Recorded QASPER findings:

- full-set dense Recall@5: **66.10%**;
- full-set hybrid RRF Recall@5: **65.43%**;
- therefore dense remains default;
- on the matched 50-question sample, dense Recall@5 was **70%** and
  hybrid+reranker reached **74%**.

Explain that V2 keeps experimental improvements optional when a benchmark does
not justify replacing the validated default.

## 9. Finish with safety behavior

Use a question whose answer is absent from the document.

The expected behavior is not to invent an answer. V2 should either recover
support through bounded retrieval or return insufficient verified evidence.

## Short oral conclusion

> V1 proved the document-RAG pipeline. V2 keeps that stable baseline and adds
> broader document coverage, guarded local generation, semantic verification,
> and a more efficient failure-aware agent. The design keeps every improvement
> inspectable and benchmarked instead of automatically replacing a stronger
> baseline.
