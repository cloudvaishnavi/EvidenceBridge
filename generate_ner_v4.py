
import json
import random
from pathlib import Path
from datetime import date, timedelta

from transformers import AutoTokenizer

# ============================================================
# CONFIGURATION
# ============================================================

SEED = 20261102
random.seed(SEED)

MODEL_PATH = "models/EvidenceBridge_BioBERT/baseline_v1"
SCHEMA_PATH = Path(
    "models/EvidenceBridge_BioBERT/india_ner_schema_v4.json"
)

OUTPUT_DIR = Path("data/ner_v4/raw")
OUTPUT_FILE = OUTPUT_DIR / "all_records.jsonl"

MAX_LENGTH = 192

COUNTS = {
    "invoice": 300,
    "prescription": 200,
    "discharge": 200,
    "insurance": 300
}

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    use_fast=True,
    local_files_only=True
)

schema = json.loads(
    SCHEMA_PATH.read_text(encoding="utf-8")
)

VALID_LABELS = set(schema["label2id"])

# Extract entity names from BIO labels.
# Example: B-HOSPITAL -> HOSPITAL

VALID_ENTITIES = {
    label[2:]
    for label in schema["labels"]
    if label.startswith("B-")
}

if len(VALID_ENTITIES) != schema["entity_count"]:
    raise ValueError(
        f"Schema entity-count mismatch: "
        f"expected {schema['entity_count']}, "
        f"found {len(VALID_ENTITIES)}"
    )

# ============================================================
# INDIA-RELEVANT SYNTHETIC VALUES
# ============================================================

PATIENT_NAMES = [
    "Rahul Sharma", "Priya Reddy", "Arjun Kumar",
    "Sneha Patil", "Ananya Rao", "Vikram Shetty",
    "Kavya Nair", "Aarav Mehta", "Pooja Desai",
    "Rohan Kulkarni", "Meera Iyer", "Aditya Joshi",
    "Divya Menon", "Sanjay Gowda", "Neha Verma",
    "Kiran Hegde", "Sahana Murthy", "Manoj Bhat",
    "Aishwarya Pillai", "Harish Naidu", "Nikhil Das",
    "Lakshmi Krishnan", "Varun Sinha", "Deepa Nayak",
    "Abhishek Jain", "Ritu Malhotra", "Shreya Ghosh",
    "Pranav Rao", "Anjali Kulkarni", "Suresh Patil"
]

HOSPITALS = [
    "Apollo Hospitals", "Fortis Hospital",
    "Manipal Hospital", "Narayana Health",
    "Aster CMI Hospital", "Sahyadri Medical Centre",
    "Kaveri General Hospital",
    "Sanjeevani Multispeciality Hospital",
    "Vikram Hospital", "Sparsh Hospital",
    "Rainbow Children's Hospital", "Columbia Asia Hospital",
    "Sagar Hospitals", "BGS Gleneagles Hospital",
    "Shree Sai Medical Centre", "City Care Hospital"
]

DIAGNOSES = [
    "Type 2 diabetes mellitus",
    "Essential hypertension",
    "Acute bronchitis",
    "Community acquired pneumonia",
    "Urinary tract infection",
    "Dengue fever",
    "Iron deficiency anaemia",
    "Chronic kidney disease",
    "Gastroesophageal reflux disease",
    "Acute gastroenteritis",
    "Hypothyroidism",
    "Cholecystitis",
    "Migraine",
    "Osteoarthritis",
    "Vitamin D deficiency",
    "Upper respiratory tract infection",
    "Coronary artery disease",
    "Asthma"
]

PROCEDURES = [
    "Chest radiography",
    "Ultrasound examination",
    "Electrocardiography",
    "Appendectomy",
    "Laparoscopic cholecystectomy",
    "Wound dressing",
    "Intravenous fluid therapy",
    "Blood glucose monitoring",
    "CT scan",
    "MRI examination",
    "Nebulization",
    "Endoscopy",
    "Dialysis",
    "Physiotherapy"
]

