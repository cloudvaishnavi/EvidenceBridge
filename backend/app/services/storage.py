"""
Storage Service for EvidenceBridge.
Manages asynchronous MongoDB operations for storing, retrieving,
and querying claims and their associated provenance.
"""

from datetime import datetime, timezone
import re
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, DuplicateKeyError, ServerSelectionTimeoutError

from app.config import get_settings
from app.services.auth import (
    DEMO_USER_ID,
    DEMO_USER_EMAIL,
    DEMO_USER_NAME,
    DEMO_USER_ROLE,
    DEMO_USER_ORG,
    DEMO_USER_DEFAULT_PW,
    hash_password,
)
from app.models.schemas import (
    AuditTrail,
    Claim,
    ClaimHighlight,
    DecisionOverview,
    GapsAndRisks,
    GuidelineSupportOverview,
    InsightsSummaryResponse,
    LocationFrequency,
    PriceAlertsOverview,
    ProcedureFrequency,
    VerificationResult,
)
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
        self._users_collection: Optional[AsyncIOMotorCollection] = None
        self._collection: Optional[AsyncIOMotorCollection] = None
        self._verifications_collection: Optional[AsyncIOMotorCollection] = None
        self._audit_trails_collection: Optional[AsyncIOMotorCollection] = None
        self._trust_density_collection: Optional[AsyncIOMotorCollection] = None
        self._evaluations_collection: Optional[AsyncIOMotorCollection] = None
        self._community_stories_collection: Optional[AsyncIOMotorCollection] = None

        # In-memory users for offline / test environments
        self._in_memory_users: dict[str, dict[str, Any]] = {}
        demo_pw_hash = hash_password(DEMO_USER_DEFAULT_PW)
        demo_doc = {
            "user_id": DEMO_USER_ID,
            "name": DEMO_USER_NAME,
            "email": DEMO_USER_EMAIL.lower(),
            "hashed_password": demo_pw_hash,
            "role": DEMO_USER_ROLE,
            "organization": DEMO_USER_ORG,
            "created_at": datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        }
        self._in_memory_users[DEMO_USER_EMAIL.lower()] = demo_doc
        self._in_memory_users["demo"] = demo_doc
        self._in_memory_users["demo@evidencebridge.local"] = demo_doc
        self._in_memory_users[DEMO_USER_ID] = demo_doc

        self._in_memory_stories: list[dict[str, Any]] = [
            {
                "story_id": "story_init_01",
                "title": "Finding My Routine with Type 2 Diabetes",
                "story_text": "When I was first diagnosed with an A1c of 8.2%, I felt overwhelmed by all the medication rules and billing confusion. What helped me keep going was taking it one meal at a time, joining a walking group with my neighbor, and finding a pharmacist who took the time to explain generic metformin. It gets easier.",
                "author_name": "David M.",
                "condition_or_topic": "Type 2 Diabetes",
                "contact_email": None,
                "contact_instagram": "@david_walks_daily",
                "consent_acknowledged": True,
                "created_at": datetime(2026, 10, 20, 14, 30, tzinfo=timezone.utc),
            },
            {
                "story_id": "story_init_02",
                "title": "Coping with Unexplained Severe Migraines",
                "story_text": "Living with weekly unilateral migraines meant missing work and family dinners. Getting the MRI cleared my worst fears, but what really helped was keeping a calm symptom journal, practicing sleep hygiene, and knowing I wasn't alone. Sending strength to anyone dealing with invisible pain.",
                "author_name": "Ananya S.",
                "condition_or_topic": "Chronic Migraine",
                "contact_email": "ananya.stories@coping.org",
                "contact_instagram": None,
                "consent_acknowledged": True,
                "created_at": datetime(2026, 10, 21, 9, 15, tzinfo=timezone.utc),
            },
            {
                "story_id": "story_init_03",
                "title": "Advocating for Fair Bills After Surgery",
                "story_text": "After an emergency procedure, receiving a surprise bill for thousands of dollars triggered immense anxiety. What helped was asking for the itemized statement, checking public fee benchmarks, and writing a polite dispute letter. Don't be afraid to ask for line-by-line itemization.",
                "author_name": "Elena R.",
                "condition_or_topic": "Medical Billing Recovery",
                "contact_email": None,
                "contact_instagram": "@elena_patient_advocate",
                "consent_acknowledged": True,
                "created_at": datetime(2026, 10, 22, 16, 45, tzinfo=timezone.utc),
            },
        ]
        self._in_memory_claims: list[dict[str, Any]] = []
        self._in_memory_verifications: list[dict[str, Any]] = []
        self._in_memory_audit_trails: list[AuditTrail] = []

    async def connect(self) -> None:
        """Initialize connection pool to MongoDB and ensure indexes."""
        if self._client is None:
            # STRICT SECURITY RULE: Never log connection string, username, password, or cluster address
            logger.info(f"Connecting to MongoDB database '{self.settings.MONGODB_DB_NAME}'...")
            self._client = AsyncIOMotorClient(
                self.settings.mongodb_connection_uri,
                serverSelectionTimeoutMS=self.settings.MONGODB_TIMEOUT_MS,
            )
        self._db = self._client[self.settings.MONGODB_DB_NAME]
        self._users_collection = self._db[self.settings.MONGODB_USERS_COLLECTION]
        self._collection = self._db[self.settings.MONGODB_CLAIMS_COLLECTION]
        self._verifications_collection = self._db[self.settings.MONGODB_VERIFICATIONS_COLLECTION]
        self._audit_trails_collection = self._db[self.settings.MONGODB_AUDIT_TRAILS_COLLECTION]
        self._trust_density_collection = self._db[self.settings.MONGODB_TRUST_DENSITY_COLLECTION]
        self._evaluations_collection = self._db[self.settings.MONGODB_EVALUATIONS_COLLECTION]
        self._community_stories_collection = self._db[self.settings.MONGODB_COMMUNITY_STORIES_COLLECTION]

        try:
            # Ping database to verify connection
            await self._client.admin.command("ping")
            logger.info(f"MongoDB connection established to database: {self.settings.MONGODB_DB_NAME}")
            await self._ensure_indexes()
        except Exception as e:
            logger.warning(f"MongoDB ping failed at startup (server may be offline or credentials invalid): {type(e).__name__}. Operating in in-memory fallback mode.")
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = None
            self._db = None
            self._users_collection = None
            self._collection = None
            self._verifications_collection = None
            self._audit_trails_collection = None
            self._trust_density_collection = None
            self._evaluations_collection = None
            self._community_stories_collection = None

    async def close(self) -> None:
        """Close MongoDB connection pool."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._users_collection = None
            self._collection = None
            self._verifications_collection = None
            self._audit_trails_collection = None
            self._trust_density_collection = None
            self._evaluations_collection = None
            self._community_stories_collection = None
            logger.info("MongoDB connection closed")

    async def _ensure_indexes(self) -> None:
        """Create indexes on users, claims, verifications, and audit_trails."""
        if self._users_collection is not None:
            try:
                await self._users_collection.create_index("user_id", unique=True)
                await self._users_collection.create_index("email", unique=True)
                logger.info("MongoDB indexes verified on collection 'users'")
                # Pre-seed demo user in MongoDB if not exists
                existing_demo = await self._users_collection.find_one({"email": DEMO_USER_EMAIL.lower()})
                if not existing_demo:
                    await self._users_collection.insert_one({
                        "user_id": DEMO_USER_ID,
                        "name": DEMO_USER_NAME,
                        "email": DEMO_USER_EMAIL.lower(),
                        "hashed_password": hash_password(DEMO_USER_DEFAULT_PW),
                        "role": DEMO_USER_ROLE,
                        "organization": DEMO_USER_ORG,
                        "created_at": datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
                    })
                    logger.info("Seeded canonical Demo Auditor into MongoDB users collection")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on users: {e}")
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

        if self._evaluations_collection is not None:
            try:
                await self._evaluations_collection.create_index("run_id", unique=True)
                await self._evaluations_collection.create_index("timestamp")
                logger.info("MongoDB indexes verified on collection 'evaluation_runs'")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on evaluation_runs: {e}")

        if self._community_stories_collection is not None:
            try:
                await self._community_stories_collection.create_index("story_id", unique=True)
                await self._community_stories_collection.create_index("created_at")
                logger.info("MongoDB indexes verified on collection 'community_stories'")
            except Exception as e:
                logger.warning(f"Failed to ensure MongoDB indexes on community_stories: {e}")

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
            eval_cnt = await self.count_evaluation_reports()
            return {
                "status": "healthy",
                "database": self.settings.MONGODB_DB_NAME,
                "collection": self.settings.MONGODB_CLAIMS_COLLECTION,
                "claims_count": claims_cnt,
                "verifications_count": verifications_cnt,
                "audit_trails_count": audit_cnt,
                "trust_density_count": trust_cnt,
                "evaluation_runs_count": eval_cnt,
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

    @property
    def evaluations_collection(self) -> AsyncIOMotorCollection:
        """Access the evaluation reports collection."""
        if self._evaluations_collection is None:
            raise StorageError("StorageService is not connected. Call connect() first.")
        return self._evaluations_collection

    @property
    def community_stories_collection(self) -> AsyncIOMotorCollection:
        """Access the community recovery stories collection."""
        if self._community_stories_collection is None:
            if self._db is None:
                raise StorageError("StorageService is not connected. Call connect() first.")
            self._community_stories_collection = self._db[self.settings.MONGODB_COMMUNITY_STORIES_COLLECTION]
        return self._community_stories_collection

    @property
    def users_collection(self) -> AsyncIOMotorCollection:
        """Access the users collection."""
        if self._users_collection is None:
            if self._db is None:
                raise StorageError("StorageService is not connected. Call connect() first.")
            self._users_collection = self._db[self.settings.MONGODB_USERS_COLLECTION]
        return self._users_collection

    async def create_user(self, user_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new user account in MongoDB and in-memory cache.
        Ensures email uniqueness.
        """
        email_key = user_dict["email"].strip().lower()
        if email_key in self._in_memory_users:
            raise DuplicateKeyError(f"User with email '{email_key}' already exists")

        # Save to MongoDB if connected
        try:
            if self._client is not None and self._db is not None:
                doc = dict(user_dict)
                await self.users_collection.insert_one(doc)
                logger.info(f"User {user_dict['user_id']} created in MongoDB")
        except DuplicateKeyError:
            raise DuplicateKeyError(f"User with email '{email_key}' already exists in database")
        except Exception as e:
            logger.warning(f"Could not persist user to MongoDB (in-memory saved): {e}")

        # Update in-memory index
        self._in_memory_users[email_key] = user_dict
        self._in_memory_users[user_dict["user_id"]] = user_dict
        return user_dict

    async def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        """Retrieve user by email from MongoDB or in-memory fallback."""
        clean_email = email.strip().lower()
        try:
            if self._client is not None and self._db is not None:
                doc = await self.users_collection.find_one({"email": clean_email}, {"_id": 0})
                if doc:
                    return doc
        except Exception as e:
            logger.debug(f"Failed to query MongoDB for user email: {e}")

        return self._in_memory_users.get(clean_email)

    async def get_user_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        """Retrieve user by user_id from MongoDB or in-memory fallback."""
        clean_id = user_id.strip()
        try:
            if self._client is not None and self._db is not None:
                doc = await self.users_collection.find_one({"user_id": clean_id}, {"_id": 0})
                if doc:
                    return doc
        except Exception as e:
            logger.debug(f"Failed to query MongoDB for user_id: {e}")

        for u in self._in_memory_users.values():
            if u.get("user_id") == clean_id:
                return u
        return None

    async def insert_claim(self, claim: Claim) -> Claim:
        """
        Persist a claim to MongoDB or in-memory fallback.
        Raises DuplicateKeyError if claim_id already exists.
        """
        doc = claim.model_dump(mode="python")
        if self._client is not None and self._db is not None:
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

        # In-memory fallback
        if any(c.get("claim_id") == claim.claim_id for c in self._in_memory_claims):
            raise StorageError(f"Claim with id '{claim.claim_id}' already exists")
        self._in_memory_claims.insert(0, doc)
        return claim

    async def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Retrieve a single claim by its unique claim_id."""
        if self._client is not None and self._db is not None:
            try:
                doc = await self.collection.find_one({"claim_id": claim_id}, {"_id": 0})
                if not doc:
                    return None
                return Claim.model_validate(doc)
            except Exception as e:
                logger.error(f"Failed to retrieve claim {claim_id}: {e}")
                raise StorageError(f"Database query failed: {e}") from e

        # In-memory fallback
        doc = next((c for c in self._in_memory_claims if c.get("claim_id") == claim_id), None)
        return Claim.model_validate(doc) if doc else None

    def _build_claims_query(
        self,
        location: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Construct MongoDB query dictionary with optional location and user_id isolation."""
        clauses: list[dict[str, Any]] = []

        if location:
            loc_clean = location.strip().lower()
            clauses.append({
                "$or": [
                    {"location.normalized_key": loc_clean},
                    {"location.city": {"$regex": f"^{re.escape(location.strip())}$", "$options": "i"}},
                ]
            })

        if user_id:
            clean_uid = user_id.strip()
            if clean_uid in (DEMO_USER_ID, "demo"):
                # For demo auditor, also include legacy/unassigned claims so prototype demo remains populated
                clauses.append({
                    "$or": [
                        {"user_id": clean_uid},
                        {"user_id": None},
                        {"user_id": {"$exists": False}},
                    ]
                })
            else:
                clauses.append({"user_id": clean_uid})

        if not clauses:
            return {}
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    async def list_claims(
        self,
        limit: int = 50,
        skip: int = 0,
        location: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[Claim]:
        """Retrieve a paginated list of claims sorted newest first, optionally filtered by location and user_id."""
        if self._collection is None or self._db is None:
            return []
        try:
            query = self._build_claims_query(location=location, user_id=user_id)
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

    async def count_claims(
        self,
        location: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> int:
        """Return total number of claims in collection, optionally filtered by location and user_id."""
        if self._collection is None or self._db is None:
            return 0
        try:
            query = self._build_claims_query(location=location, user_id=user_id)
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.warning(f"Failed to count claims: {e}")
            return 0

    async def insert_verification(self, verification: VerificationResult) -> VerificationResult:
        """
        Persist or update a verification result linked to claim_id in MongoDB or in-memory fallback.
        Uses upsert on claim_id so re-verifications cleanly replace old audits.
        """
        doc = verification.model_dump(mode="python")
        if self._client is not None and self._db is not None:
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

        # In-memory fallback
        self._in_memory_verifications = [v for v in self._in_memory_verifications if v.get("claim_id") != verification.claim_id]
        self._in_memory_verifications.append(doc)
        return verification

    async def get_verification(self, claim_id: str) -> Optional[VerificationResult]:
        """Retrieve a verification result by claim_id."""
        if self._client is not None and self._db is not None:
            try:
                doc = await self.verifications_collection.find_one({"claim_id": claim_id}, {"_id": 0})
                if not doc:
                    return None
                return VerificationResult.model_validate(doc)
            except Exception as e:
                logger.error(f"Failed to retrieve verification for claim {claim_id}: {e}")
                raise StorageError(f"Database query failed: {e}") from e

        # In-memory fallback
        doc = next((v for v in self._in_memory_verifications if v.get("claim_id") == claim_id), None)
        return VerificationResult.model_validate(doc) if doc else None

    async def count_verifications(self) -> int:
        """Return total number of verification records in collection."""
        if self._client is not None and self._db is not None:
            try:
                return await self.verifications_collection.count_documents({})
            except Exception as e:
                logger.warning(f"Failed to count verifications: {e}")
                return 0
        return len(self._in_memory_verifications)

    async def insert_audit_trail(self, audit_trail: AuditTrail) -> AuditTrail:
        """
        Persist or update an audit trail linked to claim_id and verification_id in MongoDB.
        Uses upsert on audit_id.
        """
        doc = audit_trail.model_dump(mode="python")
        if self._client is not None and self._db is not None:
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

        # In-memory fallback
        self._in_memory_audit_trails = [a for a in self._in_memory_audit_trails if a.audit_id != audit_trail.audit_id]
        self._in_memory_audit_trails.append(audit_trail)
        return audit_trail

    async def get_audit_trail_by_claim_id(self, claim_id: str) -> Optional[AuditTrail]:
        """Retrieve the most recent audit trail for a claim."""
        if self._client is not None and self._db is not None:
            try:
                cursor = self.audit_trails_collection.find({"claim_id": claim_id}, {"_id": 0}).sort("created_at", -1).limit(1)
                docs = await cursor.to_list(length=1)
                if not docs:
                    return None
                return AuditTrail.model_validate(docs[0])
            except Exception as e:
                logger.error(f"Failed to retrieve audit trail for claim {claim_id}: {e}")
                raise StorageError(f"Database query failed: {e}") from e

        # In-memory fallback
        matching = [a for a in self._in_memory_audit_trails if a.claim_id == claim_id]
        return matching[-1] if matching else None

    async def get_audit_trail_by_verification_id(self, verification_id: str) -> Optional[AuditTrail]:
        """Retrieve audit trail by its verification_id."""
        if self._client is not None and self._db is not None:
            try:
                doc = await self.audit_trails_collection.find_one({"verification_id": verification_id}, {"_id": 0})
                if not doc:
                    return None
                return AuditTrail.model_validate(doc)
            except Exception as e:
                logger.error(f"Failed to retrieve audit trail for verification {verification_id}: {e}")
                raise StorageError(f"Database query failed: {e}") from e

        # In-memory fallback
        return next((a for a in self._in_memory_audit_trails if a.verification_id == verification_id), None)

    async def count_audit_trails(self) -> int:
        """Return total number of audit trail records in collection."""
        if self._client is not None and self._db is not None:
            try:
                return await self.audit_trails_collection.count_documents({})
            except Exception as e:
                logger.warning(f"Failed to count audit trails: {e}")
                return 0
        return len(self._in_memory_audit_trails)

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

    # ==========================================================================
    # Layer 6: Evaluation Harness Storage
    # ==========================================================================

    async def save_evaluation_report(self, report_dict: dict[str, Any]) -> str:
        """
        Persist an EvaluationReport to MongoDB.
        Uses upsert on run_id.
        """
        run_id = report_dict.get("run_id")
        if not run_id:
            raise StorageError("Evaluation report missing run_id")
        try:
            await self.evaluations_collection.update_one(
                {"run_id": run_id},
                {"$set": report_dict},
                upsert=True,
            )
            logger.info(f"Saved evaluation report '{run_id}' with {report_dict.get('total_samples', 0)} samples")
            return run_id
        except Exception as e:
            logger.error(f"Failed to save evaluation report {run_id}: {e}")
            raise StorageError(f"Evaluation report save failed: {e}") from e

    async def get_evaluation_report(self, run_id: str) -> Optional[dict[str, Any]]:
        """Retrieve an evaluation report by run_id."""
        try:
            return await self.evaluations_collection.find_one({"run_id": run_id}, {"_id": 0})
        except Exception as e:
            logger.error(f"Failed to retrieve evaluation report {run_id}: {e}")
            return None

    async def list_evaluation_reports(
        self,
        limit: int = 20,
        skip: int = 0,
        user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve recent evaluation reports sorted by timestamp descending, optionally filtered by user_id."""
        try:
            query: dict[str, Any] = {}
            if user_id:
                clean_uid = user_id.strip()
                if clean_uid in (DEMO_USER_ID, "demo"):
                    query = {"$or": [{"user_id": clean_uid}, {"user_id": None}, {"user_id": {"$exists": False}}]}
                else:
                    query = {"user_id": clean_uid}

            cursor = (
                self.evaluations_collection.find(query, {"_id": 0})
                .sort("timestamp", -1)
                .skip(skip)
                .limit(limit)
            )
            records: list[dict[str, Any]] = []
            async for doc in cursor:
                records.append(doc)
            return records
        except Exception as e:
            logger.error(f"Failed to list evaluation reports: {e}")
            return []

    async def count_evaluation_reports(self, user_id: Optional[str] = None) -> int:
        """Return total number of evaluation runs stored."""
        try:
            query: dict[str, Any] = {}
            if user_id:
                clean_uid = user_id.strip()
                if clean_uid in (DEMO_USER_ID, "demo"):
                    query = {"$or": [{"user_id": clean_uid}, {"user_id": None}, {"user_id": {"$exists": False}}]}
                else:
                    query = {"user_id": clean_uid}
            return await self.evaluations_collection.count_documents(query)
        except Exception as e:
            logger.warning(f"Failed to count evaluation reports: {e}")
            return 0

    # -----------------------------------------------------------------------
    # Community Stories (Recovery Stories) Storage Methods
    # -----------------------------------------------------------------------

    async def save_community_story(self, story_data: dict[str, Any]) -> str:
        """Insert a new voluntary community recovery story."""
        story_doc = dict(story_data)
        story_id = story_doc.get("story_id", "")
        try:
            if self._client is not None and self._db is not None:
                await self.community_stories_collection.insert_one(dict(story_doc))
        except Exception as e:
            logger.warning(f"MongoDB write failed for community story (fallback in-memory): {e}")

        # Always update in-memory list so tests & offline work instantly
        existing_idx = next((i for i, s in enumerate(self._in_memory_stories) if s.get("story_id") == story_id), None)
        if existing_idx is not None:
            self._in_memory_stories[existing_idx] = story_doc
        else:
            self._in_memory_stories.insert(0, story_doc)
        return story_id

    async def list_community_stories(
        self,
        limit: int = 50,
        skip: int = 0,
        user_id: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List community recovery stories, sorted newest first, optionally filtered by user_id."""
        try:
            if self._client is not None and self._db is not None:
                query: dict[str, Any] = {}
                if user_id:
                    clean_uid = user_id.strip()
                    if clean_uid in (DEMO_USER_ID, "demo"):
                        query = {"$or": [{"user_id": clean_uid}, {"user_id": None}, {"user_id": {"$exists": False}}]}
                    else:
                        query = {"user_id": clean_uid}

                total = await self.community_stories_collection.count_documents(query)
                cursor = (
                    self.community_stories_collection.find(query, {"_id": 0})
                    .sort("created_at", -1)
                    .skip(skip)
                    .limit(limit)
                )
                stories: list[dict[str, Any]] = []
                async for doc in cursor:
                    stories.append(doc)
                if total > 0 or stories:
                    return stories, total
        except Exception as e:
            logger.warning(f"Failed to query MongoDB community stories (fallback in-memory): {e}")

        mem_stories = self._in_memory_stories
        if user_id:
            clean_uid = user_id.strip()
            if clean_uid in (DEMO_USER_ID, "demo"):
                mem_stories = [s for s in mem_stories if s.get("user_id") in (clean_uid, None) or "user_id" not in s]
            else:
                mem_stories = [s for s in mem_stories if s.get("user_id") == clean_uid]

        total = len(mem_stories)
        sliced = mem_stories[skip : skip + limit]
        return sliced, total

    async def get_community_story(self, story_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a specific community story by story_id."""
        try:
            if self._client is not None and self._db is not None:
                doc = await self.community_stories_collection.find_one({"story_id": story_id}, {"_id": 0})
                if doc:
                    return doc
        except Exception as e:
            logger.warning(f"MongoDB lookup failed for story {story_id}: {e}")

        return next((s for s in self._in_memory_stories if s.get("story_id") == story_id), None)

    async def count_community_stories(self, user_id: Optional[str] = None) -> int:
        """Return total count of community stories."""
        try:
            if self._client is not None and self._db is not None:
                query: dict[str, Any] = {}
                if user_id:
                    clean_uid = user_id.strip()
                    if clean_uid in (DEMO_USER_ID, "demo"):
                        query = {"$or": [{"user_id": clean_uid}, {"user_id": None}, {"user_id": {"$exists": False}}]}
                    else:
                        query = {"user_id": clean_uid}
                return await self.community_stories_collection.count_documents(query)
        except Exception as e:
            logger.warning(f"Failed to count community stories: {e}")

        if user_id:
            return len([s for s in self._in_memory_stories if s.get("user_id") == user_id.strip()])
        return len(self._in_memory_stories)

    async def get_insights_summary(self, user_id: Optional[str] = None) -> InsightsSummaryResponse:
        """
        Compute aggregated metrics across claims and verifications for visual charts and statistics dashboard.
        When user_id is provided, filters data specifically to that user's personal memory.
        """
        claims_docs: list[dict[str, Any]] = []
        verifs_docs: list[dict[str, Any]] = []

        try:
            if self._client is not None and self._db is not None:
                c_query = self._build_claims_query(user_id=user_id) if user_id else {}
                cursor = self.collection.find(c_query, {"_id": 0})
                async for doc in cursor:
                    claims_docs.append(doc)

                # Get matching verification records
                if user_id and claims_docs:
                    user_claim_ids = [c.get("claim_id") for c in claims_docs if c.get("claim_id")]
                    v_cursor = self.verifications_collection.find(
                        {"claim_id": {"$in": user_claim_ids}}, {"_id": 0}
                    )
                else:
                    v_cursor = self.verifications_collection.find({}, {"_id": 0})

                async for v_doc in v_cursor:
                    verifs_docs.append(v_doc)
        except Exception as e:
            logger.warning(f"Failed to query collections for insights: {e}")

        # If user is a newly registered individual and has no claims yet, return a clean empty personal profile
        if user_id and user_id not in (DEMO_USER_ID, "demo"):
            if not claims_docs:
                return InsightsSummaryResponse(
                    total_claims=0,
                    total_verified=0,
                    decision_overview=DecisionOverview(),
                    price_alerts_overview=PriceAlertsOverview(),
                    guideline_support_overview=GuidelineSupportOverview(),
                    gaps_and_risks=GapsAndRisks(),
                    top_procedures=[],
                    top_locations=[],
                    recent_risk_claims=[],
                    is_baseline_fallback=False,
                )

        # If database is empty or demo user without custom claims, return baseline benchmarks from controlled evaluation cases
        if not claims_docs and not verifs_docs:
            return self._generate_baseline_insights()

        return self._aggregate_insights(claims_docs, verifs_docs, is_baseline=False)

    def _aggregate_insights(
        self,
        claims_docs: list[dict[str, Any]],
        verifs_docs: list[dict[str, Any]],
        is_baseline: bool = False,
    ) -> InsightsSummaryResponse:
        """Calculate statistical summaries across claims and verification documents."""
        claims_by_id = {c.get("claim_id"): c for c in claims_docs if c.get("claim_id")}

        # 1. Decision Overview
        approved = sum(1 for v in verifs_docs if str(v.get("action", "")).lower() == "accept")
        flagged = sum(1 for v in verifs_docs if str(v.get("action", "")).lower() == "flag")
        held = sum(1 for v in verifs_docs if str(v.get("action", "")).lower() == "abstain")
        total_verified = len(verifs_docs)

        decision_overview = DecisionOverview(
            approved=approved,
            flagged=flagged,
            held=held,
            total=total_verified,
        )

        # 2. Price Alerts Overview
        price_alerts = sum(1 for v in verifs_docs if v.get("cost_anomaly_flag") is True)
        normal_charges = total_verified - price_alerts

        moderate = 0
        severe = 0
        extreme = 0

        for v in verifs_docs:
            anomaly = v.get("anomaly_details") or {}
            severity = str(anomaly.get("severity", "")).lower()
            mult = float(anomaly.get("multiplier", 0.0) or 0.0)

            if severity == "extreme" or mult >= 10.0:
                extreme += 1
            elif severity == "severe" or (5.0 <= mult < 10.0):
                severe += 1
            elif severity == "moderate" or (3.0 <= mult < 5.0):
                moderate += 1

        price_alerts_overview = PriceAlertsOverview(
            normal_charges=max(0, normal_charges),
            price_alerts=price_alerts,
            moderate=moderate,
            severe=severe,
            extreme=extreme,
            total=total_verified,
        )

        # 3. Guideline Support Overview
        supported = sum(1 for v in verifs_docs if str(v.get("verdict", "")).lower() == "supported")
        partially = sum(1 for v in verifs_docs if str(v.get("verdict", "")).lower() == "partially_supported")
        contradicted = sum(1 for v in verifs_docs if str(v.get("verdict", "")).lower() == "contradicted")
        insufficient = sum(1 for v in verifs_docs if str(v.get("verdict", "")).lower() == "insufficient_evidence")

        guideline_overview = GuidelineSupportOverview(
            supported=supported,
            partially_supported=partially,
            contradicted=contradicted,
            insufficient_evidence=insufficient,
            total=total_verified,
        )

        # 4. Gaps and Risks
        unbenchmarked = sum(
            1 for v in verifs_docs
            if "unbenchmarked" in str(v.get("abstain_reason", "")).lower()
            or (v.get("anomaly_details") or {}).get("benchmark_matched") is False
        )

        gaps_and_risks = GapsAndRisks(
            insufficient_evidence_claims=insufficient,
            extreme_price_markups=extreme,
            held_by_safety_rules=held,
            unbenchmarked_high_cost=unbenchmarked,
        )

        # 5. Top Procedures
        procedure_counts: dict[str, int] = {}
        for c in claims_docs:
            fields = c.get("extracted_fields") or {}
            ent = fields.get("entity")
            if ent and ent.strip():
                clean_ent = ent.strip()
                procedure_counts[clean_ent] = procedure_counts.get(clean_ent, 0) + 1

        if not procedure_counts:
            for v in verifs_docs:
                cid = v.get("claim_id", "Unknown Claim")
                procedure_counts[cid] = procedure_counts.get(cid, 0) + 1

        top_procedures = [
            ProcedureFrequency(procedure_name=k, count=v)
            for k, v in sorted(procedure_counts.items(), key=lambda item: item[1], reverse=True)[:6]
        ]

        # 6. Top Locations
        location_counts: dict[str, dict[str, int]] = {}
        for c in claims_docs:
            loc = c.get("location") or {}
            city = loc.get("city") or "Unspecified Metro"
            if city not in location_counts:
                location_counts[city] = {"claims": 0, "anomalies": 0}
            location_counts[city]["claims"] += 1
            cid = c.get("claim_id")
            if cid:
                v = next((x for x in verifs_docs if x.get("claim_id") == cid), None)
                if v and v.get("cost_anomaly_flag"):
                    location_counts[city]["anomalies"] += 1

        top_locations = [
            LocationFrequency(
                location_name=k,
                claims_count=val["claims"],
                anomalies_count=val["anomalies"],
            )
            for k, val in sorted(location_counts.items(), key=lambda item: item[1]["claims"], reverse=True)[:6]
        ]

        # 7. Recent Risk Claims
        recent_risks: list[ClaimHighlight] = []
        for v in verifs_docs:
            act = str(v.get("action", "")).lower()
            is_anomaly = bool(v.get("cost_anomaly_flag", False))
            if act in ["flag", "abstain"] or is_anomaly:
                cid = v.get("claim_id", "")
                c = claims_by_id.get(cid, {})
                fields = c.get("extracted_fields") or {}
                recent_risks.append(
                    ClaimHighlight(
                        claim_id=cid,
                        entity=fields.get("entity") or "Medical Procedure",
                        action=v.get("action", "flag"),
                        verdict=v.get("verdict"),
                        cost_range=fields.get("cost_range"),
                        reason=v.get("abstain_reason") or (v.get("anomaly_details") or {}).get("explanation") or v.get("reasoning"),
                        timestamp=c.get("timestamp") or v.get("timestamp"),
                    )
                )

        return InsightsSummaryResponse(
            total_claims=len(claims_docs) or len(verifs_docs),
            total_verified=total_verified,
            decision_overview=decision_overview,
            price_alerts_overview=price_alerts_overview,
            guideline_support_overview=guideline_overview,
            gaps_and_risks=gaps_and_risks,
            top_procedures=top_procedures,
            top_locations=top_locations,
            recent_risk_claims=recent_risks[:6],
            is_baseline_fallback=is_baseline,
        )

    def _generate_baseline_insights(self) -> InsightsSummaryResponse:
        """Provide realistic baseline statistics derived from gold-standard controlled clinical cases."""
        return InsightsSummaryResponse(
            total_claims=8,
            total_verified=8,
            decision_overview=DecisionOverview(
                approved=3,
                flagged=3,
                held=2,
                total=8,
            ),
            price_alerts_overview=PriceAlertsOverview(
                normal_charges=6,
                price_alerts=2,
                moderate=0,
                severe=1,
                extreme=1,
                total=8,
            ),
            guideline_support_overview=GuidelineSupportOverview(
                supported=5,
                partially_supported=0,
                contradicted=1,
                insufficient_evidence=2,
                total=8,
            ),
            gaps_and_risks=GapsAndRisks(
                insufficient_evidence_claims=2,
                extreme_price_markups=1,
                held_by_safety_rules=2,
                unbenchmarked_high_cost=1,
            ),
            top_procedures=[
                ProcedureFrequency(procedure_name="0.9% Sodium Chloride (Normal Saline) 1,000 mL", count=2),
                ProcedureFrequency(procedure_name="CPT 70551 MRI Brain without contrast", count=1),
                ProcedureFrequency(procedure_name="Metformin hydrochloride 1,000 mg", count=1),
                ProcedureFrequency(procedure_name="CPT 36415 Routine Venipuncture", count=1),
                ProcedureFrequency(procedure_name="Azithromycin 250 mg (Z-Pak)", count=1),
                ProcedureFrequency(procedure_name="Lisinopril 20 mg", count=1),
            ],
            top_locations=[
                LocationFrequency(location_name="Cleveland, OH", claims_count=2, anomalies_count=1),
                LocationFrequency(location_name="Houston, TX", claims_count=2, anomalies_count=0),
                LocationFrequency(location_name="Chicago, IL", claims_count=2, anomalies_count=0),
                LocationFrequency(location_name="Atlanta, GA", claims_count=1, anomalies_count=0),
                LocationFrequency(location_name="San Francisco, CA", claims_count=1, anomalies_count=1),
            ],
            recent_risk_claims=[
                ClaimHighlight(
                    claim_id="ctrl_04_saline_overcharge",
                    entity="0.9% Sodium Chloride Normal Saline 1,000 mL",
                    action="flag",
                    verdict="supported",
                    cost_range="$720.00",
                    reason="Cost anomaly: 16.0x hospital markup over expected $45.00 maximum.",
                ),
                ClaimHighlight(
                    claim_id="ctrl_03_bronchitis_antibiotic",
                    entity="Azithromycin 250 mg (Z-Pak)",
                    action="flag",
                    verdict="contradicted",
                    cost_range="$24.00",
                    reason="Contradicted by CDC & GOLD guidelines for uncomplicated viral bronchitis.",
                ),
                ClaimHighlight(
                    claim_id="ctrl_05_venipuncture_markup",
                    entity="CPT 36415 Routine Venipuncture",
                    action="flag",
                    verdict="supported",
                    cost_range="$125.00",
                    reason="Cost anomaly: 5.0x markup over regional median ($25.00).",
                ),
                ClaimHighlight(
                    claim_id="ctrl_07_unbenchmarked_therapy",
                    entity="Robotic Spine Laser Ablation",
                    action="abstain",
                    verdict="insufficient_evidence",
                    cost_range="$12,500.00",
                    reason="Safety rule UNBENCHMARKED_HIGH_COST triggered (charge > $100 without public benchmark).",
                ),
                ClaimHighlight(
                    claim_id="ctrl_06_unsupported_herb",
                    entity="Intravenous Ozone Infusion",
                    action="abstain",
                    verdict="insufficient_evidence",
                    cost_range=None,
                    reason="Safety rule NO_RELEVANT_EVIDENCE triggered (no authoritative guidelines found).",
                ),
            ],
            is_baseline_fallback=True,
        )


# Global singleton instance for application lifecycle
storage_service = StorageService()
