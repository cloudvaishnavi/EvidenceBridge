import json
from pathlib import Path

source = Path(
    "models/EvidenceBridge_BioBERT/india_ner_recovered_20_records.jsonl"
)

output = Path(
    "models/EvidenceBridge_BioBERT/india_ner_recovered_20_records_corrected.jsonl"
)

records = [
    json.loads(line)
    for line in source.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

record = next(r for r in records if r["record_id"] == "INV-102")

# Verify expected tokens before modifying anything.
assert record["tokens"][10] == "102"
assert record["tokens"][12] == "2"

# Correct the two incorrect labels.
record["ner_tags"][10] = "I-INVOICE_NUMBER"
record["ner_tags"][12] = "B-QUANTITY"

# Save to a NEW file. Preserve the original.
with output.open("w", encoding="utf-8") as f:
    for item in records:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("INV-102 annotations corrected.")
print("Saved to:", output)

for token, label in zip(record["tokens"], record["ner_tags"]):
    print(f"{token:22} {label}")