ROOMS = [
    "General Ward",
    "Semi Private Room",
    "Private Room",
    "Intensive Care Unit",
    "Deluxe Room",
    "Twin Sharing Room"
]

MEDICINES = [
    ("Metformin", "Glycomet", "Metformin hydrochloride"),
    ("Paracetamol", "Dolo", "Paracetamol"),
    ("Telmisartan", "Telma", "Telmisartan"),
    ("Amlodipine", "Amlong", "Amlodipine besylate"),
    ("Amoxicillin", "Novamox", "Amoxicillin"),
    ("Vitamin D3", "Uprise D3", "Cholecalciferol"),
    ("Atorvastatin", "Atorva", "Atorvastatin calcium"),
    ("Pantoprazole", "Pan", "Pantoprazole sodium"),
    ("Cetirizine", "Cetzine", "Cetirizine hydrochloride"),
    ("Azithromycin", "Azithral", "Azithromycin"),
    ("Losartan", "Losar", "Losartan potassium"),
    ("Omeprazole", "Omez", "Omeprazole"),
    ("Glimepiride", "Amaryl", "Glimepiride"),
    ("Cefixime", "Taxim-O", "Cefixime"),
    ("Montelukast", "Montair", "Montelukast sodium"),
    ("Rabeprazole", "Rablet", "Rabeprazole sodium"),
    ("Levothyroxine", "Thyronorm", "Levothyroxine sodium"),
    ("Diclofenac", "Voveran", "Diclofenac sodium"),
    ("Domperidone", "Domstal", "Domperidone"),
    ("Iron supplement", "Orofer", "Ferrous ascorbate")
]

INSURERS = [
    "Star Health and Allied Insurance",
    "HDFC ERGO General Insurance",
    "ICICI Lombard General Insurance",
    "Care Health Insurance",
    "Niva Bupa Health Insurance",
    "Bajaj Allianz General Insurance",
    "New India Assurance",
    "Tata AIG General Insurance",
    "SBI General Insurance",
    "United India Insurance"
]

TPAS = [
    "Medi Assist Healthcare Services",
    "Health Insurance TPA of India",
    "Paramount Health Services",
    "Family Health Plan Insurance TPA",
    "Vidal Health TPA",
    "Raksha Health Insurance TPA",
    "MDIndia Health Insurance TPA"
]

GST_STATES = [
    "29", "27", "07", "33",
    "36", "09", "32", "24"
]

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ============================================================
# VALUE GENERATORS
# ============================================================

def gstin():
    pan = (
        "".join(random.choices(ALPHABET, k=5))
        + "".join(random.choices("0123456789", k=4))
        + random.choice(ALPHABET)
    )

    return (
        random.choice(GST_STATES)
        + pan
        + "1Z"
        + random.choice(
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )
    )


def patient_id():
    return f"PT{random.randint(100000, 999999)}"


def money(value):
    return f"INR {value:,}"


def random_date():
    start = date(2025, 1, 1)
    day = start + timedelta(
        days=random.randint(0, 670)
    )
    return day.strftime("%d/%m/%Y")


def medicine_details():
    generic, brand, ingredient = random.choice(MEDICINES)

    strength = random.choice([
        "250 mg", "500 mg", "650 mg", "100 mg",
        "200 mg", "5 mg", "10 mg", "20 mg",
        "40 mg", "50 mg", "1000 mg", "60000 IU",
        "1 g", "2.5 mg", "75 mg"
    ])

    dosage = random.choice([
        "1 tablet once daily",
        "1 tablet twice daily",
        "1 capsule after meals",
        "1 tablet after meals when required",
        "5 ml twice daily",
        "1 tablet every morning",
        "1 capsule three times daily",
        "1 tablet at bedtime",
        "1 tablet before breakfast",
        "1 capsule once weekly"
    ])

    return generic, brand, ingredient, strength, dosage


# ============================================================
# DOCUMENT BUILDER
# ============================================================

