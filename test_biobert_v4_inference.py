import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_PATH = "models/EvidenceBridge_BioBERT/model_1_biobert_v4/best_model"
MAX_LENGTH = 192

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

assert model.config.num_labels == 69, (
    f"Expected 69 labels, found {model.config.num_labels}"
)

def extract_entities(text):
    encoded = tokenizer(
        text,
        return_tensors="pt",
        return_offsets_mapping=True,
        truncation=True,
        max_length=MAX_LENGTH
    )

    offsets = encoded.pop("offset_mapping")[0].tolist()
    inputs = {key: value.to(device) for key, value in encoded.items()}

    with torch.no_grad():
        logits = model(**inputs).logits[0]
        probabilities = torch.softmax(logits, dim=-1)
        predictions = logits.argmax(dim=-1).tolist()

    entities = []
    current = None

    def save_current():
        if current is not None:
            start, end = current["start"], current["end"]
            entities.append({
                "entity": current["entity"],
                "text": text[start:end],
                "confidence": round(
                    sum(current["scores"]) / len(current["scores"]), 4
                )
            })

    for (start, end), pred, probs in zip(
        offsets, predictions, probabilities
    ):
        if start == end:
            continue

        label = model.config.id2label[pred]
        confidence = probs[pred].item()

        if label == "O":
            save_current()
            current = None
            continue

        prefix, entity_type = label.split("-", 1)

        if prefix == "B" or current is None or current["entity"] != entity_type:
            save_current()
            current = {
                "entity": entity_type,
                "start": start,
                "end": end,
                "scores": [confidence]
            }
        else:
            current["end"] = end
            current["scores"].append(confidence)

    save_current()
    return entities


if __name__ == "__main__":
    print("EvidenceBridge BioBERT V4 loaded successfully.")
    print(f"Device: {device}")
    print(f"Number of labels: {model.config.num_labels}")

    sample = """
HOSPITAL BILLING DETAILS

Name of Beneficiary: Ananya Rao
Facility: Apollo Hospitals
UHID: UH20261182
Bill Ref: BILL-2026-7781
Issued On: 15/10/2026

Particulars: Paracetamol
Manufacturer Brand: Calpol
Dose Strength: 500 mg
Number of Units: 12
Rate Per Unit: INR 15
Net Payable: INR 180
"""

    results = extract_entities(sample)

    print("\n===== V4 ENTITY EXTRACTION =====")

    for item in results:
        print(
            f'{item["entity"]:22} | '
            f'{item["text"]:30} | '
            f'Confidence: {item["confidence"]:.4f}'
        )

    print(f"\nTotal entities extracted: {len(results)}")
