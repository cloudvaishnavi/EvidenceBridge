
import json
import torch
from pathlib import Path
from transformers import (
    AutoConfig,
    AutoModelForTokenClassification,
    AutoTokenizer,
)

V3_PATH = Path(
    "models/EvidenceBridge_BioBERT/model_1_biobert_v3/best_model"
)

SCHEMA_PATH = Path(
    "models/EvidenceBridge_BioBERT/india_ner_schema_v4.json"
)

BASELINE_PATH = Path(
    "models/EvidenceBridge_BioBERT/baseline_v1"
)

OUTPUT_PATH = Path(
    "models/EvidenceBridge_BioBERT/model_1_biobert_v4_init"
)

# --------------------------------------------------
# 1. Load V4 schema
# --------------------------------------------------

schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

label2id = schema["label2id"]
id2label = {int(k): v for k, v in schema["id2label"].items()}

num_labels = len(label2id)

assert num_labels == 69, f"Expected 69 labels, got {num_labels}"

# --------------------------------------------------
# 2. Load trained V3 model
# --------------------------------------------------

old_model = AutoModelForTokenClassification.from_pretrained(
    str(V3_PATH)
)

old_id2label = {
    int(k): v
    for k, v in old_model.config.id2label.items()
}

assert len(old_id2label) == 67

# Verify all existing label IDs are unchanged.
for old_id, old_label in old_id2label.items():
    assert id2label[old_id] == old_label, (
        f"Label mismatch at ID {old_id}: "
        f"{old_label} != {id2label[old_id]}"
    )

print("V3 label mapping verified: 67/67")

# --------------------------------------------------
# 3. Create a new 69-label model
# --------------------------------------------------

config = AutoConfig.from_pretrained(
    str(V3_PATH),
    num_labels=num_labels,
    id2label=id2label,
    label2id=label2id,
)

new_model = AutoModelForTokenClassification.from_config(config)

# --------------------------------------------------
# 4. Copy the complete BERT encoder
# --------------------------------------------------

old_encoder = getattr(old_model, old_model.base_model_prefix)
new_encoder = getattr(new_model, new_model.base_model_prefix)

new_encoder.load_state_dict(old_encoder.state_dict())

# --------------------------------------------------
# 5. Copy existing classifier weights
# --------------------------------------------------

with torch.no_grad():
    new_model.classifier.weight[:67].copy_(
        old_model.classifier.weight
    )

    new_model.classifier.bias[:67].copy_(
        old_model.classifier.bias
    )

# Rows 67 and 68 retain their newly initialized values.

# --------------------------------------------------
# 6. Verify classifier dimensions
# --------------------------------------------------

assert new_model.classifier.weight.shape == (69, 768)
assert new_model.classifier.bias.shape == (69,)

# --------------------------------------------------
# 7. Save V4 initialization
# --------------------------------------------------

OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

new_model.save_pretrained(str(OUTPUT_PATH))

tokenizer = AutoTokenizer.from_pretrained(str(BASELINE_PATH))
tokenizer.save_pretrained(str(OUTPUT_PATH))

# --------------------------------------------------
# 8. Final verification
# --------------------------------------------------

saved_model = AutoModelForTokenClassification.from_pretrained(
    str(OUTPUT_PATH)
)

assert saved_model.classifier.weight.shape == (69, 768)
assert saved_model.config.num_labels == 69

with torch.no_grad():
    assert torch.equal(
        saved_model.classifier.weight[:67],
        old_model.classifier.weight
    )

    assert torch.equal(
        saved_model.classifier.bias[:67],
        old_model.classifier.bias
    )

print("\n========== V4 INITIALIZATION SUCCESS ==========")
print("V3 labels copied: 67")
print("New labels initialized: 2")
print("Total labels:", saved_model.config.num_labels)
print("Classifier shape:", tuple(saved_model.classifier.weight.shape))
print("Encoder weights: copied from V3")
print("Existing classifier weights: verified")
print("V4 saved at:", OUTPUT_PATH)
print("V3 checkpoint: unchanged")
