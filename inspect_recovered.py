import json
from pathlib import Path

path = Path("models/EvidenceBridge_BioBERT/india_ner_recovered_20_records.jsonl")

with open(path, "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

print("RECOVERED DATASET")
print("=" * 60)
print("Total records:", len(records))

for i, record in enumerate(records[:3], 1):
    print(f"\nRECORD {i}")
    print("-" * 60)

    print("Record ID:", record.get("record_id"))
    print("Document type:", record.get("document_type"))
    print("Text:", record.get("text"))
    print("Token count:", len(record.get("tokens", [])))
    print("Label count:", len(record.get("ner_tags", [])))

    print("\nFirst 30 token-label pairs:")
    for token, label in zip(
        record.get("tokens", [])[:30],
        record.get("ner_tags", [])[:30]
    ):
        print(f"{token:25} {label}")