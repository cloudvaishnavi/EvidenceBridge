
import json
from pathlib import Path

path = Path("models/EvidenceBridge_BioBERT/india_ner_schema.json")

with open(path, "r", encoding="utf-8") as f:
    schema = json.load(f)

print("INDIA NER SCHEMA")
print("=" * 50)
print(json.dumps(schema, indent=2, ensure_ascii=False))
