
import json
import random
from collections import defaultdict, Counter
from pathlib import Path

SEED = 42

INPUT = Path("data/ner_v4/raw/all_records.jsonl")
OUTPUT = Path("data/ner_v4/splits")

random.seed(SEED)


def main():
    with INPUT.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    groups = defaultdict(list)

    for record in records:
        heading = record["text"].split(".", 1)[0].strip()
        key = (record["document_type"], heading)
        groups[key].append(record)

    train = []
    validation = []
    test = []

    types = sorted({r["document_type"] for r in records})

    for doc_type in types:
        headings = sorted(
            heading
            for dtype, heading in groups
            if dtype == doc_type
        )

        random.shuffle(headings)

        train_headings = headings[:2]
        val_heading = headings[2]
        test_heading = headings[3]

        for heading in train_headings:
            train.extend(groups[(doc_type, heading)])

        validation.extend(groups[(doc_type, val_heading)])
        test.extend(groups[(doc_type, test_heading)])

    random.shuffle(train)
    random.shuffle(validation)
    random.shuffle(test)

    # Verify record separation.
    train_ids = {r["record_id"] for r in train}
    val_ids = {r["record_id"] for r in validation}
    test_ids = {r["record_id"] for r in test}

    assert not train_ids & val_ids
    assert not train_ids & test_ids
    assert not val_ids & test_ids

    def heading_set(data):
        return {
            (r["document_type"], r["text"].split(".", 1)[0].strip())
            for r in data
        }

    train_headings = heading_set(train)
    val_headings = heading_set(validation)
    test_headings = heading_set(test)

    assert not train_headings & val_headings
    assert not train_headings & test_headings
    assert not val_headings & test_headings

    OUTPUT.mkdir(parents=True, exist_ok=True)

    for name, data in [
        ("train.jsonl", train),
        ("validation.jsonl", validation),
        ("test.jsonl", test)
    ]:
        with (OUTPUT / name).open("w", encoding="utf-8") as f:
            for record in data:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("\nV4 HEADING-BASED SPLIT COMPLETE")
    print("Total:", len(records))
    print("Train:", len(train))
    print("Validation:", len(validation))
    print("Test:", len(test))
    print("Train heading families:", len(train_headings))
    print("Validation heading families:", len(val_headings))
    print("Test heading families:", len(test_headings))
    print("Heading overlap:", len(
        (train_headings & val_headings)
        | (train_headings & test_headings)
        | (val_headings & test_headings)
    ))

    print("\nDocument distribution:")
    for name, data in [
        ("Train", train),
        ("Validation", validation),
        ("Test", test)
    ]:
        print(name, dict(Counter(r["document_type"] for r in data)))

    print("\nAssigned headings:")
    for name, data in [
        ("Train", train),
        ("Validation", validation),
        ("Test", test)
    ]:
        print(f"\n{name}:")
        for dtype, heading in sorted(heading_set(data)):
            print(f"  {dtype}: {heading}")


if __name__ == "__main__":
    main()
