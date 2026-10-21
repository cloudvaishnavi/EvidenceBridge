"""
Claim Verification & Support Scoring Service for EvidenceBridge.
Retrieves relevant clinical guidelines and evidence passages from the local knowledge base,
prompts the local Ollama LLM to judge support vs contradiction,
and combines clinical evidence with cost anomaly detection to produce an audit verdict.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Optional
import httpx

from app.config import get_settings
from app.models.schemas import (
    Claim,
    CostAnomalyDetails,
    EvidenceSnippet,
    VerificationAction,
    VerificationResult,
    VerificationVerdict,
)
from app.services.cost_anomaly import cost_anomaly_service
from app.services.extraction import ExtractionError, OllamaConnectionError
from app.services.vector_store import vector_store_service
from app.utils.logger import logger


VERIFICATION_SYSTEM_PROMPT = """You are an expert clinical auditor evaluating the veracity of a healthcare claim against authoritative medical guidelines.

Your task is to determine whether the provided authoritative evidence passages SUPPORT, PARTIALLY SUPPORT, CONTRADICT, or provide INSUFFICIENT EVIDENCE for the medical claim.

VERDICT DEFINITIONS:
1. "supported" (support_score: 0.70 to 1.00):
   The guideline explicitly validates the drug, procedure, indication, or reported outcome/adverse effect as clinically sound.
2. "partially_supported" (support_score: 0.40 to 0.69):
   The guideline confirms the entity exists and has relevant medical use, but reported outcomes or specific details are only partially corroborated or partially atypical.
3. "contradicted" (support_score: 0.00 to 0.39):
   The guideline explicitly discourages, refutes, or contradicts the claim (e.g. antibiotic prescribed for viral bronchitis, contraindicated therapy, or clinically false outcome claims).
4. "insufficient_evidence" (support_score: 0.00 to 0.30):
   The passages do not provide enough medical facts to judge the claim.

OUTPUT STRICTLY A VALID JSON OBJECT WITH THIS FORMAT:
{
  "verdict": "supported" | "partially_supported" | "contradicted" | "insufficient_evidence",
  "support_score": float between 0.0 and 1.0,
  "reasoning": "Clear 1-3 sentence factual explanation directly referencing the evidence passages"
}

