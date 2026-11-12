
import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path("models/EvidenceBridge_BioBERT/baseline_v1")

dataset_file = DATA_DIR / "dataset.jsonl"
labels_file = DATA_DIR / "label_mapping.json"

print("=" * 55)
print("BIOBERT DATASET INSPECTION")
print("=" * 55)

# Load records
records = []

with open(dataset_file, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

# Load label mapping
with open(labels_file, "r", encoding="utf-8") as f:
    label_mapping = json.load(f)

print("\nTotal records:", len(records))
print("Total labels:", len(label_mapping))

print("\nLABEL MAPPING:")
print(label_mapping)

print("\nFIRST TWO RECORDS:")
for record in records[:2]:
    print(json.dumps(record, indent=2, ensure_ascii=False))

print("\nRECORD KEYS:")
if records:
    print(list(records[0].keys()))

print("\nDATASET INSPECTION COMPLETE")
