"""Retrieval-augmented generation layers."""

from .classical import ClassicalRAG, build_rag_prompt
from .generators import (
    ExtractiveGenerator,
    GroundedLocalGenerator,
    OpenAICompatibleGenerator,
    TextGenerator,
)

__all__ = [
    "ClassicalRAG",
    "ExtractiveGenerator",
    "GroundedLocalGenerator",
    "OpenAICompatibleGenerator",
    "TextGenerator",
    "build_rag_prompt",
]