def make_document(record_id, document_type, fields):
    """
    fields: list of (entity_type, value, prefix)
    """

    layout = random.randint(0, 3)

    if layout == 0:
        heading = {
            "invoice": "TAX INVOICE",
            "prescription": "MEDICAL PRESCRIPTION",
            "discharge": "DISCHARGE SUMMARY",
            "insurance": "HEALTH INSURANCE CLAIM"
        }[document_type]

    elif layout == 1:
        heading = {
            "invoice": "PATIENT BILLING STATEMENT",
            "prescription": "DOCTOR'S PRESCRIPTION",
            "discharge": "HOSPITAL DISCHARGE REPORT",
            "insurance": "CASHLESS CLAIM FORM"
        }[document_type]

    elif layout == 2:
        heading = {
            "invoice": "HOSPITAL ACCOUNT DETAILS",
            "prescription": "OUTPATIENT MEDICATION RECORD",
            "discharge": "INPATIENT SUMMARY",
            "insurance": "INSURANCE REIMBURSEMENT RECORD"
        }[document_type]

    else:
        heading = {
            "invoice": "FINAL BILL",
            "prescription": "PRESCRIPTION NOTE",
            "discharge": "PATIENT RELEASE DOCUMENT",
            "insurance": "CLAIM SETTLEMENT DOCUMENT"
        }[document_type]

    text_parts = [heading + ". "]
    spans = []
    cursor = len(text_parts[0])

    for entity, value, prefix in fields:
        separator = random.choice([" ", "\n", " | "])
        segment = separator + prefix + value + "."
        text_parts.append(segment)

        start = cursor + len(separator) + len(prefix)
        end = start + len(value)

        if (
            segment[
                len(separator) + len(prefix):
                len(separator) + len(prefix) + len(value)
            ] != value
        ):
            raise ValueError("Character span mismatch")

        spans.append((start, end, entity))
        cursor += len(segment)

    text = "".join(text_parts)

    return {
        "record_id": record_id,
        "document_type": document_type,
        "text": text,
        "spans": spans
    }


# ============================================================
# INVOICE GENERATOR
# ============================================================

def generate_invoice(index):
    hospital = random.choice(HOSPITALS)
    name = random.choice(PATIENT_NAMES)
    pid = patient_id()

    invoice_no = (
        f"INV-{random.randint(2025, 2026)}-{index:06d}"
    )

    quantity = random.randint(1, 30)
    unit = random.randrange(50, 5001, 25)

    line = quantity * unit
    discount = random.randrange(
        0, min(line, 10001), 100
    )

    subtotal = line
    tax = random.randrange(0, 2501, 50)
    total = subtotal - discount + tax

    fields = [
        ("HOSPITAL", hospital, "Hospital: "),
        ("PATIENT_NAME", name, "Patient Name: "),
        ("PATIENT_ID", pid, "Patient ID: "),
        ("GSTIN", gstin(), "GSTIN: "),
        ("INVOICE_NUMBER", invoice_no, "Invoice Number: "),
        ("DATE", random_date(), "Invoice Date: "),
        ("DIAGNOSIS", random.choice(DIAGNOSES), "Diagnosis: "),
        ("ROOM_TYPE", random.choice(ROOMS), "Room Type: "),
        ("QUANTITY", str(quantity), "Quantity: "),
        ("HSN_SAC", random.choice([
            "999311", "999312", "998311",
            "998312", "999313"
        ]), "HSN/SAC: "),
        ("UNIT_PRICE", money(unit), "Unit Price: "),
        ("LINE_AMOUNT", money(line), "Line Amount: "),
        ("SUBTOTAL", money(subtotal), "Subtotal: "),
        ("DISCOUNT", money(discount), "Discount: "),
        ("TAX_AMOUNT", money(tax), "Tax Amount: "),
        ("INVOICE_TOTAL", money(total), "Invoice Total: ")
    ]

    random.shuffle(fields)

    return make_document(
        f"V4-INV-{index:04d}",
        "invoice",
        fields
    )


# ============================================================
# PRESCRIPTION GENERATOR
# ============================================================

