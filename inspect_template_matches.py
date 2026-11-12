
import json
import re
from pathlib import Path

DATA = Path("data/ner_v2/splits")

TARGETS = {
    "SYN-INS-V2-0017",
    "SYN-INS-V2-0007",
    "SYN-DIS-V2-0008",
    "SYN-INS-V2-0014",
}

def normalize(text):
    text = text.lower()

    text = re.sub(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "<DATE>", text
    )

    text = re.sub(
        r"\binr\s*[\d,]+(?:\.\d+)?",
        "<AMOUNT>", text
    )

    text = re.sub(
        r"\b(?:pt|inv|pa|pat|clm)[-_]?[a-z0-9-]+\b",
        "<ID>", text
    )

    text = re.sub(r"\b\d+\b", "<NUM>", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def load_records(filename):
    with (DATA / filename).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


train = load_records("train.jsonl")
test = load_records("test.jsonl")

train_map = {}

for record in train:
    key = normalize(record["text"])
    train_map.setdefault(key, []).append(record)

print("\n========== EXACT TEMPLATE MATCHES ==========")

for record in test:

    if record["record_id"] not in TARGETS:
        continue

    key = normalize(record["text"])
    matches = train_map.get(key, [])

    print("\nTEST RECORD:", record["record_id"])

    for match in matches:
        print("MATCHING TRAIN RECORD:", match["record_id"])
        print("TEST TEXT:", record["text"])
        print("TRAIN TEXT:", match["text"])

print("\nMATCH INSPECTION COMPLETED")
