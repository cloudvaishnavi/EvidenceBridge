import json
import torch
from sentence_transformers import SentenceTransformer, util

ORIGINAL = "data/bge/evaluation/ekacare_20_ocr.json"
NORMALIZED = "data/bge/evaluation/ekacare_20_ocr_normalized.json"
QUERIES = "data/bge/evaluation/ekacare_retrieval_queries.json"

MODELS = {
    "Original BGE": "models/EvidenceBridge_BGE/base_model",
    "Fine-tuned BGE": "models/EvidenceBridge_BioBERT/model_2_retrieval/bge_finetuned"
}

def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)

def make_chunks(text, max_chars=1400):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks, current = [], ""

    for line in lines:
        if len(current) + len(line) + 1 > max_chars and current:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        chunks.append(current)

    return chunks or [text[:max_chars]]

def prepare_documents(records):
    chunks, doc_ids = [], []

    for record in records:
        doc_id = f"ekacare_{record['record_id'] + 1:02d}"

        for chunk in make_chunks(record["ocr_text"]):
            chunks.append(chunk)
            doc_ids.append(doc_id)

    return chunks, doc_ids

def evaluate(model, chunks, chunk_doc_ids, queries, query_embeddings):
    embeddings = model.encode(
        chunks,
        batch_size=8,
        convert_to_tensor=True,
        normalize_embeddings=True
    )

    similarities = util.cos_sim(query_embeddings, embeddings)
    ranks = []
    details = []

    for i, query in enumerate(queries):
        scores = {}

        for j, doc_id in enumerate(chunk_doc_ids):
            score = similarities[i][j].item()
            scores[doc_id] = max(scores.get(doc_id, -1), score)

        ranking = sorted(scores, key=scores.get, reverse=True)
        target = query["relevant_doc_id"]
        rank = ranking.index(target) + 1
        ranks.append(rank)

        details.append({
            "query": query["query"],
            "relevant_doc_id": target,
            "rank": rank,
            "top_3": ranking[:3]
        })

    total = len(ranks)

    metrics = {
        "recall_at_1": sum(r <= 1 for r in ranks) / total,
        "recall_at_3": sum(r <= 3 for r in ranks) / total,
        "mrr": sum(1 / r for r in ranks) / total
    }

    del embeddings, similarities
    return metrics, details

original_records = load_json(ORIGINAL)
normalized_records = load_json(NORMALIZED)
queries = load_json(QUERIES)

original_chunks, original_ids = prepare_documents(original_records)
normalized_chunks, normalized_ids = prepare_documents(normalized_records)

query_texts = [
    "Represent this sentence for searching relevant passages: " + q["query"]
    for q in queries
]

device = "cuda" if torch.cuda.is_available() else "cpu"
results = {}

print("Device:", device)
print("Queries:", len(queries))
print("Original OCR chunks:", len(original_chunks))
print("Normalized OCR chunks:", len(normalized_chunks))

for model_name, model_path in MODELS.items():
    print(f"\n===== {model_name} =====")

    model = SentenceTransformer(model_path, device=device)

    query_embeddings = model.encode(
        query_texts,
        batch_size=8,
        convert_to_tensor=True,
        normalize_embeddings=True
    )

    for version, chunks, ids in [
        ("Original OCR", original_chunks, original_ids),
        ("Normalized OCR", normalized_chunks, normalized_ids)
    ]:
        metrics, details = evaluate(
            model, chunks, ids, queries, query_embeddings
        )

        results[f"{model_name} | {version}"] = {
            "metrics": metrics,
            "details": details
        }

        print(f"\n{version}")
        print("Recall@1:", round(metrics["recall_at_1"], 4))
        print("Recall@3:", round(metrics["recall_at_3"], 4))
        print("MRR:", round(metrics["mrr"], 4))

    del model, query_embeddings

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

output = "data/bge/evaluation/ekacare_ocr_normalization_comparison.json"

with open(output, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n===== FINAL COMPARISON =====")

for name, result in results.items():
    m = result["metrics"]
    print(
        f"{name:38s} | "
        f"R@1={m['recall_at_1']:.4f} | "
        f"R@3={m['recall_at_3']:.4f} | "
        f"MRR={m['mrr']:.4f}"
    )

print("\nSaved:", output)
