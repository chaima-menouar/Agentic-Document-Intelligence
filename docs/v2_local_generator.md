# V2 Grounded Local Generator

Milestone 12 upgrades the optional local generation path while keeping the
deterministic extractive baseline as a zero-cost fallback.

## Flow

```text
retrieved evidence
  -> strict grounded RAG prompt
  -> local OpenAI-compatible LLM
  -> citation contract validation
      -> valid: return answer
      -> invalid: one repair request
          -> valid: return repaired answer
          -> invalid: deterministic extractive fallback
  -> Mode B / C verification continues unchanged
```

## Grounding contract

The V2 local generator requires:

- only source labels present in the retrieved Evidence section;
- at least one valid citation for a non-abstaining answer;
- every factual sentence to carry a valid citation;
- the exact `INSUFFICIENT_EVIDENCE` signal when the evidence is insufficient.

The guard rejects invented labels such as `[S99]`. A repair prompt is sent once
by default. If the model still violates the contract, the offline extractive
baseline returns a deterministic grounded answer instead.

## Local model server

The UI accepts any local service that exposes an OpenAI-compatible
`/chat/completions` endpoint, including local inference applications such as
Ollama or LM Studio.

Default endpoint shown in the UI:

```text
http://localhost:11434/v1
```

The model name remains user-configurable because available local models depend
on the machine and inference server.

## Cost and privacy

No paid external API is required. When the endpoint points to a local inference
server, the generation request remains on the user's machine/environment.

## Validation

`.github/workflows/v2-local-generator-e2e.yml` validates:

1. unit tests for valid, uncited, invalid-label, repair, and fallback cases;
2. the real HTTP code path against a local OpenAI-compatible test server;
3. the repair request after an uncited first response;
4. Streamlit module compilation.