def generate_prescription(index):
    generic, brand, ingredient, strength, dosage = (
        medicine_details()
    )

    fields = [
        ("HOSPITAL", random.choice(HOSPITALS), "Hospital: "),
        ("PATIENT_NAME", random.choice(PATIENT_NAMES), "Patient: "),
        ("PATIENT_ID", patient_id(), "Patient ID: "),
        ("DATE", random_date(), "Prescription Date: "),
        ("DIAGNOSIS", random.choice(DIAGNOSES), "Diagnosis: "),
        ("GENERIC_NAME", generic, "Generic Medicine: "),
        ("BRAND_NAME", brand, "Brand: "),
        ("ACTIVE_INGREDIENT", ingredient, "Active Ingredient: "),
        ("STRENGTH", strength, "Strength: "),
        ("DOSAGE", dosage, "Dosage Instructions: ")
    ]

    random.shuffle(fields)

    return make_document(
        f"V4-PRES-{index:04d}",
        "prescription",
        fields
    )


# ============================================================
# DISCHARGE GENERATOR
# ============================================================

def generate_discharge(index):
    admission = (
        date(2025, 1, 1)
        + timedelta(days=random.randint(0, 650))
    )

    discharge = admission + timedelta(
        days=random.randint(1, 20)
    )

    fields = [
        ("HOSPITAL", random.choice(HOSPITALS), "Hospital: "),
        ("PATIENT_NAME", random.choice(PATIENT_NAMES), "Patient Name: "),
        ("PATIENT_ID", patient_id(), "Patient ID: "),
        ("ADMISSION_DATE", admission.strftime("%d/%m/%Y"), "Admission Date: "),
        ("DISCHARGE_DATE", discharge.strftime("%d/%m/%Y"), "Discharge Date: "),
        ("DATE", discharge.strftime("%d/%m/%Y"), "Report Date: "),
        ("DIAGNOSIS", random.choice(DIAGNOSES), "Final Diagnosis: "),
        ("PROCEDURE", random.choice(PROCEDURES), "Procedure Performed: "),
        ("ROOM_TYPE", random.choice(ROOMS), "Room Type: "),
        (
            "PACKAGE_CODE",
            f"PKG-{random.choice(['MED', 'SUR', 'CARD', 'GEN'])}-{random.randint(100, 9999)}",
            "Package Code: "
        )
    ]

    random.shuffle(fields)

    return make_document(
        f"V4-DIS-{index:04d}",
        "discharge",
        fields
    )


# ============================================================
# INSURANCE GENERATOR
# ============================================================

def generate_insurance(index):
    claim = random.randrange(20000, 500001, 500)
    approved = random.randrange(
        10000, claim + 1, 500
    )

    deduction = random.randrange(
        0, min(approved, 50001) + 1, 500
    )

    payable = max(
        0,
        claim - approved + deduction
    )

    fields = [
        ("HOSPITAL", random.choice(HOSPITALS), "Hospital: "),
        ("PATIENT_NAME", random.choice(PATIENT_NAMES), "Patient Name: "),
        ("PATIENT_ID", patient_id(), "Patient ID: "),
        ("INSURER", random.choice(INSURERS), "Insurer: "),
        ("TPA", random.choice(TPAS), "TPA: "),
        (
            "POLICY_NUMBER",
            f"POL-{random.randint(2024, 2026)}-{random.randint(100000, 999999)}",
            "Policy Number: "
        ),
        (
            "CLAIM_REFERENCE",
            f"CLM-{random.randint(2025, 2026)}-{index:06d}",
            "Claim Reference: "
        ),
        (
            "INVOICE_NUMBER",
            f"INV-{random.randint(2025, 2026)}-{index:06d}",
            "Invoice Number: "
        ),
        (
            "PREAUTH_NUMBER",
            f"PA-{random.randint(100000, 999999)}",
            "Preauthorization Number: "
        ),
        ("DATE", random_date(), "Claim Date: "),
        ("CLAIM_AMOUNT", money(claim), "Claim Amount: "),
        ("APPROVED_AMOUNT", money(approved), "Approved Amount: "),
        ("INSURANCE_DEDUCTION", money(deduction), "Insurance Deduction: "),
        ("PATIENT_PAYABLE", money(payable), "Patient Payable: ")
    ]

    random.shuffle(fields)

    return make_document(
        f"V4-INS-{index:04d}",
        "insurance",
        fields
    )


