import json
import torch
from sentence_transformers import SentenceTransformer, util

BASE_PATH = "models/EvidenceBridge_BGE/base_model"
FINETUNED_PATH = "models/EvidenceBridge_BioBERT/model_2_retrieval/bge_finetuned"

DOCS_PATH = "data/evaluation/india_demo_documents.json"
QUERIES_PATH = "data/bge/evaluation/india_retrieval_queries.json"

with open(DOCS_PATH, encoding="utf-8-sig") as f:
    documents = json.load(f)

with open(QUERIES_PATH, encoding="utf-8-sig") as f:
    queries = json.load(f)

doc_ids = [d["id"] for d in documents]
doc_texts = [d["text"] for d in documents]

device = "cuda" if torch.cuda.is_available() else "cpu"

models = {
    "Original BGE": BASE_PATH,
    "Fine-tuned BGE": FINETUNED_PATH
}

for name, path in models.items():
    print(f"\n===== {name} =====")

    model = SentenceTransformer(path, device=device)

    doc_embeddings = model.encode(
        doc_texts,
        convert_to_tensor=True,
        normalize_embeddings=True
    )

    query_embeddings = model.encode(
        [q["query"] for q in queries],
        convert_to_tensor=True,
        normalize_embeddings=True
    )

    similarities = util.cos_sim(query_embeddings, doc_embeddings)

    r1 = 0
    r2 = 0
    reciprocal_ranks = []

    for i, query in enumerate(queries):
        ranking = torch.argsort(
            similarities[i], descending=True
        ).tolist()

        ranked_ids = [doc_ids[j] for j in ranking]
        rank = ranked_ids.index(query["relevant_doc_id"]) + 1

        r1 += int(rank <= 1)
        r2 += int(rank <= 2)
        reciprocal_ranks.append(1 / rank)

        print(f"Rank: {rank} | Query: {query['query']}")

    total = len(queries)

    print(f"Recall@1: {r1 / total:.4f}")
    print(f"Recall@2: {r2 / total:.4f}")
    print(f"MRR: {sum(reciprocal_ranks) / total:.4f}")

    del model, doc_embeddings, query_embeddings, similarities
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
