import json
from pathlib import Path

path = Path(
    "models/EvidenceBridge_BioBERT/"
    "india_ner_recovered_20_records_v2.jsonl"
)

with open(path, "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

errors = []

for record in records:
    tokens = record["tokens"]
    labels = record["ner_tags"]
    rid = record["record_id"]

    if len(tokens) != len(labels):
        errors.append(f"{rid}: token-label length mismatch")
        continue

    for i, label in enumerate(labels):
        if label.startswith("I-"):
            entity = label[2:]

            if i == 0 or labels[i - 1] not in (
                f"B-{entity}", f"I-{entity}"
            ):
                errors.append(
                    f"{rid}: invalid {label} at token {i}"
                )

print("TOTAL RECORDS:", len(records))
print("STRUCTURAL ERRORS:", len(errors))

for error in errors:
    print(error)

print(
    "VALIDATION PASSED"
    if not errors
    else "VALIDATION FAILED"
)