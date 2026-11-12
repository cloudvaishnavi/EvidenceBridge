
import json
from transformers import AutoTokenizer

MODEL_DIR = "models/EvidenceBridge_BioBERT/baseline_v1"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    use_fast=True,
    local_files_only=True
)

path = "data/ner_v2/invoice_samples.jsonl"

with open(path, "r", encoding="utf-8") as f:
    record = json.loads(f.readline())

text = record["text"]

encoding = tokenizer(
    text,
    return_offsets_mapping=True,
    truncation=True,
    max_length=192
)

print("=" * 75)
print("WORDPIECE TOKEN ALIGNMENT DIAGNOSTIC")
print("=" * 75)

for token_id, (start, end) in zip(
    encoding["input_ids"],
    encoding["offset_mapping"]
):
    token = tokenizer.convert_ids_to_tokens(token_id)

    if start == end:
        continue

    print(
        f"{token:20} | "
        f"{text[start:end]:20} | "
        f"{start:3}-{end:3}"
    )

print("\nDIAGNOSTIC COMPLETED")
