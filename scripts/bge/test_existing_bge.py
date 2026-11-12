from sentence_transformers import SentenceTransformer
import torch

model_path = "models/EvidenceBridge_BioBERT/model_2_retrieval/bge_finetuned"

print("Loading existing fine-tuned BGE checkpoint...")

model = SentenceTransformer(
    model_path,
    device="cuda" if torch.cuda.is_available() else "cpu"
)

texts = [
    "Paracetamol 500 mg was billed at INR 180.",
    "The hospital invoice contains a medicine charge of INR 180.",
    "The patient was diagnosed with acute gastroenteritis.",
    "The insurance company approved INR 70000 for the claim."
]

embeddings = model.encode(
    texts,
    convert_to_tensor=True,
    normalize_embeddings=True
)

print("\nModel loaded successfully.")
print("Embedding shape:", embeddings.shape)
print("Embedding dimensions:", embeddings.shape[1])
print("Device:", embeddings.device)
print("Similarity between first two sentences:",
      round(torch.matmul(embeddings[0], embeddings[1]).item(), 4))
