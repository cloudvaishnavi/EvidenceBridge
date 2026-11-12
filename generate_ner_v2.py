
import json
import random
from pathlib import Path
from transformers import AutoTokenizer

# Configuration
MODEL_PATH = "models/EvidenceBridge_BioBERT/baseline_v1"
OUTPUT_DIR = Path("data/ner_v2")
OUTPUT_FILE = OUTPUT_DIR / "invoice_samples.jsonl"

random.seed(42)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    use_fast=True,
    local_files_only=True
)

HOSPITALS = [
    "Apollo Hospitals", "Fortis Hospital",
    "Manipal Hospital", "Narayana Health",
    "Kaveri General Hospital", "Sahyadri Medical Centre",
    "Aster CMI Hospital", "Sanjeevani Multispeciality Hospital"
]

DIAGNOSES = [
    "Type 2 diabetes mellitus", "Essential hypertension",
    "Acute bronchitis", "Pneumonia",
    "Cholecystitis", "Urinary tract infection"
]

ROOMS = [
    "General Ward",
    "Semi Private Room",
    "Private Room"
]

# Synthetic HSN/SAC-like examples.
# Not verified tax classifications.
HSN_SAC_CODES = [
    "999311", "999312", "999313",
    "998311", "998312"
]


def generate_gstin():
    """Generate a GSTIN-shaped synthetic identifier."""
    state_code = random.choice(["29", "27", "07", "33", "36"])

    pan = "".join(
        random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5)
    )
    pan += "".join(
        random.choices("0123456789", k=4)
    )
    pan += random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    entity_number = "1"
    default_character = "Z"
    checksum_placeholder = random.choice(
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    return (
        f"{state_code}{pan}"
        f"{entity_number}{default_character}{checksum_placeholder}"
    )


def build_document(index):
    hospital = random.choice(HOSPITALS)
    gstin = generate_gstin()

    patient_id = f"PT{random.randint(10000, 99999)}"
    invoice = f"INV-26-{index:05d}"
    date = f"{random.randint(1, 28):02d}/10/2026"

    quantity = random.randint(1, 5)
    unit_price = random.choice([500, 750, 1200, 1500, 2500])

    line_amount = quantity * unit_price
    discount = random.choice([0, 100, 200, 300])
    subtotal = line_amount
    tax = random.choice([0, 90, 180])
    total = subtotal - discount + tax

    room = random.choice(ROOMS)
    diagnosis = random.choice(DIAGNOSES)
    hsn_sac = random.choice(HSN_SAC_CODES)

    text = (
        f"Hospital: {hospital}. "
        f"GSTIN: {gstin}. "
        f"Patient ID: {patient_id}. "
        f"Invoice number: {invoice}. "
        f"Invoice date: {date}. "
        f"Diagnosis: {diagnosis}. "
        f"Room type: {room}. "
        f"Quantity: {quantity}. "
        f"HSN/SAC code: {hsn_sac}. "
        f"Unit price: INR {unit_price}. "
        f"Line amount: INR {line_amount}. "
        f"Subtotal: INR {subtotal}. "
        f"Discount: INR {discount}. "
        f"Tax amount: INR {tax}. "
        f"Final invoice total: INR {total}."
    )

    fields = [
        ("Hospital: ", hospital, "HOSPITAL"),
        ("GSTIN: ", gstin, "GSTIN"),
        ("Patient ID: ", patient_id, "PATIENT_ID"),
        ("Invoice number: ", invoice, "INVOICE_NUMBER"),
        ("Invoice date: ", date, "DATE"),
        ("Diagnosis: ", diagnosis, "DIAGNOSIS"),
        ("Room type: ", room, "ROOM_TYPE"),
        ("Quantity: ", str(quantity), "QUANTITY"),
        ("HSN/SAC code: ", hsn_sac, "HSN_SAC"),
        ("Unit price: ", f"INR {unit_price}", "UNIT_PRICE"),
        ("Line amount: ", f"INR {line_amount}", "LINE_AMOUNT"),
        ("Subtotal: ", f"INR {subtotal}", "SUBTOTAL"),
        ("Discount: ", f"INR {discount}", "DISCOUNT"),
        ("Tax amount: ", f"INR {tax}", "TAX_AMOUNT"),
        ("Final invoice total: ", f"INR {total}", "INVOICE_TOTAL")
    ]

    spans = []

    for prefix, value, entity in fields:
        prefix_pos = text.index(prefix)
        start = prefix_pos + len(prefix)
        end = start + len(value)

        if text[start:end] != value:
            raise ValueError(
                f"Span mismatch: {entity}, invoice {index}"
            )

        spans.append((start, end, entity))

    return {
        "record_id": f"SYN-INV-V2-{index:04d}",
        "document_type": "invoice",
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
            i
            for i, (ts, te) in enumerate(
                encoding["offset_mapping"]
            )
            if ts != te and ts < end and te > start
        ]

        if not matching:
            raise ValueError(
                f"No tokens found for {entity} "
                f"in {record['record_id']}"
            )

        for position, token_index in enumerate(matching):
            if labels[token_index] != "O":
                raise ValueError(
                    f"Overlapping annotation: "
                    f"{record['record_id']}"
                )

            labels[token_index] = (
                "B-" if position == 0 else "I-"
            ) + entity

    if len(tokens) != len(labels):
        raise ValueError("Token-label length mismatch")

    return {
        "record_id": record["record_id"],
        "document_type": record["document_type"],
        "text": record["text"],
        "tokens": tokens,
        "ner_tags": labels
    }


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    for i in range(1, 51):
        document = build_document(i)
        converted = convert_to_bio(document)

        f.write(
            json.dumps(converted, ensure_ascii=False) + "\n"
        )

print("Invoice dataset generated successfully.")
print("Records: 50")
print("GSTIN annotations: 50")
print("HSN_SAC annotations: 50")
print("Output:", OUTPUT_FILE)
