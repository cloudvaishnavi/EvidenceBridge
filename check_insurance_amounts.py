import json
from pathlib import Path

path = Path("data/ner_v2/insurance_samples.jsonl")

errors = []

with path.open(encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

for record in records:
    text = " ".join(record["tokens"])

    # Reconstruct entity values
    entities = {}
    current_type = None
    current_tokens = []

    for token, label in zip(record["tokens"], record["ner_tags"]):
        if label.startswith("B-"):
            if current_type:
                entities[current_type] = " ".join(current_tokens)
            current_type = label[2:]
            current_tokens = [token]
        elif label.startswith("I-") and current_type == label[2:]:
            current_tokens.append(token)
        else:
            if current_type:
                entities[current_type] = " ".join(current_tokens)
            current_type = None
            current_tokens = []

    if current_type:
        entities[current_type] = " ".join(current_tokens)

    def amount(name):
        value = entities[name].replace("##", "").replace(" ", "").lower().replace("inr", "").replace(",", "").strip()
        return float(value)

    claim = amount("CLAIM_AMOUNT")
    approved = amount("APPROVED_AMOUNT")
    deduction = amount("INSURANCE_DEDUCTION")
    payable = amount("PATIENT_PAYABLE")

    if approved > claim or deduction > approved:
        errors.append((record["record_id"], "Invalid amount relationship"))

    if round(claim - approved + deduction, 2) != round(payable, 2):
        errors.append((record["record_id"], "Amount calculation mismatch"))

print("TOTAL RECORDS:", len(records))
print("FINANCIAL CONSISTENCY ERRORS:", len(errors))

for record_id, error in errors:
    record = next(r for r in records if r["record_id"] == record_id)

    entities = {}
    current_type = None
    current_tokens = []

    for token, label in zip(record["tokens"], record["ner_tags"]):
        if label.startswith("B-"):
            if current_type:
                entities[current_type] = " ".join(current_tokens)
            current_type = label[2:]
            current_tokens = [token]
        elif label.startswith("I-") and current_type == label[2:]:
            current_tokens.append(token)
        else:
            if current_type:
                entities[current_type] = " ".join(current_tokens)
            current_type = None
            current_tokens = []

    if current_type:
        entities[current_type] = " ".join(current_tokens)

    print(f"\n{record_id}")
    for field in ["CLAIM_AMOUNT", "APPROVED_AMOUNT",
                  "INSURANCE_DEDUCTION", "PATIENT_PAYABLE"]:
        print(f"{field}: {entities.get(field)}")
print("CHECK COMPLETE")