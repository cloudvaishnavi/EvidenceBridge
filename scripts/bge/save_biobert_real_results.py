import json

results = {
    "dataset": "EkaCare Medical Records Parsing Validation Set",
    "shard": "test-00000.parquet",
    "document_type": "Prescription",
    "model": "EvidenceBridge BioBERT V4",
    "checkpoint": "models/EvidenceBridge_BioBERT/model_1_biobert_v4/best_model",
    "ocr_engine": "RapidOCR",
    "evaluation_type": "Qualitative real-document pilot",
    "predicted_entities": [
        {"type": "DATE", "text": "28"},
        {"type": "CLAIM_REFERENCE", "text": "- mar - 2023"},
        {"type": "DIAGNOSIS", "text": "bipolar mood disorder"},
        {"type": "BRAND_NAME", "text": "##tripil sr"},
        {"type": "STRENGTH", "text": "400 mg"},
        {"type": "ACTIVE_INGREDIENT", "text": "sodium valproate 500"},
        {"type": "ACTIVE_INGREDIENT", "text": "valproic acid 145"},
        {"type": "ACTIVE_INGREDIENT", "text": "valparin chron"},
        {"type": "BRAND_NAME", "text": "##o"},
        {"type": "ACTIVE_INGREDIENT", "text": "oxcarbazepine 300 mg oleptal dt 300"},
        {"type": "ACTIVE_INGREDIENT", "text": "quetiapine 100"},
        {"type": "ACTIVE_INGREDIENT", "text": "qutipin sr 100"}
    ],
    "observations": [
        "Diagnosis correctly identified.",
        "Some medicine strengths correctly identified.",
        "Date entity fragmented.",
        "Brand and active ingredient classifications inconsistent.",
        "Adjacent entities merged."
    ],
    "limitation": "One real prescription tested. No quantitative real-world F1 score established."
}

path = "data/bge/evaluation/biobert_real_sample_results.json"

with open(path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("Saved:", path)
