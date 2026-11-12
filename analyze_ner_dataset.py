
import json
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path("models/EvidenceBridge_BioBERT/baseline_v1")

with open(DATA_DIR / "dataset.jsonl", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

with open(DATA_DIR / "label_mapping.json", encoding="utf-8") as f:
    label2id = json.load(f)

id2label = {v: k for k, v in label2id.items()}

entity_counts = Counter()
document_counts = Counter()
document_types = Counter()
invalid_bio = []

for record in records:
    tags = [id2label[x] for x in record["ner_tags"]]
    tokens = record["tokens"]

    document_types[record["document_type"]] += 1

    for tag in tags:
        if tag.startswith("B-"):
            entity = tag[2:]
            entity_counts[entity] += 1
            document_counts[entity] += 1

    if len(tokens) != len(tags):
        invalid_bio.append(record["record_id"])

    for i, tag in enumerate(tags):
        if tag.startswith("I-"):
            entity = tag[2:]
            if i == 0 or tags[i-1] not in [f"B-{entity}", f"I-{entity}"]:
                invalid_bio.append(record["record_id"])
                break

print("=" * 55)
print("BIOBERT DATASET QUALITY REPORT")
print("=" * 55)

print("\nDOCUMENT DISTRIBUTION:")
for name, count in document_types.items():
    print(name, ":", count)

print("\nENTITY MENTION COUNTS:")
for entity, count in sorted(entity_counts.items()):
    print(f"{entity:25s}: {count}")

print("\nENTITY TYPES FOUND:", len(entity_counts))
print("TOTAL ENTITY MENTIONS:", sum(entity_counts.values()))

missing = set(
    label[2:] for label in label2id
    if label.startswith("B-")
) - set(entity_counts)

print("\nENTITY TYPES WITH ZERO EXAMPLES:")
print(sorted(missing))

print("\nBIO ALIGNMENT ISSUES:", invalid_bio)

print("\nDATASET QUALITY ANALYSIS COMPLETE")
