
import json
import re
from pathlib import Path
from collections import defaultdict
from sklearn.model_selection import GroupShuffleSplit

# ============================================================
# CONFIGURATION
# ============================================================

SOURCE_DIR = Path("data/ner_v2/splits")
OUTPUT_DIR = Path("data/ner_v3/splits")

FILES = [
    "train.jsonl",
    "validation.jsonl",
    "test.jsonl"
]

# ============================================================
# TEMPLATE NORMALIZATION
# ============================================================

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


# ============================================================
# LOAD ALL EXISTING RECORDS
# ============================================================

records = []
seen_ids = set()

for filename in FILES:

    path = SOURCE_DIR / filename

    with path.open(encoding="utf-8") as f:

        for line in f:

            if not line.strip():
                continue

            record = json.loads(line)
            record_id = record["record_id"]

            if record_id in seen_ids:
                raise ValueError(
                    f"Duplicate record ID: {record_id}"
                )

            seen_ids.add(record_id)
            records.append(record)

print("Total records loaded:", len(records))

# ============================================================
# BUILD TEMPLATE GROUPS
# ============================================================

template_to_group = {}
groups = []

for record in records:

    signature = normalize(record["text"])

    if signature not in template_to_group:
        template_to_group[signature] = len(template_to_group)

    groups.append(template_to_group[signature])

print("Unique template groups:", len(set(groups)))

# ============================================================
# GROUP-AWARE TRAIN / VALIDATION / TEST SPLIT
# ============================================================

splitter_1 = GroupShuffleSplit(
    n_splits=1,
    test_size=0.15,
    random_state=42
)

trainval_idx, test_idx = next(
    splitter_1.split(records, groups=groups)
)

trainval_records = [records[i] for i in trainval_idx]
trainval_groups = [groups[i] for i in trainval_idx]

splitter_2 = GroupShuffleSplit(
    n_splits=1,
    test_size=0.1764705882,
    random_state=43
)

train_idx, val_idx = next(
    splitter_2.split(
        trainval_records,
        groups=trainval_groups
    )
)

train_records = [trainval_records[i] for i in train_idx]
val_records = [trainval_records[i] for i in val_idx]
test_records = [records[i] for i in test_idx]

# ============================================================
# VERIFY GROUP SEPARATION
# ============================================================

def get_signatures(data):
    return {normalize(record["text"]) for record in data}

train_signatures = get_signatures(train_records)
val_signatures = get_signatures(val_records)
test_signatures = get_signatures(test_records)

assert not (train_signatures & val_signatures)
assert not (train_signatures & test_signatures)
assert not (val_signatures & test_signatures)

# ============================================================
# SAVE V3 SPLITS
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

splits = {
    "train": train_records,
    "validation": val_records,
    "test": test_records
}

for name, data in splits.items():

    path = OUTPUT_DIR / f"{name}.jsonl"

    with path.open("w", encoding="utf-8") as f:

        for record in data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"{name}: {len(data)} records saved")

# ============================================================
# FINAL REPORT
# ============================================================

print("\n========== V3 SPLIT REPORT ==========")

print("Total:", len(records))
print("Train:", len(train_records))
print("Validation:", len(val_records))
print("Test:", len(test_records))

print("Train/validation overlap:", len(
    train_signatures & val_signatures
))

print("Train/test overlap:", len(
    train_signatures & test_signatures
))

print("Validation/test overlap:", len(
    val_signatures & test_signatures
))

print("\nV3 GROUP-AWARE SPLITS CREATED")
print("Original V2 splits remain untouched.")
