
import json
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path("data/ner_v2")

FILES = [
    DATA_DIR / "invoice_samples.jsonl",
    DATA_DIR / "prescription_samples.jsonl",
    DATA_DIR / "discharge_samples.jsonl",
    DATA_DIR / "insurance_samples.jsonl",
    Path("models/EvidenceBridge_BioBERT/india_ner_recovered_20_records_v2.jsonl")
]

SCHEMA_PATH = Path(
    "models/EvidenceBridge_BioBERT/india_ner_schema.json"
)

def load_records(path):
    if not path.exists():
        print(f"WARNING: Missing file: {path}")
        return []

    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    entity_types = sorted({
    label.split("-", 1)[1]
    for label in schema["labels"]
    if label != "O"
    })
    counts = Counter()
    document_counts = Counter()
    errors = []
    total_records = 0

    for path in FILES:
        records = load_records(path)

        for record in records:
            total_records += 1

            tokens = record["tokens"]
            tags = record["ner_tags"]
            record_id = record.get("record_id", "UNKNOWN")

            if len(tokens) != len(tags):
                errors.append(
                    f"{record_id}: token/tag length mismatch"
                )
                continue

            previous_entity = None

            for token, tag in zip(tokens, tags):
                if tag == "O":
                    previous_entity = None
                    continue

                if "-" not in tag:
                    errors.append(f"{record_id}: invalid tag {tag}")
                    previous_entity = None
                    continue

                prefix, entity = tag.split("-", 1)

                if entity not in entity_types:
                    errors.append(
                        f"{record_id}: unknown entity {entity}"
                    )

                if prefix == "B":
                    counts[entity] += 1
                    document_counts[entity] += 1
                    previous_entity = entity

                elif prefix == "I":
                    if previous_entity != entity:
                        errors.append(
                            f"{record_id}: invalid BIO transition "
                            f"{tag} after {previous_entity}"
                        )

                    else:
                        previous_entity = entity

                else:
                    errors.append(
                        f"{record_id}: invalid BIO prefix {prefix}"
                    )
                    previous_entity = None

    print("=" * 65)
    print("EVIDENCEBRIDGE - FULL NER ANNOTATION AUDIT")
    print("=" * 65)

    print("\nTotal records inspected:", total_records)
    print("Entity types in schema:", len(entity_types))

    print("\nENTITY FREQUENCY")
    print("-" * 65)

    for entity in sorted(entity_types):
        print(f"{entity:25} {counts[entity]:5}")

    print("\nMISSING ENTITY TYPES")
    print("-" * 65)

    missing = [
        entity for entity in entity_types
        if counts[entity] == 0
    ]

    print(missing if missing else "None")

    print("\nBIO ANNOTATION ERRORS")
    print("-" * 65)

    print("Total errors:", len(errors))

    for error in errors[:50]:
        print(error)

    if len(errors) > 50:
        print("Additional errors:", len(errors) - 50)

    print("\nAUDIT COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    main()
