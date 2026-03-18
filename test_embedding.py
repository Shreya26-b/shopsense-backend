# test_embedding.py
from services.embedding import embed_text, embed_texts

# ── Test 1: Single embedding ──────────────────────────────
print("\n── Test 1: Single embedding ──")
vector = embed_text("AirPods Pro, Electronics, $249.99")
print(f"Input:  'AirPods Pro, Electronics, $249.99'")
print(f"Output: vector of {len(vector)} numbers")
print(f"First 5 values: {vector[:5].round(4)}")

# ── Test 2: Multiple embeddings ───────────────────────────
print("\n── Test 2: Multiple embeddings ──")
texts = [
    "AirPods Pro, Electronics, $249.99",
    "Mechanical Keyboard, Electronics, $89.99",
    "Ergonomic Chair, Furniture, $399.99",
]
vectors = embed_texts(texts)
print(f"Input:  {len(texts)} text chunks")
print(f"Output: matrix of shape {vectors.shape}")
print(f"        ({vectors.shape[0]} chunks × {vectors.shape[1]} dimensions)")

# ── Test 3: Semantic similarity ───────────────────────────
print("\n── Test 3: Semantic similarity ──")
from numpy.linalg import norm

def cosine_similarity(a, b):
    return float(np.dot(a, b) / (norm(a) * norm(b)))

import numpy as np

v1 = embed_text("wireless earbuds")
v2 = embed_text("AirPods Pro bluetooth headphones")
v3 = embed_text("Ergonomic Office Chair")

sim_12 = cosine_similarity(v1, v2)
sim_13 = cosine_similarity(v1, v3)

print(f"'wireless earbuds' vs 'AirPods Pro bluetooth headphones': {sim_12:.4f}")
print(f"'wireless earbuds' vs 'Ergonomic Office Chair':           {sim_13:.4f}")
print(f"\nHigher score = more similar meaning")
print(f"'wireless earbuds' should be much closer to 'AirPods Pro' than 'Chair'")