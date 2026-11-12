import json
import re
from collections import Counter, defaultdict

SOURCE = "data/bge/evaluation/ekacare_20_ocr.json"

def normalize(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())

with open(SOURCE, encoding="utf-8-sig") as f:
    records = json.load(f)

overall = Counter()
by_type = defaultdict(Counter)

for record in records:
    ocr = normalize(record["ocr_text"])
    local = Counter()

    pattern = (
        r"Rubric ID:\s*(\d+)\s*\n"
        r"Category ID:\s*([^\n]+)\s*\n"
        r"Criterion:\s*([^\n]+)"
    )

    for _, category, criterion in re.findall(pattern, record["rubrics"]):
        category = category.strip()

        quoted = re.findall(r"'([^']*)'", criterion)
        expected = next(
            (v for v in quoted if v.strip().lower() not in
             {"none", "null", "string"}),
            None
        )

        if expected is None:
            continue

        key = normalize(expected)
        if not key:
            continue

        local["checked"] += 1

        if key in ocr:
            local["found"] += 1
        else:
            local["not_found"] += 1

    overall.update(local)
    by_type[record["document_type"]].update(local)

    percentage = (
        100 * local["found"] / local["checked"]
        if local["checked"] else 0
    )

    print(
        f"Document {record['record_id'] + 1:02d} | "
        f"{record['document_type']:12s} | "
        f"{local['found']}/{local['checked']} | "
        f"{percentage:.1f}%"
    )

print("\nOVERALL OCR EVIDENCE COVERAGE")
print("Checked:", overall["checked"])
print("Found:", overall["found"])
print("Not found:", overall["not_found"])

if overall["checked"]:
    print(
        "Coverage:",
        round(100 * overall["found"] / overall["checked"], 2),
        "%"
    )

print("\nBY DOCUMENT TYPE")
for doc_type, counts in by_type.items():
    pct = 100 * counts["found"] / counts["checked"]
    print(
        f"{doc_type}: {counts['found']}/{counts['checked']} "
        f"({pct:.1f}%)"
    )

print("\nNOTE: Literal evidence coverage is NOT rubric accuracy.")
