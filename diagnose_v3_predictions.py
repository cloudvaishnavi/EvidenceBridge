
import json
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForTokenClassification

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_DIR = Path(
    "models/EvidenceBridge_BioBERT/model_1_biobert_v3/best_model"
)

TEST_FILE = Path("data/ner_v3/splits/test.jsonl")

WEAK_ENTITIES = {
    "BRAND_NAME",
    "GENERIC_NAME",
    "INSURANCE_DEDUCTION",
    "INVOICE_TOTAL",
    "LINE_AMOUNT",
    "SUBTOTAL",
    "UNIT_PRICE",
}

device = "cuda" if torch.cuda.is_available() else "cpu"

# ============================================================
# LOAD MODEL AND TOKENIZER
# ============================================================

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    local_files_only=True
)

model = AutoModelForTokenClassification.from_pretrained(
    MODEL_DIR,
    local_files_only=True
).to(device)

model.eval()

print("=" * 70)
print("BIOBERT V3 - CORRECTED WEAK ENTITY DIAGNOSTICS")
print("=" * 70)

print("Device:", device)
print("Model loaded successfully")


# ============================================================
# RECONSTRUCT PREDICTED ENTITIES USING CHARACTER OFFSETS
# ============================================================

def extract_entities(text, labels, offsets):

    entities = []
    current = None

    for label, (start, end) in zip(labels, offsets):

        if start == end:
            continue

        if label.startswith("B-"):

            if current:
                entities.append(current)

            current = {
                "type": label[2:],
                "start": start,
                "end": end
            }

        elif label.startswith("I-"):

            entity_type = label[2:]

            if current and current["type"] == entity_type:
                current["end"] = end

            else:
                if current:
                    entities.append(current)

                current = {
                    "type": entity_type,
                    "start": start,
                    "end": end
                }

        else:

            if current:
                entities.append(current)
                current = None

    if current:
        entities.append(current)

    return [
        (entity["type"], text[entity["start"]:entity["end"]])
        for entity in entities
    ]


# ============================================================
# RECONSTRUCT ACTUAL ANNOTATIONS FROM WORDPIECE TOKENS
# ============================================================

def extract_actual_entities(tokens, tags):

    entities = []

    current_type = None
    current_tokens = []

    def save_entity():

        if current_type and current_tokens:

            value = ""

            for token in current_tokens:

                if token.startswith("##"):
                    value += token[2:]

                else:
                    value += (" " if value else "") + token

            entities.append((current_type, value))

    for token, tag in zip(tokens, tags):

        if tag.startswith("B-"):

            save_entity()

            current_type = tag[2:]
            current_tokens = [token]

        elif tag.startswith("I-"):

            entity_type = tag[2:]

            if current_type == entity_type:
                current_tokens.append(token)

            else:
                save_entity()

                current_type = entity_type
                current_tokens = [token]

        else:

            save_entity()

            current_type = None
            current_tokens = []

    save_entity()

    return entities


# ============================================================
# LOAD TEST DATASET
# ============================================================

with TEST_FILE.open(encoding="utf-8") as f:

    records = [
        json.loads(line)
        for line in f
        if line.strip()
    ]

print("\nTest records loaded:", len(records))


# ============================================================
# RUN DIAGNOSTICS
# ============================================================

for record in records:

    text = record["text"]

    # --------------------------------------------------------
    # Actual annotated entities
    # --------------------------------------------------------

    actual_entities = [
        (entity_type, value)
        for entity_type, value in extract_actual_entities(
            record["tokens"],
            record["ner_tags"]
        )
        if entity_type in WEAK_ENTITIES
    ]

    # --------------------------------------------------------
    # Model prediction
    # --------------------------------------------------------

    inputs = tokenizer(
        text,
        return_tensors="pt",
        return_offsets_mapping=True,
        truncation=True,
        max_length=192
    )

    offsets = inputs.pop("offset_mapping")[0].tolist()

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        logits = model(**inputs).logits

    predicted_ids = logits.argmax(dim=-1)[0].tolist()

    predicted_labels = [
        model.config.id2label[index]
        for index in predicted_ids
    ]

    predicted_entities = extract_entities(
        text,
        predicted_labels,
        offsets
    )

    relevant_predictions = [
        (entity_type, value)
        for entity_type, value in predicted_entities
        if entity_type in WEAK_ENTITIES
    ]

    # --------------------------------------------------------
    # Display only relevant records
    # --------------------------------------------------------

    if not actual_entities and not relevant_predictions:
        continue

    print("\n" + "=" * 70)

    print("RECORD:", record["record_id"])

    print("\nTEXT:")
    print(text[:500])

    print("\nACTUAL WEAK ENTITIES:")

    if actual_entities:

        for entity_type, value in actual_entities:
            print(f"  {entity_type}: {value}")

    else:
        print("  None")

    print("\nPREDICTED WEAK ENTITIES:")

    if relevant_predictions:

        for entity_type, value in relevant_predictions:
            print(f"  {entity_type}: {value}")

    else:
        print("  None")


# ============================================================
# COMPLETION
# ============================================================

print("\n" + "=" * 70)
print("DIAGNOSTICS COMPLETE")
print("=" * 70)
