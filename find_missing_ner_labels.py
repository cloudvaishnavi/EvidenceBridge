import json
from pathlib import Path

schema_path = Path("models/EvidenceBridge_BioBERT/india_ner_schema.json")

with schema_path.open(encoding="utf-8") as f:
    schema = json.load(f)

print("SCHEMA STRUCTURE:")
print("Keys:", list(schema.keys()))

print("\nSCHEMA CONTENT:")
print(json.dumps(schema, indent=2)[:5000])
