from train_biobert_v2 import (
    train_records,
    val_records,
    test_records,
    prepare_record
)

print("=" * 60)
print("EVIDENCEBRIDGE - BIOBERT V2 ALIGNMENT TEST")
print("=" * 60)

for split_name, records in [
    ("TRAIN", train_records),
    ("VALIDATION", val_records),
    ("TEST", test_records)
]:
    for record in records:
        result = prepare_record(record)

        assert len(result["input_ids"]) == len(result["labels"]), (
            f"Length mismatch: {record['record_id']}"
        )

        assert len(result["input_ids"]) <= 192, (
            f"Sequence too long: {record['record_id']}"
        )

    print(
        f"{split_name}: "
        f"{len(records)}/{len(records)} records aligned successfully"
    )

print("\nALL TOKEN ALIGNMENT CHECKS PASSED")