# EvidenceBridge 🩺🔍
### Evidence-Auditing & Cost-Anomaly Engine for Healthcare Claims & Hospital Bills

> **[!IMPORTANT]**
> **Scope of this Layer (Layer 2):**
> **This layer adds claim verification and basic cost anomaly detection.** Full hyperlocal trust density and advanced evaluation come later.

---

EvidenceBridge is an open-source, local-first engine designed to audit healthcare claims, patient reports, and hospital bills. It provides end-to-end traceability, structured clinical/cost extraction, tamper-evident provenance, guideline-backed claim verification, and pricing anomaly detection without relying on paid external APIs.

---

## 🏗️ Architecture (Layer 1 + Layer 2)

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
       └─────────────▲─────────────┘                 └─────────────┬─────────────┘
                     │                                             │
                     │         ┌───────────────────────────────────┘
                     │         │
                     │         ▼
       ┌─────────────┴───────────────────────────────────────────────────────────┐
       │ Layer 2: Claim Verification & Cost Anomaly Engine                       │
       │                                                                         │
       │ 1. Evidence Retrieval:                                                  │
       │    - Hybrid ChromaDB Vector Search + Keyword Corroboration              │
       │    - Retrieves top-k authoritative medical guideline passages           │
       │                                                                         │
       │ 2. Support Scoring (Ollama LLM):                                        │
       │    - "supported"             (0.70 - 1.00)                              │
       │    - "partially_supported"   (0.40 - 0.69)                              │
       │    - "contradicted"          (0.00 - 0.39)                              │
       │    - "insufficient_evidence" (0.00 - 0.30)                              │
       │                                                                         │
       │ 3. Cost Anomaly Detection:                                              │
       │    - Compares billed price against CMS Medicare / Fair Health max       │
       │    - Flags if price > threshold multiplier (default: 3.0×)              │
       │    - Categorizes severity: Moderate (3×), Severe (5×), Extreme (10×+)   │
       │                                                                         │
       │ 4. Decision Synthesis:                                                  │
       │    - [ACCEPT]  -> Supported evidence + normal cost                      │
       │    - [FLAG]    -> Contradicted, partially supported, or cost anomaly    │
       │    - [ABSTAIN] -> Insufficient evidence in knowledge base               │
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
│   │   │   └── routes.py             # FastAPI routes (/extract, /verify, /extract-and-verify, /health)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py            # Pydantic models (Claim, VerificationResult, CostBenchmark)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── cost_anomaly.py       # Cost anomaly detection service (CMS/NADAC benchmarks)
│   │   │   ├── extraction.py         # Ollama structured JSON extraction pipeline
│   │   │   ├── provenance.py         # SHA-256 hashing & source metadata linkage
│   │   │   ├── storage.py            # Async MongoDB storage service (claims & verifications)
│   │   │   ├── vector_store.py       # Local ChromaDB vector indexing (offline semantic store)
│   │   │   └── verification.py       # Evidence retrieval & LLM support scoring engine
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── logger.py             # Formatted logging utility
│   │   ├── config.py                 # Pydantic Settings & environment config
│   │   └── main.py                   # FastAPI application initialization & lifespan
│   ├── tests/
│   │   ├── conftest.py               # Shared pytest fixtures
│   │   ├── test_api.py               # FastAPI endpoint integration tests
│   │   ├── test_cost_anomaly.py      # Benchmark matching & cost markup multiplier tests
│   │   ├── test_extraction.py        # Extraction parsing and fallback tests
│   │   ├── test_provenance.py        # Cryptographic hashing & tamper-check tests
│   │   ├── test_schemas.py           # Pydantic schema validation tests
│   │   └── test_verification.py      # Support scoring, contradiction, and abstention tests
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

## ⚖️ The Verdict & Action Decision Framework

EvidenceBridge separates clinical truth from billing fairness to form an auditable decision:

### 1. Evidence Verdicts
| Verdict | Support Score | Clinical Interpretation |
| :--- | :---: | :--- |
| **`supported`** | `0.70 – 1.00` | Authoritative guideline directly validates the indication, drug, procedure, and outcome. |
| **`partially_supported`** | `0.40 – 0.69` | Treatment is recognized, but details (outcome, dosage, context) are partially atypical or incomplete. |
| **`contradicted`** | `0.00 – 0.39` | Clinical guideline **explicitly refutes** the claim (e.g., prescribing Azithromycin for viral bronchitis). |
| **`insufficient_evidence`** | `0.00 – 0.30` | No relevant medical guidelines or clinical facts exist in the knowledge base. |

