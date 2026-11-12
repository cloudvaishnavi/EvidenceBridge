
import json
from pathlib import Path
from transformers import AutoTokenizer

MODEL_PATH = "models/EvidenceBridge_BioBERT/baseline_v1"
DATA_DIR = Path("data/ner_v2/splits")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    use_fast=True,
    local_files_only=True
)

for split in ["train", "validation", "test"]:
    path = DATA_DIR / f"{split}.jsonl"

    with path.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    for record in records:
        ids = tokenizer.convert_tokens_to_ids(record["tokens"])

        unknown = [
            (token, label)
            for token, token_id, label in zip(
                record["tokens"], ids, record["ner_tags"]
            )
            if token_id == tokenizer.unk_token_id
        ]

        if unknown:
            print("\nSPLIT:", split)
            print("RECORD:", record["record_id"])
            print("UNKNOWN TOKENS:")
            for token, label in unknown:
                print(repr(token), "->", label)

            print("\nORIGINAL TEXT:")
            print(record["text"])
