# EvidenceBridge 🩺🔍
### Evidence-Auditing & Cost-Anomaly Engine for Healthcare Claims & Hospital Bills

> **[!IMPORTANT]**
> **Scope of this Layer (Layer 3):**
> **Layer 3 adds rigorous abstention + full decision audit trail.** Hyperlocal trust density and frontend come later.

---

EvidenceBridge is an open-source, local-first engine designed to audit healthcare claims, patient reports, and hospital bills. It provides end-to-end traceability, structured clinical/cost extraction, tamper-evident provenance, guideline-backed claim verification, pricing anomaly detection, a deterministic safety-gated abstention policy, and a transparent 7-stage decision graph.

---

## 🏗️ Architecture (Layers 1, 2, and 3)

```
                     ┌──────────────────────────────────────────────┐
                     │ Raw Unstructured Text                        │
                     │ - Clinical Progress Notes                    │
                     │ - Patient Community Forum Reports            │
                     │ - Itemized Hospital Bill Line Items          │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌────────────────────────────────────────────────┐
                    │ POST /extract  OR  POST /extract-and-verify    │
                    └───────────────────────┬────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
     ┌─────────────────────────────┐                ┌─────────────────────────────┐
     │ Local LLM Extraction Engine │                │ Provenance Engine           │
     │ (Ollama: phi3:mini / llama) │                │ - Verbatim Snippet Anchor   │
     │ - Strict JSON Schema        │                │ - SHA-256 Digest of Source  │
     │ - Entity (Drug/Procedure)   │                │ - Source URL & Timestamp    │
     │ - Outcome / Side Effect     │                │ - Unique Claim ID           │
     │ - Cost / Price Range        │                │ - Tamper-Proof Audit Trail  │
     │ - Location & Sentiment      │                │                             │
     │ - Confidence Score          │                │                             │
     └──────────────┬──────────────┘                └──────────────┬──────────────┘
                    │                                              │
                    └───────────────────────┬──────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────┐
                         │ Assembled Traceable Claim Object    │
                         └──────────────────┬──────────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
       ┌───────────────────────────┐                 ┌───────────────────────────┐
       │ MongoDB Document Store    │                 │ Local Knowledge Base      │
       │ - "claims" collection     │                 │ - Clinical Guidelines     │
       │ - "verifications" coll    │                 │ - Public Price Benchmarks │
       │ - "audit_trails" coll     │                 └─────────────┬─────────────┘
       └─────────────▲─────────────┘                               │
                     │                                             │
                     │         ┌───────────────────────────────────┘
                     │         │
                     │         ▼
       ┌─────────────┴───────────────────────────────────────────────────────────┐
       │ Layer 2 & 3: Verification, Cost Anomaly & Audit Trail Engine           │
       │                                                                         │
       │ 1. Hybrid Retrieval & Ranking (BM25 + ChromaDB Vector):                 │
       │    - Combines term frequency & IDF with vector embeddings               │
       │    - Entity anchor boosting and relevance threshold gating (0.35)       │
       │    - Explicitly labels used passages vs discarded (with reason)         │
       │                                                                         │
       │ 2. Cost Anomaly Detection:                                              │
       │    - Evaluates billed charges against CMS/NADAC price benchmarks        │
       │    - Flags markups exceeding threshold multiplier (default: 3.0×)       │
       │    - Categorizes severity: Moderate (3×), Severe (5×), Extreme (10×+)   │
       │                                                                         │
       │ 3. Deterministic Abstention Policy Gates:                               │
       │    - [Rule 1] ENTITY_NOT_FOUND: Entity empty or unrecognized            │
       │    - [Rule 2] NO_RELEVANT_EVIDENCE: All passages below threshold (0.35) │
       │    - [Rule 3] CONFLICTING_EVIDENCE: Conflicting guideline consensus     │
       │    - [Rule 4] LOW_MODEL_CONFIDENCE: Score < 0.40 without contradiction  │
       │    - [Rule 5] UNBENCHMARKED_HIGH_COST: Charge > $100 with no benchmark  │
       │                                                                         │
       │ 4. Support Scoring (Ollama LLM):                                        │
       │    - Evaluates usable evidence: "supported", "partially_supported",     │
       │      "contradicted", or "insufficient_evidence"                         │
       │                                                                         │
       │ 5. Full Decision Audit Trail (7 Stages):                                │
       │    EXTRACTION ➔ PROVENANCE ➔ RETRIEVAL ➔ COST_AUDIT ➔                   │
       │    CLINICAL_VERIFICATION ➔ ABSTENTION_GATE ➔ FINAL_ACTION              │
       │    [Persisted in MongoDB "audit_trails" linked to claim & verif ID]     │
       └─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
evidencebridge/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py             # FastAPI routes (/extract, /verify, /audit, /health)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py            # Pydantic models (Claim, VerificationResult, AuditTrail)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── abstention.py         # Deterministic 5-rule safety abstention engine
│   │   │   ├── audit.py              # 7-stage decision graph & audit trail service
│   │   │   ├── cost_anomaly.py       # Cost anomaly detection service (CMS/NADAC benchmarks)
│   │   │   ├── extraction.py         # Ollama structured JSON extraction pipeline
│   │   │   ├── provenance.py         # SHA-256 hashing & source metadata linkage
│   │   │   ├── storage.py            # Async MongoDB storage service (claims, verifs, audits)
│   │   │   ├── vector_store.py       # Local ChromaDB vector indexing (offline semantic store)
│   │   │   └── verification.py       # Hybrid retrieval & Ollama support scoring engine
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── logger.py             # Formatted logging utility
│   │   ├── config.py                 # Pydantic Settings & environment config
│   │   └── main.py                   # FastAPI application initialization & lifespan
│   ├── tests/
│   │   ├── conftest.py               # Shared pytest fixtures
│   │   ├── test_abstention.py        # Tests for all 5 deterministic abstention rules
│   │   ├── test_api.py               # FastAPI endpoint integration tests (including audit)
│   │   ├── test_audit.py             # 7-stage decision graph & passage lineage tests
│   │   ├── test_cost_anomaly.py      # Benchmark matching & cost markup multiplier tests
│   │   ├── test_extraction.py        # Extraction parsing and fallback tests
│   │   ├── test_provenance.py        # Cryptographic hashing & tamper-check tests
│   │   ├── test_retrieval_ranking.py # BM25 + Vector hybrid ranking and threshold tests
│   │   ├── test_schemas.py           # Pydantic schema validation tests
│   │   └── test_verification.py      # Support scoring, contradiction, and action tests
│   ├── Dockerfile                    # Container definition for backend
│   └── requirements.txt              # Core Python dependencies
├── data/
│   ├── knowledge/                    # Local Ground-Truth Knowledge Base
│   │   ├── clinical_guidelines_samples.json # 12 authoritative guideline excerpts (ADA, AHA, CDC, etc.)
│   │   └── price_benchmarks.json     # Public pricing benchmarks (CMS, Fair Health, NADAC)
│   └── samples/                      # 13 realistic sample records
│       ├── samples.json              # Aggregated JSON array of all samples
│       ├── sample_01_clinical_note_diabetes.json
│       ├── sample_02_bill_inflated_er_visit.json
│       ├── sample_03_patient_post_semaglutide.json
│       ├── sample_04_bill_inflated_tylenol.json
│       ├── sample_05_clinical_note_hypertension.json
│       ├── sample_06_bill_knee_mri_overcharge.json
│       ├── sample_07_patient_post_knee_arthroscopy.json
│       ├── sample_08_clinical_note_pneumonia.json
│       ├── sample_09_bill_routine_blood_panel.json
│       ├── sample_10_patient_post_botox_migraine.json
│       ├── sample_11_contradicted_antibiotic_bronchitis.json  # [CONTRADICTED]
│       ├── sample_12_cost_anomaly_extreme_saline.json         # [EXTREME COST ANOMALY (16×)]
│       └── sample_13_unverified_rare_herb.json                # [ABSTAIN (insufficient evidence)]
├── scripts/
│   ├── setup_ollama.sh               # Ollama install/verify/pull helper (Linux/macOS)
│   ├── setup_ollama.ps1              # Ollama install/verify/pull helper (Windows)
│   └── seed_data.py                  # Batch ingestion and verification CLI
├── .env.example                      # Configuration template
├── .gitignore                        # Git exclusion rules
├── docker-compose.yml                # Multi-container orchestration (Mongo + Backend)
└── README.md                         # Documentation and setup instructions
```

