
import json
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path("data/ner_v2/splits")

WEAK_ENTITIES = [
    "APPROVED_AMOUNT",
    "BRAND_NAME",
    "CLAIM_AMOUNT",
    "DISCOUNT",
    "INSURANCE_DEDUCTION",
    "INVOICE_TOTAL",
    "LINE_AMOUNT",
    "SUBTOTAL",
    "UNIT_PRICE",
]

counts = Counter()
examples = defaultdict(list)

with (DATA / "train.jsonl").open(encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)

        tokens = record["tokens"]
        tags = record["ner_tags"]

        current_tokens = []
        current_entity = None

        for token, tag in zip(tokens, tags):

            if tag.startswith("B-"):
                if current_entity:
                    entity_text = "".join(current_tokens).replace("##", "")
                    examples[current_entity].append(entity_text)

                current_entity = tag[2:]
                current_tokens = [token]

            elif tag.startswith("I-") and current_entity == tag[2:]:
                current_tokens.append(token)

            else:
                if current_entity:
                    entity_text = "".join(current_tokens).replace("##", "")
                    examples[current_entity].append(entity_text)

                current_entity = None
                current_tokens = []

        if current_entity:
            entity_text = "".join(current_tokens).replace("##", "")
            examples[current_entity].append(entity_text)

for entity in WEAK_ENTITIES:
    counts[entity] = len(examples[entity])

print("\n========== WEAK ENTITY TRAINING AUDIT ==========")

for entity in WEAK_ENTITIES:
    print(f"\n{entity}: {counts[entity]} training examples")

    for example in examples[entity][:8]:
        print("  -", example)

print("\nAUDIT COMPLETED")
