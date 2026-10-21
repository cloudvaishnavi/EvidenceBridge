"""
Storage Service for EvidenceBridge.
Manages asynchronous MongoDB operations for storing, retrieving,
and querying claims and their associated provenance.
"""

from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, DuplicateKeyError, ServerSelectionTimeoutError

from app.config import get_settings
from app.models.schemas import Claim, VerificationResult
from app.utils.logger import logger


class StorageError(Exception):
    """Generic storage exception."""
    pass


class StorageService:
    """Asynchronous MongoDB storage client for EvidenceBridge claims."""

    def __init__(self, client: Optional[AsyncIOMotorClient] = None):
        self.settings = get_settings()
        self._client: Optional[AsyncIOMotorClient] = client
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._collection: Optional[AsyncIOMotorCollection] = None
        self._verifications_collection: Optional[AsyncIOMotorCollection] = None

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
            logger.info("MongoDB connection closed")

    async def _ensure_indexes(self) -> None:
        """Create indexes on claim_id, timestamp, and source_hash."""
        if self._collection is not None:
            try:
                await self._collection.create_index("claim_id", unique=True)
                await self._collection.create_index("timestamp")
                await self._collection.create_index("provenance.source_hash")
                await self._collection.create_index("extracted_fields.entity")
                logger.info("MongoDB indexes verified on collection 'claims'")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on claims: {e}")

        if self._verifications_collection is not None:
            try:
                await self._verifications_collection.create_index("claim_id", unique=True)
                await self._verifications_collection.create_index("verified_at")
                await self._verifications_collection.create_index("verdict")
                await self._verifications_collection.create_index("action")
                logger.info("MongoDB indexes verified on collection 'verifications'")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on verifications: {e}")

    async def check_health(self) -> dict[str, Any]:
        """Check MongoDB connection and return status."""
        if self._client is None:
            return {"status": "uninitialized", "error": "Client not connected"}
        try:
            await self._client.admin.command("ping")
            claims_cnt = await self.count_claims()
            verifications_cnt = await self.count_verifications()
            return {
                "status": "healthy",
                "database": self.settings.MONGODB_DB_NAME,
                "collection": self.settings.MONGODB_CLAIMS_COLLECTION,
                "claims_count": claims_cnt,
                "verifications_count": verifications_cnt,
            }
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

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

    async def list_claims(self, limit: int = 50, skip: int = 0) -> list[Claim]:
        """Retrieve a paginated list of claims sorted newest first."""
        try:
            cursor = (
                self.collection.find({}, {"_id": 0})
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

    async def count_claims(self) -> int:
        """Return total number of claims in collection."""
        try:
            return await self.collection.count_documents({})
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


# Global singleton instance for application lifecycle
storage_service = StorageService()
