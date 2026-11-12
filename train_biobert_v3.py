
import json
import torch
import numpy as np

from pathlib import Path
from datasets import Dataset
from seqeval.metrics import (
    precision_score,
    recall_score,
    f1_score,
    classification_report
)

from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback,
    set_seed
)

# ============================================================
# CONFIGURATION
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

set_seed(42)

BASE_MODEL = "models/EvidenceBridge_BioBERT/baseline_v1"

SCHEMA_PATH = Path(
    "models/EvidenceBridge_BioBERT/india_ner_schema.json"
)

# V3 leakage-controlled dataset
DATA_DIR = Path("data/ner_v3/splits")

# Separate V3 output directory — V2 remains untouched
OUTPUT_DIR = Path(
    "models/EvidenceBridge_BioBERT/model_1_biobert_v3"
)

# Training configuration (same as V2)
MAX_LENGTH = 192
EPOCHS = 5

TRAIN_BATCH_SIZE = 2
EVAL_BATCH_SIZE = 2

GRADIENT_ACCUMULATION = 4

LEARNING_RATE = 1e-5

# ============================================================
# DEVICE
# ============================================================

device = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("EVIDENCEBRIDGE - BIOBERT V3 TRAINING")
print("=" * 60)

print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print(
        "GPU Memory:",
        round(
            torch.cuda.get_device_properties(0).total_memory
            / (1024 ** 3), 2
        ),
        "GB"
    )

# ============================================================
# DEVICE
# ============================================================

device = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("EVIDENCEBRIDGE - BIOBERT V2 TRAINING")
print("=" * 60)

print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print(
        "GPU Memory:",
        round(
            torch.cuda.get_device_properties(0).total_memory
            / (1024 ** 3), 2
        ),
        "GB"
    )

# ============================================================
# LOAD SCHEMA
# ============================================================

with SCHEMA_PATH.open(encoding="utf-8") as f:
    schema = json.load(f)

label2id = schema["label2id"]
id2label = {
    int(k): v for k, v in schema["id2label"].items()
}

NUM_LABELS = len(label2id)

assert NUM_LABELS == 67, (
    f"Expected 67 labels, found {NUM_LABELS}"
)

print("\nLabels:", NUM_LABELS)

# ============================================================
# LOAD TOKENIZER
# ============================================================

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    use_fast=True,
    local_files_only=True
)

assert tokenizer.is_fast, "Fast tokenizer required"

print("Tokenizer loaded successfully")

# ============================================================
# LOAD DATA
# ============================================================

