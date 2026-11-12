
import json
from pathlib import Path
from collections import defaultdict

DATA = Path("data/ner_v2/splits/train.jsonl")

TARGETS = [
    "APPROVED_AMOUNT",
    "CLAIM_AMOUNT",
    "DISCOUNT",
    "INSURANCE_DEDUCTION",
    "INVOICE_TOTAL",
    "LINE_AMOUNT",
    "SUBTOTAL",
    "UNIT_PRICE",
    "BRAND_NAME"
]

examples = defaultdict(list)

with DATA.open(encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)

        text = record["text"]
        tokens = record["tokens"]
        tags = record["ner_tags"]

        cursor = 0
        spans = []

        for token, tag in zip(tokens, tags):
            if token in {"[CLS]", "[SEP]", "[PAD]"}:
                continue

            clean = token[2:] if token.startswith("##") else token
            start = text.lower().find(clean.lower(), cursor)

            if start == -1:
                continue

            end = start + len(clean)
            spans.append((start, end, tag))
            cursor = end

        i = 0

        while i < len(spans):
            start, end, tag = spans[i]

            if not tag.startswith("B-"):
                i += 1
                continue

            entity = tag[2:]

            if entity not in TARGETS:
                i += 1
                continue

            j = i + 1

            while (
                j < len(spans)
                and spans[j][2] == f"I-{entity}"
            ):
                j += 1

            entity_start = start
            entity_end = spans[j - 1][1]

            value = text[entity_start:entity_end]

            context_start = max(0, entity_start - 65)
            context_end = min(len(text), entity_end + 65)

            context = text[context_start:context_end]

            examples[entity].append({
                "value": value,
                "context": context,
                "record": record["record_id"]
            })

            i = j

print("\n========== ENTITY CONTEXT AUDIT ==========")

for entity in TARGETS:
    print(f"\n\n### {entity}")

    for item in examples[entity][:4]:
        print("\nValue:", item["value"])
        print("Context:", item["context"])
        print("Record:", item["record"])

print("\nCONTEXT AUDIT COMPLETED")
