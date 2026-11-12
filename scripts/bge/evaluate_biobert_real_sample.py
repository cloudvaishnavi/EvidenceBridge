
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_PATH = "models/EvidenceBridge_BioBERT/model_1_biobert_v4/best_model"

# Exact text returned by RapidOCR.
text = """8:42
4G
Prescription
Date:28-Mar-2023
Complaints:
·MTDONRX
·SOBER
·NO SEIZURES
·NOMOODSYMPTOMS
MSE:NOE/OEPS
Diagnosis:BIPOLARMOOD DISORDER
R
Medicine
Dose
Timing-Freq.-Duration
Qty
QTRIPILSR400MG
0-0-1(tab)
AfterFood-daily-6Months
180
ON
Timing:1tab-AfterDinner
Sodiumvalproate500MG+ValproicAcid145MG
VALPARINCHRONO50OMGTABLET
0-0-1(tab)
AfterFood-daily-6Months
180
Timing:1tab-AfterDinner
Oxcarbazepine300MG
OLEPTALDT300MGTABLET
1-0-1(tab)
AfterFood-daily-6Months
360
Timing:1tab-AfterBreakfast,1tab-AfterDinner
Quetiapine100MG
QUTIPINSR100MGTABLET
0-0-1(tab)
AfterFood-daily-6Months
180
Timing:1tab-AfterDinner
NextVisit:6months(24-Sep-2023-Sunday)"""

def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH)

    model.to(device)
    model.eval()

    encoded = tokenizer(
        text,
        return_tensors="pt",
        return_offsets_mapping=True,
        truncation=True,
        max_length=512
    )

    offsets = encoded.pop("offset_mapping")[0].tolist()
    inputs = {key: value.to(device) for key, value in encoded.items()}

    with torch.no_grad():
    logits = model(**inputs).logits

probabilities = torch.softmax(logits, dim=-1)[0]
confidence_values, predictions_tensor = probabilities.max(dim=-1)

predictions = predictions_tensor.cpu().tolist()
confidence_values = confidence_values.cpu().tolist()

print("\n===== TOKEN-LEVEL DIAGNOSTICS =====")

input_ids = inputs["input_ids"][0].cpu().tolist()
tokens = tokenizer.convert_ids_to_tokens(input_ids)

for token, (start, end), prediction, confidence in zip(
    tokens, offsets, predictions, confidence_values
):
    if start == end:
        continue

    label = model.config.id2label[prediction]
    original_text = text[start:end]

    print(
        f"Token: {token:22} "
        f"| Text: {original_text:25} "
        f"| Label: {label:24} "
        f"| Confidence: {confidence:.4f}"
    )
    entities = []
    current_label = None
    current_start = None
    current_end = None

    for prediction, (start, end) in zip(predictions, offsets):

        # Ignore special tokens.
        if start == end:
            continue

        label = model.config.id2label[prediction]

        if label == "O":
            if current_label is not None:
                entities.append(
                    (current_label, current_start, current_end)
                )
                current_label = None
            continue

        prefix, entity_type = label.split("-", 1)

        # Start a new entity for B labels or a changed entity type.
        if prefix == "B" or entity_type != current_label:
            if current_label is not None:
                entities.append(
                    (current_label, current_start, current_end)
                )

            current_label = entity_type
            current_start = start
            current_end = end

        else:
            # Continue the current I-entity.
            current_end = end

    if current_label is not None:
        entities.append(
            (current_label, current_start, current_end)
        )

    print("DEVICE:", device)
    print("\n===== BIOBERT REAL-DOCUMENT ENTITIES =====")

    for entity_type, start, end in entities:
        extracted_text = text[start:end]
        print(f"{entity_type:25} | {extracted_text}")

    print(f"\nTotal entities extracted: {len(entities)}")
    print("Inference completed.")


if __name__ == "__main__":
    main()
