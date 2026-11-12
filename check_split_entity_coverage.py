
import json
from pathlib import Path
from collections import Counter

SPLIT_DIR = Path("data/ner_v2/splits")

for split in ["train", "validation", "test"]:
    path = SPLIT_DIR / f"{split}.jsonl"
    counts = Counter()

    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)

            for label in record["ner_tags"]:
                if label.startswith("B-"):
                    counts[label[2:]] += 1

    print(f"\n{split.upper()} ENTITY COVERAGE")
    print("Entity types:", len(counts))
    print("GSTIN:", counts["GSTIN"])
    print("HSN_SAC:", counts["HSN_SAC"])

    print("Missing entities:")
    print(sorted(set([
        "PATIENT_ID", "HOSPITAL", "INVOICE_NUMBER", "GSTIN",
        "INSURER", "TPA", "POLICY_NUMBER", "DIAGNOSIS",
        "PROCEDURE", "BRAND_NAME", "GENERIC_NAME",
        "ACTIVE_INGREDIENT", "STRENGTH", "DOSAGE", "DATE",
        "ADMISSION_DATE", "DISCHARGE_DATE", "INVOICE_TOTAL",
        "LINE_AMOUNT", "TAX_AMOUNT", "DISCOUNT", "UNIT_PRICE",
        "QUANTITY", "HSN_SAC", "ROOM_TYPE", "PACKAGE_CODE",
        "CLAIM_AMOUNT", "APPROVED_AMOUNT", "PATIENT_PAYABLE",
        "INSURANCE_DEDUCTION", "SUBTOTAL", "PREAUTH_NUMBER",
        "CLAIM_REFERENCE"
    ]) - set(counts)))
