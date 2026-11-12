import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForTokenClassification

model_path = Path(
    "models/EvidenceBridge_BioBERT/baseline_v1"
)

print("=" * 55)
print("EVIDENCEBRIDGE — BIOBERT LOCAL CHECK")
print("=" * 55)

print("Model directory exists:", model_path.exists())
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print(
        "GPU memory:",
        round(
            torch.cuda.get_device_properties(0).total_memory
            / (1024 ** 3),
            2
        ),
        "GB"
    )

print("\nLoading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    str(model_path),
    local_files_only=True
)

print("Tokenizer loaded.")

print("\nLoading BioBERT model...")

model = AutoModelForTokenClassification.from_pretrained(
    str(model_path),
    local_files_only=True
)

print("Model loaded.")
print("Number of labels:", model.config.num_labels)
print("Model parameters:", sum(p.numel() for p in model.parameters()))

text = "Hospital Apollo Invoice Number INV-102 Total INR 12500"

inputs = tokenizer(
    text,
    return_tensors="pt",
    truncation=True,
    max_length=192
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

inputs = {k: v.to(device) for k, v in inputs.items()}

with torch.no_grad():
    outputs = model(**inputs)

print("\nSmoke test successful.")
print("Input tokens:", tokenizer.convert_ids_to_tokens(inputs["input_ids"][0]))
print("Output shape:", tuple(outputs.logits.shape))
print("Device:", device)

print("\nBIOBERT LOCAL CHECK PASSED")