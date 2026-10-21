# EvidenceBridge 🩺🔍
### Evidence-Auditing & Cost-Anomaly Engine for Healthcare Claims & Hospital Bills

> **[!IMPORTANT]**
> **Scope of this Foundational Layer:**
> **This layer only does extraction + provenance.** Claim verification, cost anomaly detection, and abstention come in later layers.

---

EvidenceBridge is an open-source, local-first engine designed to audit healthcare claims, patient reports, and hospital bills. It provides end-to-end traceability, structured clinical/cost extraction, and tamper-evident provenance without relying on paid external APIs.

---

## 🏗️ Architecture (Foundational Layer)

```
                     ┌──────────────────────────────────────────────┐
                     │ Raw Unstructured Text                        │
                     │ - Clinical Progress Notes                    │
                     │ - Patient Community Forum Reports            │
                     │ - Itemized Hospital Bill Line Items          │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                           ┌──────────────────────────────────┐
                           │   FastAPI /extract Endpoint      │
                           └────────────────┬─────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
     ┌─────────────────────────────┐                ┌─────────────────────────────┐
     │ Local LLM Extraction Engine │                │ Provenance Service          │
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
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
     ┌─────────────────────────────┐                ┌─────────────────────────────┐
     │ MongoDB ("claims" collection│                │ Local ChromaDB Vector Store │
     │ - Full Document Store       │                │ - Semantic Embeddings       │
     │ - Indexed by claim_id & hash│                │ - 100% Offline Retrieval    │
     └─────────────────────────────┘                └─────────────────────────────┘
```

---

## 📁 Repository Structure

```
evidencebridge/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py             # FastAPI routes (/extract, /claims/{id}, /health)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py            # Pydantic models (Claim, Provenance, ExtractedFields)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── extraction.py         # Ollama structured JSON extraction pipeline
│   │   │   ├── provenance.py         # SHA-256 hashing & source metadata linkage
│   │   │   ├── storage.py            # Async MongoDB storage service (Motor)
│   │   │   └── vector_store.py       # Local ChromaDB vector indexing
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── logger.py             # Formatted logging utility
│   │   ├── config.py                 # Pydantic Settings & environment config
│   │   └── main.py                   # FastAPI application initialization & lifespan
│   ├── tests/
│   │   ├── conftest.py               # Shared pytest fixtures
│   │   ├── test_api.py               # FastAPI endpoint integration tests
│   │   ├── test_extraction.py        # Extraction parsing and fallback tests
│   │   ├── test_provenance.py        # Cryptographic hashing & tamper-check tests
│   │   └── test_schemas.py           # Pydantic schema validation tests
│   ├── Dockerfile                    # Container definition for backend
│   └── requirements.txt              # Core Python dependencies
├── data/
│   └── samples/                      # 10 realistic sample records
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
│       └── sample_10_patient_post_botox_migraine.json
├── scripts/
│   ├── setup_ollama.sh               # Ollama install/verify/pull helper (Linux/macOS)
│   ├── setup_ollama.ps1              # Ollama install/verify/pull helper (Windows)
│   └── seed_data.py                  # Batch ingestion and seeding CLI
├── .env.example                      # Configuration template
├── .gitignore                        # Git exclusion rules
├── docker-compose.yml                # Multi-container orchestration (Mongo + Backend)
└── README.md                         # Documentation and setup instructions
```

---

## ⚙️ Quickstart

### Option 1: Docker Compose (Recommended if Docker is installed)

1. **Clone and enter repository:**
   ```bash
   git clone https://github.com/your-username/evidencebridge.git
   cd evidencebridge
   ```

2. **Copy configuration:**
   ```bash
   cp .env.example .env
   ```

3. **Start Ollama on your host machine and pull the default model:**
   ```bash
   # In a separate terminal or via desktop app
   ollama serve
   ollama pull phi3:mini
   ```

4. **Launch containers:**
   ```bash
   docker compose up --build
   ```

5. The API is now live at: `http://localhost:8000` (Interactive Docs: `http://localhost:8000/docs`).

---

### Option 2: Local Python Setup (Offline / Local-First)

