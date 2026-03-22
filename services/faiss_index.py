# services/faiss_index.py
import os
import json
import gc
import faiss
import numpy as np
from services.embedding import embed_text, texts_to_chunks, get_model
from database import database

INDEX_DIR = "faiss_index"
os.makedirs(INDEX_DIR, exist_ok=True)


# ── Build index ───────────────────────────────────────────

async def build_user_index(user_id: str) -> dict:
    """
    Fetches products and orders from DB, converts to text chunks,
    embeds them in small batches to stay within 512MB RAM,
    and saves the FAISS index to disk.
    """

    # ── 1. Fetch products ─────────────────────────────────
    products = await database.fetch_all(
        """
        SELECT id, name, category, price, stock
        FROM "Product"
        WHERE "userId" = :user_id
        """,
        {"user_id": user_id}
    )

    # ── 2. Fetch most recent 100 orders only ──────────────
    # Limiting to 100 keeps memory usage within 512MB free tier
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
        ORDER BY o."orderDate" DESC
        LIMIT 100
        """,
        {"user_id": user_id}
    )

    if not products and not orders:
        return {"indexed": 0, "message": "No data found for this user"}

    # ── 3. Convert to text chunks ─────────────────────────
    chunks = texts_to_chunks(
        [dict(p) for p in products],
        [dict(o) for o in orders]
    )
    print(f"Created {len(chunks)} chunks for user {user_id[:8]}...")

    # ── 4. Free memory before embedding ──────────────────
    gc.collect()

    # ── 5. Embed in small batches to save RAM ─────────────
    print(f"Embedding {len(chunks)} chunks...")
    model       = get_model()
    batch_size  = 4
    all_vectors = []

    for i in range(0, len(chunks), batch_size):
        batch   = chunks[i:i + batch_size]
        vectors = model.encode(
            batch,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        all_vectors.append(vectors)
        gc.collect()    # free after every batch

    # ── 6. Stack all vectors ──────────────────────────────
    vectors = np.vstack(all_vectors).astype(np.float32)

    # ── 7. Free batch memory ──────────────────────────────
    del all_vectors
    gc.collect()

    # ── 8. Normalize for cosine similarity ────────────────
    faiss.normalize_L2(vectors)

    # ── 9. Build FAISS index ──────────────────────────────
    dimension = vectors.shape[1]   # 384
    index     = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    print(f"FAISS index built with {index.ntotal} vectors")

    # ── 10. Save index to disk ────────────────────────────
    index_path = os.path.join(INDEX_DIR, f"{user_id}.index")
    faiss.write_index(index, index_path)

    # ── 11. Save chunks as metadata ───────────────────────
    meta_path = os.path.join(INDEX_DIR, f"{user_id}.json")
    with open(meta_path, "w") as f:
        json.dump(chunks, f)

    # ── 12. Free index memory ─────────────────────────────
    del vectors
    del index
    gc.collect()

    print(f"Index saved to {index_path}")

    return {
        "indexed":  len(chunks),
        "products": len(products),
        "orders":   len(orders),
        "message":  "Index built successfully"
    }


# ── Load index ────────────────────────────────────────────

def load_user_index(user_id: str):
    """
    Loads a user's FAISS index and metadata from disk.
    Returns (index, chunks) or (None, None) if not found.
    """
    index_path = os.path.join(INDEX_DIR, f"{user_id}.index")
    meta_path  = os.path.join(INDEX_DIR, f"{user_id}.json")

    if not os.path.exists(index_path):
        return None, None

    index = faiss.read_index(index_path)
    with open(meta_path, "r") as f:
        chunks = json.load(f)

    return index, chunks


# ── Search index ──────────────────────────────────────────

def search_index(user_id: str, question: str, top_k: int = 5):
    """
    Searches the user's FAISS index for the most relevant chunks.
    Returns top_k most similar text chunks.
    """
    index, chunks = load_user_index(user_id)

    if index is None:
        return []

    # Embed the question
    query_vector = embed_text(question)
    query_vector = query_vector.reshape(1, -1).astype(np.float32)
    faiss.normalize_L2(query_vector)

    # Search
    distances, indices = index.search(query_vector, top_k)

    results = []
    for i, idx in enumerate(indices[0]):
        if idx != -1:
            results.append({
                "chunk": chunks[idx],
                "score": float(distances[0][i]),
                "rank":  i + 1
            })

    return results