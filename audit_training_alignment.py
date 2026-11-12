
import json
from pathlib import Path
from transformers import AutoTokenizer

BASE_MODEL = "models/EvidenceBridge_BioBERT/baseline_v1"
DATA_DIR = Path("data/ner_v2/splits")

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    use_fast=True,
    local_files_only=True
)

def audit_record(record):
    text = record["text"]
    tokens = record["tokens"]
    tags = record["ner_tags"]

    cursor = 0
    spans = []

    for token, label in zip(tokens, tags):

    # Skip tokenizer special tokens
        if token in tokenizer.all_special_tokens:
            continue

        clean = token[2:] if token.startswith("##") else token
        start = text.lower().find(clean.lower(), cursor)

        if start == -1:
            return False, f"Cannot locate token: {token}"

        end = start + len(clean)
        spans.append((start, end, label))
        cursor = end

    encoding = tokenizer(
        text,
        return_offsets_mapping=True,
        truncation=True,
        max_length=192
    )

    mismatches = []

    for start, end in encoding["offset_mapping"]:
        if start == end:
            continue

        matches = [
            (ws, we, label)
            for ws, we, label in spans
            if ws < end and we > start
        ]

        if len(matches) != 1:
            mismatches.append(
                f"Offset {start}-{end}: {len(matches)} matches"
            )

    return len(mismatches) == 0, mismatches


total = 0
passed = 0
failed = []

for split in ["train.jsonl", "validation.jsonl", "test.jsonl"]:
    path = DATA_DIR / split

    with path.open(encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            total += 1

            ok, result = audit_record(record)

            if ok:
                passed += 1
            else:
                failed.append((record["record_id"], result))

print("\n========== ALIGNMENT AUDIT ==========")
print("Total records:", total)
print("Passed:", passed)
print("Failed:", len(failed))

for record_id, errors in failed[:10]:
    print("\n", record_id, errors)

print("\nAUDIT COMPLETED")
