from transformers import AutoTokenizer

MODEL_PATH = "models/EvidenceBridge_BioBERT/baseline_v1"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    use_fast=True,
    local_files_only=True
)

text = (
    "Hospital: Apollo Hospitals. "
    "Invoice number: INV-26-93004. "
    "Quantity: 2. "
    "Unit price: INR 1500."
)

# Use field-specific anchors to avoid matching repeated values.
entities = [
    ("Hospital: ", "Apollo Hospitals", "HOSPITAL"),
    ("Invoice number: ", "INV-26-93004", "INVOICE_NUMBER"),
    ("Quantity: ", "2", "QUANTITY"),
    ("Unit price: ", "INR 1500", "UNIT_PRICE"),
]

spans = []

for prefix, value, entity_type in entities:
    field_start = text.index(prefix) + len(prefix)
    start = text.index(value, field_start)
    end = start + len(value)

    spans.append((start, end, entity_type))

encoding = tokenizer(
    text,
    return_offsets_mapping=True,
    truncation=True
)

tokens = tokenizer.convert_ids_to_tokens(encoding["input_ids"])
labels = ["O"] * len(tokens)

for start, end, entity_type in spans:
    matching_tokens = []

    for i, (token_start, token_end) in enumerate(
        encoding["offset_mapping"]
    ):
        if token_start == token_end:
            continue

        if token_start < end and token_end > start:
            matching_tokens.append(i)

    assert matching_tokens, f"No tokens found for {entity_type}"

    for position, token_index in enumerate(matching_tokens):
        labels[token_index] = (
            "B-" if position == 0 else "I-"
        ) + entity_type

print("TOKEN                 LABEL")
print("-" * 45)

for token, label in zip(tokens, labels):
    print(f"{token:22} {label}")

# Explicitly verify the quantity annotation.
quantity_tokens = [
    tokens[i]
    for i, label in enumerate(labels)
    if label == "B-QUANTITY"
]

assert quantity_tokens == ["2"], (
    f"Incorrect quantity annotation: {quantity_tokens}"
)

assert not any(
    token == "26" and label == "B-QUANTITY"
    for token, label in zip(tokens, labels)
)

print("\nALL ANNOTATION CHECKS PASSED")