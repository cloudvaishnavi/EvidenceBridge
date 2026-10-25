# EvidenceBridge 🩺🔍
### Evidence-Auditing & Cost-Anomaly Engine for Healthcare Claims & Hospital Bills

[![Tests](https://img.shields.io/badge/Tests-157%20Passed-emerald.svg)](backend/tests)
[![Architecture](https://img.shields.io/badge/Architecture-Layers%201--6%20Complete-sky.svg)](README.md)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local--First%20%7C%20Zero%20Data%20Leaks-blue.svg)](README.md)
[![UI](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite%205-indigo.svg)](frontend)
[![Voice AI](https://img.shields.io/badge/Voice%20AI-English%20%26%20Kannada-teal.svg)](README.md)
[![License](https://img.shields.io/badge/License-Apache--2.0-slate.svg)](LICENSE)

**EvidenceBridge** is an open-source, local-first clinical decision-support and cost-anomaly auditing platform. It audits hospital bills, itemized billing statements, and clinical encounter notes against authoritative medical guidelines (ACR, ADA, AHA, CDC, GOLD) and public pricing benchmarks (CMS, Fair Health, NADAC) with complete cryptographic transparency.

Unlike generative black-box LLMs that hallucinate justifications when ungrounded, EvidenceBridge enforces deterministic safety gates, dual-assessment retention (clinical support vs. financial markup), an immutable 7-stage audit graph, hyperlocal provider reliability scoring, offline calibration metrics, and an accessible multilingual AI voice assistant.

---

## 🎯 What EvidenceBridge IS and What It Is NOT

| EvidenceBridge IS | EvidenceBridge Is NOT |
| :--- | :--- |
| **An auditor decision-support tool** that flags potential price markups and guideline inconsistencies for human review. | **NOT an automated denial system** or claims adjudication replacement. Humans retain all final authority. |
| **A local-first, privacy-preserving pipeline** that processes sensitive bills entirely offline via Ollama without cloud leakage. | **NOT a diagnostic medical device** or diagnostic software (FDA 510(k) or SaMD). |
| **A deterministic, explainable safety engine** that refuses to guess when evidence or benchmarks are absent. | **NOT a provider of clinical medical advice**, patient diagnosis, or personalized treatment plans. |
| **A cryptographic audit trail system** that records SHA-256 provenance and reasons for discarded guidelines. | **NOT an infallible arbiter of medical truth** — guidelines represent population standards and evolve. |
| **A supportive peer-sharing space (Community Stories)** for personal coping narratives with mandatory disclaimers. | **NOT a medical consultation forum or advice network** — peer stories are personal anecdotes and never clinical guidance. |

---

## ✨ Key Unique Features & Differentiators

1. **Deterministic 5-Rule Abstention Safety Gate**:
   Unlike standard generative LLMs that fabricate plausible justifications when uncertain, EvidenceBridge enforces 5 deterministic safety gates (`ENTITY_NOT_FOUND`, `NO_RELEVANT_EVIDENCE`, `CONFLICTING_EVIDENCE`, `LOW_MODEL_CONFIDENCE`, `UNBENCHMARKED_HIGH_COST`). If confidence is inadequate or reference data is missing, the system safely **ABSTAINS**.
2. **Dual-Assessment Retention (Clinical Necessity vs. Billing Markup)**:
   A claim can be clinically indicated yet financially predatory (e.g., 0.9% Normal Saline at $720 vs. $5–$45 benchmark). EvidenceBridge preserves both the raw model assessment (`supported`) and the policy override (`FLAG`), preventing medical necessity from obscuring extreme markups.
3. **7-Stage Cryptographic Decision Audit Graph**:
   Every claim audit generates an immutable execution record detailing all 7 stages: Extraction, SHA-256 Provenance, Hybrid Retrieval (with explicit discard reasons), Cost Audit, Clinical Verification, Abstention Gate, and Final Action.
4. **Anatomical & CPT Hybrid Ranking**:
   Hybrid retrieval couples BM25 term weighting with ChromaDB vector search and strict anatomical/CPT validation, ensuring a brain MRI claim never retrieves knee guidelines or general imaging notes.
5. **Multi-Tier Pricing-Anomaly Engine**:
   Evaluates billed charges against CMS, Fair Health, and NADAC benchmarks, categorizing markups into *Moderate* (3.0×–5.0×), *Severe* (5.0×–10.0×), and *Extreme* ($\ge 10.0\times$) severity tiers.
6. **Hyperlocal Regional Trust Density**:
   Tracks regional hospital compliance and billing anomaly rates across metropolitan markets with time-decay recency weighting (45-day exponential decay).
7. **Built-in Evaluation & Calibration Harness (ECE)**:
   Measures system reliability across gold-standard cases, tracking macro F1, cost anomaly detection precision/recall, over/under-abstention rates, and Expected Calibration Error (ECE).
8. **100% Free Multilingual AI Voice Assistant (English & Kannada / ಕನ್ನಡ)**:
   Browser-native speech recognition and synthesis paired with local Ollama for audible navigation and claim explanations with zero paid cloud APIs.
9. **Community Recovery Stories with Permanent Disclaimers**:
   A compassionate peer space for voluntary coping stories with optional public contact sharing, strictly isolated from the clinical audit pipeline.

---

## 💻 Technology Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2 (strict validation), Motor (async MongoDB driver), ChromaDB (vector store), rank-bm25, pytest.
- **Local AI & NLP**: Ollama (`phi3:mini`, `llama3.1:8b`), local semantic vector embeddings, regex & rule-based NER.
- **Frontend**: React 18, Vite 5, TypeScript 5, Tailwind CSS 3, Web Speech API (`SpeechRecognition`, `SpeechSynthesis`).
- **Database & Storage**: MongoDB (with automatic, zero-config in-memory fallback for all collections).

---

## 🏗️ Architecture (Full End-to-End Decision Pipeline)

```
                     ┌──────────────────────────────────────────────┐
                     │ Raw Unstructured Medical Document            │
                     │ - Clinical Progress Notes (EHR)              │
                     │ - Itemized Hospital Bill Line Items          │
                     │ - Patient Invoices & Encounter Summaries     │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌────────────────────────────────────────────────┐
                    │ POST /extract-and-verify                       │
                    └───────────────────────┬────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
     ┌─────────────────────────────┐                ┌─────────────────────────────┐
     │ Stage 1: Extraction Engine  │                │ Stage 2: Provenance Engine  │
     │ (Ollama: phi3:mini / llama) │                │ - Verbatim Snippet Anchor   │
     │ - Strict JSON Schema        │                │ - SHA-256 Digest of Source  │
     │ - Clinical Entity & CPT Code│                │ - Source URL & Timestamp    │
     │ - Reported Cost / Range     │                │ - Unique Claim ID           │
     │ - Location & Sentiment      │                │ - Tamper-Proof Audit Lineage│
     │ - Extractor Confidence      │                │                             │
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
       │ MongoDB Document Store    │                 │ Ground-Truth Knowledge    │
       │ - "claims" collection     │                 │ - Clinical Guidelines KB  │
       │ - "verifications" coll    │                 │ - Public Price Benchmarks │
       │ - "audit_trails" coll     │                 │   (CMS, Fair Health)      │
       │ - "community_stories" coll│                 └─────────────┬─────────────┘
       └─────────────▲─────────────┘                               │
                     │                                             │
                     │         ┌───────────────────────────────────┘
                     │         │
                     │         ▼
       ┌─────────────┴───────────────────────────────────────────────────────────┐
       │ Decision Pipeline & Verification Engine                                │
       │                                                                         │
       │ Stage 3: Hybrid Retrieval & Ranking (BM25 + ChromaDB Vector):           │
       │   - Combines term frequency & IDF with dense vector embeddings          │
       │   - Entity anchor boosting and relevance threshold gating (0.35)        │
       │   - Explicitly records used passages vs discarded (with reason)         │
       │                                                                         │
       │ Stage 4: Pricing-Anomaly Engine:                                        │
       │   - Evaluates billed charges against CMS/NADAC price benchmarks         │
       │   - Flags markups exceeding threshold multiplier (default: 3.0×)        │
       │   - Categorizes severity: Moderate (3×), Severe (5×), Extreme (10×+)    │
       │                                                                         │
       │ Stage 5: Clinical Support Scoring (Ollama LLM):                         │
       │   - Evaluates usable evidence: "supported", "partially_supported",      │
       │     "contradicted", or "insufficient_evidence"                          │
       │                                                                         │
       │ Stage 6: Deterministic Abstention Policy Gates:                         │
       │   - [Rule 1] ENTITY_NOT_FOUND: Entity empty or unrecognized             │
       │   - [Rule 2] NO_RELEVANT_EVIDENCE: All passages below threshold (0.35)  │
       │   - [Rule 3] CONFLICTING_EVIDENCE: Conflicting guideline consensus      │
       │   - [Rule 4] LOW_MODEL_CONFIDENCE: Score < 0.40 without contradiction   │
       │   - [Rule 5] UNBENCHMARKED_HIGH_COST: Charge > $100 with no benchmark   │
       │                                                                         │
       │ Stage 7: Final Action & Dual-Retention Synthesis:                       │
       │   - Synthesizes model verdict, pricing anomaly flag, & safety gates     │
       │   - Action: ACCEPT (Approved), FLAG (Review), ABSTAIN (Held)            │
       │   - Retains BOTH raw model verdict and policy override reason           │
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
│   │   │   └── routes.py             # FastAPI routes (/extract-and-verify, /audit, /stories, /evaluate, /health)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py            # Pydantic models (Claim, VerificationResult, AuditTrail, EvaluationReport, CommunityStory)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── abstention.py         # Deterministic 5-rule safety abstention engine
│   │   │   ├── audit.py              # 7-stage decision graph & audit trail service
│   │   │   ├── cost_anomaly.py       # Cost anomaly detection service (CMS/NADAC benchmarks)
│   │   │   ├── evaluation.py         # Layer 6 evaluation harness & ECE calibration engine
│   │   │   ├── extraction.py         # Ollama structured JSON extraction pipeline
│   │   │   ├── provenance.py         # SHA-256 hashing & source metadata linkage
│   │   │   ├── storage.py            # Async MongoDB storage service (claims, verifs, audits, stories, evals)
│   │   │   ├── trust_density.py      # Geographic trust density & time-decay scoring
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
│   │   ├── test_api.py               # FastAPI endpoint integration tests
│   │   ├── test_audit.py             # 7-stage decision graph & passage lineage tests
│   │   ├── test_community_stories.py # Tests for Community Stories CRUD, validation & limits
│   │   ├── test_controlled_cases.py  # End-to-end evaluation tests across labeled control cases
│   │   ├── test_cost_anomaly.py      # Benchmark matching & cost markup multiplier tests
│   │   ├── test_evaluation.py        # Evaluation runner, metrics computation & ECE calibration tests
│   │   ├── test_extraction.py        # Extraction parsing and fallback tests
│   │   ├── test_location.py          # Location extraction & normalization tests
│   │   ├── test_provenance.py        # Cryptographic hashing & tamper-check tests
│   │   ├── test_retrieval_ranking.py # BM25 + Vector hybrid ranking, anatomical & CPT matching
│   │   ├── test_schemas.py           # Pydantic schema validation tests
│   │   ├── test_trust_density.py     # Trust density math, time-decay & insight tests
│   │   └── test_verification.py      # Support scoring, contradiction, and action tests
│   ├── Dockerfile                    # Container definition for backend
│   └── requirements.txt              # Core Python dependencies
├── frontend/                         # Modern React 18 + Vite 5 + TypeScript + Tailwind UI
│   ├── src/
│   │   ├── api/client.ts             # Typed REST API client
│   │   ├── components/               # UI components (AuditTrailViewer, VoiceAssistant, AuthModal, etc.)
│   │   ├── context/                  # AuthContext (session state) & VoiceContext (Web Speech API)
│   │   ├── pages/                    # Landing, Home (Audit), Claims, ClaimDetail, TrustDensity, Evaluation, CommunityStories
│   │   ├── types.ts                  # Shared TypeScript interfaces
│   │   └── App.tsx                   # React Router route configuration
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── data/
│   ├── evaluation/
│   │   └── controlled_cases.json     # 8 gold-standard benchmark cases across major verdict paths
│   ├── knowledge/                    # Local Ground-Truth Knowledge Base
│   │   ├── clinical_guidelines_samples.json # 16 authoritative guideline excerpts (ACR, ADA, AHA, CDC, GOLD)
│   │   └── price_benchmarks.json     # Public pricing benchmarks (CMS, Fair Health, NADAC)
│   └── samples/                      # Realistic sample records
│       ├── samples.json              # Aggregated JSON array of all samples
│       └── sample_*.json             # Individual test fixtures
├── scripts/
│   ├── run_evaluation.py             # CLI runner for Layer 6 evaluation harness
│   ├── setup_ollama.sh               # Ollama install/verify/pull helper (Linux/macOS)
│   ├── setup_ollama.ps1              # Ollama install/verify/pull helper (Windows)
│   └── seed_data.py                  # Batch ingestion and verification CLI
├── .env.example                      # Configuration template
├── .gitignore                        # Git exclusion rules
├── docker-compose.yml                # Multi-container orchestration (Mongo + Backend)
└── README.md                         # Project documentation and guide
```
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

## ⚙️ Quickstart (Run Backend & Frontend)

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Ollama** installed ([https://ollama.com/download](https://ollama.com/download)) with model `phi3:mini` or `llama3.1:8b`
- **MongoDB** running locally (`mongodb://localhost:27017`) or free Atlas instance *(Note: if MongoDB is offline, EvidenceBridge automatically falls back to an in-memory datastore with pre-seeded data)*

### 2. Setup Local AI Model (Ollama)
On Linux/macOS:
```bash
./scripts/setup_ollama.sh
```
On Windows (PowerShell):
```powershell
.\scripts\setup_ollama.ps1
```
Or manually:
```bash
ollama run phi3:mini
```

### 3. Setup Python Backend
```bash
# Create & activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```
Default configuration values in `.env`:
```env
APP_NAME=EvidenceBridge
APP_ENV=development
PORT=8000
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
MONGODB_URL=mongodb://localhost:27017
# Or for MongoDB Atlas deployment (Never commit real credentials to git):
# MONGODB_URI=mongodb+srv://USER:PASS@cluster.mongodb.net/evidencebridge
MONGODB_DB_NAME=evidencebridge
MONGODB_USERS_COLLECTION=users
AUTH_SECRET_KEY=change-in-production-random-secret-key-min-32-chars
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=1440
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini
KNOWLEDGE_BASE_DIR=./data/knowledge
COST_ANOMALY_THRESHOLD_MULTIPLIER=3.0
RETRIEVAL_RELEVANCE_THRESHOLD=0.35
MIN_CONFIDENCE_THRESHOLD=0.40
```

### 5. Launch Backend Service
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger documentation is available at `http://localhost:8000/docs`.

### 6. Launch Frontend UI
In a separate terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`.

### 7. Instant 1-Click Interactive Demo
- Open `http://localhost:5173`.
- Click **⚡ Demo (Vasavi)** in the top navigation bar to sign in instantly as *Vasavi (Clinical Claims Reviewer)* with zero configuration.
- On the **Audit Claim** workspace, select any pre-configured scenario (e.g., *Normal Saline $720 Overcharge*, *Brain MRI $650*, *Bronchitis Antibiotics $24*) to run a live end-to-end audit.
- Inspect the 7-stage cryptographic audit trail or click **🔊 Read Result Aloud** to experience the AI voice assistant.

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

#### The 7 Decision Stages & Recorded Telemetry

EvidenceBridge executes a deterministic 7-stage decision graph for every claim audit:

| Stage # | Stage Name | Inputs & Telemetry Recorded | Outputs & Rationale |
|---|---|---|---|
| **1** | `EXTRACTION` | Raw document text, source type (`hospital_bill`, `clinical_note`, `forum_post`) | Extracted clinical entity, billed cost range, clinical outcome, location, model confidence |
| **2** | `PROVENANCE` | Original text and source metadata | Verifiable SHA-256 cryptographic digest, verbatim snippet anchor, tamper verification |
| **3** | `HYBRID_RETRIEVAL` | Clinical entity and document query tokens | BM25 + ChromaDB vector search, usable vs discarded passages count, relevance scores, discard reasons |
| **4** | `COST_AUDIT` | Extracted cost amount and procedure entity | Benchmark matched (or "no benchmark matched"), typical range, markup multiplier, severity |
| **5** | `CLINICAL_VERIFICATION` | Usable guideline passages and claim text | **Raw model assessment**: original verdict (`supported`, `partially_supported`, `contradicted`), support score (0.0–1.0), clinical reasoning, conflict assessment |
| **6** | `ABSTENTION_GATE` | 5 deterministic safety rules and raw model assessment | Gate evaluation, rule triggered (if any), pre-gate model verdict, and override status |
| **7** | `FINAL_ACTION` | Clinical support, cost anomaly flag, and abstention outcome | Final operational action (`ACCEPT`, `FLAG`, `ABSTAIN`), `policy_override_applied` flag, and explicit override rationale |

> **Dual Retention of Model Assessment & Policy Overrides:**
> When safety policy overrides the raw model verdict (e.g., model deemed a claim "supported" but extreme billing markups forced `FLAG`, or unbenchmarked high cost forced `ABSTAIN`), **both the original model assessment and the final policy override are retained**. Reviewers can see exactly what the model concluded and why policy intervened.

**Response Preview:**
```json
{
  "success": true,
  "audit_trail": {
    "audit_id": "aud_7b819a00e54d3129",
    "claim_id": "clm_8f2b4e19c0a34b92",
    "verification_id": "ver_41c0e39a2b1f4812",
    "raw_model_verdict": "supported",
    "raw_model_support_score": 0.88,
    "policy_override_applied": true,
    "policy_override_reason": "Cost anomaly detected (16.0× benchmark max) forced action to FLAG despite model verdict 'supported'.",
    "steps": [
      {
        "step_name": "EXTRACTION",
        "input_summary": "Raw source text (84 chars, origin: hospital_bill)",
        "output_summary": "Extracted Entity='0.9% Sodium Chloride Normal Saline 1,000 mL', Cost='$720.00', Outcome='None', Location='Cleveland', Confidence=0.94",
        "details": {
          "entity": "0.9% Sodium Chloride Normal Saline 1,000 mL",
          "cost_range": "$720.00",
          "confidence": 0.94
        }
      },
      {
        "step_name": "PROVENANCE",
        "input_summary": "Raw text verification against SHA-256 cryptographic digest",
        "output_summary": "Cryptographic digest=e3b0c44298fc1c14... (verified), Snippet='MIDWEST GENERAL HOSPITAL...', SourceURL=unspecified",
        "details": {
          "source_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "tamper_check_passed": true
        }
      },
      {
        "step_name": "HYBRID_RETRIEVAL",
        "input_summary": "Query: entity='0.9% Sodium Chloride Normal Saline 1,000 mL', text excerpt (84 chars)",
        "output_summary": "Retrieved 5 candidate guidelines (1 usable above 0.35 threshold, 4 discarded). Top score=0.88",
        "details": {
          "total_retrieved": 5,
          "used_count": 1,
          "discarded_count": 4,
          "relevance_threshold": 0.35
        }
      },
      {
        "step_name": "COST_AUDIT",
        "input_summary": "Claim cost='$720.00' for entity='0.9% Sodium Chloride Normal Saline 1,000 mL'",
        "output_summary": "Benchmark='0.9% Sodium Chloride (Normal Saline) IV Solution' ($5.00 - $45.00). Billed=$720.00 (16.0× max, Anomaly=True, Severity=EXTREME).",
        "details": {
          "benchmark_matched": true,
          "benchmark_name": "0.9% Sodium Chloride (Normal Saline) IV Solution",
          "cpt_code": "J7030",
          "extracted_amount": 720.0,
          "multiplier": 16.0,
          "is_anomaly": true,
          "severity": "extreme"
        }
      },
      {
        "step_name": "CLINICAL_VERIFICATION",
        "input_summary": "Ollama judgment on 1 usable authoritative guidelines",
        "output_summary": "Model Verdict=supported, SupportScore=0.88, ConflictDetected=False. Reasoning: 'Normal saline is standard for IV hydration...'",
        "details": {
          "raw_model_verdict": "supported",
          "raw_model_support_score": 0.88,
          "conflict_assessment": null
        }
      },
      {
        "step_name": "ABSTENTION_GATE",
        "input_summary": "Evaluating 5 deterministic safety rules against claim and model verdict 'supported'",
        "output_summary": "PASSED: All 5 safety gates cleared (valid entity, relevant evidence, no unresolvable conflict, confidence floor met, cost benchmark valid).",
        "details": {
          "should_abstain": false,
          "policy_override_applied": false
        }
      },
      {
        "step_name": "FINAL_ACTION",
        "input_summary": "Synthesizing raw model verdict='supported', cost_anomaly=True, abstention=False",
        "output_summary": "Action=FLAG (Verdict=supported). Policy override: Flagged due to cost anomaly (16.0× markup) despite model verdict 'supported'.",
        "details": {
          "final_action": "flag",
          "final_verdict": "supported",
          "raw_model_verdict": "supported",
          "policy_override_applied": true,
          "policy_override_reason": "Cost anomaly detected (16.0× benchmark max) forced action to FLAG despite model verdict 'supported'."
        }
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
    "final_verdict": "supported",
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

## 🎯 Clinical Knowledge Base Expansion & Controlled Evaluation (Step 3)

### 1. Expanded Knowledge Base Coverage
To prevent over-abstention on routine healthcare encounters while strictly preserving safety gates, the local knowledge base was expanded with authoritative clinical guidelines and public pricing benchmarks:
- **MRI Brain without Contrast (CPT 70551)**: Guidelines from the American College of Radiology (ACR) & American Academy of Neurology (AAN), establishing clear indications (persistent headache with red flags, focal neurological deficits, new-onset seizures) and explicit exclusions (routine uncomplicated tension headache). CMS/Fair Health benchmark ($450–$1,400).
- **Routine Venipuncture (CPT 36415)**: Clinical & Laboratory Standards Institute (CLSI) & CMS Laboratory Manual guideline for diagnostic blood draw collections, paired with CMS CLFS benchmark ($5–$25).
- **Chest Radiography 2 Views (CPT 71046)**: ACR Thoracic Imaging guidelines for acute respiratory symptoms (dyspnea, fever, cough, chest pain), paired with CMS MPFS benchmark ($40–$190).
- **Complete Blood Count with Differential (CPT 85025)**: CAP & AACC guidelines for diagnostic hematology and infection monitoring, paired with CMS CLFS benchmark ($10–$45).

### 2. Anatomical Site & Procedure Code Retrieval Safeguards
Retrieval matching was hardened to prevent false cross-procedure matches (such as retrieving knee MRI guidelines when auditing a brain MRI claim):
- **Anatomical Region Partitioning**: Automatically tracks anatomical domains (`brain`, `knee`, `chest`, `abdomen`, `spine`). Candidate guidelines addressing a conflicting anatomical region without mentioning the queried region are explicitly penalized and labeled as discarded (`discard_reason: Anatomical mismatch`).
- **Exact CPT Code Disambiguation**: Queries with 5-digit CPT codes (e.g., `70551`) receive heavy anchor boosts for matching guidelines, while candidate guidelines with conflicting CPT codes (e.g., `73721`) are labeled as discarded.
- **Minimum Ceiling Normalization**: Prevents low-scoring noise (such as a single generic word match) from being normalized to `1.0`.

### 3. Controlled Evaluation Set (`data/evaluation/controlled_cases.json`)
A labeled ground-truth set of 8 controlled test cases exercises every major verdict and action pathway:
1. `ctrl_01_supported_metformin`: First-line T2D oral therapy at normal cost → **SUPPORTED / ACCEPT**
2. `ctrl_02_supported_brain_mri`: CPT 70551 with focal red flags at $650 → **SUPPORTED / ACCEPT**
3. `ctrl_03_contradicted_bronchitis_antibiotic`: Azithromycin for acute viral bronchitis → **CONTRADICTED / FLAG**
4. `ctrl_04_cost_anomaly_saline_extreme`: 0.9% Normal Saline billed at $720 (16.0× markup) → **SUPPORTED (model) / FLAG (policy override)**
5. `ctrl_05_cost_anomaly_venipuncture`: CPT 36415 billed at $125 (5.0× markup) → **SUPPORTED (model) / FLAG (policy override)**
6. `ctrl_06_abstain_rare_unsupported_entity`: Intravenous ozone infusion (no evidence in KB) → **INSUFFICIENT_EVIDENCE / ABSTAIN (Rule 2)**
7. `ctrl_07_abstain_unbenchmarked_high_cost`: Experimental robotic spine laser ablation billed at $12,500 → **INSUFFICIENT_EVIDENCE / ABSTAIN (Rule 5)**
8. `ctrl_08_supported_lisinopril_normal_cost`: Essential hypertension Lisinopril therapy at $12 → **SUPPORTED / ACCEPT**

---

## 💰 Pricing-Anomaly Engine & Benchmark Auditing (Step 4)

### 1. Benchmark Matching Hierarchy
EvidenceBridge matches billed hospital line items and clinical notes against public CMS, Fair Health, and NADAC price benchmarks using a deterministic three-tier hierarchy:
1. **Target Entity Code Match (Highest Priority)**: Matches exact 5-digit CPT (e.g. `70551`, `99285`) or HCPCS codes (e.g. `J7030`, `J0585`) extracted in the entity string. This prevents other procedures mentioned in multi-line bill backgrounds from overriding the target service.
2. **Context Code Alignment**: When the entity string lacks a code, matches codes found in document text if the candidate benchmark shares procedure keywords with the entity.
3. **Keyword Scoring & Anatomical Validation**: Compares entity words and benchmark keywords while enforcing strict anatomical compatibility (`brain`, `knee`, `chest`, `abdomen`, `spine`). Mismatched body parts (e.g., knee MRI vs brain MRI) are rejected.

### 2. Multiplier Thresholds & Severity Tiers
Billed amounts are evaluated against the benchmark's typical range (`typical_min` to `typical_max`):
$$\text{markup\_multiplier} = \frac{\text{billed\_amount}}{\text{typical\_max}}$$

| Markup Multiplier | Anomaly Flag | Severity Tier | Example | Operational Effect |
|---|---|---|---|---|
| $< 3.0\times$ | `false` | `none` | Brain MRI at $650 (0.46× max) | Action determined by clinical support (e.g., `ACCEPT`) |
| $3.0\times \le M < 5.0\times$ | `true` | `moderate` | CMP at $340 (4.0× max) | Policy override forces action to `FLAG` |
| $5.0\times \le M < 10.0\times$ | `true` | `severe` | Venipuncture at $125 (5.0× max) | Policy override forces action to `FLAG` |
| $\ge 10.0\times$ | `true` | `extreme` | Normal Saline at $720 (16.0× max) | Policy override forces action to `FLAG` |

### 3. What "No Benchmark Matched" Means for Reviewers
- **Explicit Telemetry**: When an extracted procedure has no entry in `price_benchmarks.json`, `CostAnomalyDetails` records `benchmark_matched: false`, `benchmark_name: null`, and explanation: `"No public pricing benchmark found for entity '...'. Auditing deferred."`
- **Audit Lineage**: The `COST_AUDIT` step in the 7-stage decision graph explicitly flags `benchmark_matched: false` and `benchmark_name: "no benchmark matched"`.
- **Safety Gate Safeguard (Rule 5)**: If the unbenchmarked charge exceeds **$100.00**, deterministic safety gate Rule 5 (`UNBENCHMARKED_HIGH_COST`) prevents the system from blindly issuing an automated `ACCEPT` action. Instead, the system safely **ABSTAINS** until human review or benchmark grounding is provided.

---

## 🧪 Automated Test Suite

Run all 152 unit and integration tests:
```bash
pytest backend/tests -v
```

Tests cover:
- ✅ **Visual Insights & Dashboard API**: Aggregation endpoint (`GET /insights/summary`), decision distributions, price markup tier breakdowns, guideline compliance counts, systemic gaps & risks, top procedures, and baseline fallback
- ✅ **Community Stories API & Storage**: Endpoints (`GET /stories`, `POST /stories`, `GET /stories/{id}`), character limits, validation, voluntary contact sanitization, MongoDB and in-memory fallback persistence
- ✅ **Evaluation Harness & Calibration (Layer 6)**: Statistical classification metrics (precision, recall, macro F1), cost anomaly detection metrics, abstention gate safety tracking (over/under-abstention), reliability calibration with Expected Calibration Error (ECE), Markdown summary generation, and `/evaluate` endpoints
- ✅ **Cost Anomaly Engine Hardening**: Extended numeric parsing (currencies, prefixes, suffixes, decimals), exact CPT priority matching, anatomical validation, and full coverage of moderate/severe/extreme severity tiers
- ✅ **Controlled Evaluation Cases**: End-to-end verification of all 8 control cases across major verdict paths
- ✅ **Schemas**: Complete validation of Claim, VerificationResult, AuditTrail, CostAnomalyDetails, LocationInfo, TrustDensityMetrics, EvaluationReport, CommunityStory, and InsightsSummaryResponse models
- ✅ **Provenance**: SHA-256 cryptographic digests & tamper detection
- ✅ **Extraction**: Ollama structured JSON parsing & markdown stripping
- ✅ **Hybrid Retrieval Quality**: BM25 + Vector ranking, entity anchoring, anatomical & CPT disambiguation, used vs discarded passage labeling
- ✅ **Abstention Policy Gates**: Deterministic enforcement of all 5 safety rules (missing entity, no evidence, conflicting guidelines, low confidence, unbenchmarked high cost)
- ✅ **Decision Audit Trail**: Full 7-stage decision graph recording, dual retention of model assessment & policy overrides
- ✅ **Location Extraction**: City/state regex extraction, normalization, stop-word filtering, prominent-city fallback
- ✅ **Trust Density Math**: Support ratio (with partial credit), anomaly rate, time-decay recency weighting, tier assignment
- ✅ **Trust Density Edge Cases**: Zero claims, single claim, all-abstained, no verifications
- ✅ **Hand-Calculated Mathematical Hardening (Step 5)**: Synthetic 4-claim ground truth test, exact exponential decay math (45d decay constant), sparse all-abstained low-tier narrative assertions, zero/single claim boundaries
- ✅ **FastAPI Endpoints**: All endpoints including `/extract-and-verify`, `/audit/{id}`, `/stories`, `/insights/summary`, `/evaluate`, `/trust-density/{key}`, `/trust-density`, `/claims?location=...`


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

#### Metric Definitions & Mathematical Formulas

EvidenceBridge calculates trust density using four deterministic components:

1. **Audited (Verified) Claims (`verified_claims`)**:
   Total claims for a locality that have completed the verification audit pipeline (evaluated against clinical guidelines and pricing benchmarks). Every audited claim receives a triage action (`ACCEPT`, `FLAG`, or `ABSTAIN`).
   > *Note:* "Verified" means pipeline-audited, not necessarily clinically confirmed.

2. **Conclusive Support Ratio (`support_ratio`)**:
   Measures clinical guideline agreement among conclusive audits:
   $$\text{support\_ratio} = \begin{cases} \frac{\text{supported} + 0.5 \times \text{partially\_supported}}{\text{conclusive\_audits}}, & \text{if } \text{conclusive\_audits} > 0 \\ 0.0, & \text{if } \text{conclusive\_audits} = 0 \end{cases}$$
   where:
   $$\text{conclusive\_audits} = \text{supported} + \text{partially\_supported} + \text{contradicted}$$
   - **Exclusion of Abstentions**: Abstained claims (`INSUFFICIENT_EVIDENCE` / `ABSTAIN`) are excluded from the denominator. Lack of guideline coverage in the local knowledge base is unestablished evidence, not clinical contradiction.
   - **Zero Conclusive Floor**: If zero conclusive evaluations exist (e.g. all claims were abstained), the support ratio evaluates strictly to `0.0` (0%).

3. **Cost Anomaly Rate (`cost_anomaly_rate`)**:
   $$\text{cost\_anomaly\_rate} = \begin{cases} \frac{\text{cost\_anomaly\_count}}{\text{verified\_claims}}, & \text{if } \text{verified\_claims} > 0 \\ 0.0, & \text{if } \text{verified\_claims} = 0 \end{cases}$$
   Evaluates to `0.0` (0%) when no anomalies are detected. Locality narrative summaries report `"zero detected billing anomalies"` when the rate is 0.0%, rather than asserting anomalies exist.

4. **Recency-Weighted Volume (`recency_volume`)**:
   Accounts for temporal relevance by applying continuous exponential decay to claim ages:
   $$\Delta t_i = \frac{\max(0, (t_{\text{now}} - t_i).\text{total\_seconds}())}{86400.0} \quad \text{(fractional days)}$$
   $$w_i = \exp\left(-\frac{\Delta t_i}{\tau}\right)$$
   $$\text{recency\_volume} = \sum_{i=1}^{N} w_i$$
   $$\text{volume\_factor} = \min\left(1.0, \frac{\text{recency\_volume}}{\text{MIN\_VOLUME}}\right)$$
   - **Decay Constant $\tau$**: Configurable via `TRUST_DENSITY_TIME_DECAY_DAYS` (default `45.0` days). At $45$ days, a claim's weight decays to $1/e \approx 0.368$.
   - **Half-Life $t_{1/2}$**:
     $$t_{1/2} = \tau \ln(2) \approx 45.0 \times 0.69315 \approx 31.19 \text{ days}$$
   - **Minimum Volume Threshold**: Configurable via `TRUST_DENSITY_MIN_VOLUME` (default `5` claims). Future timestamps are clamped to $\Delta t_i \ge 0$ ($w_i = 1.0$), preventing score explosions or negative weights.

5. **Composite Trust Density Score (`density_score`)**:
   $$\text{raw\_density} = w_{\text{support}} \times \text{support\_ratio} + w_{\text{anomaly}} \times (1.0 - \text{cost\_anomaly\_rate}) + w_{\text{volume}} \times \text{volume\_factor}$$
   $$\text{density\_score} = \begin{cases} 0.0, & \text{if } \text{verified\_claims} = 0 \\ \text{round}\left(\text{clamp}_{[0, 1]}(\text{raw\_density}), 4\right), & \text{otherwise} \end{cases}$$
   - Default weights: $w_{\text{support}} = 0.45$, $w_{\text{anomaly}} = 0.35$, $w_{\text{volume}} = 0.20$.
   - If zero claims have been audited (`verified_claims == 0`), `density_score` is strictly `0.0`.

#### Categorical Trust Tiers & Threshold Boundaries

| Tier | Evaluation Condition | Meaning | Operational Action |
|---|---|---|---|
| `insufficient_data` | `verified_claims < 2` | Sample size too small to draw conclusive inference | Require additional claim audits before applying rules |
| `critical_alert` | `(cost_anomaly_rate >= 0.50 and cost_anomaly_count >= 2)` OR `(density_score < 0.30 and flagged_count >= 2)` | Systematic billing fraud or severe clinical non-compliance | Prior authorization and mandatory line-item itemization |
| `high` | `density_score >= 0.75` | High clinical guideline compliance and fair pricing | Eligible for expedited automated adjudication |
| `moderate` | `0.50 <= density_score < 0.75` | Generally compliant; stable guidelines or occasional anomalies | Standard automated verification with spot audits on outliers |
| `low` | `density_score < 0.50` | Low score due to contradictions, anomalies, or unrepresented baseline | Secondary clinical necessity and price-benchmark review |

#### Small-Sample & Sparse-Data Transparency (Step 5 Hardening)

In real-world healthcare audits, small metropolitan samples can easily distort statistical trust metrics if not properly contextualized:

1. **Preliminary Labeling for Sparse Samples ($2 \le \text{verified\_claims} < 5$)**:
   - The UI and API narratives explicitly prefix assessments with `PRELIMINARY ASSESSMENT (N audited claims):`.
   - The frontend renders an inline `Preliminary (Sparse Data)` badge to prevent premature policy enforcement.
2. **Unrepresented Guidelines vs. Confirmed Provider Risk**:
   - When all audited claims in a locality are abstained due to unrepresented guidelines (`eval_conclusive == 0`) and zero billing anomalies are detected (`cost_anomaly_count == 0`), the locality is labeled **`UNRESOLVED BASELINE`** (or `MODERATE TRUST` depending on volume), **never `ELEVATED RISK`**.
   - The narrative explicitly reports: *"Clinical guideline adherence is inconclusive (N claim(s) abstained due to unrepresented clinical guidelines). Zero detected billing anomalies across N audited claims. Low score reflects lack of guideline coverage rather than confirmed non-compliance."*
   - Recommendation directs auditors to expand guideline coverage rather than penalizing healthcare providers.
3. **Empty & Single-Claim Safety**:
   - 0 claims: `density_score = 0.0`, `trust_tier = INSUFFICIENT_DATA`, summary reports *"zero recorded claims"*.
   - 1 claim: `trust_tier = INSUFFICIENT_DATA`, summary reports *"minimum 2 verified claims required"*.

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

## 🖥️ Layer 5: Elevated Frontend & Healthcare Audit Workspace

EvidenceBridge includes an elevated, local-first web UI inspired by clean, professional healthcare platforms (WebMD / Epic / Athenahealth) built with **React 18 + Vite + TypeScript + Tailwind CSS**. It features a modern patient/auditor landing page, lightweight local authentication with 1-click demo login, and user-facing plain-English language designed for healthcare professionals, auditors, and patients.

### Key Views & Capabilities

- **Healthcare Landing Page (`/` when unauthenticated or `/welcome`)**:
  - Clear plain-English value proposition ("Audit hospital bills & medical claims with total transparency").
  - Live interactive dual-decision comparison card (e.g. Normal Saline 1,000 mL at $720 billed vs $5–$45 benchmark showing both guideline support and financial markup flag).
  - 3 Core Pillars: "See Why a Claim Was Decided", "Spot Hidden Price Markups", and "Safe Refusals — We Never Guess".
  - 3-Step verification roadmap and 4 controlled scenario quick-cards (Routine Metformin, Brain MRI w/o contrast, Saline overcharge, Bronchitis antibiotics).
- **Lightweight Auditor Authentication**:
  - Supports email/username + password login and sign-up with persistent `localStorage` session state.
  - **1-Click Demo Auditor**: Instantly logs in as *Vasavi (Clinical Claims Reviewer)* with zero configuration.
  - Header profile pill displaying active reviewer name, avatar initials, role, and sign-out action.
- **Audit & Extraction Workspace (`/audit`)**:
  - Stepped 3-phase workflow: 1. Input Clinical Note / Bill Line, 2. Review Extracted Information, 3. View Decision & Evidence.
  - One-click realistic clinical presets (Normal Saline $720 Overcharge, Routine Metformin $15, Brain MRI $650, Bronchitis Antibiotics $24, Experimental Unbenchmarked Therapy $45,000).
  - High-contrast visual decision banners (`Approved`, `Flagged for Review`, `Held for Information`).
  - Pricing benchmark comparison bar visually contrasting standard ranges against extreme markups.
- **Claims Explorer (`/claims`)**:
  - Searchable claims browser with instant filter pills (`All Claims`, `Approved`, `Flagged for Review`, `Held for Information`).
  - Dedicated "Price Alerts Only" toggle and live search by procedure name, CPT code, or metropolitan city.
- **Claim Detail & 7-Stage Audit Graph (`/claims/:claimId`)**:
  - Clinical timeline checklist featuring plain-English stage names:
    1. *Reading Document (Extraction)*
    2. *Verifying Authenticity (Provenance Fingerprint)*
    3. *Finding Medical Guidelines (Hybrid Search)*
    4. *Checking Regional Prices (Pricing Audit)*
    5. *Clinical Review (Guideline Verification)*
    6. *Safety Gate (Abstention Safeguards)*
    7. *Final Decision (Action & Rationale)*
  - Expandable stage inspectors, Document Authenticity Fingerprint (SHA-256) copy tool, and full clinical guideline citation cards with relevance scores and discard explanations.
  - **Single-Claim Visual Summary**: Visual indicators directly above the source text rendering Extraction Confidence (0–100%), Guideline Match / Support Score (0–100%), and Cost Markup Level (color-coded gauge contrasting billed charge against CMS ceiling).
- **Visual Insights & Statistics Dashboard (`/insights` or `/dashboard`)**:
  - Interactive graphical analytics powered by Recharts translating complex auditing findings into plain English:
    - *Triage Decision Distribution*: Donut breakdown comparing Approved vs. Flagged for Review vs. Held by Safety Gates.
    - *Price Anomaly & Severity Breakdown*: Bar chart quantifying Normal Charges, Moderate Markups (3×–5×), Severe Markups (5×–10×), and Extreme Markups (≥10×).
    - *Clinical Evidence Support Breakdown*: Distribution of Supported, Partially Supported, Contradicted, and Insufficient Evidence verdicts.
    - *Systemic Risks & Coverage Gaps*: 4 high-priority indicator cards tracking insufficient evidence cases, extreme markups, safety rule holds, and unbenchmarked high-cost procedures.
    - *Procedure & Regional Frequency*: Ranked breakdown of top audited procedures and metropolitan pricing anomaly rankings.
    - *Notable Risk Claims*: Highlight cards for quick inspection of flagged or held claims with 1-click drill-down into the 7-stage audit graph.
- **Regional Hospital Reliability Score (`/trust-density`)**:
  - Metropolitan trust dashboard explaining: *"How reliable are billing and clinical practices in this area?"*
  - Plain-English metric cards: Total Audited Claims, Guideline Compliance Rate, Price Anomaly Rate, and Time-Decayed Activity Volume.
  - Trust level indicators: `High Trust`, `Moderate Trust`, `Needs Scrutiny`, `Critical Alert`, and `Insufficient Data`.
- **Evaluation & Calibration Harness (`/evaluation`)**:
  - Interactive evaluation dashboard with live execution progress across the 8 gold-standard benchmark cases.
  - Plain-English diagnostic cards: Clinical Verdict Accuracy, Action Alignment, Financial Markup Detection, Safety Abstention Rate, and Expected Calibration Error (ECE).
  - Formatted Markdown report export with 1-click clipboard copy.

- **Community Stories / Recovery Journeys (`/community`)**:
  - Supportive peer space where individuals voluntarily share personal experiences of illness, coping mechanisms, and recovery journeys.
  - **Zero Medical Advice / Safety Guarantee**: Completely isolated from the clinical claims auditing engine. No automated diagnoses, clinical claims, or treatment advice are permitted.
  - **Permanent Medical Disclaimer**: Stated prominently on every view:
    > *"These are personal stories shared by individuals. They are not medical advice, diagnosis, or treatment recommendations. Always consult qualified healthcare professionals for medical decisions."*
  - **Voluntary Public Contact Sharing**: Users can optionally provide their email or Instagram handle (with explicit consent checkboxes) so peers can reach out directly.
  - **Topic Filtering & Search**: Clean filter pills (*Type 2 Diabetes*, *Chronic Migraines*, *Medical Debt & Billing*, *Physical Rehab*, *Mental Health*) and live keyword search.
  - **Resilient Offline Architecture**: Backed by MongoDB with in-memory pre-seeded stories fallback, ensuring 100% cost-free, zero-downtime operation.

- **AI Voice Assistant (English & Kannada / ಕನ್ನಡ)**:
  - 100% cost-free, browser-based voice assistant built with native Web Speech API (`SpeechRecognition` + `SpeechSynthesis`) and local Ollama.
  - Floating microphone trigger in bottom-right (available after login).
  - Voice navigation commands ("Go to home", "Go to claims", "Insights", "Regional trust", "Evaluation", "Community stories", "Log out").
  - Document-aware Q&A when inspecting claims ("Read this result", "Why was this flagged?", "What is the price problem?", "Explain this claim").
  - Dedicated "🔊 Read Result Aloud" button on both Audit and Claim Detail pages.
  - Kannada support (`kn-IN`) for voice commands and spoken explanations with client-side clinical synthesis fallback.
  - Live transcript, visual waveform, and command history log.

### Plain-English Healthcare Terminology

| Technical Pipeline Term | Plain-English UI Translation |
|---|---|
| `ACCEPT` | **Approved (Matches Clinical Guidelines)** |
| `FLAG` | **Flagged for Review (Potential Issue Detected)** |
| `ABSTAIN` | **Held for Information (Safe Policy Refusal)** |
| `Cost Anomaly` | **Price Alert / Unusually High Charge** |
| `Support Score` | **Guideline Match Confidence** |
| `Hyperlocal Trust Density` | **Regional Hospital Reliability Score** |
| `Provenance SHA-256` | **Document Authenticity Fingerprint** |
| `Abstention Gate` | **Safety Gate / Safeguards Check** |

---

## 🔐 User Authentication, Personal Memory & Cloud Deployment

EvidenceBridge includes a production-grade authentication and personal memory architecture designed for secure cloud deployment (e.g. MongoDB Atlas) while maintaining 100% offline portability.

### Architecture Highlights
- **Persistent User Accounts**: User credentials and profile metadata are stored in the MongoDB `users` collection.
- **Cryptographic Password Hashing**: Passwords are one-way hashed using `bcrypt` with salt rounds prior to persistence.
- **Stateless Bearer JWT Tokens**: Signed JSON Web Tokens (`HS256`) enable secure, stateless authorization headers (`Authorization: Bearer <token>`) across all API interactions.
- **Personal Memory & Data Isolation**:
  - Newly registered auditor accounts receive a clean, isolated personal memory workspace.
  - Audited claims, submitted Community Stories, and evaluation executions are attributed to the user's `user_id`.
  - Claims explorer, personal audit logs, and insight metrics reflect each user's unique audit history without cross-tenant leakage.
- **Instant Demo Reviewer Access**:
  - The built-in Demo Auditor session (*Vasavi, Clinical Claims Reviewer*) is pre-seeded with baseline demonstration claims, benchmark datasets, and regional records for instant evaluation.
- **Zero-Config Offline Fallback**:
  - When running without a live database or during CI unit testing, an in-memory cache preserves authentication state and test users seamlessly.

### MongoDB Atlas Deployment & Security Configuration

EvidenceBridge supports connecting directly to a managed MongoDB Atlas cluster in production.

1. In MongoDB Atlas, configure your cluster and database user credentials.
2. In your deployment environment (or `.env` file), configure `MONGODB_URI`:

```env
# MongoDB Atlas Connection String (Placeholder example — never commit actual secrets):
MONGODB_URI=mongodb+srv://USER:PASS@cluster.mongodb.net/evidencebridge

# JWT Session Configuration
AUTH_SECRET_KEY=generate-a-strong-random-secret-key-32-characters
AUTH_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Production CORS Origin Security
APP_ENV=production
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://app.your-frontend-domain.com
```

### Production CORS & Cross-Origin Security

EvidenceBridge enforces explicit origin whitelisting when credentials (Bearer JWT tokens) are enabled, complying strictly with W3C Cross-Origin Resource Sharing specifications.

- **Local Development (`APP_ENV=development`)**: Automatically authorizes local development servers (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`).
- **Production (`APP_ENV=production`)**: Only permits explicitly listed frontend origins configured in `ALLOWED_ORIGINS`. Never uses wildcard (`*`) when credentials are enabled, preventing unauthorized cross-origin data exposure.

### Frontend Production Deployment & API Base URL Configuration

When deploying the React/Vite frontend to a decoupled hosting platform (e.g. Netlify, Vercel, Render, Cloudflare Pages, AWS S3/CloudFront):

1. **Configure Backend Endpoint**: Set the environment variable `VITE_API_BASE_URL` in your hosting dashboard:
   ```env
   # Format: https://<your-backend-host>/api/v1 (no trailing slash)
   VITE_API_BASE_URL=https://api.evidencebridge.org/api/v1
   ```
   If omitted or left empty, the application defaults to `/api/v1`, using Vite's local dev reverse proxy to target `http://localhost:8000`.

2. **Optional Hosted Ollama Endpoint**: To use an external or hosted Ollama service for AI voice synthesis explanations:
   ```env
   VITE_OLLAMA_BASE_URL=https://ollama.evidencebridge.org
   ```
   If unset, the voice assistant operates with high-quality deterministic natural language synthesis in both English and Kannada, avoiding browser mixed-content blocks.

3. **SPA Client-Side Routing Fallback**: EvidenceBridge includes out-of-the-box routing fallback configurations so page refreshes and direct links (e.g. `/audit`, `/claims`, `/hospitals`, `/insights`) resolve properly:
   - **Netlify**: Handled automatically via `frontend/public/_redirects` (`/*  /index.html  200`).
   - **Vercel**: Configured via `frontend/vercel.json` rewrites.

4. **Production Build**:
   ```bash
   cd frontend
   npm run build
   ```
   The compiled static assets will be output to `frontend/dist/`.

> [!CAUTION]
> **Strict Secret Protection**: Never commit actual database connection strings, passwords, or authentication keys to source control or logs. EvidenceBridge automatically masks and sanitizes database connection logging to guarantee credentials are never exposed in terminal outputs or diagnostic traces.

### Auth API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/signup` | Register a new auditor account (Name, Email, Password, optional Organization) |
| `POST` | `/auth/login` | Authenticate with email and password to receive a signed JWT token |
| `POST` | `/auth/demo` | 1-Click instant sign-in as Vasavi (Demo Auditor) |
| `GET` | `/auth/me` | Inspect the currently authenticated auditor profile and session validity |

---

## 📊 Layer 6: Evaluation Harness, Basic Metrics & Abstention Calibration

EvidenceBridge includes an automated evaluation harness capable of measuring its own reliability across clinical verdict accuracy, triage action alignment, financial markup detection, and abstention gate safety calibration.

### Core Metrics

1. **Clinical Verdict Classification**:
   - Evaluated across classes: `supported`, `partially_supported`, `contradicted`, `insufficient_evidence`.
   - Computes per-class Precision, Recall, F1 score, support counts, Overall Verdict Accuracy, and Macro F1.
2. **Decision Action Alignment**:
   - Evaluated across actions: `ACCEPT`, `FLAG`, `ABSTAIN`.
   - Computes per-action Precision, Recall, F1 score, Overall Action Accuracy, and Macro F1.
3. **Cost Anomaly Detection**:
   - Binary detection performance: Precision, Recall, F1 score, True/False Positives, and True/False Negatives.
4. **Abstention Gate Safety & Calibration**:
   - Total abstention rate ($N_{\text{abstained}} / N$).
   - **Correct Abstentions (True Positives)**: Safety gate properly intervened on unsupported or unbenchmarked claims.
   - **Over-Abstentions (False Positives)**: System refused judgment on a valid claim (signals need to expand local clinical guidelines).
   - **Under-Abstentions (False Negatives)**: System produced a conclusive judgment on a claim lacking evidence (critical safety defect).
   - Abstention Precision, Recall, and F1.
5. **Support Score Reliability Calibration (ECE)**:
   - Evaluates whether model support scores reflect empirical accuracy.
   - Divides support scores into 5 equal-width confidence bins ($[0.0, 0.2), [0.2, 0.4), \dots$).
   - Computes Expected Calibration Error:
     $$\text{ECE} = \sum_{b=1}^M \frac{|B_b|}{N} |\text{empirical\_accuracy}_b - \text{avg\_confidence}_b|$$

### Evaluation CLI Runner

Run the offline-capable evaluation harness from terminal:
```bash
# Run evaluation across controlled clinical cases (deterministic offline mode)
python scripts/run_evaluation.py --offline

# Run evaluation with live Ollama model
python scripts/run_evaluation.py

# Save Markdown and JSON evaluation reports
python scripts/run_evaluation.py --offline --save-md evaluation_report.md --save-json evaluation_report.json
```

### Evaluation API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/evaluate` | Run evaluation over benchmark cases (supports `offline_mode`, `case_ids`, `dataset_path`) |
| `GET` | `/evaluate/{run_id}` | Retrieve a historical evaluation report with full metrics & Markdown summary |
| `GET` | `/evaluate` | List recent evaluation runs stored in MongoDB |

### Example cURL
```bash
# Trigger an evaluation run in offline mode
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"offline_mode": true}'

# Fetch specific evaluation report
curl http://localhost:8000/evaluate/eval_5a5f487fa149
```

---

## ⚠️ Safety, Clinical Grounding & Legal Disclaimers

> [!CAUTION]
> **PLEASE READ BEFORE USING THIS SYSTEM**

1. **Auditor Decision Support Only (Not Clinical Advice)**:
   EvidenceBridge is a research and claims-auditing tool created to assist healthcare reviewers, compliance teams, and patients in inspecting billed medical claims and verifying itemized statements against established literature. It **does NOT dispense medical advice, provide medical diagnoses, or prescribe treatments**. Never use EvidenceBridge as a replacement for consultation with a licensed medical professional.

2. **Ground-Truth Knowledge Base Completeness**:
   The built-in clinical knowledge base contains representative excerpts from authoritative guidelines (e.g., ACR Appropriateness Criteria, ADA Standards of Care, AHA Guidelines, CDC Guidelines, GOLD Report). It is not an exhaustive compendium of all medical knowledge. When authoritative evidence is absent, the system's deterministic safety gates will trigger a policy **ABSTENTION** to prevent hallucinated conclusions.

3. **Pricing Benchmark Limitations**:
   Price benchmarks are synthesized from public datasets including CMS Hospital Price Transparency, Fair Health charge percentiles, and NADAC drug acquisition costs. Actual negotiated hospital rates, commercial insurance contracts, in-network/out-of-network status, and local variations may differ. Pricing anomaly flags denote statistical variance exceeding benchmark thresholds, not definitive proof of billing fraud or legal non-compliance.

4. **Community Stories Section Strict Disclaimer**:
   The Community Recovery Stories section represents voluntary, peer-shared personal experiences of navigating illness and coping mechanisms. **Stories shared are strictly non-clinical personal narratives and must never be interpreted as clinical protocols, drug efficacy claims, or medical guidance.** Readers must consult their physician before changing any treatment or therapy.

5. **Privacy, Security & Offline Operation**:
   EvidenceBridge is designed as a local-first system. All text extraction, provenance hashing, hybrid retrieval, vector search, pricing anomaly detection, LLM judgment, and speech processing can operate entirely on local infrastructure with **zero Protected Health Information (PHI) transmitted to external commercial AI APIs**.

---

## 🗺️ Roadmap & Completed Layers

- [x] **Layer 1:** Local Ingestion, Ollama structured extraction, tamper-evident SHA-256 provenance, MongoDB storage with in-memory fallback.
- [x] **Layer 2:** Claim Verification, Support Scoring (0.0–1.0), Decision Triad (ACCEPT, FLAG, ABSTAIN), and Multi-Tier Cost Anomaly Detection against public CMS/Fair Health benchmarks.
- [x] **Layer 3:** Rigorous 5-Rule Abstention Engine, BM25 + Vector Hybrid Retrieval Ranking, and Full 7-Stage Decision Audit Graph.
- [x] **Layer 4:** Hyperlocal Trust Density — geographic claim aggregation, recency-weighted density scoring, human-auditable location insights, and `/trust-density` endpoints.
- [x] **Layer 5:** Modern Healthcare Web UI — React 18 + Vite 5 + TypeScript + Tailwind CSS with landing page, 1-click demo auditor login, interactive claims explorer, and 7-stage audit graph inspector.
- [x] **Voice AI:** Browser-native AI Voice Assistant supporting English & Kannada (`kn-IN`) navigation and claim Q&A with zero paid cloud APIs.
- [x] **Community:** Supportive Community Recovery Stories section with topic filtering, character limits, voluntary public contact sharing, and permanent safety disclaimers.
- [x] **Layer 6:** Evaluation Harness, Basic Metrics & Abstention Calibration — automated evaluation runner, verdict/action classification metrics, cost anomaly precision/recall/F1, over/under-abstention tracking, binned reliability calibration (ECE), and `/evaluate` endpoints.
- [ ] **Layer 7 (Future):** Enterprise Multi-Tenant RBAC, Distributed EHR Connectors (HL7 FHIR / SMART on FHIR), and Continuous Monitoring Telemetry.


---

## 📄 License
Apache-2.0. Open-source, local-first, privacy-preserving healthcare analytics.
