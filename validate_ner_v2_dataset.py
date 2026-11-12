import json
from pathlib import Path
from collections import Counter

FILES = [
    "data/ner_v2/invoice_samples.jsonl",
    "data/ner_v2/prescription_samples.jsonl",
    "data/ner_v2/discharge_samples.jsonl",
    "data/ner_v2/insurance_samples.jsonl",
    "models/EvidenceBridge_BioBERT/india_ner_recovered_20_records_v2.jsonl",
]

all_records = []
errors = []
ids = set()
texts = set()
entity_counts = Counter()
document_counts = Counter()

for filename in FILES:
    path = Path(filename)

    if not path.exists():
        errors.append(f"Missing file: {filename}")
        continue

    with path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue

            record = json.loads(line)
            rid = record["record_id"]
            tokens = record["tokens"]
            labels = record["ner_tags"]

            if rid in ids:
                errors.append(f"Duplicate ID: {rid}")
            ids.add(rid)

            if record["text"] in texts:
                errors.append(f"Duplicate text: {rid}")
            texts.add(record["text"])

            if len(tokens) != len(labels):
                errors.append(f"Token-label mismatch: {rid}")
                continue

            if len(tokens) > 192:
                errors.append(f"Sequence exceeds 192 tokens: {rid}")

            previous_entity = None

            for label in labels:
                if label == "O":
                    previous_entity = None
                elif label.startswith("B-"):
                    entity = label[2:]
                    entity_counts[entity] += 1
                    previous_entity = entity
                elif label.startswith("I-"):
                    entity = label[2:]
                    if previous_entity != entity:
                        errors.append(
                            f"Invalid BIO transition: {rid} ({label})"
                        )
                    previous_entity = entity
                else:
                    errors.append(f"Invalid label: {rid} ({label})")

            document_counts[record["document_type"]] += 1
            all_records.append(record)

print("\nTOTAL DOCUMENTS:", len(all_records))
print("UNIQUE IDS:", len(ids))
print("UNIQUE TEXTS:", len(texts))
print("DOCUMENT DISTRIBUTION:", dict(document_counts))
print("ENTITY TYPES COVERED:", len(entity_counts))
print("ENTITY COUNTS:")

for entity, count in sorted(entity_counts.items()):
    print(f"{entity:25} {count}")

print("\nTOTAL VALIDATION ERRORS:", len(errors))

for error in errors[:30]:
    print(error)

print("\nDATASET VALIDATION COMPLETE")