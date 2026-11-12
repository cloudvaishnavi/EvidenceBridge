import json
from pathlib import Path
from collections import defaultdict

TRAIN = Path("data/ner_v3/splits/train.jsonl")

TARGETS = {
    "GENERIC_NAME",
    "BRAND_NAME",
    "ACTIVE_INGREDIENT",
    "UNIT_PRICE",
    "LINE_AMOUNT",
    "SUBTOTAL",
    "INVOICE_TOTAL",
    "INSURANCE_DEDUCTION",
    "PATIENT_NAME",
    "QUANTITY",
}

def extract_entities(record):
    entities = []
    current_tokens = []
    current_label = None

    for token, tag in zip(record["tokens"], record["ner_tags"]):
        if tag.startswith("B-"):
            if current_tokens:
                entities.append((current_label, " ".join(current_tokens)))

            current_label = tag[2:]
            current_tokens = [token.replace("##", "")]

        elif tag.startswith("I-") and current_tokens:
            current_tokens.append(token.replace("##", ""))

        else:
            if current_tokens:
                entities.append((current_label, " ".join(current_tokens)))
            current_tokens = []
            current_label = None

    if current_tokens:
        entities.append((current_label, " ".join(current_tokens)))

    return entities


groups = defaultdict(list)

with open(TRAIN, encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)

        for label, value in extract_entities(record):
            if label in TARGETS:
                groups[label].append(
                    (record["record_id"], value)
                )

for label in sorted(TARGETS):
    print(f"\n{'=' * 60}")
    print(label, "| examples:", len(groups[label]))
    print("=" * 60)

    for record_id, value in groups[label][:12]:
        print(record_id, ":", value)