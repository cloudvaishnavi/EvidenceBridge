from transformers import AutoTokenizer

path = "models/EvidenceBridge_BioBERT/baseline_v1"

tokenizer = AutoTokenizer.from_pretrained(
    path,
    use_fast=True,
    local_files_only=True
)

print("Fast tokenizer:", tokenizer.is_fast)

text = "Hospital Apollo Invoice Number INV-102 Total INR 12500"

result = tokenizer(
    text,
    return_offsets_mapping=True,
    truncation=True
)

for token, offset in zip(
    tokenizer.convert_ids_to_tokens(result["input_ids"]),
    result["offset_mapping"]
):
    print(f"{token:20} {offset}")

print("\nTOKENIZER CHECK PASSED")