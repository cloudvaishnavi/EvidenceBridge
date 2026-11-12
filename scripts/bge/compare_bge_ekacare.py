import json
import torch
from sentence_transformers import SentenceTransformer, util

OCR_PATH = "data/bge/evaluation/ekacare_20_ocr.json"
QUERIES_PATH = "data/bge/evaluation/ekacare_retrieval_queries.json"

MODELS = {
    "Original BGE": "models/EvidenceBridge_BGE/base_model",
    "Fine-tuned BGE": "models/EvidenceBridge_BioBERT/model_2_retrieval/bge_finetuned"
}

with open(OCR_PATH, encoding="utf-8-sig") as f:
    records = json.load(f)

with open(QUERIES_PATH, encoding="utf-8-sig") as f:
    queries = json.load(f)

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

doc_chunks = []
chunk_doc_ids = []

for record in records:
    doc_id = f"ekacare_{record['record_id'] + 1:02d}"
    chunks = make_chunks(record["ocr_text"])

    for chunk in chunks:
        doc_chunks.append(chunk)
        chunk_doc_ids.append(doc_id)

doc_ids = sorted(set(chunk_doc_ids))
query_texts = [
    "Represent this sentence for searching relevant passages: " + q["query"]
    for q in queries
]

device = "cuda" if torch.cuda.is_available() else "cpu"
results = {}

for model_name, model_path in MODELS.items():
    print(f"\n===== {model_name} =====")
    model = SentenceTransformer(model_path, device=device)

    chunk_embeddings = model.encode(
        doc_chunks,
        batch_size=8,
        convert_to_tensor=True,
        normalize_embeddings=True
    )

    query_embeddings = model.encode(
        query_texts,
        batch_size=8,
        convert_to_tensor=True,
        normalize_embeddings=True
    )

    similarities = util.cos_sim(query_embeddings, chunk_embeddings)

    ranks = []
    details = []

    for i, query in enumerate(queries):
        doc_scores = {}

        for j, doc_id in enumerate(chunk_doc_ids):
            score = similarities[i][j].item()
            doc_scores[doc_id] = max(doc_scores.get(doc_id, -1), score)

        ranking = sorted(doc_scores, key=doc_scores.get, reverse=True)
        target = query["relevant_doc_id"]
        rank = ranking.index(target) + 1
        ranks.append(rank)

        details.append({
            "query": query["query"],
            "relevant_doc_id": target,
            "rank": rank,
            "top_3": ranking[:3]
        })

        print(f"Rank: {rank:2d} | {target} | {query['query']}")

    total = len(ranks)
    metrics = {
        "recall_at_1": sum(r <= 1 for r in ranks) / total,
        "recall_at_3": sum(r <= 3 for r in ranks) / total,
        "mrr": sum(1 / r for r in ranks) / total
    }

    results[model_name] = {
        "metrics": metrics,
        "details": details
    }

    print("Recall@1:", round(metrics["recall_at_1"], 4))
    print("Recall@3:", round(metrics["recall_at_3"], 4))
    print("MRR:", round(metrics["mrr"], 4))

    del model, chunk_embeddings, query_embeddings, similarities
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

output_path = "data/bge/evaluation/ekacare_20_bge_comparison.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\nComparison saved:", output_path)

