import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_PATH = "models/EvidenceBridge_BioBERT/model_1_biobert_v3/best_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

text = """
HEALTHCARE INVOICE
Hospital: Sri Lakshmi Multispeciality Hospital
Patient ID: PT908721
Invoice Number: INV-2026-908
Patient Name: Rahul Sharma
Invoice Date: 02/11/2026
Medicine: Paracetamol
Brand Name: Dolo
Strength: 650 mg
Quantity: 10
Unit Price: INR 20
Invoice Total: INR 200
"""

inputs = tokenizer(
    text,
    return_tensors="pt",
    truncation=True,
    max_length=192,
    return_offsets_mapping=True
)

offsets = inputs.pop("offset_mapping")[0].tolist()
inputs = {k: v.to(device) for k, v in inputs.items()}

with torch.no_grad():
    outputs = model(**inputs)

predictions = outputs.logits.argmax(dim=-1)[0].cpu().tolist()

id2label = model.config.id2label

print("\n===== EVIDENCEBRIDGE BIOBERT V3 =====\n")

for (start, end), pred in zip(offsets, predictions):
    if start == end:
        continue

    label = id2label[pred]

    if label != "O":
        print(f"{text[start:end]:25} -> {label}")