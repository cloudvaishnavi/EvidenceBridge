
import json
from pathlib import Path
from collections import Counter

ROOT = Path("data/ner_v3/splits")
SCHEMA_PATH = Path("models/EvidenceBridge_BioBERT/india_ner_schema.json")

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    schema = json.load(f)

entity_types = {
    label[2:]
    for label in schema["labels"]
    if label.startswith("B-")
}

print("=" * 65)
print("EVIDENCEBRIDGE - V3 SPLIT ENTITY COVERAGE AUDIT")
print("=" * 65)

all_passed = True

for split_name in ["train", "validation", "test"]:
    file_path = ROOT / f"{split_name}.jsonl"
    counts = Counter()
    records = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)
            records += 1

            tags = record.get("ner_tags", record.get("tags", []))

            for tag in tags:
                if tag.startswith("B-"):
                    counts[tag[2:]] += 1

    missing = sorted(entity_types - set(counts))

    print(f"\n{split_name.upper()}")
    print("-" * 50)
    print(f"Records: {records}")
    print(f"Entity types present: {len(counts)}/{len(entity_types)}")
    print(f"Missing entity types: {missing if missing else 'None'}")

    if missing:
        all_passed = False

print("\n" + "=" * 65)
print("FINAL RESULT:", "ALL SPLITS HAVE FULL ENTITY COVERAGE"
      if all_passed else "SOME ENTITY TYPES ARE MISSING")
print("=" * 65)
