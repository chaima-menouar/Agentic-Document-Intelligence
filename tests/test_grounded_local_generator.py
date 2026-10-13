"""Tests for the V2 guarded local generator."""

from app.rag import GroundedLocalGenerator


PROMPT = """Answer the question using ONLY the evidence below.

Rules:
1. Do not use outside knowledge.
2. End every factual sentence with one or more source labels such as [S1].
3. Only cite labels that appear in the evidence; never invent a label.
4. If the evidence is not sufficient to answer, output exactly:
   INSUFFICIENT_EVIDENCE

Question:
What does the system use?

Evidence:
[S1] page=1
The system uses BGE embeddings for semantic retrieval.

[S2] page=2
FAISS stores the vectors for efficient search.

Answer:
"""


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("No fake response left.")
        return self.responses.pop(0)


class FakeFallback:
    def __init__(self, answer: str = "Fallback answer [S1]"):
        self.answer = answer
        self.calls = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.answer


def test_valid_grounded_answer_passes_without_repair() -> None:
    client = FakeClient([
        "The system uses BGE embeddings for semantic retrieval [S1]."
    ])
    fallback = FakeFallback()
    generator = GroundedLocalGenerator(
        client=client,
        fallback=fallback,
        max_repair_attempts=1,
    )

    answer = generator.generate(PROMPT)

    assert answer.endswith("[S1].")
    assert len(client.prompts) == 1
    assert fallback.calls == []


def test_uncited_answer_is_repaired_once() -> None:
    client = FakeClient([
        "The system uses BGE embeddings for semantic retrieval.",
        "The system uses BGE embeddings for semantic retrieval [S1].",
    ])
    fallback = FakeFallback()
    generator = GroundedLocalGenerator(
        client=client,
        fallback=fallback,
        max_repair_attempts=1,
    )

    answer = generator.generate(PROMPT)

    assert "[S1]" in answer
    assert len(client.prompts) == 2
    assert "previous answer violated the citation contract" in client.prompts[1].lower()
    assert "[S1], [S2]" in client.prompts[1]
    assert fallback.calls == []


def test_invented_citation_falls_back_when_repair_is_still_invalid() -> None:
    client = FakeClient([
        "The answer is supported [S9].",
        "Still unsupported [S99].",
    ])
    fallback = FakeFallback("The system uses BGE embeddings for semantic retrieval [S1]")
    generator = GroundedLocalGenerator(
        client=client,
        fallback=fallback,
        max_repair_attempts=1,
    )

    answer = generator.generate(PROMPT)

    assert answer.endswith("[S1]")
    assert len(client.prompts) == 2
    assert fallback.calls == [PROMPT]


def test_insufficient_evidence_signal_is_accepted_without_repair() -> None:
    client = FakeClient(["INSUFFICIENT_EVIDENCE"])
    fallback = FakeFallback()
    generator = GroundedLocalGenerator(
        client=client,
        fallback=fallback,
        max_repair_attempts=1,
    )

    answer = generator.generate(PROMPT)

    assert answer == "INSUFFICIENT_EVIDENCE"
    assert len(client.prompts) == 1
    assert fallback.calls == []


def test_repair_can_be_disabled_and_falls_back_immediately() -> None:
    client = FakeClient(["Answer without citations."])
    fallback = FakeFallback("Fallback answer [S2]")
    generator = GroundedLocalGenerator(
        client=client,
        fallback=fallback,
        max_repair_attempts=0,
    )

    answer = generator.generate(PROMPT)

    assert answer == "Fallback answer [S2]"
    assert len(client.prompts) == 1
    assert fallback.calls == [PROMPT]


def test_every_factual_sentence_requires_a_citation() -> None:
    client = FakeClient([
        "BGE provides embeddings [S1]. FAISS stores vectors.",
        "BGE provides embeddings [S1]. FAISS stores vectors [S2].",
    ])
    fallback = FakeFallback()
    generator = GroundedLocalGenerator(
        client=client,
        fallback=fallback,
        max_repair_attempts=1,
    )

    answer = generator.generate(PROMPT)

    assert "BGE provides embeddings [S1]." in answer
    assert "FAISS stores vectors [S2]." in answer
    assert len(client.prompts) == 2
    assert fallback.calls == []
