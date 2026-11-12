
import json
import torch
from pathlib import Path
from collections import defaultdict
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_DIR = "models/EvidenceBridge_BioBERT/model_1_biobert_v2/best_model"
TEST_FILE = Path("data/ner_v2/splits/test.jsonl")

WEAK_ENTITIES = {
    "BRAND_NAME",
    "CLAIM_AMOUNT",
    "DISCOUNT",
    "INSURANCE_DEDUCTION",
    "INVOICE_TOTAL",
    "LINE_AMOUNT",
    "SUBTOTAL",
    "UNIT_PRICE",
    "APPROVED_AMOUNT",
    "TAX_AMOUNT",
    "GENERIC_NAME"
}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("Loading saved V2 model...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    use_fast=True,
    local_files_only=True
)

model = AutoModelForTokenClassification.from_pretrained(
    MODEL_DIR,
    local_files_only=True
).to(device)

model.eval()

with TEST_FILE.open("r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]


def get_gold_entities(record):
    text = record["text"]
    entities = []
    cursor = 0
    spans = []

    for token, label in zip(record["tokens"], record["ner_tags"]):
        clean = token[2:] if token.startswith("##") else token

        if clean in tokenizer.all_special_tokens:
            continue

        start = text.lower().find(clean.lower(), cursor)

        if start == -1:
            raise ValueError(
                f"Cannot align {token!r} in {record['record_id']}"
            )

        end = start + len(clean)
        spans.append((start, end, label))
        cursor = end

    current_type = None
    current_start = None
    current_end = None

    for start, end, label in spans:
        if label == "O":
            if current_type:
                entities.append((
                    current_type,
                    text[current_start:current_end].strip()
                ))
            current_type = None
            continue

        prefix, entity_type = label.split("-", 1)

        if prefix == "B" or current_type != entity_type:
            if current_type:
                entities.append((
                    current_type,
                    text[current_start:current_end].strip()
                ))

            current_type = entity_type
            current_start = start
            current_end = end

        else:
            current_end = end

    if current_type:
        entities.append((
            current_type,
            text[current_start:current_end].strip()
        ))

    return entities


def get_predicted_entities(text):
    encoded = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=192,
        return_offsets_mapping=True
    )

    offsets = encoded.pop("offset_mapping")[0].tolist()

    encoded = {
        key: value.to(device)
        for key, value in encoded.items()
    }

    with torch.no_grad():
        logits = model(**encoded).logits

    predictions = logits.argmax(dim=-1)[0].cpu().tolist()

    entities = []
    current_type = None
    current_start = None
    current_end = None

    for (start, end), label_id in zip(offsets, predictions):
        if start == end:
            continue

        label = model.config.id2label[label_id]

        if label == "O":
            if current_type:
                entities.append((
                    current_type,
                    text[current_start:current_end].strip()
                ))
            current_type = None
            continue

        prefix, entity_type = label.split("-", 1)

        if prefix == "B" or current_type != entity_type:
            if current_type:
                entities.append((
                    current_type,
                    text[current_start:current_end].strip()
                ))

            current_type = entity_type
            current_start = start
            current_end = end

        else:
            current_end = end

    if current_type:
        entities.append((
            current_type,
            text[current_start:current_end].strip()
        ))

    return entities


errors = defaultdict(lambda: {"missing": [], "extra": []})

for record in records:
    gold = set(get_gold_entities(record))
    predicted = set(get_predicted_entities(record["text"]))

    for entity in gold - predicted:
        if entity[0] in WEAK_ENTITIES:
            errors[entity[0]]["missing"].append(
                (record["record_id"], entity[1])
            )

    for entity in predicted - gold:
        if entity[0] in WEAK_ENTITIES:
            errors[entity[0]]["extra"].append(
                (record["record_id"], entity[1])
            )

print("\n" + "=" * 65)
print("V2 WEAK ENTITY ERROR ANALYSIS")
print("=" * 65)

for entity_type in sorted(WEAK_ENTITIES):
    result = errors[entity_type]

    print(f"\n{entity_type}")
    print("-" * 55)

    print("Missing predictions:", len(result["missing"]))
    for record_id, value in result["missing"][:5]:
        print(f"  FN | {record_id} | {value}")

    print("Extra predictions:", len(result["extra"]))
    for record_id, value in result["extra"][:5]:
        print(f"  FP | {record_id} | {value}")

print("\nERROR ANALYSIS COMPLETED")
