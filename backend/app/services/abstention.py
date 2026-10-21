"""
Abstention Policy Service for EvidenceBridge.
Enforces rigorous, deterministic safety gates that decide when the system MUST ABSTAIN
from issuing an ACCEPT or FLAG judgment to prevent hallucinations, false positives,
and ungrounded medical/cost assertions.
"""

from enum import Enum
from typing import Optional

from app.config import get_settings
from app.models.schemas import (
    Claim,
    CostAnomalyDetails,
    EvidencePassage,
    VerificationVerdict,
)
from app.utils.logger import logger


class AbstentionRule(str, Enum):
    """Enumeration of deterministic abstention rules."""
    NO_RELEVANT_EVIDENCE = "NO_RELEVANT_EVIDENCE"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    LOW_MODEL_CONFIDENCE = "LOW_MODEL_CONFIDENCE"
    UNBENCHMARKED_HIGH_COST = "UNBENCHMARKED_HIGH_COST"


class AbstentionDecision:
    """Encapsulates outcome of the abstention policy evaluation."""

    def __init__(
        self,
        should_abstain: bool,
        rule_triggered: Optional[AbstentionRule] = None,
        reason: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.should_abstain = should_abstain
        self.rule_triggered = rule_triggered
        self.reason = reason
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "should_abstain": self.should_abstain,
            "rule_triggered": self.rule_triggered.value if self.rule_triggered else None,
            "reason": self.reason,
            "details": self.details
        }


class AbstentionPolicyService:
    """Rigorous gatekeeper service evaluating abstention conditions."""

    def __init__(self):
        self.settings = get_settings()
        self.relevance_threshold = self.settings.RETRIEVAL_RELEVANCE_THRESHOLD
        self.min_confidence = self.settings.MIN_CONFIDENCE_THRESHOLD
        self.abstain_on_unbenchmarked_cost = self.settings.ABSTAIN_ON_UNBENCHMARKED_HIGH_COST

    def evaluate(
        self,
        claim: Claim,
        passages: list[EvidencePassage],
        cost_details: CostAnomalyDetails,
        model_verdict: Optional[VerificationVerdict] = None,
        model_support_score: Optional[float] = None,
        model_reasoning: Optional[str] = None
    ) -> AbstentionDecision:
        """
        Evaluate full set of abstention rules.
        Returns AbstentionDecision with rule name and explainable rationale.
        """
        entity = claim.extracted_fields.entity.strip()

        # Rule 1: Entity missing or unrecognized in knowledge base
        if not entity or entity.lower() in ("unknown", "unspecified medical entity", "none"):
            reason = "Entity could not be identified with sufficient precision for clinical verification."
            logger.info(f"Abstention triggered [{AbstentionRule.ENTITY_NOT_FOUND.value}] for claim {claim.claim_id}: {reason}")
            return AbstentionDecision(
                should_abstain=True,
                rule_triggered=AbstentionRule.ENTITY_NOT_FOUND,
                reason=reason,
                details={"entity": entity}
            )

        # Rule 2: No relevant passages above threshold
        usable_passages = [p for p in passages if p.used_in_decision and p.relevance_score >= self.relevance_threshold]
        if not usable_passages:
            max_rel = max((p.relevance_score for p in passages), default=0.0)
            reason = (
                f"No authoritative clinical guidelines in local knowledge base exceeded the relevance "
                f"threshold ({self.relevance_threshold:.2f}). Maximum observed relevance was {max_rel:.2f} for entity '{entity}'."
            )
            logger.info(f"Abstention triggered [{AbstentionRule.NO_RELEVANT_EVIDENCE.value}] for claim {claim.claim_id}: {reason}")
            return AbstentionDecision(
                should_abstain=True,
                rule_triggered=AbstentionRule.NO_RELEVANT_EVIDENCE,
                reason=reason,
                details={"entity": entity, "max_relevance": max_rel, "threshold": self.relevance_threshold}
            )

        # Rule 3: Conflicting evidence of similar strength
        # Detect if model reasoning reports conflicting or contradictory guideline passages
        if model_reasoning:
            conflict_keywords = [
                "conflicting guidelines", "contradictory evidence", "lack of consensus",
                "mixed recommendations", "equally supported and discouraged", "inconclusive evidence"
            ]
            has_conflict = any(kw in model_reasoning.lower() for kw in conflict_keywords)
            if has_conflict or model_verdict == VerificationVerdict.INSUFFICIENT_EVIDENCE:
                reason = (
                    "Authoritative passages exhibit conflicting recommendations or lack consensus for this clinical scenario. "
                    "System abstains from formulating a decisive judgment."
                )
                logger.info(f"Abstention triggered [{AbstentionRule.CONFLICTING_EVIDENCE.value}] for claim {claim.claim_id}: {reason}")
                return AbstentionDecision(
                    should_abstain=True,
                    rule_triggered=AbstentionRule.CONFLICTING_EVIDENCE,
                    reason=reason,
                    details={"model_reasoning": model_reasoning}
                )

        # Rule 4: Model confidence below threshold (unless explicit contradiction)
        if model_support_score is not None:
            # Explicit contradiction is a definitive clinical finding (score ~0.0-0.3)
            is_explicit_contradiction = (model_verdict == VerificationVerdict.CONTRADICTED)
            if not is_explicit_contradiction and model_support_score < self.min_confidence:
                reason = (
                    f"Verification support score ({model_support_score:.2f}) is below the required confidence "
                    f"floor ({self.min_confidence:.2f}) without a definitive contradiction."
                )
                logger.info(f"Abstention triggered [{AbstentionRule.LOW_MODEL_CONFIDENCE.value}] for claim {claim.claim_id}: {reason}")
                return AbstentionDecision(
                    should_abstain=True,
                    rule_triggered=AbstentionRule.LOW_MODEL_CONFIDENCE,
                    reason=reason,
                    details={"support_score": model_support_score, "threshold": self.min_confidence}
                )

        # Rule 5: Significant cost data present ($100+), but no price benchmark found
        if self.abstain_on_unbenchmarked_cost and cost_details.extracted_amount:
            amount = cost_details.extracted_amount
            if amount >= 100.0 and cost_details.benchmark_max is None:
                # If claim has high cost but no benchmark in knowledge base to compare against
                reason = (
                    f"Substantial financial charge of ${amount:,.2f} reported, but no public pricing benchmark "
                    f"exists in local knowledge base for entity '{entity}'. Cost fairness cannot be audited."
                )
                logger.info(f"Abstention triggered [{AbstentionRule.UNBENCHMARKED_HIGH_COST.value}] for claim {claim.claim_id}: {reason}")
                return AbstentionDecision(
                    should_abstain=True,
                    rule_triggered=AbstentionRule.UNBENCHMARKED_HIGH_COST,
                    reason=reason,
                    details={"extracted_amount": amount, "entity": entity}
                )

        # Passed all gates: No abstention required
        return AbstentionDecision(
            should_abstain=False,
            rule_triggered=None,
            reason=None,
            details={"usable_passages_count": len(usable_passages)}
        )


abstention_service = AbstentionPolicyService()
