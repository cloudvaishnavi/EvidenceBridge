import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_PATH = "models/EvidenceBridge_BioBERT/model_1_biobert_v4/best_model"

text = """
Prescription Date: 28-Mar-2023
Complaints: MTD ON RX, SOBER, NO SEIZURES, NO MOOD SYMPTOMS
MSE: NO E/O EPS
Diagnosis: BIPOLAR MOOD DISORDER
QTRIPIL SR 400 MG
Sodium valproate 500 MG + Valproic Acid 145 MG
VALPARIN CHRONO 500MG TABLET
Oxcarbazepine 300 MG
OLEPTAL DT 300MG TABLET
Quetiapine 100 MG
QUTIPIN SR 100MG TABLET
"""

device = "cuda" if torch.cuda.is_available() else "cpu"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH).to(device)
model.eval()

inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
inputs = {k: v.to(device) for k, v in inputs.items()}

with torch.no_grad():
    predictions = model(**inputs).logits.argmax(-1)[0].cpu().tolist()

tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0].cpu())
entities = []
current_type = None
current_tokens = []

def save_entity():
    if current_tokens:
        word = tokenizer.convert_tokens_to_string(current_tokens).strip()
        if word:
            entities.append((current_type, word))

for token, pred in zip(tokens, predictions):
    label = model.config.id2label[pred]

    if token in tokenizer.all_special_tokens:
        save_entity()
        current_type = None
        current_tokens = []
        continue

    if label == "O":
        save_entity()
        current_type = None
        current_tokens = []
        continue

    prefix, entity_type = label.split("-", 1)

    if prefix == "B" or entity_type != current_type:
        save_entity()
        current_type = entity_type
        current_tokens = [token]
    else:
        current_tokens.append(token)

save_entity()

print("===== BIOBERT COMPLETE ENTITY SPANS =====")
for entity_type, value in entities:
    print(f"{entity_type:22} | {value}")

print("\nTotal predicted entities:", len(entities))
