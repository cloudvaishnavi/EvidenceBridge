from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5",
    device="cpu"
)

model.save("models/EvidenceBridge_BGE/base_model")

print("Original BGE base model downloaded and saved.")
print("Embedding dimensions:", model.get_sentence_embedding_dimension())
