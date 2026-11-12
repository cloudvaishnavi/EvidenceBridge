import json
import random
from pathlib import Path
from transformers import AutoTokenizer

random.seed(45)

MODEL_PATH = "models/EvidenceBridge_BioBERT/baseline_v1"
OUTPUT = Path("data/ner_v2/insurance_samples.jsonl")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    use_fast=True,
    local_files_only=True
)

HOSPITALS = [
    "Apollo Hospitals, Bengaluru",
    "Fortis Hospital, Bengaluru",
    "Manipal Hospital, Bengaluru",
    "Narayana Health, Bengaluru",
    "Kaveri General Hospital",
    "Sahyadri Medical Centre"
]

INSURERS = [
    "Star Health and Allied Insurance",
    "HDFC ERGO General Insurance",
    "ICICI Lombard General Insurance",
    "Care Health Insurance",
    "Niva Bupa Health Insurance"
]

TPAS = [
    "Medi Assist Healthcare Services",
    "Health Insurance TPA of India",
    "Paramount Health Services",
    "Family Health Plan Insurance TPA"
]


def build_record(index):
    hospital = random.choice(HOSPITALS)
    insurer = random.choice(INSURERS)
    tpa = random.choice(TPAS)

    patient_id = f"PT{random.randint(10000, 99999)}"
    policy = f"POL-26-{random.randint(100000, 999999)}"
    claim_ref = f"CLM-26-{index:05d}"
    invoice = f"INV-BLR-26-{index:05d}"
    preauth = f"PA-26-{random.randint(10000, 99999)}"

    day = random.randint(1, 28)
    date = f"{day:02d}/10/2026"

    claim_amount = random.randrange(50000, 250001, 5000)
    approved_amount = random.randrange(30000, claim_amount + 1, 5000)
    insurance_deduction = random.randrange(1000, 20001, 1000)
    patient_payable = (
    claim_amount - approved_amount + insurance_deduction
    )

    fields = [
        ("Hospital", hospital, "HOSPITAL"),
        ("Patient ID", patient_id, "PATIENT_ID"),
        ("Insurer", insurer, "INSURER"),
        ("TPA", tpa, "TPA"),
        ("Policy number", policy, "POLICY_NUMBER"),
        ("Claim reference", claim_ref, "CLAIM_REFERENCE"),
        ("Invoice number", invoice, "INVOICE_NUMBER"),
        ("Preauthorization number", preauth, "PREAUTH_NUMBER"),
        ("Claim date", date, "DATE"),
        ("Claim amount", f"INR {claim_amount}", "CLAIM_AMOUNT"),
        ("Approved amount", f"INR {approved_amount}", "APPROVED_AMOUNT"),
        ("Insurance deduction", f"INR {insurance_deduction}", "INSURANCE_DEDUCTION"),
        ("Patient payable", f"INR {patient_payable}", "PATIENT_PAYABLE")
    ]

    text = (
        "Health insurance claim document. "
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
        "record_id": f"SYN-INS-V2-{index:04d}",
        "document_type": "insurance",
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

print("Insurance dataset generated successfully.")
print("Records: 50")
print("Output:", OUTPUT)