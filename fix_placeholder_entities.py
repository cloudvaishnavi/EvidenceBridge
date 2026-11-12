import json
from pathlib import Path

path = Path(
    "models/EvidenceBridge_BioBERT/"
    "india_ner_recovered_20_records_corrected.jsonl"
)

records = [
    json.loads(line)
    for line in path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

targets = {
    "SYN-INV-GSTIN-001": "GSTIN",
    "SYN-INV-HSN-001": "HSN_SAC"
}

for record in records:
    if record["record_id"] not in targets:
        continue

    entity = targets[record["record_id"]]

    for i, label in enumerate(record["ner_tags"]):
        if label in (f"B-{entity}", f"I-{entity}"):
            record["ner_tags"][i] = "O"

    print(f"Corrected placeholder: {record['record_id']}")

output = path.with_name("india_ner_recovered_20_records_v2.jsonl")

with output.open("w", encoding="utf-8") as f:
    for record in records:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print("\nSaved:", output)