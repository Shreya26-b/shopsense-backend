# services/faiss_index.py
import os
import json
import faiss
import numpy as np
from services.embedding import embed_text, embed_texts, texts_to_chunks
from database import database

# Directory where FAISS indexes are saved
# One index file per user: faiss_index/{user_id}.index
# One metadata file per user: faiss_index/{user_id}.json
INDEX_DIR = "faiss_index"
os.makedirs(INDEX_DIR, exist_ok=True)


# ── Building the index ────────────────────────────────────

async def build_user_index(user_id: str) -> dict:
    """
    Fetches all products and orders for a user from the database,
    converts them to text chunks, embeds them, and saves the
    FAISS index to disk.

    Called when:
    - A user uploads a CSV (re-index after new data)
    - Manually triggered for a user
    """

    # ── 1. Fetch products from database ──────────────────
    products = await database.fetch_all(
        """
        SELECT id, name, category, price, stock
        FROM "Product"
        WHERE "userId" = :user_id
        """,
        {"user_id": user_id}
    )

    # ── 2. Fetch orders with product + customer names ─────
    # We JOIN here to get human-readable names instead of IDs
    # This makes the text chunks much more descriptive
    orders = await database.fetch_all(
        """
        SELECT
            o.id,
            o.quantity,
            o.revenue,
            o."orderDate"  as order_date,
            p.name         as product_name,
            c.name         as customer_name
        FROM "Order" o
        JOIN "Product"  p ON o."productId"  = p.id
        JOIN "Customer" c ON o."customerId" = c.id
        WHERE o."userId" = :user_id
        """,
        {"user_id": user_id}
    )

    if not products and not orders:
        return {"indexed": 0, "message": "No data found for this user"}

    # ── 3. Convert rows to text chunks ───────────────────
    # Each row becomes a descriptive sentence
    # e.g. "Product: AirPods Pro, Category: Electronics, Price: $249.99"
    chunks = texts_to_chunks(
        [dict(p) for p in products],
        [dict(o) for o in orders]
    )

    print(f"📝 Created {len(chunks)} text chunks for user {user_id[:8]}...")

    # ── 4. Embed all chunks into vectors ──────────────────
    # Shape: (num_chunks, 384)
    # This is the slowest step — takes 5-15 seconds for 220 chunks
    print(f"🔢 Embedding {len(chunks)} chunks...")
    vectors = embed_texts(chunks)

    # ── 5. Normalize vectors for cosine similarity ────────
    # FAISS uses L2 (Euclidean) distance by default
    # Normalizing vectors makes L2 distance equivalent to cosine similarity
    # This gives us better semantic search results
    faiss.normalize_L2(vectors)

    # ── 6. Build the FAISS index ──────────────────────────
    dimension = vectors.shape[1]  # 384

    # IndexFlatL2 = exact search using L2 distance
    # "Flat" means it stores all vectors and compares exactly
    # Good for our size (220 vectors) — would need approximate
    # search (IndexIVFFlat) for millions of vectors
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)

    print(f"✅ FAISS index built with {index.ntotal} vectors")

    # ── 7. Save index to disk ─────────────────────────────
    index_path = os.path.join(INDEX_DIR, f"{user_id}.index")
    faiss.write_index(index, index_path)

    # ── 8. Save chunks as metadata ────────────────────────
    # FAISS only stores vectors — not the original text
    # We need to save the chunks separately so we can return
    # the actual text when a vector is retrieved
    meta_path = os.path.join(INDEX_DIR, f"{user_id}.json")
    with open(meta_path, "w") as f:
        json.dump(chunks, f)

    print(f"💾 Index saved to {index_path}")

    return {
        "indexed":   len(chunks),
        "products":  len(products),
        "orders":    len(orders),
        "message":   "Index built successfully"
    }


# ── Loading the index ─────────────────────────────────────

def load_user_index(user_id: str):
    """
    Loads a user's FAISS index and metadata from disk.
    Returns (index, chunks) tuple or (None, None) if not found.

    Called on every chat query — loading from disk is fast
    because the OS caches recently used files in memory.
    """
    index_path = os.path.join(INDEX_DIR, f"{user_id}.index")
    meta_path  = os.path.join(INDEX_DIR, f"{user_id}.json")

    if not os.path.exists(index_path):
        return None, None

    index  = faiss.read_index(index_path)
    with open(meta_path, "r") as f:
        chunks = json.load(f)

    return index, chunks


# ── Searching the index ───────────────────────────────────

def search_index(user_id: str, question: str, top_k: int = 5):
    """
    Searches a user's FAISS index for chunks most relevant
    to the question. Returns top_k most similar text chunks.

    This is the RETRIEVAL step of RAG.
    """

    # Load the user's index from disk
    index, chunks = load_user_index(user_id)

    if index is None:
        return []

    # Embed the question using the same model
    # CRITICAL: must use the same model as when building the index
    # Different models produce incompatible vector spaces
    query_vector = embed_text(question)

    # Reshape to 2D array — FAISS expects (num_queries, dimensions)
    query_vector = query_vector.reshape(1, -1).astype(np.float32)

    # Normalize for cosine similarity (same as when building)
    faiss.normalize_L2(query_vector)

    # Search — returns distances and indices of top_k matches
    # distances: how similar each result is (lower = more similar after normalization)
    # indices: which chunks in our list matched
    distances, indices = index.search(query_vector, top_k)

    # Retrieve the actual text chunks using the indices
    results = []
    for i, idx in enumerate(indices[0]):
        if idx != -1:  # -1 means no result found
            results.append({
                "chunk":    chunks[idx],
                "score":    float(distances[0][i]),
                "rank":     i + 1
            })

    return results