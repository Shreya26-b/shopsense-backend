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
    
    Each chunk is a human-readable sentence describing one record.
    The quality of these chunks directly affects RAG accuracy —
    more descriptive chunks = better retrieval results.
    """
    chunks = []

    # Convert each product to a descriptive text chunk
    for p in products:
        chunk = (
            f"Product: {p['name']}, "
            f"Category: {p['category'] or 'Uncategorized'}, "
            f"Price: ${float(p['price']):.2f}, "
            f"Stock: {p['stock']} units available"
        )
        chunks.append(chunk)

    # Convert each order to a descriptive text chunk
    for o in orders:
        chunk = (
            f"Order: {o['product_name']} purchased by {o['customer_name']}, "
            f"Quantity: {o['quantity']} units, "
            f"Revenue: ${float(o['revenue']):.2f}, "
            f"Date: {o['order_date'].strftime('%B %Y')}"
        )
        chunks.append(chunk)

    return chunks