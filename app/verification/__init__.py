"""Claim extraction and evidence-grounding verification."""

from .claim_extractor import extract_claims
from .verifier import CitationGroundingVerifier, lexical_support_score
from .verified_rag import VerifiedRAG

__all__ = [
    "CitationGroundingVerifier",
    "VerifiedRAG",
    "extract_claims",
    "lexical_support_score",
]
