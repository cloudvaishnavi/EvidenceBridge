
import json
from pathlib import Path
from collections import Counter
from sklearn.model_selection import train_test_split

FILES = [
    "data/ner_v2/invoice_samples.jsonl",
    "data/ner_v2/prescription_samples.jsonl",
    "data/ner_v2/discharge_samples.jsonl",
    "data/ner_v2/insurance_samples.jsonl",
    "models/EvidenceBridge_BioBERT/india_ner_recovered_20_records_v2.jsonl",
]

OUTPUT = Path("data/ner_v2/splits")
OUTPUT.mkdir(parents=True, exist_ok=True)

records = []

for filename in FILES:
    with open(filename, encoding="utf-8") as f:
        records.extend(
            json.loads(line)
            for line in f if line.strip()
        )

# Split by document type to preserve category balance.
train_val, test = train_test_split(
    records,
    test_size=0.15,
    random_state=42,
    stratify=[r["document_type"] for r in records]
)

train, val = train_test_split(
    train_val,
    test_size=0.15 / 0.85,
    random_state=42,
    stratify=[r["document_type"] for r in train_val]
)

splits = {
    "train": train,
    "validation": val,
    "test": test
}

for name, data in splits.items():
    path = OUTPUT / f"{name}.jsonl"

    with path.open("w", encoding="utf-8") as f:
        for record in data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"{name.upper()}: {len(data)} documents")
    print("  Distribution:", dict(Counter(
        r["document_type"] for r in data
    )))

print("\nTOTAL:", sum(len(x) for x in splits.values()))
print("SPLITS CREATED:", OUTPUT)
