# services/recommendations.py
import numpy as np
import faiss
import json
import os
from services.embedding import embed_texts
from services.faiss_index import INDEX_DIR

def get_product_recommendations(
    user_id:    str,
    top_k:      int = 3,
    min_score:  float = 0.5
) -> list[dict]:
    """
    For each product in the user's FAISS index,
    finds the top_k most similar other products.

    Uses cosine similarity on product embeddings.
    Only returns recommendations above min_score threshold.

    Returns list of:
    {
        "product": "AirPods Pro",
        "recommendations": [
            {"product": "Noise Cancelling Headphones", "score": 0.91},
            {"product": "Wireless Mouse", "score": 0.79},
            {"product": "Webcam HD", "score": 0.82},
        ]
    }
    """

    # ── 1. Load the user's index and chunks ───────────────
    index_path = os.path.join(INDEX_DIR, f"{user_id}.index")
    meta_path  = os.path.join(INDEX_DIR, f"{user_id}.json")

    if not os.path.exists(index_path):
        return []

    index  = faiss.read_index(index_path)
    with open(meta_path, "r") as f:
        chunks = json.load(f)

    # ── 2. Separate product chunks from order chunks ──────
    # Product chunks start with "Product:"
    # Order chunks start with "Order:"
    product_chunks = [
        (i, chunk) for i, chunk in enumerate(chunks)
        if chunk.startswith("Product:")
    ]

    if not product_chunks:
        return []

    print(f"📦 Computing recommendations for {len(product_chunks)} products...")

    # ── 3. Extract product names from chunks ──────────────
    # Chunk format: "Product: AirPods Pro, Category: Electronics..."
    def extract_product_name(chunk: str) -> str:
        try:
            # Split by comma, take first part, remove "Product: " prefix
            return chunk.split(",")[0].replace("Product: ", "").strip()
        except:
            return chunk[:30]

    # ── 4. Get vectors for all product chunks ─────────────
    # Re-embed just the product chunks for comparison
    product_texts  = [chunk for _, chunk in product_chunks]
    product_names  = [extract_product_name(c) for c in product_texts]
    product_vectors = index.reconstruct_n(
        product_chunks[0][0],
        len(product_chunks)
    ) if hasattr(index, 'reconstruct_n') else None

    # If reconstruct_n not available re-embed the chunks
    if product_vectors is None:
        product_vectors = embed_texts(product_texts).astype(np.float32)
        faiss.normalize_L2(product_vectors)

    # ── 5. Build a mini FAISS index for products only ─────
    # This lets us do product-to-product similarity search
    dimension    = product_vectors.shape[1]
    product_index = faiss.IndexFlatIP(dimension)  # IP = inner product = cosine similarity
    product_index.add(product_vectors)

    # ── 6. Find similar products for each product ─────────
    recommendations = []

    for i, name in enumerate(product_names):
        # Search for top_k + 1 because the product itself
        # will always be the most similar (score = 1.0)
        query_vector = product_vectors[i].reshape(1, -1)
        scores, indices = product_index.search(query_vector, top_k + 1)

        similar = []
        for score, idx in zip(scores[0], indices[0]):
            # Skip the product itself
            if idx == i:
                continue

            # Only include results above the similarity threshold
            if float(score) < min_score:
                continue

            similar.append({
                "product": product_names[idx],
                "score":   round(float(score), 3)
            })

            if len(similar) == top_k:
                break

        recommendations.append({
            "product":         name,
            "recommendations": similar
        })

    print(f"✅ Recommendations computed for {len(recommendations)} products")
    return recommendations