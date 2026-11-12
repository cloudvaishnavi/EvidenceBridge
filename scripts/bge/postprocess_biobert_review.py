import json
from collections import Counter

SOURCE = "data/bge/evaluation/ekacare_20_biobert.json"
OUTPUT = "data/bge/evaluation/ekacare_20_biobert_review.json"

THRESHOLD = 0.50

ALLOWED = {
    "Prescription": {
        "PATIENT_NAME", "DATE", "DIAGNOSIS", "HOSPITAL",
        "BRAND_NAME", "GENERIC_NAME", "ACTIVE_INGREDIENT",
        "STRENGTH", "DOSAGE", "QUANTITY"
    },
    "Lab-report": {
        "PATIENT_NAME", "DATE", "DIAGNOSIS", "PROCEDURE",
        "HOSPITAL", "ADMISSION_DATE", "DISCHARGE_DATE"
    }
}

with open(SOURCE, encoding="utf-8-sig") as f:
    records = json.load(f)

summary = Counter()
review_records = []

for record in records:
    reviewed_entities = []

    for entity in record["entities"]:
        item = dict(entity)

        confidence_ok = entity["confidence"] >= THRESHOLD
        type_ok = entity["label"] in ALLOWED.get(
            record["document_type"], set()
        )

        if confidence_ok and type_ok:
            item["review_status"] = "CANDIDATE_NOT_VERIFIED"
            summary["candidate_not_verified"] += 1
        else:
            item["review_status"] = "REVIEW_REQUIRED"

            if not confidence_ok:
                item["review_reason"] = "LOW_CONFIDENCE"
                summary["low_confidence"] += 1
            else:
                item["review_reason"] = "DOCUMENT_TYPE_MISMATCH"
                summary["type_mismatch"] += 1

        reviewed_entities.append(item)

    review_records.append({
        **record,
        "entities": reviewed_entities
    })

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(review_records, f, ensure_ascii=False, indent=2)

print("Documents:", len(review_records))
print("Original predictions:", sum(len(r["entities"]) for r in records))
print("\nReview summary:")
for key, value in summary.items():
    print(f"{key}: {value}")

print("\nSaved:", OUTPUT)
print("Original BioBERT output remains unchanged.")
