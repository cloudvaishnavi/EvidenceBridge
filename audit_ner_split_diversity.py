
import json
import re
from pathlib import Path
from collections import defaultdict, Counter

DATA = Path("data/ner_v2/splits")

TARGETS = {
    "APPROVED_AMOUNT",
    "BRAND_NAME",
    "CLAIM_AMOUNT",
    "DISCOUNT",
    "INSURANCE_DEDUCTION",
    "INVOICE_TOTAL",
    "LINE_AMOUNT",
    "SUBTOTAL",
    "UNIT_PRICE",
}

def extract_entities(path):
    results = defaultdict(list)

    with path.open(encoding="utf-8") as f:
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
                j = i + 1

                while (
                    j < len(spans)
                    and spans[j][2] == f"I-{entity}"
                ):
                    j += 1

                if entity in TARGETS:
                    value = text[start:spans[j - 1][1]]
                    normalized = re.sub(
                        r"\s+", " ", value.lower().strip()
                    )

                    results[entity].append(normalized)

                i = j

    return results


splits = {}

for name in ["train", "validation", "test"]:
    splits[name] = extract_entities(
        DATA / f"{name}.jsonl"
    )

print("\n========== DATASET DIVERSITY ==========")

for entity in sorted(TARGETS):
    print(f"\n{entity}")

    for split_name, records in splits.items():
        values = records[entity]

        print(
            f"{split_name:12} "
            f"total={len(values):3} "
            f"unique={len(set(values)):3}"
        )

    train_values = set(splits["train"][entity])
    test_values = set(splits["test"][entity])

    shared = train_values.intersection(test_values)

    print("Shared train/test values:", len(shared))

print("\nDIVERSITY AUDIT COMPLETED")
