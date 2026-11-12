import json
from pathlib import Path
from transformers import AutoTokenizer

MODEL = "models/EvidenceBridge_BioBERT/baseline_v1"
FILE = Path("data/ner_v3/splits/train.jsonl")

tokenizer = AutoTokenizer.from_pretrained(MODEL)

record = next(
    r for r in map(json.loads, FILE.open(encoding="utf-8"))
    if r["record_id"] == "SYN-INV-V2-0001"
)

text = record["text"]
cursor = 0

print("\nCHARACTER SPAN RECONSTRUCTION\n")

for token, label in zip(record["tokens"], record["ner_tags"]):
    clean = token[2:] if token.startswith("##") else token

    if clean in tokenizer.all_special_tokens:
        continue

    start = text.lower().find(clean.lower(), cursor)

    if start == -1:
        print("ALIGNMENT ERROR:", token)
        break

    end = start + len(clean)

    if label.startswith("B-"):
        print(f"\n{label[2:]}:")

    if label != "O":
        print(f"  Token: {token:10} | Text: {text[start:end]}")

    cursor = end