"""
Audit Trail Service for EvidenceBridge.
Constructs, records, and retrieves transparent decision graphs (AuditTrails)
for healthcare claim verification, tracking every transformation and reasoning step.
"""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from app.models.schemas import (
    AuditTrail,
    Claim,
    CostAnomalyDetails,
    DecisionStep,
    EvidencePassage,
    VerificationAction,
    VerificationResult,
    VerificationVerdict,
)
from app.services.abstention import AbstentionDecision
from app.services.storage import storage_service
from app.utils.logger import logger


class AuditService:
    """Service to create, store, and query complete decision audit trails."""

    @staticmethod
    def create_step(
        step_name: str,
        input_summary: str,
        output_summary: str,
        details: Optional[dict[str, Any]] = None
    ) -> DecisionStep:
        """Create a single standardized decision step."""
        return DecisionStep(
            step_name=step_name,
            input_summary=input_summary,
            output_summary=output_summary,
            details=details or {},
            timestamp=datetime.now(timezone.utc)
        )

    @classmethod
    def record_full_audit(
        cls,
        claim: Claim,
        verification: VerificationResult,
        passages: list[EvidencePassage],
        cost_details: CostAnomalyDetails,
        abstention_decision: AbstentionDecision,
        audit_id: Optional[str] = None
    ) -> AuditTrail:
        """
        Assemble the complete 7-stage decision graph for a verified claim.
        """
        aid = audit_id or f"aud_{uuid.uuid4().hex[:16]}"
        steps: list[DecisionStep] = []

        # Step 1: Extraction Stage
        steps.append(cls.create_step(
            step_name="EXTRACTION",
            input_summary=f"Raw source text ({len(claim.original_text)} chars, origin: {claim.source_type})",
            output_summary=(
                f"Extracted Entity='{claim.extracted_fields.entity}', "
                f"Outcome='{claim.extracted_fields.effect_or_outcome or 'None'}', "
                f"Cost='{claim.extracted_fields.cost_range or 'None'}', "
                f"Confidence={claim.confidence:.2f}"
            ),
            details={
                "entity": claim.extracted_fields.entity,
                "cost_range": claim.extracted_fields.cost_range,
                "sentiment": claim.extracted_fields.sentiment.value,
                "confidence": claim.confidence
            }
        ))

        # Step 2: Provenance Binding
        steps.append(cls.create_step(
            step_name="PROVENANCE",
            input_summary=f"Raw text verification against SHA-256 digest",
            output_summary=(
                f"Cryptographic digest={claim.provenance.source_hash[:16]}..., "
                f"Snippet='{claim.provenance.original_snippet[:60]}...', "
                f"SourceURL={claim.provenance.source_url or 'unspecified'}"
            ),
            details={
                "source_hash": claim.provenance.source_hash,
                "text_length": claim.provenance.text_length,
                "ingested_at": str(claim.provenance.ingested_at)
            }
        ))

        # Step 3: Hybrid Retrieval
        used_count = sum(1 for p in passages if p.used_in_decision)
        discarded_count = len(passages) - used_count
        top_rel = max((p.relevance_score for p in passages), default=0.0)
        steps.append(cls.create_step(
            step_name="HYBRID_RETRIEVAL",
            input_summary=f"Query: entity='{claim.extracted_fields.entity}', text excerpt",
            output_summary=(
                f"Retrieved {len(passages)} passages ({used_count} used, {discarded_count} discarded). "
                f"Top relevance score={top_rel:.2f}"
            ),
            details={
                "total_retrieved": len(passages),
                "used_count": used_count,
                "discarded_count": discarded_count,
                "top_relevance": top_rel,
                "passages": [
                    {
                        "passage_id": p.passage_id,
                        "title": p.title,
                        "score": p.relevance_score,
                        "used": p.used_in_decision,
                        "discard_reason": p.discard_reason
                    }
                    for p in passages
                ]
            }
        ))

        # Step 4: Cost Anomaly Audit
        steps.append(cls.create_step(
            step_name="COST_AUDIT",
            input_summary=f"Claim cost='{claim.extracted_fields.cost_range or 'None'}'",
            output_summary=(
                f"Anomaly={cost_details.is_anomaly}, "
                f"Severity={cost_details.severity.upper()}, "
                f"Multiplier={cost_details.multiplier or 1.0:.1f}×. {cost_details.explanation}"
            ),
            details=cost_details.model_dump()
        ))

        # Step 5: Clinical Verification (Ollama)
        steps.append(cls.create_step(
            step_name="CLINICAL_VERIFICATION",
            input_summary=f"Ollama judgment on {used_count} authoritative passages",
            output_summary=(
                f"Verdict={verification.verdict.value}, "
                f"SupportScore={verification.support_score:.2f}, "
                f"Reasoning='{verification.reasoning[:120]}...'"
            ),
            details={
                "verdict": verification.verdict.value,
                "support_score": verification.support_score,
                "reasoning": verification.reasoning
            }
        ))

        # Step 6: Abstention Gate
        steps.append(cls.create_step(
            step_name="ABSTENTION_GATE",
            input_summary="Evaluating deterministic abstention policies",
            output_summary=(
                f"AbstainTriggered={abstention_decision.should_abstain}, "
                f"Rule={abstention_decision.rule_triggered.value if abstention_decision.rule_triggered else 'NONE'}. "
                f"Reason='{abstention_decision.reason or 'Passed all safety gates'}'"
            ),
            details=abstention_decision.to_dict()
        ))

        # Step 7: Final Action Synthesis
        steps.append(cls.create_step(
            step_name="FINAL_ACTION",
            input_summary="Synthesizing clinical support score, cost anomaly flag, and abstention outcome",
            output_summary=(
                f"Action={verification.action.value.upper()}, "
                f"Verdict={verification.verdict.value}, "
                f"CostAnomalyFlag={verification.cost_anomaly_flag}"
            ),
            details={
                "action": verification.action.value,
                "verdict": verification.verdict.value,
                "cost_anomaly_flag": verification.cost_anomaly_flag,
                "abstain_reason": verification.abstain_reason
            }
        ))

        audit_trail = AuditTrail(
            audit_id=aid,
            claim_id=claim.claim_id,
            verification_id=verification.verification_id,
            steps=steps,
            passages_considered=passages,
            final_verdict=verification.verdict,
            final_action=verification.action,
            final_reasoning=verification.reasoning,
            abstain_triggered=abstention_decision.should_abstain,
            abstain_reason=verification.abstain_reason or abstention_decision.reason,
            cost_anomaly_flag=verification.cost_anomaly_flag,
            created_at=datetime.now(timezone.utc)
        )

        logger.info(f"Recorded audit trail {aid} for claim {claim.claim_id} with {len(steps)} decision steps")
        return audit_trail

    @staticmethod
    async def save_audit_trail(audit_trail: AuditTrail) -> AuditTrail:
        """Persist audit trail in MongoDB."""
        return await storage_service.insert_audit_trail(audit_trail)

    @staticmethod
    async def get_audit_trail_by_claim(claim_id: str) -> Optional[AuditTrail]:
        """Fetch audit trail by claim ID."""
        return await storage_service.get_audit_trail_by_claim_id(claim_id)

    @staticmethod
    async def get_audit_trail_by_verification(verification_id: str) -> Optional[AuditTrail]:
        """Fetch audit trail by verification ID."""
        return await storage_service.get_audit_trail_by_verification_id(verification_id)


audit_service = AuditService()
