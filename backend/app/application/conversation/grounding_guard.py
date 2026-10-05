"""
Strict Anti-Hallucination Grounding Guard.

Enforces binary grounding verification based on active generation presence,
evidence retrieval count, and calibrated Cross-Encoder relevance score thresholds.
Provides mandatory standard bilingual fallback messages when evidence is insufficient.
"""

from dataclasses import dataclass
from typing import List, Optional
from app.application.rag.schemas import RetrievalCandidate

# Mandatory standard fallback messages approved in PRD / Rules
ENGLISH_FALLBACK = "Information is not available in the knowledge base."
KANNADA_FALLBACK = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."


@dataclass(frozen=True)
class GroundingResult:
    """Outcome of the strict grounding evaluation."""
    is_grounded: bool
    fallback_message: Optional[str]
    top_score: Optional[float]
    evidence_count: int


class GroundingGuard:
    """Validates evidence presence and quality before constructing client responses."""

    def __init__(self, min_score_threshold: float = -6.0):
        self.min_score_threshold = min_score_threshold

    def evaluate(
        self,
        candidates: List[RetrievalCandidate],
        language: str,
        active_generation_id: Optional[str],
    ) -> GroundingResult:
        """
        Evaluate if retrieved evidence is sufficient and trustworthy.

        Args:
            candidates: Ranked list of RetrievalCandidate items from Phase 7 retrieval.
            language: Detected language ('en', 'kn', or 'kn-mixed').
            active_generation_id: UUID of the current active knowledge generation in MySQL.

        Returns:
            GroundingResult with boolean decision and localized fallback message if ungrounded.
        """
        fallback_msg = KANNADA_FALLBACK if language in ("kn", "kn-mixed") else ENGLISH_FALLBACK

        if not active_generation_id or not candidates:
            return GroundingResult(
                is_grounded=False,
                fallback_message=fallback_msg,
                top_score=None,
                evidence_count=0,
            )

        top_cand = candidates[0]
        top_score = top_cand.reranker_score

        # If reranker score exists and is below calibrated threshold -> ungrounded
        if top_score is not None and top_score < self.min_score_threshold:
            return GroundingResult(
                is_grounded=False,
                fallback_message=fallback_msg,
                top_score=top_score,
                evidence_count=0,
            )

        return GroundingResult(
            is_grounded=True,
            fallback_message=None,
            top_score=top_score,
            evidence_count=len(candidates),
        )
