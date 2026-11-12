import json
from pathlib import Path
from test_biobert_v4_inference import extract_entities

INPUT_FILE = Path("data/samples/samples.json")
OUTPUT_FILE = Path("data/evaluation/biobert_v4_sample_predictions.json")

with INPUT_FILE.open("r", encoding="utf-8") as f:
    samples = json.load(f)

results = []

for sample in samples:
    predictions = extract_entities(sample["text"])

    results.append({
        "sample_id": sample.get("id"),
        "source_type": sample.get("source_type"),
        "text": sample["text"],
        "predictions": predictions
    })

with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Documents evaluated: {len(results)}")
print(f"Total entities extracted: {sum(len(r['predictions']) for r in results)}")
print(f"Saved predictions: {OUTPUT_FILE}")
