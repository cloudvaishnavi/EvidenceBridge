import json
from pathlib import Path
from test_biobert_v4_inference import extract_entities

input_file = Path("data/evaluation/india_demo_documents.json")
output_file = Path("data/evaluation/india_demo_predictions.json")
with input_file.open("r", encoding="utf-8-sig") as f:
    documents = json.load(f)

results = []

for doc in documents:
    predictions = extract_entities(doc["text"])

    results.append({
        "document_id": doc["id"],
        "document_type": doc["document_type"],
        "predictions": predictions
    })

    print(f"\n===== {doc['document_type'].upper()} =====")

    for item in predictions:
        print(
            f"{item['entity']:22} | "
            f"{item['text']:35} | "
            f"{item['confidence']:.4f}"
        )

with output_file.open("w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n===== EVALUATION SUMMARY =====")
print("Documents:", len(results))
print("Entities:", sum(len(r["predictions"]) for r in results))
print("Saved:", output_file)
