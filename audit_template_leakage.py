
import json
import re
from pathlib import Path
from collections import defaultdict

DATA = Path("data/ner_v2/splits")

def normalize(text):
    text = text.lower()

    # Replace dates
    text = re.sub(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "<DATE>", text
    )

    # Replace INR amounts
    text = re.sub(
        r"\binr\s*[\d,]+(?:\.\d+)?",
        "<AMOUNT>", text
    )

    # Replace IDs and reference numbers
    text = re.sub(
        r"\b(?:pt|inv|pa|pat|clm)[-_]?[a-z0-9-]+\b",
        "<ID>", text
    )

    # Replace remaining long numeric sequences
    text = re.sub(r"\b\d+\b", "<NUM>", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def load_split(filename):
    records = []

    with (DATA / filename).open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)

            records.append({
                "id": record["record_id"],
                "template": normalize(record["text"])
            })

    return records


train = load_split("train.jsonl")
validation = load_split("validation.jsonl")
test = load_split("test.jsonl")

train_templates = defaultdict(list)

for record in train:
    train_templates[record["template"]].append(record["id"])

print("\n========== TEMPLATE LEAKAGE AUDIT ==========")

for name, records in [
    ("VALIDATION", validation),
    ("TEST", test)
]:
    exact_matches = []

    for record in records:
        if record["template"] in train_templates:
            exact_matches.append(record["id"])

    print(f"\n{name}")
    print("Total records:", len(records))
    print("Matching training templates:", len(exact_matches))
    print("Unique templates:", len(set(r["template"] for r in records)))

    for record_id in exact_matches[:10]:
        print("Matching record:", record_id)

print("\nTEMPLATE AUDIT COMPLETED")