def load_jsonl(filename):
    path = DATA_DIR / filename

    with path.open(encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


train_records = load_jsonl("train.jsonl")
val_records = load_jsonl("validation.jsonl")
test_records = load_jsonl("test.jsonl")

print("\nDataset sizes:")
print("Train:", len(train_records))
print("Validation:", len(val_records))
print("Test:", len(test_records))

# ============================================================
# VERIFY LABELS AND TOKEN ALIGNMENT
# ============================================================

def verify_records(records, split_name):
    for record in records:
        tokens = record["tokens"]
        tags = record["ner_tags"]

        if len(tokens) != len(tags):
            raise ValueError(
                f"Token-label mismatch: {record['record_id']}"
            )

        if len(tokens) > MAX_LENGTH:
            raise ValueError(
                f"Sequence too long: {record['record_id']}"
            )

        unknown = set(tags) - set(label2id)

        if unknown:
            raise ValueError(
                f"Unknown labels in {record['record_id']}: {unknown}"
            )

    print(f"{split_name}: verified")


verify_records(train_records, "Training")
verify_records(val_records, "Validation")
verify_records(test_records, "Testing")

# ============================================================
# CONVERT PRETOKENIZED RECORDS
# ============================================================



def prepare_record(record):
    text = record["text"]
    original_tokens = record["tokens"]
    original_labels = record["ner_tags"]

    if len(original_tokens) != len(original_labels):
        raise ValueError(
            f"Token-label mismatch: {record['record_id']}"
        )

    word_spans = []
    cursor = 0

    # Recover character spans from the original annotations.
    for token, label in zip(original_tokens, original_labels):

        clean_token = (
            token[2:] if token.startswith("##") else token
        )

        # Ignore special tokens that are not present in document text.
        if clean_token in tokenizer.all_special_tokens:
            continue

        start = text.lower().find(clean_token.lower(), cursor)

        if start == -1:
            raise ValueError(
                f"Cannot align {token!r} in {record['record_id']}"
            )

        end = start + len(clean_token)

        word_spans.append((start, end, label))
        cursor = end

    # Tokenize the original document using BioBERT.
    encoding = tokenizer(
        text,
        max_length=MAX_LENGTH,
        truncation=True,
        padding=False,
        return_offsets_mapping=True
    )

    aligned_labels = []
    previous_word_span = None

    for start, end in encoding["offset_mapping"]:

        # Special tokens such as [CLS] and [SEP].
        if start == end:
            aligned_labels.append(-100)
            previous_word_span = None
            continue

        matched_index = next(
            (
                i
                for i, (ws, we, _) in enumerate(word_spans)
                if ws < end and we > start
            ),
            None
        )

        # Token has no corresponding original annotation.
        if matched_index is None:
            aligned_labels.append(label2id["O"])
            previous_word_span = None
            continue

        ws, we, original_label = word_spans[matched_index]

        if original_label == "O":
            aligned_labels.append(label2id["O"])
            previous_word_span = matched_index
            continue

        prefix, entity = original_label.split("-", 1)

        # First subword keeps the original BIO label.
        # Subsequent subwords receive the I- label.
        if previous_word_span == matched_index:
            output_label = f"I-{entity}"
        else:
            output_label = original_label

        if output_label not in label2id:
            raise ValueError(
                f"Unknown aligned label {output_label} "
                f"in {record['record_id']}"
            )

        aligned_labels.append(label2id[output_label])
        previous_word_span = matched_index

    if len(encoding["input_ids"]) != len(aligned_labels):
        raise ValueError(
            f"Alignment mismatch: {record['record_id']}"
        )

    return {
        "input_ids": encoding["input_ids"],
        "attention_mask": encoding["attention_mask"],
        "labels": aligned_labels
    }

def make_dataset(records):
    prepared = [
        prepare_record(record)
        for record in records
    ]

    return Dataset.from_list(prepared)


train_dataset = make_dataset(train_records)
val_dataset = make_dataset(val_records)
test_dataset = make_dataset(test_records)

# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading BioBERT checkpoint...")

model = AutoModelForTokenClassification.from_pretrained(
    BASE_MODEL,
    num_labels=NUM_LABELS,
    id2label=id2label,
    label2id=label2id,
    local_files_only=True
)

assert model.config.num_labels == NUM_LABELS

print("BioBERT loaded successfully")

# ============================================================
# DATA COLLATOR
# ============================================================

data_collator = DataCollatorForTokenClassification(
    tokenizer=tokenizer,
    padding=True,
    pad_to_multiple_of=8 if torch.cuda.is_available() else None
)

# ============================================================
# METRICS
# ============================================================

def compute_metrics(eval_prediction):
    logits, labels = eval_prediction

    predictions = np.argmax(logits, axis=-1)

    true_predictions = []
    true_labels = []

    for prediction, label in zip(predictions, labels):
        current_predictions = []
        current_labels = []

        for predicted_id, true_id in zip(prediction, label):
            if true_id == -100:
                continue

            current_predictions.append(
                id2label[int(predicted_id)]
            )

            current_labels.append(
                id2label[int(true_id)]
            )

        true_predictions.append(current_predictions)
        true_labels.append(current_labels)

    return {
        "precision": precision_score(
            true_labels, true_predictions, zero_division=0
        ),
        "recall": recall_score(
            true_labels, true_predictions, zero_division=0
        ),
        "f1": f1_score(
            true_labels, true_predictions, zero_division=0
        )
    }

# ============================================================
# TRAINING ARGUMENTS
# ============================================================

training_args = TrainingArguments(
    output_dir=str(OUTPUT_DIR),

    num_train_epochs=EPOCHS,

    per_device_train_batch_size=TRAIN_BATCH_SIZE,
    per_device_eval_batch_size=EVAL_BATCH_SIZE,

    gradient_accumulation_steps=GRADIENT_ACCUMULATION,

    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_steps=20,

    optim="adamw_torch",

    fp16=torch.cuda.is_available(),
    gradient_checkpointing=True,

    eval_strategy="epoch",
    save_strategy="epoch",

    load_best_model_at_end=True,
    metric_for_best_model="eval_f1",
    greater_is_better=True,

    save_total_limit=2,

    logging_strategy="steps",
    logging_steps=10,

    report_to="none",

    dataloader_num_workers=0,
    dataloader_pin_memory=torch.cuda.is_available(),

    seed=42
)

# ============================================================
# TRAINER
# ============================================================

trainer = Trainer(
    model=model,
    args=training_args,

    train_dataset=train_dataset,
    eval_dataset=val_dataset,

    processing_class=tokenizer,
    data_collator=data_collator,

    compute_metrics=compute_metrics,

    callbacks=[
        EarlyStoppingCallback(
            early_stopping_patience=2
        )
    ]
)

# ============================================================
# TRAIN
# ============================================================

print("\nStarting BioBERT V2 training...")
print("Do not close this terminal during training.")

train_result = trainer.train()

print("\nTRAINING COMPLETE")

print("\nBest checkpoint:")
print(trainer.state.best_model_checkpoint)

print("\nBest validation metric:")
print(trainer.state.best_metric)

# ============================================================
# SAVE BEST MODEL
# ============================================================

trainer.save_model(str(OUTPUT_DIR / "best_model"))
tokenizer.save_pretrained(str(OUTPUT_DIR / "best_model"))

# ============================================================
# FINAL TEST EVALUATION
# ============================================================

print("\nRunning final test evaluation...")

test_metrics = trainer.evaluate(
    eval_dataset=test_dataset,
    metric_key_prefix="test"
)

print("\nTEST METRICS")

for key, value in test_metrics.items():
    print(f"{key}: {value}")

# ============================================================
# DETAILED ENTITY REPORT
# ============================================================

predictions_output = trainer.predict(test_dataset)

logits = predictions_output.predictions
labels = predictions_output.label_ids

predictions = np.argmax(logits, axis=-1)

true_predictions = []
true_labels = []

for prediction, label in zip(predictions, labels):
    pred_sequence = []
    label_sequence = []

    for predicted_id, true_id in zip(prediction, label):
        if true_id == -100:
            continue

        pred_sequence.append(
            id2label[int(predicted_id)]
        )

        label_sequence.append(
            id2label[int(true_id)]
        )

    true_predictions.append(pred_sequence)
    true_labels.append(label_sequence)

report = classification_report(
    true_labels,
    true_predictions,
    zero_division=0
)

print("\nENTITY-LEVEL CLASSIFICATION REPORT")
print(report)

# ============================================================
# SAVE RESULTS
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with (OUTPUT_DIR / "test_metrics.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(
        test_metrics,
        f,
        indent=4,
        default=float
    )

with (OUTPUT_DIR / "entity_report.txt").open(
    "w", encoding="utf-8"
) as f:
    f.write(report)

print("\nModel saved at:", OUTPUT_DIR / "best_model")
print("Metrics saved successfully.")

if torch.cuda.is_available():
    print(
        "\nPeak GPU allocated:",
        round(
            torch.cuda.max_memory_allocated() / (1024 ** 3),
            2
        ),
        "GB"
    )

print("\nBIOBERT V2 PIPELINE FINISHED")
