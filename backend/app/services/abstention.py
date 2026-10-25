"""
Abstention Policy Service for EvidenceBridge.
Enforces rigorous, deterministic safety gates that decide when the system MUST ABSTAIN
from issuing an ACCEPT or FLAG judgment to prevent hallucinations, false positives,
and ungrounded medical/cost assertions.
"""

from enum import Enum
from typing import Any, Optional

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
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
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
        model_reasoning: Optional[str] = None,
        model_conflict_assessment: Optional[dict[str, Any]] = None
    ) -> AbstentionDecision:
        """
        Evaluate full set of abstention rules.
        Returns AbstentionDecision with rule name and explainable rationale.
        """
        entity = claim.extracted_fields.entity.strip()
        audit_details = {
            "original_model_verdict": model_verdict.value if model_verdict else None,
            "conflict_assessment": model_conflict_assessment,
            "conflict_assessment_valid": False
        }

        # Rule 1: Entity missing or unrecognized in knowledge base
        if not entity or entity.lower() in ("unknown", "unspecified medical entity", "none"):
            reason = "Entity could not be identified with sufficient precision for clinical verification."
            logger.info(f"Abstention triggered [{AbstentionRule.ENTITY_NOT_FOUND.value}] for claim {claim.claim_id}: {reason}")
            return AbstentionDecision(
                should_abstain=True,
                rule_triggered=AbstentionRule.ENTITY_NOT_FOUND,
                reason=reason,
                details={**audit_details, "entity": entity}
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
                details={
                    **audit_details,
                    "entity": entity,
                    "max_relevance": max_rel,
                    "threshold": self.relevance_threshold
                }
            )

        has_verified_conflict = self._has_verified_conflict(
            model_conflict_assessment,
            usable_passages
        )
        audit_details["conflict_assessment_valid"] = has_verified_conflict

        # Conflict wording is not evidence; require validated references to opposing passages.
        if (
            has_verified_conflict
            and model_verdict != VerificationVerdict.CONTRADICTED
        ):
            reason = (
                "Usable authoritative passages support opposing positions for this clinical scenario. "
                "System abstains from formulating a decisive judgment."
            )
            logger.info(f"Abstention triggered [{AbstentionRule.CONFLICTING_EVIDENCE.value}] for claim {claim.claim_id}: {reason}")
            return AbstentionDecision(
                should_abstain=True,
                rule_triggered=AbstentionRule.CONFLICTING_EVIDENCE,
                reason=reason,
                details={
                    **audit_details,
                    "supporting_passage_ids": model_conflict_assessment["supporting_passage_ids"],
                    "opposing_passage_ids": model_conflict_assessment["opposing_passage_ids"]
                }
            )

        # Insufficient evidence is an abstention condition, but does not imply conflict.
        if model_verdict == VerificationVerdict.INSUFFICIENT_EVIDENCE:
            reason = "Available evidence does not provide enough medical facts to judge the claim."
            logger.info(f"Abstention triggered [{AbstentionRule.INSUFFICIENT_EVIDENCE.value}] for claim {claim.claim_id}: {reason}")
            return AbstentionDecision(
                should_abstain=True,
                rule_triggered=AbstentionRule.INSUFFICIENT_EVIDENCE,
                reason=reason,
                details=audit_details
            )

        if (
            isinstance(model_conflict_assessment, dict)
            and model_conflict_assessment.get("has_conflict") is True
            and not has_verified_conflict
            and model_verdict != VerificationVerdict.CONTRADICTED
        ):
            reason = (
                "The model indicated opposing evidence, but its passage references could not be verified. "
                "System abstains until the evidence can be assessed reliably."
            )
            logger.info(f"Abstention triggered [{AbstentionRule.INSUFFICIENT_EVIDENCE.value}] for claim {claim.claim_id}: {reason}")
            return AbstentionDecision(
                should_abstain=True,
                rule_triggered=AbstentionRule.INSUFFICIENT_EVIDENCE,
                reason=reason,
                details=audit_details
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
                    details={
                        **audit_details,
                        "support_score": model_support_score,
                        "threshold": self.min_confidence
                    }
                )

        # Rule 5: Significant cost data present ($100+ or ₹8,000+), but no price benchmark found
        if self.abstain_on_unbenchmarked_cost and cost_details.extracted_amount:
            amount = cost_details.extracted_amount
            cost_curr = getattr(cost_details, "currency", "INR") or "INR"
            threshold_amount = 8000.0 if cost_curr == "INR" else 100.0
            curr_sym = "₹" if cost_curr == "INR" else ("€" if cost_curr == "EUR" else ("£" if cost_curr == "GBP" else "$"))

            if amount >= threshold_amount and cost_details.benchmark_max is None:
                # If claim has high cost but no benchmark in knowledge base to compare against
                reason = (
                    f"Substantial financial charge of {curr_sym}{amount:,.2f} ({cost_curr}) reported, but no public pricing benchmark "
                    f"exists in local knowledge base for entity '{entity}'. Cost fairness cannot be audited."
                )
                logger.info(f"Abstention triggered [{AbstentionRule.UNBENCHMARKED_HIGH_COST.value}] for claim {claim.claim_id}: {reason}")
                return AbstentionDecision(
                    should_abstain=True,
                    rule_triggered=AbstentionRule.UNBENCHMARKED_HIGH_COST,
                    reason=reason,
                    details={**audit_details, "extracted_amount": amount, "currency": cost_curr, "entity": entity}
                )

        # Passed all gates: No abstention required
        return AbstentionDecision(
            should_abstain=False,
            rule_triggered=None,
            reason=None,
            details={
                **audit_details,
                "usable_passages_count": len(usable_passages)
            }
        )

    @staticmethod
    def _has_verified_conflict(
        assessment: Optional[dict[str, Any]],
        usable_passages: list[EvidencePassage]
    ) -> bool:
        """Require distinct, non-empty opposing passage references from usable evidence."""
        if not isinstance(assessment, dict) or assessment.get("has_conflict") is not True:
            return False

        supporting_ids = assessment.get("supporting_passage_ids")
        opposing_ids = assessment.get("opposing_passage_ids")
        if not isinstance(supporting_ids, list) or not isinstance(opposing_ids, list):
            return False
        if not supporting_ids or not opposing_ids:
            return False
        if any(not isinstance(passage_id, str) or not passage_id.strip()
               for passage_id in supporting_ids + opposing_ids):
            return False

        supporting_set = set(supporting_ids)
        opposing_set = set(opposing_ids)
        available_ids = {passage.passage_id for passage in usable_passages}
        return (
            supporting_set.isdisjoint(opposing_set)
            and supporting_set.issubset(available_ids)
            and opposing_set.issubset(available_ids)
        )


abstention_service = AbstentionPolicyService()