STRICT RULE: Do not output markdown or text outside the JSON object.
"""


class VerificationService:
    """Service to verify claims against local evidence guidelines using local Ollama model."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.settings = get_settings()
        self.base_url = (base_url or self.settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or self.settings.OLLAMA_MODEL
        self.timeout = self.settings.OLLAMA_TIMEOUT_SECONDS
        self.guidelines_file = self._resolve_guidelines_path()
        self.guidelines: list[dict[str, Any]] = []
        self._guidelines_indexed = False
        self.load_guidelines()

    def _resolve_guidelines_path(self) -> Path:
        """Locate clinical_guidelines_samples.json across known paths."""
        candidates = [
            Path(self.settings.KNOWLEDGE_BASE_DIR) / "clinical_guidelines_samples.json",
            Path(__file__).parent.parent.parent.parent / "data" / "knowledge" / "clinical_guidelines_samples.json",
            Path("./data/knowledge/clinical_guidelines_samples.json"),
            Path("../data/knowledge/clinical_guidelines_samples.json"),
        ]
        for path in candidates:
            if path.exists():
                return path.resolve()
        return Path("./data/knowledge/clinical_guidelines_samples.json")

    def load_guidelines(self) -> None:
        """Load guideline documents from disk."""
        if not self.guidelines_file.exists():
            logger.warning(f"Guidelines file not found at: {self.guidelines_file}")
            return

        try:
            with open(self.guidelines_file, "r", encoding="utf-8") as f:
                self.guidelines = json.load(f)
            logger.info(f"Loaded {len(self.guidelines)} clinical guidelines from {self.guidelines_file.name}")
        except Exception as e:
            logger.error(f"Failed to load clinical guidelines: {e}")

    def index_guidelines_in_vector_store(self) -> None:
        """Index guideline passages into ChromaDB for semantic retrieval."""
        if self._guidelines_indexed or not self.guidelines:
            return

        try:
            if not vector_store_service._client:
                vector_store_service.initialize()

            if vector_store_service._client:
                collection = vector_store_service._client.get_or_create_collection(
                    name=self.settings.CHROMA_GUIDELINES_COLLECTION
                )
                ids = [g["guideline_id"] for g in self.guidelines]
                docs = [f"Title: {g['title']}\nSource: {g['source']}\nText: {g['text']}" for g in self.guidelines]
                metas = [
                    {
                        "guideline_id": g["guideline_id"],
                        "title": g["title"],
                        "source": g["source"],
                        "topics": " ".join(g.get("topics", []))
                    }
                    for g in self.guidelines
                ]
                collection.upsert(ids=ids, documents=docs, metadatas=metas)
                logger.info(f"Indexed {len(ids)} clinical guidelines into ChromaDB collection '{self.settings.CHROMA_GUIDELINES_COLLECTION}'")
                self._guidelines_indexed = True
        except Exception as e:
            logger.warning(f"Could not index guidelines into ChromaDB (will use keyword search fallback): {e}")

    def retrieve_evidence_passages(self, entity: str, claim_text: str, k: int = 3) -> list[EvidenceSnippet]:
        """
        Retrieve top-k relevant clinical guidelines using hybrid search:
        ChromaDB semantic retrieval with keyword corroboration.
        """
        query_text = f"{entity} {claim_text}".strip()
        snippets: list[EvidenceSnippet] = []
        entity_tokens = set(re.findall(r"\w+", entity.lower())) - {
            "mg", "ml", "oral", "tablet", "solution", "daily", "the", "and", "for", "with", "cpt", "dose", "unit"
        }

        # 1. Try vector store retrieval
        try:
            if not self._guidelines_indexed:
                self.index_guidelines_in_vector_store()

            if vector_store_service._client:
                collection = vector_store_service._client.get_collection(
                    name=self.settings.CHROMA_GUIDELINES_COLLECTION
                )
                results = collection.query(
                    query_texts=[query_text],
                    n_results=min(k, len(self.guidelines))
                )
                if results and results.get("ids") and results["ids"][0]:
                    ids = results["ids"][0]
                    docs = results.get("documents", [[]])[0]
                    metas = results.get("metadatas", [[]])[0]
                    dists = results.get("distances", [[]])[0] if results.get("distances") else [0.5] * len(ids)

                    for gid, doc, meta, dist in zip(ids, docs, metas, dists):
                        matched_g = next((g for g in self.guidelines if g["guideline_id"] == gid), None)
                        topics = [t.lower() for t in (matched_g.get("topics", []) if matched_g else [])]
                        title = (meta.get("title", "") or "").lower()

                        # Check if any significant entity token appears in guideline topics or title
                        has_entity_anchor = any(t in topics or t in title for t in entity_tokens if len(t) >= 4)

                        # Distance threshold check: if distance is high or entity has zero overlap, filter out
                        if dist is not None and dist > 0.95 and not has_entity_anchor:
                            continue

                        # Convert distance to relevance score
                        rel_score = max(0.0, min(1.0, 1.0 - (dist if dist is not None else 0.5)))
                        if has_entity_anchor:
                            rel_score = min(1.0, rel_score + 0.25)

                        text_val = matched_g["text"] if matched_g else doc
                        snippets.append(EvidenceSnippet(
                            guideline_id=gid,
                            title=meta.get("title", ""),
                            source=meta.get("source", ""),
                            text=text_val,
                            relevance_score=round(rel_score, 3)
                        ))
        except Exception as e:
            logger.debug(f"ChromaDB retrieval fallback to keyword matching: {e}")

        # 2. If vector retrieval returned empty or failed, use keyword/lexical retrieval
        if not snippets:
            snippets = self._lexical_retrieval(entity, claim_text, k=k)

        # Sort snippets by relevance score descending
        snippets.sort(key=lambda s: s.relevance_score or 0.0, reverse=True)
        return snippets[:k]

    def _lexical_retrieval(self, entity: str, claim_text: str, k: int = 3) -> list[EvidenceSnippet]:
        """Lexical matching over guidelines with strong entity anchoring."""
        entity_tokens = set(re.findall(r"\w+", entity.lower())) - {
            "mg", "ml", "oral", "tablet", "solution", "daily", "the", "and", "for", "with", "cpt", "dose", "unit"
        }
        claim_tokens = set(re.findall(r"\w+", claim_text.lower()))
        scored: list[tuple[float, dict[str, Any]]] = []

        for g in self.guidelines:
            score = 0.0
            topics = [t.lower() for t in g.get("topics", [])]
            title = g.get("title", "").lower()
            text = g.get("text", "").lower()

            # Require at least some entity token overlap for meaningful clinical match
            entity_matches = sum(1 for t in entity_tokens if len(t) >= 4 and (t in topics or t in title or t in text))
            if not entity_matches and entity_tokens:
                continue

            score += entity_matches * 5.0

            for token in claim_tokens:
                if len(token) <= 3:
                    continue
                if token in topics:
                    score += 2.0
                if token in title:
                    score += 1.5

            if score >= 3.0:
                scored.append((score, g))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:k]

        snippets = []
        max_score = top[0][0] if top else 1.0
        for s, g in top:
            norm_score = round(min(1.0, s / max(max_score, 10.0)), 3)
            snippets.append(EvidenceSnippet(
                guideline_id=g["guideline_id"],
                title=g["title"],
                source=g["source"],
                text=g["text"],
                relevance_score=norm_score
            ))
        return snippets

    async def verify_claim(self, claim: Claim) -> VerificationResult:
        """
        Verify an extracted Claim against local guidelines and price benchmarks.
        Returns a VerificationResult including support score, verdict, and action.
        """
        entity = claim.extracted_fields.entity
        outcome = claim.extracted_fields.effect_or_outcome or "None reported"

        # 1. Retrieve evidence snippets from local knowledge base
        snippets = self.retrieve_evidence_passages(entity, claim.original_text, k=3)

        # 2. Evaluate cost anomaly
        anomaly_details = cost_anomaly_service.evaluate_claim_cost(claim)
        has_cost_anomaly = anomaly_details.is_anomaly

        # 3. Check for lack of evidence -> ABSTAIN path
        max_relevance = max((s.relevance_score or 0.0) for s in snippets) if snippets else 0.0
        if not snippets or max_relevance < 0.40:
            logger.info(f"Claim {claim.claim_id}: Insufficient evidence in local knowledge base (max_rel={max_relevance:.2f}). Abstaining.")
            return VerificationResult(
                claim_id=claim.claim_id,
                support_score=0.0,
                verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                action=VerificationAction.ABSTAIN,
                reasoning=(
                    f"No authoritative clinical guidelines or documented evidence found in the local knowledge base "
                    f"matching medical entity '{entity}'. Verification judgment is abstained to prevent hallucinations."
                ),
                evidence_snippets=snippets,
                cost_anomaly_flag=has_cost_anomaly,
                anomaly_details=anomaly_details,
                abstain_reason=f"Zero matching clinical evidence in local knowledge base for entity '{entity}'.",
                verified_at=datetime.now(timezone.utc)
            )

        # 4. Formulate prompt for local Ollama LLM
        passages_text = "\n\n".join(
            f"[{idx}] Guideline: {s.title} ({s.source})\nText: {s.text}"
            for idx, s in enumerate(snippets, start=1)
        )

        user_prompt = (
            f"{VERIFICATION_SYSTEM_PROMPT}\n\n"
            f"CLAIM TO EVALUATE:\n"
            f"- Entity: {entity}\n"
            f"- Reported Outcome: {outcome}\n"
            f"- Source Type: {claim.source_type}\n"
            f"- Verbatim Text: \"\"\"{claim.original_text.strip()}\"\"\"\n\n"
            f"AUTHORITATIVE EVIDENCE PASSAGES:\n{passages_text}\n\n"
            f"AUDIT JSON OUTPUT:"
        )

        payload = {
            "model": self.model,
            "prompt": user_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,  # Deterministic verification
                "top_p": 0.9,
            }
        }

        # 5. Call Ollama for verification judgment
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code != 200:
                    raise ExtractionError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
                data = resp.json()
                raw_response = data.get("response", "")
        except httpx.ConnectError as e:
            logger.error(f"Cannot reach Ollama for verification: {e}")
            raise OllamaConnectionError(f"Ollama LLM unreachable at {self.base_url}: {e}")
        except Exception as e:
            logger.error(f"Verification request failed: {e}")
            raise ExtractionError(f"Verification service error: {e}")

        # 6. Parse model response
        verdict, support_score, reasoning = self._parse_verification_output(raw_response)

        # 7. Determine final action (accept, flag, abstain)
        action, abstain_reason = self._determine_action(verdict, support_score, has_cost_anomaly)

        return VerificationResult(
            claim_id=claim.claim_id,
            support_score=support_score,
            verdict=verdict,
            action=action,
            reasoning=reasoning,
            evidence_snippets=snippets,
            cost_anomaly_flag=has_cost_anomaly,
            anomaly_details=anomaly_details,
            abstain_reason=abstain_reason,
            verified_at=datetime.now(timezone.utc)
        )

    def _parse_verification_output(self, raw_text: str) -> tuple[VerificationVerdict, float, str]:
        """Parse structured verdict, support score, and reasoning from model JSON output."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        parsed: Optional[dict[str, Any]] = None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

        if not parsed or not isinstance(parsed, dict):
            logger.warning(f"Failed to parse JSON from verification output: {raw_text[:200]}")
            return (
                VerificationVerdict.PARTIALLY_SUPPORTED,
                0.50,
                "Verification output was non-standard; assigned default partially supported verdict."
            )

        # Sanitize verdict
        verdict_str = str(parsed.get("verdict") or "partially_supported").lower().strip()
        if verdict_str in [v.value for v in VerificationVerdict]:
            verdict = VerificationVerdict(verdict_str)
        else:
            verdict = VerificationVerdict.PARTIALLY_SUPPORTED

        # Sanitize score
        score_val = parsed.get("support_score")
        try:
            score = float(score_val)
            score = max(0.0, min(1.0, round(score, 3)))
        except (TypeError, ValueError):
            # Map default score based on verdict
            defaults = {
                VerificationVerdict.SUPPORTED: 0.85,
                VerificationVerdict.PARTIALLY_SUPPORTED: 0.55,
                VerificationVerdict.CONTRADICTED: 0.15,
                VerificationVerdict.INSUFFICIENT_EVIDENCE: 0.10,
            }
            score = defaults.get(verdict, 0.50)

        reasoning = str(parsed.get("reasoning") or "Evidence evaluated against clinical guidelines.").strip()

        return verdict, score, reasoning

    def _determine_action(
        self,
        verdict: VerificationVerdict,
        support_score: float,
        has_cost_anomaly: bool
    ) -> tuple[VerificationAction, Optional[str]]:
        """
        Synthesize verdict, support score, and cost anomaly flag into actionable decision.
        """
        # 1. Contradiction is a decisive finding -> FLAG
        if verdict == VerificationVerdict.CONTRADICTED:
            return (
                VerificationAction.FLAG,
                None
            )

        # 2. If evidence is insufficient or support is below floor -> Abstain
        if verdict == VerificationVerdict.INSUFFICIENT_EVIDENCE or support_score < 0.25:
            return (
                VerificationAction.ABSTAIN,
                "Support score or guideline relevance is below required threshold to formulate a decisive judgment."
            )

        # 3. Cost Anomaly -> Flag for human review
        if has_cost_anomaly:
            return (
                VerificationAction.FLAG,
                None
            )

        # 4. Partially supported -> Flag
        if verdict == VerificationVerdict.PARTIALLY_SUPPORTED:
            return (
                VerificationAction.FLAG,
                None
            )

        # 5. Cleanly supported with fair pricing -> Accept
        if verdict == VerificationVerdict.SUPPORTED and support_score >= 0.70 and not has_cost_anomaly:
            return (
                VerificationAction.ACCEPT,
                None
            )

        # Fallback
        return (
            VerificationAction.FLAG,
            None
        )


verification_service = VerificationService()
