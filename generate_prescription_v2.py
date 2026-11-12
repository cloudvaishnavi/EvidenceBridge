import json
import random
from pathlib import Path
from transformers import AutoTokenizer

random.seed(43)

MODEL_PATH = "models/EvidenceBridge_BioBERT/baseline_v1"
OUTPUT = Path("data/ner_v2/prescription_samples.jsonl")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    use_fast=True,
    local_files_only=True
)

HOSPITALS = [
    "Apollo Hospitals",
    "Fortis Hospital",
    "Manipal Hospital",
    "Narayana Health",
    "Kaveri General Hospital",
    "Sahyadri Medical Centre",
    "Aster CMI Hospital",
    "Sanjeevani Multispeciality Hospital"
]

DIAGNOSES = [
    "Type 2 diabetes mellitus",
    "Essential hypertension",
    "Acute bronchitis",
    "Pneumonia",
    "Cholecystitis",
    "Urinary tract infection",
    "Vitamin D deficiency",
    "Gastroesophageal reflux disease"
]

MEDICINES = [
    {
        "generic": "Metformin",
        "brand": "Glycomet",
        "ingredient": "Metformin hydrochloride",
        "strength": "500 mg",
        "dosage": "1 tablet twice daily with meals"
    },
    {
        "generic": "Paracetamol",
        "brand": "Dolo",
        "ingredient": "Paracetamol",
        "strength": "650 mg",
        "dosage": "1 tablet after meals when required"
    },
    {
        "generic": "Telmisartan",
        "brand": "Telma",
        "ingredient": "Telmisartan",
        "strength": "40 mg",
        "dosage": "1 tablet once daily in the morning"
    },
    {
        "generic": "Amlodipine",
        "brand": "Amlong",
        "ingredient": "Amlodipine besylate",
        "strength": "5 mg",
        "dosage": "1 tablet once daily"
    },
    {
        "generic": "Amoxicillin",
        "brand": "Novamox",
        "ingredient": "Amoxicillin",
        "strength": "500 mg",
        "dosage": "1 capsule three times daily"
    },
    {
        "generic": "Vitamin D3",
        "brand": "Uprise D3",
        "ingredient": "Cholecalciferol",
        "strength": "60000 IU",
        "dosage": "1 capsule once weekly"
    }
]


def build_record(index):
    hospital = random.choice(HOSPITALS)
    diagnosis = random.choice(DIAGNOSES)
    medicine = random.choice(MEDICINES)

    patient_id = f"PT{random.randint(10000, 99999)}"
    date = f"{random.randint(1, 28):02d}/10/2026"

    fields = [
        ("Hospital", hospital, "HOSPITAL"),
        ("Patient ID", patient_id, "PATIENT_ID"),
        ("Prescription date", date, "DATE"),
        ("Diagnosis", diagnosis, "DIAGNOSIS"),
        ("Generic medicine", medicine["generic"], "GENERIC_NAME"),
        ("Brand name", medicine["brand"], "BRAND_NAME"),
        ("Active ingredient", medicine["ingredient"], "ACTIVE_INGREDIENT"),
        ("Strength", medicine["strength"], "STRENGTH"),
        ("Dosage", medicine["dosage"], "DOSAGE")
    ]

    text = "Prescription document. " + " ".join(
        f"{name}: {value}."
        for name, value, _ in fields
    )

    spans = []

    for name, value, entity in fields:
        prefix = f"{name}: "
        prefix_pos = text.index(prefix)
        start = prefix_pos + len(prefix)
        end = start + len(value)

        assert text[start:end] == value

        spans.append((start, end, entity))

    return {
        "record_id": f"SYN-PRES-V2-{index:04d}",
        "document_type": "prescription",
        "text": text,
        "spans": spans
    }


def convert_to_bio(record):
    encoding = tokenizer(
        record["text"],
        return_offsets_mapping=True,
        truncation=True,
        max_length=192
    )

    tokens = tokenizer.convert_ids_to_tokens(
        encoding["input_ids"]
    )

    labels = ["O"] * len(tokens)

    for start, end, entity in record["spans"]:
        matching = [
            i for i, (ts, te) in enumerate(
                encoding["offset_mapping"]
            )
            if ts != te and ts < end and te > start
        ]

        if not matching:
            raise ValueError(
                f"Missing tokens for {entity}: {record['record_id']}"
            )

        for position, token_index in enumerate(matching):
            labels[token_index] = (
                "B-" if position == 0 else "I-"
            ) + entity

    assert len(tokens) == len(labels)

    return {
        "record_id": record["record_id"],
        "document_type": record["document_type"],
        "text": record["text"],
        "tokens": tokens,
        "ner_tags": labels
    }


OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8") as f:
    for i in range(1, 51):
        record = convert_to_bio(build_record(i))
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print("Prescription dataset generated successfully.")
print("Records: 50")
print("Output:", OUTPUT)