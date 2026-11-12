
import json
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_PATH = "models/EvidenceBridge_BioBERT/model_1_biobert_v4/best_model"
INPUT_PATH = "data/bge/evaluation/ekacare_20_ocr.json"
OUTPUT_PATH = "data/bge/evaluation/ekacare_20_biobert.json"

def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH)
    model.to(device)
    model.eval()

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    output = []

    for record in records:
        text = record.get("ocr_text", "")
        if not text.strip():
            continue

        encoded = tokenizer(
            text,
            return_tensors="pt",
            return_offsets_mapping=True,
            return_overflowing_tokens=True,
            truncation=True,
            max_length=512,
            stride=64,
            padding=True
        )

        offsets = encoded.pop("offset_mapping")
        encoded.pop("overflow_to_sample_mapping", None)
        inputs = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            logits = model(**inputs).logits

        probabilities = torch.softmax(logits, dim=-1)
        confidence, predictions = probabilities.max(dim=-1)

        entities = set()

        for chunk_index in range(predictions.shape[0]):
            current_label = None
            current_start = None
            current_end = None

            chunk_predictions = predictions[chunk_index].cpu().tolist()
            chunk_confidence = confidence[chunk_index].cpu().tolist()
            chunk_offsets = offsets[chunk_index].tolist()

            for pred, conf, (start, end) in zip(
                chunk_predictions, chunk_confidence, chunk_offsets
            ):
                if start == end:
                    continue

                label = model.config.id2label[pred]

                if label == "O":
                    if current_label:
                        value = text[current_start:current_end].strip()
                        if value:
                            entities.add((
                                current_label, current_start, current_end,
                                value, round(current_confidence, 4)
                            ))
                        current_label = None
                    continue

                prefix, entity_type = label.split("-", 1)

                if prefix == "B" or entity_type != current_label:
                    if current_label:
                        value = text[current_start:current_end].strip()
                        if value:
                            entities.add((
                                current_label, current_start, current_end,
                                value, round(current_confidence, 4)
                            ))

                    current_label = entity_type
                    current_start = start
                    current_end = end
                    current_confidence = conf
                else:
                    current_end = end
                    current_confidence = min(current_confidence, conf)

            if current_label:
                value = text[current_start:current_end].strip()
                if value:
                    entities.add((
                        current_label, current_start, current_end,
                        value, round(current_confidence, 4)
                    ))

        entity_list = [
            {
                "label": e[0],
                "start": e[1],
                "end": e[2],
                "text": e[3],
                "confidence": e[4]
            }
            for e in sorted(entities, key=lambda x: x[1])
        ]

        output.append({
            "record_id": record["record_id"],
            "document_type": record["document_type"],
            "ocr_text": text,
            "entities": entity_list,
            "entity_count": len(entity_list)
        })

        print(
            f"Record {record['record_id'] + 1}/20 | "
            f"{record['document_type']} | "
            f"{len(entity_list)} entities"
        )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\nMODEL 1 BATCH COMPLETE")
    print("Documents processed:", len(output))
    print("Total entities:", sum(r["entity_count"] for r in output))
    print("Saved:", OUTPUT_PATH)
    print("Device:", device)

if __name__ == "__main__":
    main()
