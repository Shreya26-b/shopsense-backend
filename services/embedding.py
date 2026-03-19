# services/embedding.py
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch
torch.set_num_threads(1)

from sentence_transformers import SentenceTransformer
import numpy as np

# Model is pre-downloaded during build phase
# This just loads from local cache — fast startup
CACHE_DIR = "/opt/render/project/src/.cache/models"
os.makedirs(CACHE_DIR, exist_ok=True)

print("Loading embedding model from cache...")
model = SentenceTransformer(
    "all-MiniLM-L6-v2",
    device="cpu",
    cache_folder=CACHE_DIR
)
print("Embedding model loaded")


def embed_text(text: str) -> np.ndarray:
    return model.encode(text, convert_to_numpy=True)


def embed_texts(texts: list[str]) -> np.ndarray:
    return model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=32
    )


def texts_to_chunks(products: list[dict], orders: list[dict]) -> list[str]:
    chunks = []

    product_stats = {}
    for o in orders:
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

    for o in orders:
        chunk = (
            f"Order: {o['product_name']} purchased by {o['customer_name']}, "
            f"Quantity: {o['quantity']} units, "
            f"Revenue: ${float(o['revenue']):.2f}, "
            f"Date: {o['order_date'].strftime('%B %Y')}"
        )
        chunks.append(chunk)

    return chunks