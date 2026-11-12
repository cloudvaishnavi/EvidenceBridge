import json
from pathlib import Path
from collections import Counter

path = Path("data/ner_v2/invoice_samples.jsonl")

def extract_entities(tokens, labels):
    results = []
    current_tokens = []
    current_type = None

    for token, label in zip(tokens, labels):
        if label.startswith("B-"):
            if current_tokens:
                results.append(
                    (current_type, tokenizer.convert_tokens_to_string(current_tokens))
                )

            current_type = label[2:]
            current_tokens = [token]

        elif label.startswith("I-") and current_type == label[2:]:
            current_tokens.append(token)

        else:
            if current_tokens:
                results.append(
                    (current_type, tokenizer.convert_tokens_to_string(current_tokens))
                )
            current_tokens = []
            current_type = None

    if current_tokens:
        results.append(
            (current_type, tokenizer.convert_tokens_to_string(current_tokens))
        )

    return results


from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    "models/EvidenceBridge_BioBERT/baseline_v1",
    local_files_only=True
)

with open(path, encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

counts = Counter()
errors = []

for record in records:
    for entity_type, value in extract_entities(
        record["tokens"], record["ner_tags"]
    ):
        counts[entity_type] += 1

    if len(record["tokens"]) != len(record["ner_tags"]):
        errors.append(record["record_id"])

print("RECORDS:", len(records))
print("\nRECONSTRUCTED ENTITY COUNTS:")

for entity, count in sorted(counts.items()):
    print(f"{entity:22} {count}")

print("\nFIRST RECORD — COMPLETE ENTITIES")

for entity, value in extract_entities(
    records[0]["tokens"], records[0]["ner_tags"]
):
    print(f"{entity:22} -> {value}")

print("\nSTRUCTURAL ERRORS:", len(errors))
print("VERIFICATION COMPLETE")