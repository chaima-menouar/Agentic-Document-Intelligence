"""Retrieval-augmented generation layers."""

from .classical import ClassicalRAG, build_rag_prompt
from .generators import ExtractiveGenerator, OpenAICompatibleGenerator, TextGenerator

__all__ = [
    "ClassicalRAG",
    "ExtractiveGenerator",
    "OpenAICompatibleGenerator",
    "TextGenerator",
    "build_rag_prompt",
]