### 2. Action Decisions
- **`ACCEPT`**: Evidence verdict is `supported` (score $\ge 0.70$) AND billed price is within normal benchmark range.
- **`FLAG`**: Triggered when a claim is `contradicted`, `partially_supported`, or contains a **cost anomaly** (> 3.0× benchmark max).
- **`ABSTAIN`**: Triggered when evidence is `insufficient_evidence` (zero matching guidelines in local knowledge base). **Prevents hallucination** by refusing to fabricate a verification judgment.

### 3. Cost Anomaly Severity
Configured by `COST_ANOMALY_THRESHOLD_MULTIPLIER` in `.env` (default: `3.0`):
- **`extreme`**: Billed price $\ge 10.0\times$ benchmark max (e.g., $74/pill for 500mg Tylenol vs $1.00 benchmark, or $720 for normal saline IV vs $45 benchmark).
- **`severe`**: Billed price $\ge 5.0\times$ benchmark max.
- **`moderate`**: Billed price $\ge 3.0\times$ benchmark max (e.g., $4,850 for Level 5 ER visit vs $1,500 benchmark).
- **`none`**: Within typical range or below anomaly threshold.

---

## ⚙️ Quickstart

### Option 1: Docker Compose (Local MongoDB + Backend)

1. **Clone repository:**
   ```bash
   git clone https://github.com/your-username/evidencebridge.git
   cd evidencebridge
   ```

2. **Copy configuration:**
   ```bash
   cp .env.example .env
   ```

3. **Start local Ollama on host and pull default model:**
   ```bash
   ollama serve
   ollama pull phi3:mini
   ```

4. **Launch containers:**
   ```bash
   docker compose up --build
   ```
   API is now live at: `http://localhost:8000` (Swagger Docs: `http://localhost:8000/docs`).

---

### Option 2: Local Python Setup (100% Offline / Local-First)

#### 1. Setup Ollama
On Linux/macOS:
```bash
chmod +x scripts/setup_ollama.sh
./scripts/setup_ollama.sh
```
On Windows (PowerShell):
```powershell
.\scripts\setup_ollama.ps1
```

#### 2. Start Local MongoDB
```bash
docker run -d -p 27017:27017 --name mongo-evidencebridge mongo:7.0
```

#### 3. Setup Python Virtual Environment
```bash
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt
```

#### 4. Configure Environment
```bash
cp .env.example .env
```
Key settings in `.env`:
```env
APP_NAME=EvidenceBridge
PORT=8000
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=evidencebridge
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini
KNOWLEDGE_BASE_DIR=./data/knowledge
COST_ANOMALY_THRESHOLD_MULTIPLIER=3.0
```

#### 5. Launch Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧪 Seeding & Auditing Sample Data

EvidenceBridge includes 13 realistic healthcare records:
- **Clinical Notes**: Diabetes titration (Metformin), hypertension (Lisinopril), pneumonia (Ceftriaxone), and viral bronchitis ([CONTRADICTED: Azithromycin]).
- **Patient Reports**: Ozempic weight loss, knee surgery surprise bills, migraine Botox protocol, and rare unverified tincture ([ABSTAIN]).
- **Hospital Bills**: Inflated ER visit ($6,825), $74 Tylenol pill markup ([EXTREME ANOMALY]), knee MRI facility fees, and $720 Normal Saline bag ([EXTREME ANOMALY]).

### Ingest and verify all samples:
```bash
python scripts/seed_data.py --url http://localhost:8000 --verify
```

---

## 📡 Example API Requests (cURL)

