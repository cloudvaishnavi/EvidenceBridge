"""
Claim Verification, Support Scoring & Hybrid Retrieval Service for EvidenceBridge.
Combines ChromaDB vector search + BM25 term weighting for evidence ranking,
enforces strict deterministic abstention safety gates, and records complete decision audit trails.
"""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any, Optional
import uuid
import httpx

from app.config import get_settings
from app.models.schemas import (
    AuditTrail,
    Claim,
    CostAnomalyDetails,
    EvidencePassage,
    EvidenceSnippet,
    VerificationAction,
    VerificationResult,
    VerificationVerdict,
)
from app.services.abstention import abstention_service
from app.services.audit import audit_service
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
  "reasoning": "Clear 1-3 sentence factual explanation directly referencing the evidence passages",
  "conflict_assessment": {
    "has_conflict": boolean,
    "supporting_passage_ids": ["passage ID", ...],
    "opposing_passage_ids": ["passage ID", ...],
    "explanation": "Brief explanation of the opposing positions"
  }
}

Set has_conflict to true only when usable passages explicitly support opposing positions
on the claim. Cite the exact passage IDs shown with each passage. Do not treat insufficient
evidence, uncertainty, or wording alone as a conflict. If conflict is not established,
set has_conflict to false and use empty passage ID lists. A contradicted verdict must
remain contradicted; do not use conflict wording alone to change it.
STRICT RULE: Do not output markdown or text outside the JSON object.
"""

ANATOMICAL_REGIONS: dict[str, set[str]] = {
    "brain": {"brain", "head", "cranial", "cerebral", "neuro", "neuroimaging", "intracranial", "encephalopathy"},
    "knee": {"knee", "patella", "meniscus", "meniscal"},
    "chest": {"chest", "thorax", "thoracic", "lung", "pulmonary"},
    "abdomen": {"abdomen", "abdominal", "pelvis", "pelvic"},
    "spine": {"spine", "spinal", "lumbar", "cervical", "vertebra"},
}



class VerificationService:
    """Service to verify claims against local evidence guidelines using local Ollama model."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.settings = get_settings()
        self.base_url = (base_url or self.settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or self.settings.OLLAMA_MODEL
        self.timeout = self.settings.OLLAMA_TIMEOUT_SECONDS
        self.relevance_threshold = self.settings.RETRIEVAL_RELEVANCE_THRESHOLD
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

    def _compute_bm25_scores(self, query_tokens: list[str], entity_tokens: set[str]) -> dict[str, float]:
        """
        Compute BM25-style scores for all guidelines based on query and entity tokens.
        Includes TF saturation (k1=1.5), length normalization (b=0.75), IDF term weighting,
        and anchor boosts for exact CPT codes and clinical entity matches.
        """
        scores: dict[str, float] = {}
        if not self.guidelines or not query_tokens:
            return scores

        N = len(self.guidelines)
        k1 = 1.5
        b = 0.75

        # Check for 5-digit CPT codes in query and entity tokens
        cpt_pattern = re.compile(r"\b\d{5}\b")
        query_cpts = set(cpt_pattern.findall(" ".join(query_tokens))) | set(cpt_pattern.findall(" ".join(entity_tokens)))

        # Document lengths (in tokens)
        doc_lens = {
            g["guideline_id"]: len(re.findall(r"\w+", f"{g['title']} {' '.join(g.get('topics', []))} {g['text']}".lower()))
            for g in self.guidelines
        }
        avg_len = sum(doc_lens.values()) / max(N, 1)

        # Document frequency (DF) per token
        df: dict[str, int] = {}
        for token in query_tokens:
            df[token] = sum(
                1 for g in self.guidelines
                if token in g["title"].lower() or token in g["text"].lower() or any(token in t.lower() for t in g.get("topics", []))
            )

        for g in self.guidelines:
            gid = g["guideline_id"]
            d_len = doc_lens.get(gid, avg_len)
            title_text = g["title"].lower()
            body_text = g["text"].lower()
            topics_text = " ".join(g.get("topics", [])).lower()
            combined_text = f"{title_text} {topics_text} {body_text}"

            score = 0.0
            for token in query_tokens:
                # Term frequency with extra weight for titles and topics
                tf = (
                    combined_text.count(token)
                    + title_text.count(token) * 2.0
                    + topics_text.count(token) * 3.0
                )
                if tf == 0:
                    continue

                # IDF
                token_df = df.get(token, 0)
                idf = math.log((N - token_df + 0.5) / (token_df + 0.5) + 1.0)

                # TF saturation with length normalization
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (d_len / avg_len)))
                score += idf * tf_norm

            # Significant entity anchor boost (including 3-letter clinical acronyms like MRI, CMP, CBC)
            entity_matches = sum(1 for t in entity_tokens if len(t) >= 3 and (t in topics_text or t in title_text or t in body_text))
            title_topic_matches = sum(1 for t in entity_tokens if len(t) >= 3 and (t in topics_text or t in title_text))
            score += entity_matches * 3.0 + title_topic_matches * 4.0

            # Exact CPT code anchor boost
            if query_cpts:
                guide_cpts = set(cpt_pattern.findall(combined_text))
                if query_cpts & guide_cpts:
                    score += 15.0

            scores[gid] = score

        # Normalize BM25 scores with minimum ceiling to prevent noise inflation
        max_score = max(scores.values(), default=1.0)
        normalizer = max(max_score, 8.0)
        return {gid: round(min(1.0, s / normalizer), 4) for gid, s in scores.items()}

    def retrieve_hybrid_passages(self, entity: str, claim_text: str, k: int = 5) -> list[EvidencePassage]:
        """
        Ranked hybrid retrieval combining BM25 keyword matching and ChromaDB vector search.
        Evaluates relevance threshold, anatomical region compatibility, and procedure codes,
        marking passages used_in_decision vs discarded.
        """
        query_text = f"{entity} {claim_text}".strip()
        stop_words = {
            "mg", "ml", "oral", "tablet", "solution", "daily", "the", "and", "for",
            "with", "cpt", "dose", "unit", "iv", "intravenous", "infusion", "injection",
            "capsule", "vial", "per"
        }
        all_tokens = [t.lower() for t in re.findall(r"\w+", query_text) if len(t) >= 3 and t.lower() not in stop_words]
        entity_tokens = set(re.findall(r"\w+", entity.lower())) - stop_words

        # Check for 5-digit CPT codes and anatomical regions in query
        cpt_pattern = re.compile(r"\b\d{5}\b")
        query_cpts = set(cpt_pattern.findall(query_text))

        query_combined = f"{entity} {claim_text}".lower()
        query_regions = {
            region for region, keywords in ANATOMICAL_REGIONS.items()
            if any(re.search(r"\b" + re.escape(kw) + r"\b", query_combined) for kw in keywords)
        }

        # 1. Compute BM25 scores
        bm25_scores = self._compute_bm25_scores(all_tokens, entity_tokens)

        # 2. Compute ChromaDB vector distances
        vector_scores: dict[str, float] = {}
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
                    dists = results.get("distances", [[]])[0] if results.get("distances") else [0.5] * len(ids)
                    for gid, dist in zip(ids, dists):
                        sim = max(0.0, min(1.0, 1.0 - (dist if dist is not None else 0.5)))
                        vector_scores[gid] = sim
        except Exception as e:
            logger.debug(f"ChromaDB query fallback: {e}")

        # 3. Assemble hybrid passages
        passages: list[EvidencePassage] = []
        for g in self.guidelines:
            gid = g["guideline_id"]
            bm25 = bm25_scores.get(gid, 0.0)
            vec = vector_scores.get(gid, 0.0)

            # Check if vector search was active for this doc
            if gid in vector_scores:
                composite = round(0.55 * bm25 + 0.45 * vec, 3)
            else:
                composite = round(bm25, 3)

            guide_combined = f"{g['title']} {' '.join(g.get('topics', []))} {g['text']}".lower()
            topics_text = " ".join(g.get("topics", [])).lower()
            title_text = g["title"].lower()
            body_text = g["text"].lower()

            # Check anatomical region compatibility
            guide_regions = {
                region for region, keywords in ANATOMICAL_REGIONS.items()
                if any(re.search(r"\b" + re.escape(kw) + r"\b", guide_combined) for kw in keywords)
            }
            has_anatomical_conflict = bool(
                query_regions and guide_regions and not (query_regions & guide_regions)
            )

            # Check CPT code compatibility
            guide_cpts = set(cpt_pattern.findall(guide_combined))
            has_cpt_conflict = bool(
                query_cpts and guide_cpts and not (query_cpts & guide_cpts)
            )

            # Entity anchor check (supports 3+ letter tokens, e.g. mri, cmp, cbc)
            has_topic_match = any(t in topics_text or t in title_text for t in entity_tokens if len(t) >= 3)
            has_body_match = any(t in body_text for t in entity_tokens if len(t) >= 3)
            has_entity_match = has_topic_match or has_body_match

            # Threshold and discard logic
            if has_cpt_conflict:
                used = False
                composite = round(min(composite, 0.20), 3)
                discard_reason = f"CPT mismatch: guideline covers CPT {', '.join(sorted(guide_cpts))} instead of claim CPT {', '.join(sorted(query_cpts))}"
            elif has_anatomical_conflict:
                used = False
                composite = round(min(composite, 0.20), 3)
                discard_reason = f"Anatomical mismatch: guideline targets {', '.join(sorted(guide_regions))} while claim targets {', '.join(sorted(query_regions))}"
            elif entity_tokens and not has_entity_match:
                used = False
                composite = round(min(composite, 0.20), 3)
                discard_reason = f"Entity mismatch: guideline does not mention clinical entity '{entity}'"
            elif composite < self.relevance_threshold:
                used = False
                discard_reason = f"Below relevance threshold {self.relevance_threshold:.2f} (score: {composite:.2f})"
            elif entity_tokens and not has_topic_match and composite < 0.65:
                used = False
                discard_reason = "Entity mismatch: clinical entity only weakly mentioned in body text"
            else:
                used = True
                discard_reason = None

            passages.append(EvidencePassage(
                passage_id=f"pas_{uuid.uuid4().hex[:10]}",
                guideline_id=gid,
                title=g["title"],
                source=g["source"],
                text=g["text"],
                relevance_score=composite,
                used_in_decision=used,
                discard_reason=discard_reason
            ))

        # Rank by relevance score descending
        passages.sort(key=lambda p: p.relevance_score, reverse=True)
        top_passages = passages[:k]

        used_cnt = sum(1 for p in top_passages if p.used_in_decision)
        disc_cnt = len(top_passages) - used_cnt
        logger.info(f"Hybrid retrieval for '{entity}': {used_cnt} passages usable, {disc_cnt} discarded (threshold: {self.relevance_threshold:.2f})")

        return top_passages

    def retrieve_evidence_passages(self, entity: str, claim_text: str, k: int = 3) -> list[EvidenceSnippet]:
        """Backward-compatible method returning EvidenceSnippet list."""
        passages = self.retrieve_hybrid_passages(entity, claim_text, k=k)
        return [
            EvidenceSnippet(
                guideline_id=p.guideline_id or "UNKNOWN",
                title=p.title,
                source=p.source,
                text=p.text,
                relevance_score=p.relevance_score
            )
            for p in passages if p.used_in_decision
        ]

    async def verify_claim(self, claim: Claim) -> VerificationResult:
        """
        Verify an extracted Claim against local guidelines and price benchmarks.
        Executes hybrid retrieval, evaluates deterministic abstention gates,
        calls local Ollama LLM, and records complete decision audit trail.
        """
        entity = claim.extracted_fields.entity
        outcome = claim.extracted_fields.effect_or_outcome or "None reported"

        # 1. Retrieve hybrid evidence passages (with scores and discard reasons)
        passages = self.retrieve_hybrid_passages(entity, claim.original_text, k=5)
        usable_passages = [p for p in passages if p.used_in_decision]

        # Map to backwards-compatible snippets
        snippets = [
            EvidenceSnippet(
                guideline_id=p.guideline_id or "UNKNOWN",
                title=p.title,
                source=p.source,
                text=p.text,
                relevance_score=p.relevance_score
            )
            for p in usable_passages
        ]

        # 2. Evaluate cost anomaly
        anomaly_details = cost_anomaly_service.evaluate_claim_cost(claim)
        has_cost_anomaly = anomaly_details.is_anomaly

        # 3. Pre-evaluation Abstention Check (before querying LLM)
        pre_abstention = abstention_service.evaluate(
            claim=claim,
            passages=passages,
            cost_details=anomaly_details
        )

        if pre_abstention.should_abstain:
            logger.info(f"Claim {claim.claim_id}: Abstention triggered before LLM execution [{pre_abstention.rule_triggered.value}]: {pre_abstention.reason}")
            verification = VerificationResult(
                claim_id=claim.claim_id,
                support_score=0.0,
                verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                action=VerificationAction.ABSTAIN,
                reasoning=(
                    f"System abstained from judgment: {pre_abstention.reason}"
                ),
                evidence_snippets=snippets,
                passages_considered=passages,
                cost_anomaly_flag=has_cost_anomaly,
                anomaly_details=anomaly_details,
                location=claim.location,
                abstain_reason=pre_abstention.reason,
                verified_at=datetime.now(timezone.utc)
            )

            # Record full audit trail
            audit_trail = audit_service.record_full_audit(
                claim=claim,
                verification=verification,
                passages=passages,
                cost_details=anomaly_details,
                abstention_decision=pre_abstention,
                raw_model_verdict=None,
                raw_model_support_score=0.0,
                raw_model_reasoning=None,
                raw_conflict_assessment=None,
            )
            verification.audit_trail_id = audit_trail.audit_id

            try:
                await audit_service.save_audit_trail(audit_trail)
            except Exception as e:
                logger.warning(f"Failed to persist audit trail: {e}")

            return verification

        # 4. Formulate prompt for local Ollama LLM using usable passages
        passages_text = "\n\n".join(
            f"[Passage ID: {passage.passage_id}] Guideline: {passage.title} "
            f"({passage.source})\nText: {passage.text}"
            for passage in usable_passages
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
                "temperature": 0.0,
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
        raw_verdict, raw_support_score, raw_reasoning, conflict_assessment = (
            self._parse_verification_response(raw_response)
        )

        # 7. Post-evaluation Abstention Check (evaluating conflicting evidence or low confidence)
        post_abstention = abstention_service.evaluate(
            claim=claim,
            passages=passages,
            cost_details=anomaly_details,
            model_verdict=raw_verdict,
            model_support_score=raw_support_score,
            model_reasoning=raw_reasoning,
            model_conflict_assessment=conflict_assessment
        )

        if post_abstention.should_abstain:
            final_verdict = VerificationVerdict.INSUFFICIENT_EVIDENCE
            final_action = VerificationAction.ABSTAIN
            final_support_score = 0.0
            final_abstain_reason = post_abstention.reason
        else:
            final_action, final_abstain_reason = self._determine_action(raw_verdict, raw_support_score, has_cost_anomaly)
            final_verdict = raw_verdict
            final_support_score = raw_support_score

        verification = VerificationResult(
            claim_id=claim.claim_id,
            support_score=final_support_score,
            verdict=final_verdict,
            action=final_action,
            reasoning=raw_reasoning,
            evidence_snippets=snippets,
            passages_considered=passages,
            cost_anomaly_flag=has_cost_anomaly,
            anomaly_details=anomaly_details,
            location=claim.location,
            abstain_reason=final_abstain_reason,
            verified_at=datetime.now(timezone.utc)
        )

        # 8. Record and persist complete AuditTrail (preserving raw model verdict and policy overrides)
        audit_trail = audit_service.record_full_audit(
            claim=claim,
            verification=verification,
            passages=passages,
            cost_details=anomaly_details,
            abstention_decision=post_abstention,
            raw_model_verdict=raw_verdict,
            raw_model_support_score=raw_support_score,
            raw_model_reasoning=raw_reasoning,
            raw_conflict_assessment=conflict_assessment,
        )
        verification.audit_trail_id = audit_trail.audit_id

        try:
            await audit_service.save_audit_trail(audit_trail)
        except Exception as e:
            logger.warning(f"Failed to persist audit trail: {e}")

        return verification

    def _parse_verification_response(
        self,
        raw_text: str
    ) -> tuple[VerificationVerdict, float, str, Optional[dict[str, Any]]]:
        """Parse the verdict, support score, reasoning, and optional conflict assessment."""
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
                "Verification output was non-standard; assigned default partially supported verdict.",
                None
            )

        verdict_str = str(parsed.get("verdict") or "partially_supported").lower().strip()
        if verdict_str in [v.value for v in VerificationVerdict]:
            verdict = VerificationVerdict(verdict_str)
        else:
            verdict = VerificationVerdict.PARTIALLY_SUPPORTED

        score_val = parsed.get("support_score")
        try:
            score = float(score_val)
            score = max(0.0, min(1.0, round(score, 3)))
        except (TypeError, ValueError):
            defaults = {
                VerificationVerdict.SUPPORTED: 0.85,
                VerificationVerdict.PARTIALLY_SUPPORTED: 0.55,
                VerificationVerdict.CONTRADICTED: 0.15,
                VerificationVerdict.INSUFFICIENT_EVIDENCE: 0.10,
            }
            score = defaults.get(verdict, 0.50)

        reasoning = str(parsed.get("reasoning") or "Evidence evaluated against clinical guidelines.").strip()
        conflict_assessment = parsed.get("conflict_assessment")
        if not isinstance(conflict_assessment, dict):
            conflict_assessment = None
        return verdict, score, reasoning, conflict_assessment

    def _parse_verification_output(
        self,
        raw_text: str
    ) -> tuple[VerificationVerdict, float, str]:
        """Backward-compatible parser for the public verdict fields."""
        verdict, score, reasoning, _ = self._parse_verification_response(raw_text)
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

        return (
            VerificationAction.FLAG,
            None
        )


verification_service = VerificationService()
