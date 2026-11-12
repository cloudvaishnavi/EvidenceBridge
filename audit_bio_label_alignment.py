
import json
from pathlib import Path
from transformers import AutoTokenizer

# ============================================================
# CONFIGURATION
# ============================================================

BASE = "models/EvidenceBridge_BioBERT/baseline_v1"
DATA = Path("data/ner_v2/splits")
SCHEMA_PATH = Path(
    "models/EvidenceBridge_BioBERT/india_ner_schema.json"
)

MAX_LENGTH = 192

# ============================================================
# LOAD TOKENIZER AND SCHEMA
# ============================================================

tokenizer = AutoTokenizer.from_pretrained(
    BASE,
    use_fast=True,
    local_files_only=True
)

with SCHEMA_PATH.open(encoding="utf-8") as f:
    schema = json.load(f)

label2id = schema["label2id"]

print("Tokenizer loaded:", tokenizer.is_fast)
print("Schema labels:", len(label2id))

# ============================================================
# AUDIT
# ============================================================

checked = 0
errors = []
records_checked = 0

for split in ["train.jsonl", "validation.jsonl", "test.jsonl"]:

    print(f"\nChecking {split}...")

    with (DATA / split).open(encoding="utf-8") as f:

        for line in f:

            if not line.strip():
                continue

            record = json.loads(line)
            records_checked += 1

            text = record["text"]
            tokens = record["tokens"]
            tags = record["ner_tags"]

            if len(tokens) != len(tags):
                errors.append(
                    (record["record_id"], "TOKEN_TAG_LENGTH_MISMATCH")
                )
                continue

            # Recover original annotation character spans.
            spans = []
            cursor = 0

            for token, label in zip(tokens, tags):

                if token in tokenizer.all_special_tokens:
                    continue

                clean = (
                    token[2:]
                    if token.startswith("##")
                    else token
                )

                start = text.lower().find(
                    clean.lower(), cursor
                )

                if start == -1:
                    errors.append(
                        (
                            record["record_id"],
                            f"TOKEN_NOT_FOUND: {token}"
                        )
                    )
                    continue

                end = start + len(clean)

                spans.append((start, end, label))
                cursor = end

            # Tokenize original document.
            encoding = tokenizer(
                text,
                return_offsets_mapping=True,
                truncation=True,
                max_length=MAX_LENGTH
            )

            previous_index = None

            for start, end in encoding["offset_mapping"]:

                # Ignore special tokens.
                if start == end:
                    previous_index = None
                    continue

                matches = [
                    (i, ws, we, label)
                    for i, (ws, we, label) in enumerate(spans)
                    if ws < end and we > start
                ]

                # Every document token must match exactly one span.
                if len(matches) != 1:

                    errors.append(
                        (
                            record["record_id"],
                            f"SPAN_MATCH_ERROR: {start}-{end}, "
                            f"matches={len(matches)}"
                        )
                    )

                    previous_index = None
                    continue

                index, ws, we, original_label = matches[0]

                # Determine expected BIO label.
                expected = original_label

                if original_label.startswith("B-"):

                    if previous_index == index:
                        expected = "I-" + original_label[2:]

                # Verify the expected label exists in schema.
                if expected not in label2id:

                    errors.append(
                        (
                            record["record_id"],
                            f"UNKNOWN_SCHEMA_LABEL: {expected}"
                        )
                    )

                checked += 1
                previous_index = index

# ============================================================
# RESULTS
# ============================================================

print("\n" + "=" * 55)
print("BIO LABEL ALIGNMENT AUDIT RESULTS")
print("=" * 55)

print("Records checked:", records_checked)
print("Tokenizer pieces checked:", checked)
print("Errors:", len(errors))

if errors:

    print("\nFirst 20 errors:")

    for error in errors[:20]:
        print(error)

else:

    print("\nAll tokenizer pieces passed the alignment checks.")

print("\nLABEL ALIGNMENT AUDIT COMPLETED")
