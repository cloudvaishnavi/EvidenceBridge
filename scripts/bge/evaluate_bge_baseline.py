import json
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
import torch

MODEL_PATH = "models/EvidenceBridge_BioBERT/model_2_retrieval/bge_finetuned"
DOCS_PATH = "data/evaluation/india_demo_documents.json"
QUERIES_PATH = "data/bge/evaluation/india_retrieval_queries.json"
OUTPUT_PATH = "data/bge/evaluation/india_bge_baseline_results.json"

device = "cuda" if torch.cuda.is_available() else "cpu"

print("Loading existing fine-tuned BGE...")
model = SentenceTransformer(MODEL_PATH, device=device)

with open(DOCS_PATH, "r", encoding="utf-8-sig") as f:
    documents = json.load(f)

with open(QUERIES_PATH, "r", encoding="utf-8-sig") as f:
    queries = json.load(f)

doc_texts = [d["text"] for d in documents]
doc_ids = [d["id"] for d in documents]

doc_embeddings = model.encode(
    doc_texts,
    convert_to_tensor=True,
    normalize_embeddings=True
)

query_texts = [q["query"] for q in queries]

query_embeddings = model.encode(
    query_texts,
    convert_to_tensor=True,
    normalize_embeddings=True
)

similarities = util.cos_sim(query_embeddings, doc_embeddings)

results = []
reciprocal_ranks = []
recall_at_1 = 0
recall_at_2 = 0

print("\n===== INDIAN HEALTHCARE RETRIEVAL RESULTS =====")

for i, query in enumerate(queries):
    ranking = torch.argsort(similarities[i], descending=True).tolist()
    ranked_ids = [doc_ids[j] for j in ranking]
    relevant_id = query["relevant_doc_id"]

    rank = ranked_ids.index(relevant_id) + 1
    reciprocal_rank = 1 / rank

    reciprocal_ranks.append(reciprocal_rank)
    recall_at_1 += int(rank <= 1)
    recall_at_2 += int(rank <= 2)

    item = {
        "query": query["query"],
        "expected_document": relevant_id,
        "ranked_documents": ranked_ids,
        "correct_rank": rank,
        "reciprocal_rank": reciprocal_rank
    }

    results.append(item)

    print(f"\nQuery: {query['query']}")
    print("Expected:", relevant_id)
    print("Top result:", ranked_ids[0])
    print("Correct document rank:", rank)

total = len(queries)

summary = {
    "model": "Existing fine-tuned BGE",
    "documents": len(documents),
    "queries": total,
    "recall_at_1": recall_at_1 / total,
    "recall_at_2": recall_at_2 / total,
    "mrr": sum(reciprocal_ranks) / total,
    "results": results
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("\n===== BASELINE METRICS =====")
print(f"Recall@1: {summary['recall_at_1']:.4f}")
print(f"Recall@2: {summary['recall_at_2']:.4f}")
print(f"MRR:      {summary['mrr']:.4f}")
print("Saved:", OUTPUT_PATH)