#### 1. Prerequisites
- **Python 3.11+**
- **Ollama** installed ([https://ollama.com/download](https://ollama.com/download))
- **MongoDB** running locally (`mongodb://localhost:27017`) or free MongoDB Atlas cluster

#### 2. Install and Setup Ollama
On Linux/macOS:
```bash
chmod +x scripts/setup_ollama.sh
./scripts/setup_ollama.sh
```

On Windows (PowerShell):
```powershell
.\scripts\setup_ollama.ps1
```

Or manually:
```bash
# Pull lightweight phi3:mini (~2.2GB) or llama3.1:8b (~4.7GB)
ollama pull phi3:mini

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

#### 3. Start MongoDB
Using local Docker:
```bash
docker run -d -p 27017:27017 --name mongo-evidencebridge mongo:7.0
```
Or start your local MongoDB service:
- Linux: `sudo systemctl start mongod`
- macOS: `brew services start mongodb-community`
- Windows: `net start MongoDB`

#### 4. Setup Python Environment
```bash
# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt
```

#### 5. Configure Environment
```bash
cp .env.example .env
```
Default configuration inside `.env`:
```env
APP_NAME=EvidenceBridge
PORT=8000
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=evidencebridge
MONGODB_CLAIMS_COLLECTION=claims
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

#### 6. Run Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧪 Seeding Sample Data

EvidenceBridge includes 10 realistic healthcare samples across three categories:
- **Clinical Notes**: Diabetes titration, hypertension therapy, pneumonia inpatient discharge.
- **Patient Reports**: Ozempic weight loss side effects & costs, post-op knee surgery surprises, migraine Botox copays.
- **Hospital Bills**: Level 5 ER visit charge, $74 Tylenol inpatient markup, knee MRI facility fee markup, routine metabolic panel overcharge.

To seed all samples into the running backend:
```bash
python scripts/seed_data.py --url http://localhost:8000
```

---

## 📡 Example API Requests (cURL)

### 1. Check System Health
```bash
curl -X GET http://localhost:8000/health
```
**Sample Response:**
```json
{
  "status": "ok",
  "app_name": "EvidenceBridge",
  "version": "0.1.0",
  "timestamp": "2026-10-21T20:30:00Z",
  "services": {
    "mongodb": { "status": "healthy", "claims_count": 10 },
    "ollama": { "status": "healthy", "configured_model": "phi3:mini", "model_ready": true },
    "vector_store": { "status": "healthy", "vector_count": 10 }
  }
}
```

---

### 2. Extract Claim from a Clinical Note
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "PATIENT PROGRESS NOTE: 58-year-old male with poorly controlled Type 2 Diabetes Mellitus. Started on Metformin 1,000 mg twice daily with evening meals 3 months ago. Repeat laboratory evaluation demonstrates a reduction in HbA1c from 8.9% down to 7.1%. Patient tolerates therapy well with no hypoglycemic events.",
    "source_type": "clinical_note",
    "source_url": "ehr://emr-archive-internal/notes/2026-03-12/pt-88419",
    "store_claim": true
  }'
```
**Sample Response:**
```json
{
  "success": true,
  "stored": true,
  "message": "Claim successfully extracted and linked with provenance (stored)",
  "claim": {
    "claim_id": "clm_8f2b4e19c0a34b92",
    "original_text": "PATIENT PROGRESS NOTE: 58-year-old male with poorly controlled Type 2 Diabetes Mellitus...",
    "source_type": "clinical_note",
    "source_url": "ehr://emr-archive-internal/notes/2026-03-12/pt-88419",
    "timestamp": "2026-10-21T20:31:00Z",
    "extracted_fields": {
      "entity": "Metformin 1,000 mg",
      "effect_or_outcome": "Reduction in HbA1c from 8.9% down to 7.1%",
      "cost_range": null,
      "location_city": null,
      "sentiment": "positive",
      "reasoning": "Clear therapeutic reduction in HbA1c with good patient tolerance."
    },
    "confidence": 0.95,
    "provenance": {
      "source_hash": "4d8a1c97f1bb54e60...",
      "original_snippet": "PATIENT PROGRESS NOTE: 58-year-old male with poorly controlled Type 2 Diabetes Mellitus...",
      "text_length": 308,
      "source_type": "clinical_note",
      "source_url": "ehr://emr-archive-internal/notes/2026-03-12/pt-88419",
      "ingested_at": "2026-10-21T20:31:00Z"
    },
    "indexed_vector": true
  }
}
```

---

### 3. Extract Claim from an Inflated Hospital Bill Line
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ST. CATHERINE COMMUNITY HOSPITAL - MIAMI, FL. Inpatient Pharmacy Line Item: ACETAMINOPHEN 500 MG ORAL TABLET. Quantity Dispensed: 2 tablets. Revenue Code: 0250. Billed Amount: $148.00 ($74.00 per single tablet).",
    "source_type": "hospital_bill",
    "source_url": "hospital://st-catherine-miami/itemized/rx-0250",
    "store_claim": true
  }'
```

---

### 4. Retrieve Claim by Unique Claim ID
```bash
curl -X GET http://localhost:8000/claims/clm_8f2b4e19c0a34b92
```

---

### 5. List Stored Claims
```bash
curl -X GET "http://localhost:8000/claims?limit=10&skip=0"
```

---

## 🔒 Provenance & Trust Model

In EvidenceBridge, **no claim exists in isolation**. Every claim is tethered to its source:

1. **Deterministic Cryptographic Digest (`source_hash`):**
   A SHA-256 hash is computed over the exact original text. If anyone modifies even a single character of the original text, `verify_provenance()` immediately flags the mismatch.
2. **Anchor Snippet & Length:**
   Captures the initial verbatim excerpt and exact character length.
3. **Lineage Metadata:**
   Preserves origin type (`clinical_note`, `patient_report`, `hospital_bill`), original source URL/record ID, and ingestion timestamp.

---

## 🧪 Running Unit & Integration Tests

```bash
# From workspace root
pytest backend/tests -v
```

Tests cover:
- ✅ Pydantic schema validation & constraints
- ✅ Provenance hashing & tamper detection
- ✅ Extraction parsing (handling JSON, markdown blocks, and corrupt LLM outputs)
- ✅ FastAPI endpoints (`/health`, `/extract`, `/claims/{claim_id}`, `/claims`)

---

## 🗺️ Roadmap & Later Layers

- [x] **Layer 1 (This Layer):** Ingestion, Ollama extraction, provenance tracking, MongoDB storage, FastAPI.
- [ ] **Layer 2:** Evidence Audit & Multi-Source Cross-Verification (Corroborating patient reports against clinical trials and FDA labels).
- [ ] **Layer 3:** Cost Anomaly Detection (Statistical outlier analysis comparing hospital bill lines against CMS average benchmarks).
- [ ] **Layer 4:** Hyperlocal Trust Density & Abstention Framework (Safe refusal when evidence is weak or localized trust is low).
- [ ] **Layer 5:** High-Performance Verification Engine & Interactive Dashboard.

---

## 📄 License
Apache-2.0. Open-source, local-first, privacy-preserving healthcare analytics.