---

## 🛡️ The 5 Deterministic Abstention Rules

In high-stakes healthcare auditing, **guessing is unacceptable**. EvidenceBridge enforces deterministic abstention safety gates before and after model judgment:

| Rule Name | Trigger Condition | Explainable Rationale |
| :--- | :--- | :--- |
| **`ENTITY_NOT_FOUND`** | Entity is empty, null, or generic `"unspecified"`. | Cannot verify a claim whose primary medical entity cannot be resolved. |
| **`NO_RELEVANT_EVIDENCE`** | Zero guideline passages achieve composite relevance score $\ge 0.35$. | Refuses to hallucinate a judgment when no authoritative guidelines exist in knowledge base. |
| **`CONFLICTING_EVIDENCE`** | Multiple guidelines of similar strength conflict or lack medical consensus. | Protects against false certainty when clinical literature is divided. |
| **`LOW_MODEL_CONFIDENCE`** | Verification support score $< 0.40$ without an explicit contradiction. | Weak evidence links without refutation require human review. |
| **`UNBENCHMARKED_HIGH_COST`**| Financial charge reported ($\ge \$100$), but no public pricing benchmark exists. | Avoids asserting whether a high cost is fair or anomalous without ground truth benchmarks. |

---

## 📜 The 7-Stage Decision Audit Graph

