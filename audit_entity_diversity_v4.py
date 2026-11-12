import json
from collections import defaultdict

PATH = "data/ner_v3/splits/train.jsonl"

targets = {
    "GENERIC_NAME", "BRAND_NAME", "ACTIVE_INGREDIENT",
    "UNIT_PRICE", "LINE_AMOUNT", "SUBTOTAL",
    "INVOICE_TOTAL", "INSURANCE_DEDUCTION"
}

values = defaultdict(set)

with open(PATH, encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

for record in records:
    text = record["text"]
    cursor = 0
    active_label = None
    entity_start = None
    entity_end = None

    def save_entity():
        if active_label in targets and entity_start is not None:
            value = text[entity_start:entity_end].strip()
            values[active_label].add(value)

    for token, tag in zip(record["tokens"], record["ner_tags"]):
        clean = token[2:] if token.startswith("##") else token

        if clean in {"[CLS]", "[SEP]", "[PAD]"}:
            continue

        start = text.lower().find(clean.lower(), cursor)
        if start == -1:
            continue

        end = start + len(clean)
        cursor = end

        if tag.startswith("B-"):
            save_entity()
            active_label = tag[2:]
            entity_start = start
            entity_end = end

        elif tag.startswith("I-") and active_label == tag[2:]:
            entity_end = end

        else:
            save_entity()
            active_label = None
            entity_start = None
            entity_end = None

    save_entity()

for label in sorted(targets):
    print(f"\n{label}: {len(values[label])} unique values")
    for value in sorted(values[label])[:20]:
        print("  ", value)
        