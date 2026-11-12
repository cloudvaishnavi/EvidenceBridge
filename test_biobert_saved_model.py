
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_DIR = "models/EvidenceBridge_BioBERT/model_1_biobert_v2/best_model"

print("=" * 60)
print("EVIDENCEBRIDGE - SAVED BIOBERT MODEL VERIFICATION")
print("=" * 60)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("\nDevice:", device)

# Load tokenizer and trained model
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    use_fast=True,
    local_files_only=True
)

model = AutoModelForTokenClassification.from_pretrained(
    MODEL_DIR,
    local_files_only=True
)

model.to(device)
model.eval()

print("Tokenizer loaded successfully")
print("Model loaded successfully")
print("Number of labels:", model.config.num_labels)

# Sample healthcare document
text = """
Hospital: Apollo Hospital
Patient ID: PT48291
Diagnosis: Type 2 Diabetes Mellitus
Admission Date: 12/10/2026
Discharge Date: 15/10/2026
"""

# Tokenize document
inputs = tokenizer(
    text,
    return_tensors="pt",
    truncation=True,
    max_length=192
)

inputs = {
    key: value.to(device)
    for key, value in inputs.items()
}

# Predict entities
with torch.no_grad():
    outputs = model(**inputs)

predictions = torch.argmax(outputs.logits, dim=-1)[0].cpu().tolist()

# Get character offsets using the same tokenizer settings
offsets = tokenizer(
    text,
    truncation=True,
    max_length=192,
    return_offsets_mapping=True
)["offset_mapping"]

# Extract readable entities
entities = []
current_entity = None

for (start, end), label_id in zip(offsets, predictions):

    if start == end:
        continue

    label = model.config.id2label[label_id]

    if label == "O":
        if current_entity:
            entities.append(current_entity)
            current_entity = None
        continue

    prefix, entity_type = label.split("-", 1)

    if prefix == "B" or (
        current_entity
        and current_entity["type"] != entity_type
    ):
        if current_entity:
            entities.append(current_entity)

        current_entity = {
            "type": entity_type,
            "start": start,
            "end": end
        }

    elif prefix == "I" and current_entity:
        current_entity["end"] = end

if current_entity:
    entities.append(current_entity)

print("\nEXTRACTED ENTITIES")
print("-" * 60)

for entity in entities:
    value = text[entity["start"]:entity["end"]].strip()

    print(f"{entity['type']:<25}: {value}")

print("\nSAVED MODEL INFERENCE TEST COMPLETED")
print("=" * 60)
