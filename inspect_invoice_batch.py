import json
from pathlib import Path

path = Path("data/ner_v2/invoice_samples.jsonl")

with open(path, encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

print("TOTAL INVOICES:", len(records))

for record in records[:3]:
    print("\n", "=" * 60)
    print("ID:", record["record_id"])
    print("TEXT:", record["text"])
    print("TOKEN-LABEL ALIGNMENT:", len(record["tokens"]) == len(record["ner_tags"]))

    print("\nExtracted entities:")

    for token, label in zip(record["tokens"], record["ner_tags"]):
        if label.startswith("B-"):
            print(f"{label[2:]:22} {token}")

print("\nINSPECTION COMPLETE")