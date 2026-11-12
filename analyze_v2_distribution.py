import json
from pathlib import Path
from collections import Counter

path = Path(
    "models/EvidenceBridge_BioBERT/"
    "india_ner_recovered_20_records_v2.jsonl"
)

with open(path, encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

counts = Counter()

for record in records:
    for label in record["ner_tags"]:
        if label.startswith("B-"):
            counts[label[2:]] += 1

print("ENTITY DISTRIBUTION — DATASET V2")
print("=" * 55)

for entity, count in sorted(counts.items()):
    print(f"{entity:25} {count:4}")

print("\nTotal entity mentions:", sum(counts.values()))
print("Entity types represented:", len(counts))
print("Entity types missing:", 33 - len(counts))