# V2 Final Manual Test

This is intentionally the **only manual release test** required after automated
validation.

## Goal

Confirm the final Streamlit release candidate works end-to-end from a real user
interaction.

## Test configuration

Use one PDF already known to contain answerable text. Recommended settings:

- Assistant mode: **Agentic Verified RAG**
- Generator: **Offline extractive baseline**
- Retrieval: **V1 dense BGE + FAISS**
- Verifier: **V2 semantic NLI**
- Agent policy: **V2 adaptive budgeted**
- OCR: enabled
- Top-K: 5

Dense retrieval and the extractive generator are used in this release test to
avoid depending on a separate local LLM server and to isolate the validated V2
verification/agent path.

## One test

1. Start the V2 Streamlit app.
2. Upload the PDF and process it.
3. Ask one clearly answerable question from the document.
4. Pass the release only if:
   - a grounded answer is returned;
   - at least one valid citation is shown;
   - verification is not unsupported;
   - no application exception appears;
   - the cited source text is visibly relevant to the answer.

If the answer needs no extra retrieval, zero agentic rounds is valid. If the
agent runs, its trace must remain within the configured budget.

## After PASS

- Mark the draft V2 pull request ready for review.
- Merge `v2-development` into `main`.
- Optionally create a V2 release/tag.

## After FAIL

Do not merge. Capture the screenshot/error, fix the branch, rerun the automated
validation affected by the fix, then repeat this same single manual test.
