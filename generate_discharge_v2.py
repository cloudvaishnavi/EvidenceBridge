import json
import random
from pathlib import Path
from transformers import AutoTokenizer

random.seed(44)

MODEL_PATH = "models/EvidenceBridge_BioBERT/baseline_v1"
OUTPUT = Path("data/ner_v2/discharge_samples.jsonl")

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
    "Pneumonia",
    "Acute gastroenteritis",
    "Acute bronchitis",
    "Cholecystitis",
    "Type 2 diabetes mellitus",
    "Urinary tract infection",
    "Essential hypertension",
    "Dengue fever"
]

PROCEDURES = [
    "Chest radiography",
    "Laparoscopic cholecystectomy",
    "Ultrasound examination",
    "Intravenous fluid therapy",
    "Blood glucose monitoring",
    "Appendectomy",
    "Electrocardiography",
    "Wound dressing"
]

ROOMS = [
    "General Ward",
    "Semi Private Room",
    "Private Room",
    "Intensive Care Unit"
]


def build_record(index):
    hospital = random.choice(HOSPITALS)
    patient_id = f"PT{random.randint(10000, 99999)}"

    admission_day = random.randint(1, 20)
    stay = random.randint(2, 7)
    discharge_day = admission_day + stay

    admission = f"{admission_day:02d}/10/2026"
    discharge = f"{discharge_day:02d}/10/2026"
    report_date = f"{discharge_day:02d}/10/2026"

    diagnosis = random.choice(DIAGNOSES)
    procedure = random.choice(PROCEDURES)
    room = random.choice(ROOMS)
    package = f"PKG-MED-{random.randint(100, 999)}"

    fields = [
        ("Hospital", hospital, "HOSPITAL"),
        ("Patient ID", patient_id, "PATIENT_ID"),
        ("Admission date", admission, "ADMISSION_DATE"),
        ("Discharge date", discharge, "DISCHARGE_DATE"),
        ("Discharge report date", report_date, "DATE"),
        ("Final diagnosis", diagnosis, "DIAGNOSIS"),
        ("Procedure performed", procedure, "PROCEDURE"),
        ("Room type", room, "ROOM_TYPE"),
        ("Package code", package, "PACKAGE_CODE")
    ]

    text = (
        "Hospital discharge summary. "
        + " ".join(
            f"{name}: {value}."
            for name, value, _ in fields
        )
    )

    spans = []

    for name, value, entity in fields:
        prefix = f"{name}: "
        start = text.index(prefix) + len(prefix)
        end = start + len(value)

        assert text[start:end] == value

        spans.append((start, end, entity))

    return {
        "record_id": f"SYN-DIS-V2-{index:04d}",
        "document_type": "discharge",
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
                f"Missing {entity} in {record['record_id']}"
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

print("Discharge dataset generated successfully.")
print("Records: 50")
print("Output:", OUTPUT)