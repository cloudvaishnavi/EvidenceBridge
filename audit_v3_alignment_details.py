import json
from pathlib import Path
from collections import Counter

from transformers import AutoTokenizer

BASE_MODEL = "models/EvidenceBridge_BioBERT/baseline_v1"
DATA_DIR = Path("data/ner_v3/splits")

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    use_fast=True
)

counts = Counter()
examples = []

for split in ["train", "validation", "test"]:
    path = DATA_DIR / f"{split}.jsonl"

    with open(path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    for record in records:
        text = record["text"]
        spans = []
        cursor = 0

        for token, label in zip(
            record["tokens"], record["ner_tags"]
        ):
            clean = token[2:] if token.startswith("##") else token

            if clean in tokenizer.all_special_tokens:
                continue

            start = text.lower().find(clean.lower(), cursor)

            if start == -1:
                continue

            end = start + len(clean)
            spans.append((start, end, label))
            cursor = end

        encoding = tokenizer(
            text,
            truncation=True,
            max_length=192,
            return_offsets_mapping=True
        )

        for token_id, (start, end) in zip(
            encoding["input_ids"],
            encoding["offset_mapping"]
        ):
            if start == end:
                continue

            match = next(
                (
                    label for ws, we, label in spans
                    if ws < end and we > start
                ),
                None
            )

            if match is None:
                counts["unmatched"] += 1
                if len(examples) < 15:
                    examples.append(
                        (record["record_id"],
                         tokenizer.convert_ids_to_tokens(token_id),
                         text[start:end])
                    )
            else:
                counts["matched"] += 1

print("ALIGNMENT COUNTS:", dict(counts))
print("\nUNMATCHED EXAMPLES:")

for example in examples:
    print(example)