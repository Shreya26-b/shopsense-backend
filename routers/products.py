# routers/products.py
from fastapi import APIRouter, Depends
from auth import get_current_user
from database import database
from services.recommendations import get_product_recommendations

router = APIRouter(prefix="/products", tags=["Products"])


# ── All products ──────────────────────────────────────────

@router.get("/")
async def get_products(user_id: str = Depends(get_current_user)):
    """
    Returns all products for the authenticated user
    with their sales statistics.
    """
    rows = await database.fetch_all(
        """
        SELECT
            p.id,
            p.name,
            p.category,
            p.price,
            p.stock,
            COALESCE(SUM(o.revenue),  0) AS total_revenue,
            COALESCE(SUM(o.quantity), 0) AS total_units_sold,
            COALESCE(COUNT(o.id),     0) AS total_orders
        FROM "Product" p
        LEFT JOIN "Order" o ON p.id = o."productId"
        WHERE p."userId" = :user_id
        GROUP BY p.id, p.name, p.category, p.price, p.stock
        ORDER BY total_revenue DESC
        """,
        {"user_id": user_id}
    )

    return [
        {
            "id":               str(row["id"]),
            "name":             row["name"],
            "category":         row["category"],
            "price":            float(row["price"]),
            "stock":            row["stock"],
            "total_revenue":    round(float(row["total_revenue"]), 2),
            "total_units_sold": row["total_units_sold"],
            "total_orders":     row["total_orders"],
        }
        for row in rows
    ]


# ── Recommendations ───────────────────────────────────────

@router.get("/recommendations")
async def get_recommendations(
    user_id: str = Depends(get_current_user)
):
    """
    Returns top 3 similar products for each product
    using cosine similarity on FAISS embeddings.

    Used to power the "Customers Also Bought" widget.
    """
    recommendations = get_product_recommendations(
        user_id=user_id,
        top_k=3,
        min_score=0.5
    )

    if not recommendations:
        return {
            "message": "No index found. Please build index first.",
            "data":    []
        }

    return {
        "message": f"Recommendations for {len(recommendations)} products",
        "data":    recommendations
    }