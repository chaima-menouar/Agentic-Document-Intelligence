"""Claim extraction and evidence-grounding verification."""

from .claim_extractor import extract_claims
from .corrector import CorrectedVerifiedRAG, correct_verified_answer
from .verifier import CitationGroundingVerifier, lexical_support_score
from .verified_rag import VerifiedRAG

__all__ = [
    "CitationGroundingVerifier",
    "CorrectedVerifiedRAG",
    "VerifiedRAG",
    "correct_verified_answer",
    "extract_claims",
    "lexical_support_score",
]
