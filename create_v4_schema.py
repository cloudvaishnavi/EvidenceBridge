import json
from pathlib import Path

source = Path("models/EvidenceBridge_BioBERT/india_ner_schema.json")
target = Path("models/EvidenceBridge_BioBERT/india_ner_schema_v4.json")

with source.open(encoding="utf-8") as f:
    schema = json.load(f)

new_entity = "PATIENT_NAME"

if new_entity not in {
    label.split("-", 1)[1]
    for label in schema["labels"]
    if label.startswith("B-")
}:
    schema["labels"].extend([
        "B-PATIENT_NAME",
        "I-PATIENT_NAME"
    ])

    schema["label2id"]["B-PATIENT_NAME"] = len(schema["label2id"])
    schema["label2id"]["I-PATIENT_NAME"] = len(schema["label2id"])

    schema["id2label"] = {
        str(v): k for k, v in schema["label2id"].items()
    }

schema["entity_count"] = 34
schema["label_count"] = len(schema["labels"])

with target.open("w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)

print("V4 schema created:", target)
print("Entity types:", schema["entity_count"])
print("BIO labels:", schema["label_count"])
print("New labels:", schema["labels"][-2:])