Every verified claim produces an immutable `AuditTrail` record in MongoDB capturing the exact execution lineage:

1. **`EXTRACTION`**: Input text length, extracted entity, reported outcome, cost string, sentiment, and model confidence.
2. **`PROVENANCE`**: SHA-256 cryptographic digest verification, anchor snippet, source document URL.
3. **`HYBRID_RETRIEVAL`**: Total passages retrieved, ranked BM25 + Vector scores, passages marked `used_in_decision=True`, and passages marked `used_in_decision=False` with explicit `discard_reason`.
4. **`COST_AUDIT`**: Extracted dollar amount, benchmark minimum and maximum, markup multiplier, anomaly flag, and severity level.
5. **`CLINICAL_VERIFICATION`**: Prompt sent to Ollama, raw response, parsed verdict, support score ($0.0 - 1.0$), and citation reasoning.
6. **`ABSTENTION_GATE`**: Status of all 5 deterministic safety rules and detailed trigger explanation.
7. **`FINAL_ACTION`**: Composite decision (`ACCEPT`, `FLAG`, or `ABSTAIN`) with full audit trail cross-referencing.

---

## ⚙️ Quickstart

### 1. Prerequisites
- **Python 3.11+**
- **Ollama** installed ([https://ollama.com/download](https://ollama.com/download)) with model `phi3:mini` or `llama3.1:8b`
- **MongoDB** running locally (`mongodb://localhost:27017`) or free Atlas instance

### 2. Setup Ollama
On Linux/macOS:
```bash
./scripts/setup_ollama.sh
```
On Windows (PowerShell):
```powershell
.\scripts\setup_ollama.ps1
```

### 3. Setup Virtual Environment & Dependencies
```bash
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\Activate.ps1

pip install -r backend/requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```
Default configuration values in `.env`:
```env
APP_NAME=EvidenceBridge
PORT=8000
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=evidencebridge
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini
KNOWLEDGE_BASE_DIR=./data/knowledge
COST_ANOMALY_THRESHOLD_MULTIPLIER=3.0
RETRIEVAL_RELEVANCE_THRESHOLD=0.35
MIN_CONFIDENCE_THRESHOLD=0.40
```

### 5. Launch Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger documentation is available at `http://localhost:8000/docs`.

---

## 📡 Example API Requests (cURL)

### 1. Extract & Verify with Decision Audit Logging (`POST /extract-and-verify`)
```bash
curl -X POST http://localhost:8000/extract-and-verify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "MIDWEST GENERAL HOSPITAL: 0.9% Sodium Chloride (Normal Saline) IV Solution, 1,000 mL infusion bag. Unit Billed Charge: $720.00.",
    "source_type": "hospital_bill"
  }'
```
**Response Preview:**
```json
{
  "success": true,
  "claim": {
    "claim_id": "clm_8f2b4e19c0a34b92",
    "extracted_fields": {
      "entity": "0.9% Sodium Chloride (Normal Saline) IV Solution, 1,000 mL",
      "cost_range": "$720.00"
    }
  },
  "verification": {
    "verification_id": "ver_41c0e39a2b1f4812",
    "audit_trail_id": "aud_7b819a00e54d3129",
    "verdict": "supported",
    "support_score": 0.88,
    "action": "flag",
    "cost_anomaly_flag": true,
    "anomaly_details": {
      "is_anomaly": true,
      "multiplier": 16.0,
      "severity": "extreme"
    }
  },
  "audit_trail_id": "aud_7b819a00e54d3129"
}
```

---

### 2. Inspect Full Decision Audit Trail (`GET /audit/{claim_id}`)
Retrieve the full 7-stage decision graph, passages considered, and discard reasons:
```bash
curl -X GET http://localhost:8000/audit/clm_8f2b4e19c0a34b92
```
**Response Preview:**
```json
{
  "success": true,
  "audit_trail": {
    "audit_id": "aud_7b819a00e54d3129",
    "claim_id": "clm_8f2b4e19c0a34b92",
    "verification_id": "ver_41c0e39a2b1f4812",
    "steps": [
      {
        "step_name": "EXTRACTION",
        "output_summary": "Extracted Entity='0.9% Sodium Chloride Normal Saline 1,000 mL', Cost='$720.00', Confidence=0.94"
      },
      {
        "step_name": "PROVENANCE",
        "output_summary": "Cryptographic digest=e3b0c44298fc1c14... Snippet='MIDWEST GENERAL HOSPITAL...'"
      },
      {
        "step_name": "HYBRID_RETRIEVAL",
        "output_summary": "Retrieved 5 passages (1 used, 4 discarded). Top relevance score=0.88"
      },
      {
        "step_name": "COST_AUDIT",
        "output_summary": "Anomaly=True, Severity=EXTREME, Multiplier=16.0×. Billed amount of $720.00 is 16.0× higher than benchmark max of $45.00."
      },
      {
        "step_name": "CLINICAL_VERIFICATION",
        "output_summary": "Verdict=supported, SupportScore=0.88, Reasoning='Normal saline is standard for IV hydration...'"
      },
      {
        "step_name": "ABSTENTION_GATE",
        "output_summary": "AbstainTriggered=False, Rule=NONE. Reason='Passed all safety gates'"
      },
      {
        "step_name": "FINAL_ACTION",
        "output_summary": "Action=FLAG, Verdict=supported, CostAnomalyFlag=True"
      }
    ],
    "passages_considered": [
      {
        "passage_id": "pas_88a10b",
        "title": "USP & CDC Clinical Guidelines: 0.9% Sodium Chloride (Normal Saline) IV Solution",
        "relevance_score": 0.88,
        "used_in_decision": true,
        "discard_reason": null
      },
      {
        "passage_id": "pas_99c21d",
        "title": "ADA Standards of Care: Metformin in Type 2 Diabetes Mellitus",
        "relevance_score": 0.12,
        "used_in_decision": false,
        "discard_reason": "Below relevance threshold 0.35 (score: 0.12)"
      }
    ],
    "final_action": "flag",
    "cost_anomaly_flag": true
  }
}
```

---

### 3. Inspect Audit Trail by Verification ID (`GET /audit/verification/{verification_id}`)
```bash
curl -X GET http://localhost:8000/audit/verification/ver_41c0e39a2b1f4812
```

---

## 🧪 Automated Test Suite

Run all 49 unit and integration tests:
```bash
pytest backend/tests -v
```

Tests cover:
- ✅ **Schemas**: Complete validation of Claim, VerificationResult, AuditTrail, LocationInfo, TrustDensityMetrics models
- ✅ **Provenance**: SHA-256 cryptographic digests & tamper detection
- ✅ **Extraction**: Ollama structured JSON parsing & markdown stripping
- ✅ **Cost Anomaly Detection**: Numeric extraction, CPT code matching, extreme markup multiplier ($74 Tylenol, $720 Saline)
- ✅ **Hybrid Retrieval Quality**: BM25 + Vector ranking, entity anchoring, used vs discarded passage labeling
- ✅ **Abstention Policy Gates**: Deterministic enforcement of all 5 safety rules (missing entity, no evidence, conflicting guidelines, low confidence, unbenchmarked high cost)
- ✅ **Decision Audit Trail**: Full 7-stage decision graph recording and verification ID linkage
- ✅ **Location Extraction**: City/state regex extraction, normalization, stop-word filtering, prominent-city fallback
- ✅ **Trust Density Math**: Support ratio (with partial credit), anomaly rate, time-decay recency weighting, tier assignment
- ✅ **Trust Density Edge Cases**: Zero claims, single claim, all-abstained, no verifications
- ✅ **FastAPI Endpoints**: All Layer 1–4 endpoints including `/trust-density/{key}`, `/trust-density`, `/claims?location=...`

---

## 🗺️ Layer 4: Hyperlocal Trust Density

> **Layer 4 adds hyperlocal trust density. Frontend and advanced evaluation come later.**

### What it does

Every verified claim is now associated with a geographic location extracted automatically from the document text (regex + prominent-city fallback — no external geocoding API needed). EvidenceBridge aggregates verified claims by `location_key` and computes a deterministic **trust density score** that captures:

| Signal | Weight (default) |
|---|---|
| `support_ratio` — fraction of conclusive verifications that are supported | 45% |
| `1 − cost_anomaly_rate` — inverse of the billing-anomaly rate | 35% |
| `volume_factor` — recency-weighted claim volume (exponential decay) | 20% |

**Formula:**
```
density_score = 0.45 × support_ratio
              + 0.35 × (1 − cost_anomaly_rate)
              + 0.20 × min(1.0, recency_volume / MIN_VOLUME)
```

All three weights and `MIN_VOLUME` / `TIME_DECAY_DAYS` are configurable via `.env`.

**Trust Tiers:**

| Tier | Score Range | Meaning |
|---|---|---|
| `high` | ≥ 0.75 | High guideline compliance, few anomalies |
| `moderate` | 0.50–0.74 | Stable but occasional anomalies |
| `low` | 0.30–0.49 | Elevated contradictions or cost markups |
| `critical_alert` | < 0.30 with ≥ 2 anomalies | Systematic billing fraud risk |
| `insufficient_data` | < 2 verified claims | Not enough data to score |

### New Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/trust-density/{location_key}` | Get metrics + risk insight for a locality (e.g. `houston_tx`) |
| `GET` | `/trust-density` | Paginated list of all tracked locations, ranked by `density_score` |
| `POST` | `/trust-density/{location_key}/recompute` | Force-recompute metrics from live MongoDB data |
| `GET` | `/claims?location=houston_tx` | Filter claims by canonical location key or city name |

### Example cURL

```bash
# Get trust density for Houston, TX
curl http://localhost:8000/trust-density/houston_tx

# List all locations ranked by density score
curl "http://localhost:8000/trust-density?limit=10&sort_by=density_score"

# Filter claims by location
curl "http://localhost:8000/claims?location=chicago_il&limit=20"

# Force recompute after seeding new data
curl -X POST http://localhost:8000/trust-density/atlanta_ga/recompute
```

### Seed with trust density

```bash
# Ingest + verify all samples, then show per-location trust density table
python scripts/seed_data.py --verify
```

### Location key format

Canonical keys are normalized lowercase snake_case:
- `"Atlanta, GA"` → `atlanta_ga`
- `"Chicago, Illinois"` → `chicago_il`
- `"Houston, TX"` → `houston_tx`
- `"Los Angeles, CA"` → `los_angeles_ca`

Location is **best-effort** — if no city/state is found in the text, `claim.location` is `null` and the core pipeline continues without interruption.

### Layer 4 .env options

```env
TRUST_DENSITY_SUPPORT_WEIGHT=0.45
TRUST_DENSITY_ANOMALY_WEIGHT=0.35
TRUST_DENSITY_VOLUME_WEIGHT=0.20
TRUST_DENSITY_MIN_VOLUME=5
TRUST_DENSITY_TIME_DECAY_DAYS=45.0
MONGODB_TRUST_DENSITY_COLLECTION=trust_density
```

---

## 🗺️ Roadmap & Next Layers

- [x] **Layer 1:** Local Ingestion, Ollama structured extraction, tamper-evident provenance, MongoDB storage.
- [x] **Layer 2:** Claim Verification, Support Scoring (0.0–1.0), Decision Triad (ACCEPT, FLAG, ABSTAIN), and Basic Cost Anomaly Detection against public CMS/Fair Health benchmarks.
- [x] **Layer 3:** Rigorous 5-Rule Abstention Engine, BM25 + Vector Hybrid Retrieval Ranking, and Full 7-Stage Decision Audit Graph.
- [x] **Layer 4 (This Layer):** Hyperlocal Trust Density — geographic claim aggregation, recency-weighted density scoring, human-auditable location insights, and `/trust-density` endpoints.
- [ ] **Layer 5:** High-Performance Verification Engine & Interactive Web Dashboard.


---

## 📄 License
Apache-2.0. Open-source, local-first, privacy-preserving healthcare analytics.
