# Demo Guide

## Goal of the demo

Show the value added by each system mode rather than only showing the final interface.

## Recommended sequence

### 1. Introduce the problem

Explain that a standard RAG system can retrieve relevant passages and answer with citations, but citations alone do not guarantee that every generated claim is actually supported.

### 2. Show the architecture

Present the progression:

```text
Mode A: Retrieve -> Answer with citations
Mode B: Mode A -> Extract claims -> Verify -> Correct/abstain
Mode C: Mode B -> Re-retrieve unresolved claims -> Re-verify -> Stop or abstain
```

Emphasize that Mode C is bounded: it cannot search forever.

### 3. Show document ingestion

Upload one or more English text PDFs in the Streamlit interface.

Explain:
- text is extracted locally,
- chunks preserve provenance,
- BGE-small creates embeddings,
- FAISS performs semantic retrieval.

### 4. Demonstrate Mode A

Ask a question clearly answerable from the uploaded documents.

Point out:
- retrieved evidence,
- generated answer,
- inspectable citations.

Explain that this is the Classical RAG baseline.

### 5. Demonstrate Mode B

Use a case where an answer contains an unsupported or insufficiently grounded claim.

Point out:
- claim extraction,
- support labels,
- removal of unsupported claims,
- safe abstention when no supported answer remains.

Explain that verification is the first safety layer added beyond Classical RAG.

### 6. Demonstrate Mode C

Use a recoverable case where the first evidence set is insufficient but another relevant chunk exists in the index.

Point out:
- the unresolved claim becomes a focused retrieval query,
- new evidence is added,
- verification runs again,
- the system stops early once support is found.

Explain that this is agentic behavior because the system observes verification failure and decides to perform another bounded tool action.

### 7. Show benchmark results

Use the key results:

- Mode B unsupported/uncited detection: **100%** in controlled stress cases.
- Mode B safe abstention: **100%**.
- Mode C recovery of recoverable uncited cases: **90%**.
- Mode C safe abstention on truly unsupported claims: **100%**.
- Mode C retrieval bound respected: **100%**.
- Paid external API cost in the benchmark: **0**.

### 8. Explain the trade-off

Mode C is slower than A/B because it may retrieve again, but it spends the extra compute only when verification says evidence is insufficient.

### 9. Finish with limitations

State clearly:
- V1 supports English text PDFs,
- no OCR,
- verifier is conservative rather than a full entailment model,
- benchmark measures grounding/recovery, not general LLM answer quality.

## Short oral conclusion

> The main contribution is not only RAG. The system adds a verification loop and a bounded agent that can decide when more evidence is needed. If evidence cannot support the claim, the system abstains instead of hiding the uncertainty.
