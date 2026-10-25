"""
Provenance Service for EvidenceBridge.
Guarantees end-to-end traceability and immutability:
Links extracted claims back to their verbatim original text, source metadata,
and cryptographic digests so the origin of every claim is never lost.
"""

from datetime import datetime, timezone
import hashlib
from typing import Optional
import uuid

from app.models.schemas import (
    Claim,
    ExtractedFields,
    LocationInfo,
    ProvenanceMetadata,
    SourceType,
)
from app.services.location import location_service
from app.utils.logger import logger


class ProvenanceService:
    """Service to create, verify, and attach immutable provenance records to claims."""

    @staticmethod
    def compute_sha256(text: str) -> str:
        """Compute SHA-256 hexadecimal digest of input text."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def generate_claim_id() -> str:
        """Generate a clean, collision-free, prefixed claim ID."""
        return f"clm_{uuid.uuid4().hex[:16]}"

    @classmethod
    def extract_snippet(cls, text: str, max_length: int = 140) -> str:
        """Extract a representative initial snippet from raw text."""
        cleaned = " ".join(text.strip().split())
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[:max_length].rstrip() + "..."

    @classmethod
    def create_provenance(
        cls,
        original_text: str,
        source_type: Optional[str] = None,
        source_url: Optional[str] = None,
        source_timestamp: Optional[datetime] = None,
    ) -> ProvenanceMetadata:
        """Construct ProvenanceMetadata capturing full lineage of the raw text."""
        normalized_type = (source_type or SourceType.CLINICAL_NOTE.value).lower().strip()
        source_hash = cls.compute_sha256(original_text)
        snippet = cls.extract_snippet(original_text)
        now_utc = datetime.now(timezone.utc)

        return ProvenanceMetadata(
            source_hash=source_hash,
            original_snippet=snippet,
            text_length=len(original_text),
            source_type=normalized_type,
            source_url=source_url,
            source_timestamp=source_timestamp,
            ingested_at=now_utc,
        )

    @classmethod
    def assemble_claim(
        cls,
        original_text: str,
        extracted_fields: ExtractedFields,
        confidence: float,
        source_type: Optional[str] = None,
        source_url: Optional[str] = None,
        source_timestamp: Optional[datetime] = None,
        claim_id: Optional[str] = None,
        location: Optional[LocationInfo] = None,
    ) -> Claim:
        """
        Assemble a fully traceable Claim combining extracted fields,
        confidence, tamper-evident provenance, and geographic location.
        """
        cid = claim_id or cls.generate_claim_id()
        provenance = cls.create_provenance(
            original_text=original_text,
            source_type=source_type,
            source_url=source_url,
            source_timestamp=source_timestamp,
        )

        effective_timestamp = source_timestamp or provenance.ingested_at

        # Resolve location from explicit argument or automatically extract from text/fields
        resolved_location = location
        if resolved_location is None:
            resolved_location = location_service.extract_location(
                text=original_text,
                location_field=extracted_fields.location_city,
            )

        # Detect and set explicit cost_currency if cost is present
        if extracted_fields.cost_range and not extracted_fields.cost_currency:
            loc_str = ""
            if resolved_location and resolved_location.city:
                loc_str = f"{resolved_location.city} {resolved_location.state_or_region or ''}"
            elif extracted_fields.location_city:
                loc_str = extracted_fields.location_city
            try:
                from app.services.cost_anomaly import cost_anomaly_service
                extracted_fields.cost_currency = cost_anomaly_service.detect_currency(
                    extracted_fields.cost_range,
                    original_text,
                    loc_str
                )
            except Exception:
                extracted_fields.cost_currency = "USD"

        claim = Claim(
            claim_id=cid,
            original_text=original_text,
            source_type=provenance.source_type,
            source_url=source_url,
            timestamp=effective_timestamp,
            extracted_fields=extracted_fields,
            confidence=round(confidence, 4),
            provenance=provenance,
            location=resolved_location,
            indexed_vector=False,
        )

        logger.info(f"Assembled claim {claim.claim_id} for entity '{claim.extracted_fields.entity}' with provenance hash {provenance.source_hash[:12]}...")
        return claim

    @classmethod
    def verify_provenance(cls, claim: Claim) -> bool:
        """
        Verify that a claim's original text has not been tampered with
        and matches its cryptographic source hash.
        """
        expected_hash = cls.compute_sha256(claim.original_text)
        is_valid = expected_hash == claim.provenance.source_hash
        if not is_valid:
            logger.warning(
                f"Provenance integrity check FAILED for claim {claim.claim_id}. "
                f"Expected {expected_hash}, found {claim.provenance.source_hash}"
            )
        return is_valid