# ============================================================
# BIO CONVERSION AND VALIDATION
# ============================================================

def convert_to_bio(record):
    text = record["text"]
    spans = record["spans"]

    # Validate character spans.
    previous_end = -1

    for start, end, entity in sorted(spans):

        if entity not in VALID_ENTITIES:
            raise ValueError(
                f"Unknown entity: {entity}"
            )

        if (
            start < 0
            or end <= start
            or end > len(text)
        ):
            raise ValueError(
                f"Invalid span: {record['record_id']}"
            )

        if start < previous_end:
            raise ValueError(
                f"Overlapping spans: {record['record_id']}"
            )

        if not text[start:end].strip():
            raise ValueError("Empty entity span")

        previous_end = end

    # Tokenize without truncation.
    encoding = tokenizer(
        text,
        add_special_tokens=True,
        truncation=False,
        return_offsets_mapping=True
    )

    if len(encoding["input_ids"]) > MAX_LENGTH:
        raise ValueError(
            f"Record exceeds {MAX_LENGTH} tokens: "
            f"{record['record_id']}"
        )

    tokens = tokenizer.convert_ids_to_tokens(
        encoding["input_ids"]
    )

    tags = ["O"] * len(tokens)
    covered = set()

    # Assign BIO tags using character offsets.
    for start, end, entity in spans:

        matching = [
            i
            for i, (ts, te) in enumerate(
                encoding["offset_mapping"]
            )
            if ts != te and ts < end and te > start
        ]

        if not matching:
            raise ValueError(
                f"No tokenizer pieces for {entity}: "
                f"{record['record_id']}"
            )

        if any(i in covered for i in matching):
            raise ValueError(
                f"Overlapping token annotations: "
                f"{record['record_id']}"
            )

        for position, token_index in enumerate(matching):

            tags[token_index] = (
                "B-" if position == 0 else "I-"
            ) + entity

            covered.add(token_index)

    if len(tokens) != len(tags):
        raise ValueError(
            "Token/tag length mismatch"
        )

    unknown = set(tags) - VALID_LABELS

    if unknown:
        raise ValueError(
            f"Unknown BIO labels: {unknown}"
        )

    # Verify that every character span is represented.
    for start, end, entity in spans:

        represented = any(
            encoding["offset_mapping"][i][0] < end
            and encoding["offset_mapping"][i][1] > start
            and encoding["offset_mapping"][i][0]
                != encoding["offset_mapping"][i][1]
            for i in range(len(tags))
        )

        if not represented:
            raise ValueError(
                f"Unrepresented entity: {entity}"
            )

    return {
        "record_id": record["record_id"],
        "document_type": record["document_type"],
        "text": text,
        "tokens": tokens,
        "ner_tags": tags
    }


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    generators = {
        "invoice": generate_invoice,
        "prescription": generate_prescription,
        "discharge": generate_discharge,
        "insurance": generate_insurance
    }

    records = []
    counts = {}

    for doc_type, target in COUNTS.items():

        print(
            f"Generating {target} {doc_type} documents..."
        )

        for index in range(1, target + 1):

            raw = generators[doc_type](index)

            converted = convert_to_bio(raw)

            records.append(converted)

        counts[doc_type] = target

    random.shuffle(records)

    # Check coverage of all 34 entity types.
    observed = {
        tag[2:]
        for record in records
        for tag in record["ner_tags"]
        if tag.startswith("B-")
    }

    expected = VALID_ENTITIES

    missing = expected - observed

    if missing:
        raise ValueError(
            f"Missing entity types: {sorted(missing)}"
        )

    # Write only after all records pass validation.
    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        for record in records:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                ) + "\n"
            )

    print("\nV4 GENERATION COMPLETE")
    print("Total records:", len(records))
    print("Document distribution:", counts)
    print("Entity types covered:", len(observed))
    print("BIO labels available:", len(VALID_LABELS))
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
