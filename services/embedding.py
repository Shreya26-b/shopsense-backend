# services/embedding.py
from sentence_transformers import SentenceTransformer
import numpy as np

# Load the model once when the module is imported
# This takes ~3 seconds on first load but is then cached in memory
# all-MiniLM-L6-v2 produces 384-dimensional vectors
# It's small (80MB), fast, and accurate enough for our use case
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Embedding model loaded")


def embed_text(text: str) -> np.ndarray:
    """
    Convert a single string into a 384-dimensional vector.
    Used for embedding user questions at query time.
    """
    return model.encode(text, convert_to_numpy=True)


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Convert a list of strings into a matrix of vectors.
    Used for embedding all products/orders when building the FAISS index.
    
    Returns shape: (len(texts), 384)
    """
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=True)


def texts_to_chunks(products: list[dict], orders: list[dict]) -> list[str]:
    """
    Convert raw database rows into text chunks for embedding.
    Improved format includes revenue context for better retrieval.
    """
    chunks = []

    # Build order stats per product for richer product chunks
    product_stats = {}
    for o in orders:
        pid = str(o.get("product_id") or o.get("id", ""))
        pname = o.get("product_name", "")
        if pname not in product_stats:
            product_stats[pname] = {
                "total_revenue": 0,
                "total_units":   0,
                "order_count":   0
            }
        product_stats[pname]["total_revenue"] += float(o.get("revenue", 0))
        product_stats[pname]["total_units"]   += int(o.get("quantity", 0))
        product_stats[pname]["order_count"]   += 1

    # Product chunks — now include sales performance
    for p in products:
        name  = p["name"]
        stats = product_stats.get(name, {})
        chunk = (
            f"Product: {name}, "
            f"Category: {p['category'] or 'Uncategorized'}, "
            f"Price: ${float(p['price']):.2f}, "
            f"Stock: {p['stock']} units, "
            f"Total revenue: ${stats.get('total_revenue', 0):.2f}, "
            f"Total units sold: {stats.get('total_units', 0)}, "
            f"Number of orders: {stats.get('order_count', 0)}"
        )
        chunks.append(chunk)

    # Order chunks — individual transactions
    for o in orders:
        chunk = (
            f"Order: {o['product_name']} purchased by {o['customer_name']}, "
            f"Quantity: {o['quantity']} units, "
            f"Revenue: ${float(o['revenue']):.2f}, "
            f"Date: {o['order_date'].strftime('%B %Y')}"
        )
        chunks.append(chunk)

    return chunks