### 1. Ingest, Extract & Verify in One Call (`POST /extract-and-verify`)
Audit an inpatient bill line item with extreme pricing markup:
```bash
curl -X POST http://localhost:8000/extract-and-verify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "MIDWEST GENERAL HOSPITAL: 0.9% Sodium Chloride (Normal Saline) IV Solution, 1,000 mL infusion bag (HCPCS J7030). Quantity Dispensed: 1. Unit Billed Charge: $720.00.",
    "source_type": "hospital_bill",
    "store_claim": true
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
    },
    "provenance": {
      "source_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  },
  "verification": {
    "verdict": "supported",
    "support_score": 0.88,
    "action": "flag",
    "cost_anomaly_flag": true,
    "anomaly_details": {
      "is_anomaly": true,
      "extracted_amount": 720.0,
      "benchmark_max": 45.0,
      "multiplier": 16.0,
      "severity": "extreme",
      "explanation": "COST ANOMALY DETECTED: Billed amount of $720.00 is 16.0× higher than the benchmark maximum of $45.00 (typical range: $5.00 - $45.00 per 1,000 mL IV bag)."
    },
    "reasoning": "Normal saline is standard for IV hydration, but unit pricing is flagged as an extreme cost anomaly."
  }
}
```

---

### 2. Verify an Existing Claim by ID (`POST /verify/{claim_id}`)
```bash
curl -X POST http://localhost:8000/verify/clm_8f2b4e19c0a34b92
```

---

### 3. Retrieve Verification Result (`GET /verification/{claim_id}`)
```bash
curl -X GET http://localhost:8000/verification/clm_8f2b4e19c0a34b92
```

---

### 4. Handling Contradicted Clinical Claims
When evaluating `sample_11` (prescribing Azithromycin for acute viral bronchitis):
```bash
curl -X POST http://localhost:8000/extract-and-verify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Assessment: Acute viral bronchitis. Treatment: Prescribed Azithromycin 250 mg (Z-Pak) 6 tablets for acute bacterial clearance.",
    "source_type": "clinical_note"
  }'
```
**Result:**
- `verdict`: `"contradicted"`
- `support_score`: `0.10`
- `action`: `"flag"`
- `reasoning`: `"CDC and GOLD guidelines explicitly state that antibiotics are not recommended for uncomplicated acute bronchitis because >90% of cases are viral and antibiotics do not alter illness duration."`

---

### 5. Abstention on Unverified / Unknown Entities
When evaluating `sample_13` (unverified "Himalayan Blue Root Tincture"):
**Result:**
- `verdict`: `"insufficient_evidence"`
- `support_score`: `0.0`
- `action`: `"abstain"`
- `abstain_reason`: `"Zero matching clinical evidence in local knowledge base for entity 'Himalayan Blue Root Tincture'."`

---

## 🧪 Running Automated Tests

Run the complete test suite (32 unit & integration tests):
```bash
pytest backend/tests -v
```

Tests cover:
- ✅ **Schemas**: Validation, constraints, and Layer 2 models
- ✅ **Provenance**: SHA-256 cryptographic digests & tamper detection
- ✅ **Extraction**: Ollama structured JSON parsing & markdown stripping
- ✅ **Cost Anomaly Detection**: Numeric extraction, CPT code matching, extreme markup multiplier ($74 Tylenol, $720 Saline)
- ✅ **Claim Verification**: Guideline retrieval, Ollama verdict parsing, support scoring
- ✅ **Abstention Logic**: Refusal to score claims lacking ground-truth evidence
- ✅ **FastAPI Endpoints**: `/extract`, `/verify/{id}`, `/extract-and-verify`, `/verification/{id}`

---

## 🗺️ Roadmap & Later Layers

- [x] **Layer 1:** Local Ingestion, Ollama structured extraction, tamper-evident provenance, MongoDB storage.
- [x] **Layer 2 (This Layer):** Claim Verification, Support Scoring (0.0-1.0), Decision Triad (ACCEPT, FLAG, ABSTAIN), and Basic Cost Anomaly Detection against public CMS/Fair Health benchmarks.
- [ ] **Layer 3:** Statistical Cost Anomaly Engine (geographic cost indexing, unbundled code detection, CMS outlier percentiles).
- [ ] **Layer 4:** Hyperlocal Trust Density Framework (ZIP/city-level provider density, source credibility scoring).
- [ ] **Layer 5:** High-Performance Verification Engine & Interactive Dashboard.

---

## 📄 License
Apache-2.0. Open-source, local-first, privacy-preserving healthcare analytics.
