"""
Storage Service for EvidenceBridge.
Manages asynchronous MongoDB operations for storing, retrieving,
and querying claims and their associated provenance.
"""

import re
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, DuplicateKeyError, ServerSelectionTimeoutError

from app.config import get_settings
from app.models.schemas import AuditTrail, Claim, VerificationResult
from app.utils.logger import logger


class StorageError(Exception):
    """Generic storage exception."""
    pass


class StorageService:
    """Asynchronous MongoDB storage client for EvidenceBridge claims, verifications, and audit trails."""

    def __init__(self, client: Optional[AsyncIOMotorClient] = None):
        self.settings = get_settings()
        self._client: Optional[AsyncIOMotorClient] = client
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._collection: Optional[AsyncIOMotorCollection] = None
        self._verifications_collection: Optional[AsyncIOMotorCollection] = None
        self._audit_trails_collection: Optional[AsyncIOMotorCollection] = None
        self._trust_density_collection: Optional[AsyncIOMotorCollection] = None

    async def connect(self) -> None:
        """Initialize connection pool to MongoDB and ensure indexes."""
        if self._client is None:
            logger.info(f"Connecting to MongoDB at {self.settings.MONGODB_URL}")
            self._client = AsyncIOMotorClient(
                self.settings.MONGODB_URL,
                serverSelectionTimeoutMS=self.settings.MONGODB_TIMEOUT_MS,
            )
        self._db = self._client[self.settings.MONGODB_DB_NAME]
        self._collection = self._db[self.settings.MONGODB_CLAIMS_COLLECTION]
        self._verifications_collection = self._db[self.settings.MONGODB_VERIFICATIONS_COLLECTION]
        self._audit_trails_collection = self._db[self.settings.MONGODB_AUDIT_TRAILS_COLLECTION]
        self._trust_density_collection = self._db[self.settings.MONGODB_TRUST_DENSITY_COLLECTION]

        try:
            # Ping database to verify connection
            await self._client.admin.command("ping")
            logger.info(f"MongoDB connection established to database: {self.settings.MONGODB_DB_NAME}")
            await self._ensure_indexes()
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            logger.warning(f"MongoDB ping failed at startup (server may be offline): {e}")

    async def close(self) -> None:
        """Close MongoDB connection pool."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._collection = None
            self._verifications_collection = None
            self._audit_trails_collection = None
            self._trust_density_collection = None
            logger.info("MongoDB connection closed")

    async def _ensure_indexes(self) -> None:
        """Create indexes on claims, verifications, and audit_trails."""
        if self._collection is not None:
            try:
                await self._collection.create_index("claim_id", unique=True)
                await self._collection.create_index("timestamp")
                await self._collection.create_index("provenance.source_hash")
                await self._collection.create_index("extracted_fields.entity")
                await self._collection.create_index("location.normalized_key")
                logger.info("MongoDB indexes verified on collection 'claims'")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on claims: {e}")

        if self._verifications_collection is not None:
            try:
                await self._verifications_collection.create_index("claim_id", unique=True)
                await self._verifications_collection.create_index("verification_id")
                await self._verifications_collection.create_index("verified_at")
                await self._verifications_collection.create_index("verdict")
                await self._verifications_collection.create_index("action")
                logger.info("MongoDB indexes verified on collection 'verifications'")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on verifications: {e}")

        if self._audit_trails_collection is not None:
            try:
                await self._audit_trails_collection.create_index("audit_id", unique=True)
                await self._audit_trails_collection.create_index("claim_id")
                await self._audit_trails_collection.create_index("verification_id")
                await self._audit_trails_collection.create_index("created_at")
                logger.info("MongoDB indexes verified on collection 'audit_trails'")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on audit_trails: {e}")

        if self._trust_density_collection is not None:
            try:
                await self._trust_density_collection.create_index("location_key", unique=True)
                await self._trust_density_collection.create_index("density_score")
                await self._trust_density_collection.create_index("trust_tier")
                logger.info("MongoDB indexes verified on collection 'trust_density'")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on trust_density: {e}")

    async def check_health(self) -> dict[str, Any]:
        """Check MongoDB connection and return status."""
        if self._client is None:
            return {"status": "uninitialized", "error": "Client not connected"}
        try:
            await self._client.admin.command("ping")
            claims_cnt = await self.count_claims()
            verifications_cnt = await self.count_verifications()
            audit_cnt = await self.count_audit_trails()
            trust_cnt = await self.count_trust_densities()
            return {
                "status": "healthy",
                "database": self.settings.MONGODB_DB_NAME,
                "collection": self.settings.MONGODB_CLAIMS_COLLECTION,
                "claims_count": claims_cnt,
                "verifications_count": verifications_cnt,
                "audit_trails_count": audit_cnt,
                "trust_density_count": trust_cnt,
            }
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    @property
    def is_connected(self) -> bool:
        """Check if storage client is initialized."""
        return self._client is not None and self._db is not None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Access the claims collection."""
        if self._collection is None:
            raise StorageError("StorageService is not connected. Call connect() first.")
        return self._collection

    @property
    def verifications_collection(self) -> AsyncIOMotorCollection:
        """Access the verifications collection."""
        if self._verifications_collection is None:
            raise StorageError("StorageService is not connected. Call connect() first.")
        return self._verifications_collection

    @property
    def audit_trails_collection(self) -> AsyncIOMotorCollection:
        """Access the audit trails collection."""
        if self._audit_trails_collection is None:
            raise StorageError("StorageService is not connected. Call connect() first.")
        return self._audit_trails_collection

    @property
    def trust_density_collection(self) -> AsyncIOMotorCollection:
        """Access the trust density collection."""
        if self._trust_density_collection is None:
            raise StorageError("StorageService is not connected. Call connect() first.")
        return self._trust_density_collection

    async def insert_claim(self, claim: Claim) -> Claim:
        """
        Persist a claim to MongoDB.
        Raises DuplicateKeyError if claim_id already exists.
        """
        doc = claim.model_dump(mode="python")
        try:
            result = await self.collection.insert_one(doc)
            logger.info(f"Inserted claim {claim.claim_id} into MongoDB (inserted_id={result.inserted_id})")
            return claim
        except DuplicateKeyError:
            logger.warning(f"Claim {claim.claim_id} already exists in database")
            raise StorageError(f"Claim with id '{claim.claim_id}' already exists")
        except Exception as e:
            logger.error(f"Failed to insert claim {claim.claim_id}: {e}")
            raise StorageError(f"Database insertion failed: {e}") from e

    async def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Retrieve a single claim by its unique claim_id."""
        try:
            doc = await self.collection.find_one({"claim_id": claim_id}, {"_id": 0})
            if not doc:
                return None
            return Claim.model_validate(doc)
        except Exception as e:
            logger.error(f"Failed to retrieve claim {claim_id}: {e}")
            raise StorageError(f"Database query failed: {e}") from e

    async def list_claims(
        self,
        limit: int = 50,
        skip: int = 0,
        location: Optional[str] = None,
    ) -> list[Claim]:
        """Retrieve a paginated list of claims sorted newest first, optionally filtered by location."""
        try:
            query: dict[str, Any] = {}
            if location:
                loc_clean = location.strip().lower()
                query = {
                    "$or": [
                        {"location.normalized_key": loc_clean},
                        {"location.city": {"$regex": f"^{re.escape(location.strip())}$", "$options": "i"}},
                    ]
                }

            cursor = (
                self.collection.find(query, {"_id": 0})
                .sort("timestamp", -1)
                .skip(skip)
                .limit(limit)
            )
            claims: list[Claim] = []
            async for doc in cursor:
                claims.append(Claim.model_validate(doc))
            return claims
        except Exception as e:
            logger.error(f"Failed to list claims: {e}")
            raise StorageError(f"Database query failed: {e}") from e

    async def count_claims(self, location: Optional[str] = None) -> int:
        """Return total number of claims in collection, optionally filtered by location."""
        try:
            query: dict[str, Any] = {}
            if location:
                loc_clean = location.strip().lower()
                query = {
                    "$or": [
                        {"location.normalized_key": loc_clean},
                        {"location.city": {"$regex": f"^{re.escape(location.strip())}$", "$options": "i"}},
                    ]
                }
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.warning(f"Failed to count claims: {e}")
            return 0

    async def insert_verification(self, verification: VerificationResult) -> VerificationResult:
        """
        Persist or update a verification result linked to claim_id in MongoDB.
        Uses upsert on claim_id so re-verifications cleanly replace old audits.
        """
        doc = verification.model_dump(mode="python")
        try:
            await self.verifications_collection.update_one(
                {"claim_id": verification.claim_id},
                {"$set": doc},
                upsert=True
            )
            logger.info(f"Saved verification for claim {verification.claim_id} (verdict={verification.verdict.value}, action={verification.action.value})")
            return verification
        except Exception as e:
            logger.error(f"Failed to save verification for claim {verification.claim_id}: {e}")
            raise StorageError(f"Database verification insertion failed: {e}") from e

    async def get_verification(self, claim_id: str) -> Optional[VerificationResult]:
        """Retrieve a verification result by claim_id."""
        try:
            doc = await self.verifications_collection.find_one({"claim_id": claim_id}, {"_id": 0})
            if not doc:
                return None
            return VerificationResult.model_validate(doc)
        except Exception as e:
            logger.error(f"Failed to retrieve verification for claim {claim_id}: {e}")
            raise StorageError(f"Database query failed: {e}") from e

    async def count_verifications(self) -> int:
        """Return total number of verification records in collection."""
        try:
            return await self.verifications_collection.count_documents({})
        except Exception as e:
            logger.warning(f"Failed to count verifications: {e}")
            return 0

    async def insert_audit_trail(self, audit_trail: AuditTrail) -> AuditTrail:
        """
        Persist or update an audit trail linked to claim_id and verification_id in MongoDB.
        Uses upsert on audit_id.
        """
        doc = audit_trail.model_dump(mode="python")
        try:
            await self.audit_trails_collection.update_one(
                {"audit_id": audit_trail.audit_id},
                {"$set": doc},
                upsert=True
            )
            logger.info(f"Saved audit trail {audit_trail.audit_id} for claim {audit_trail.claim_id} ({len(audit_trail.steps)} steps)")
            return audit_trail
        except Exception as e:
            logger.error(f"Failed to save audit trail {audit_trail.audit_id}: {e}")
            raise StorageError(f"Database audit trail insertion failed: {e}") from e

    async def get_audit_trail_by_claim_id(self, claim_id: str) -> Optional[AuditTrail]:
        """Retrieve the most recent audit trail for a claim."""
        try:
            cursor = self.audit_trails_collection.find({"claim_id": claim_id}, {"_id": 0}).sort("created_at", -1).limit(1)
            docs = await cursor.to_list(length=1)
            if not docs:
                return None
            return AuditTrail.model_validate(docs[0])
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail for claim {claim_id}: {e}")
            raise StorageError(f"Database query failed: {e}") from e

    async def get_audit_trail_by_verification_id(self, verification_id: str) -> Optional[AuditTrail]:
        """Retrieve audit trail by its verification_id."""
        try:
            doc = await self.audit_trails_collection.find_one({"verification_id": verification_id}, {"_id": 0})
            if not doc:
                return None
            return AuditTrail.model_validate(doc)
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail for verification {verification_id}: {e}")
            raise StorageError(f"Database query failed: {e}") from e

    async def count_audit_trails(self) -> int:
        """Return total number of audit trail records in collection."""
        try:
            return await self.audit_trails_collection.count_documents({})
        except Exception as e:
            logger.warning(f"Failed to count audit trails: {e}")
            return 0

    # --------------------------------------------------------------------------
    # Layer 4: Trust Density & Location Methods
    # --------------------------------------------------------------------------

    async def get_claims_by_location(self, location_key: str) -> list[dict[str, Any]]:
        """Retrieve all claim documents matching a normalized location key or city name."""
        try:
            loc_clean = location_key.strip().lower()
            query = {
                "$or": [
                    {"location.normalized_key": loc_clean},
                    {"location.city": {"$regex": f"^{re.escape(location_key.strip())}$", "$options": "i"}},
                ]
            }
            cursor = self.collection.find(query, {"_id": 0}).sort("timestamp", -1)
            claims: list[dict[str, Any]] = []
            async for doc in cursor:
                claims.append(doc)
            return claims
        except Exception as e:
            logger.error(f"Failed to retrieve claims for location {location_key}: {e}")
            return []

    async def get_verification_by_claim_id(self, claim_id: str) -> Optional[dict[str, Any]]:
        """Retrieve raw verification document for a claim."""
        try:
            return await self.verifications_collection.find_one({"claim_id": claim_id}, {"_id": 0})
        except Exception as e:
            logger.error(f"Failed to retrieve verification for claim {claim_id}: {e}")
            return None

    async def upsert_trust_density(
        self,
        metrics_dict: dict[str, Any],
        insight_dict: Optional[dict[str, Any]] = None,
    ) -> None:
        """Persist or update aggregated trust density metrics and insight for a locality."""
        try:
            loc_key = metrics_dict["location_key"].lower()
            doc = {
                "location_key": loc_key,
                "city": metrics_dict.get("city", loc_key),
                "state_or_region": metrics_dict.get("state_or_region"),
                "metrics": metrics_dict,
                "insight": insight_dict,
                "density_score": metrics_dict.get("density_score", 0.5),
                "trust_tier": metrics_dict.get("trust_tier"),
                "total_claims": metrics_dict.get("total_claims", 0),
                "verified_claims": metrics_dict.get("verified_claims", 0),
                "last_updated": metrics_dict.get("last_updated"),
            }
            await self.trust_density_collection.update_one(
                {"location_key": loc_key},
                {"$set": doc},
                upsert=True,
            )
            logger.info(f"Upserted trust density for location '{loc_key}' (score={metrics_dict.get('density_score')})")
        except Exception as e:
            logger.error(f"Failed to upsert trust density for {metrics_dict.get('location_key')}: {e}")
            raise StorageError(f"Trust density upsert failed: {e}") from e

    async def get_trust_density(self, location_key: str) -> Optional[dict[str, Any]]:
        """Retrieve aggregated trust density record by location key."""
        try:
            loc_clean = location_key.strip().lower()
            return await self.trust_density_collection.find_one({"location_key": loc_clean}, {"_id": 0})
        except Exception as e:
            logger.error(f"Failed to retrieve trust density for {location_key}: {e}")
            return None

    async def list_trust_densities(
        self,
        limit: int = 50,
        skip: int = 0,
        sort_by: str = "density_score",
    ) -> list[dict[str, Any]]:
        """Retrieve list of trust density records, sorted by density_score or total_claims."""
        try:
            sort_field = "total_claims" if sort_by == "volume" else "density_score"
            cursor = (
                self.trust_density_collection.find({}, {"_id": 0})
                .sort(sort_field, -1)
                .skip(skip)
                .limit(limit)
            )
            records: list[dict[str, Any]] = []
            async for doc in cursor:
                records.append(doc)
            return records
        except Exception as e:
            logger.error(f"Failed to list trust density records: {e}")
            return []

    async def count_trust_densities(self) -> int:
        """Return total number of trust density location records."""
        try:
            return await self.trust_density_collection.count_documents({})
        except Exception as e:
            logger.warning(f"Failed to count trust densities: {e}")
            return 0


# Global singleton instance for application lifecycle
storage_service = StorageService()
