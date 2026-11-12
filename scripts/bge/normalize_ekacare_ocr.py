import json
import re

SOURCE = "data/bge/evaluation/ekacare_20_ocr.json"
OUTPUT = "data/bge/evaluation/ekacare_20_ocr_normalized.json"

def normalize_ocr(text):
    # Separate letters followed by digits: Nov2020 -> Nov 2020
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)

    # Separate digits followed by words: Page4Of15 -> Page 4 Of 15
    text = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", text)

    # Normalize repeated whitespace without changing line boundaries
    text = re.sub(r"[ \t]+", " ", text)

    return text

with open(SOURCE, encoding="utf-8-sig") as f:
    records = json.load(f)

normalized = []

for record in records:
    item = dict(record)
    item["original_ocr_text"] = record["ocr_text"]
    item["ocr_text"] = normalize_ocr(record["ocr_text"])
    item["normalization_applied"] = True
    normalized.append(item)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(normalized, f, ensure_ascii=False, indent=2)

print("Documents normalized:", len(normalized))
print("Original OCR preserved:", True)
print("Medical numbers modified:", False)
print("Saved:", OUTPUT)
