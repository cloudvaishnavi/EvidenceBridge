
import json
import re
from pathlib import Path
from collections import defaultdict

DATA = Path("data/ner_v2/splits")

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


families = defaultdict(list)

for split in ["train", "validation", "test"]:

    path = DATA / f"{split}.jsonl"

    with path.open(encoding="utf-8") as f:
        for line in f:

            if not line.strip():
                continue

            record = json.loads(line)
            template = normalize(record["text"])

            families[template].append({
                "id": record["record_id"],
                "split": split
            })


print("\n========== TEMPLATE FAMILY REPORT ==========")

print("Total records:", sum(len(v) for v in families.values()))
print("Unique template families:", len(families))

for index, (template, records) in enumerate(
    families.items(), start=1
):
    splits = sorted(set(r["split"] for r in records))

    print(f"\nFamily {index}")
    print("Records:", len(records))
    print("Splits:", ", ".join(splits))
    print("Record IDs:", ", ".join(r["id"] for r in records))

    if len(splits) > 1:
        print("WARNING: TEMPLATE SHARED ACROSS SPLITS")

print("\nTEMPLATE FAMILY AUDIT COMPLETED")
