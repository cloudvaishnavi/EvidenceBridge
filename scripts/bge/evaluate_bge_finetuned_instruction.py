import json
import torch
from sentence_transformers import SentenceTransformer, util

MODEL_PATH = "models/EvidenceBridge_BioBERT/model_2_retrieval/bge_finetuned"

with open("data/evaluation/india_demo_documents.json", encoding="utf-8-sig") as f:
    documents = json.load(f)

with open("data/bge/evaluation/india_retrieval_queries.json", encoding="utf-8-sig") as f:
    queries = json.load(f)

model = SentenceTransformer(
    MODEL_PATH,
    device="cuda" if torch.cuda.is_available() else "cpu"
)

doc_embeddings = model.encode(
    [d["text"] for d in documents],
    convert_to_tensor=True,
    normalize_embeddings=True
)

prefix = "Represent this sentence for searching relevant passages: "

query_embeddings = model.encode(
    [prefix + q["query"] for q in queries],
    convert_to_tensor=True,
    normalize_embeddings=True
)

similarities = util.cos_sim(query_embeddings, doc_embeddings)

doc_ids = [d["id"] for d in documents]
r1 = r2 = 0
rr = []

print("\n===== FINE-TUNED BGE WITH QUERY INSTRUCTION =====")

for i, query in enumerate(queries):
    ranking = torch.argsort(similarities[i], descending=True).tolist()
    ranked_ids = [doc_ids[j] for j in ranking]
    rank = ranked_ids.index(query["relevant_doc_id"]) + 1

    r1 += int(rank == 1)
    r2 += int(rank <= 2)
    rr.append(1 / rank)

    print(f"Rank {rank} | {query['query']}")

total = len(queries)

summary = {
    "model": "Original BGE with query instruction",
    "recall_at_1": r1 / total,
    "recall_at_2": r2 / total,
    "mrr": sum(rr) / total
}

print("\nRecall@1:", round(summary["recall_at_1"], 4))
print("Recall@2:", round(summary["recall_at_2"], 4))
print("MRR:", round(summary["mrr"], 4))

with open(
    "data/bge/evaluation/bge_finetuned_instruction_results.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=2)

print("Results saved.")


