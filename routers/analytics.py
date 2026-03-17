# routers/analytics.py
from fastapi import APIRouter, Depends
from database import database
from auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ── Overview ──────────────────────────────────────────────
# Returns the four headline KPI numbers for the dashboard
@router.get("/overview")
async def get_overview(user_id: str = Depends(get_current_user)):

    # Single query gets all four numbers at once
    result = await database.fetch_one(
        """
        SELECT
            COALESCE(SUM(revenue), 0)                    AS total_revenue,
            COUNT(*)                                      AS total_orders,
            COUNT(DISTINCT "customerId")                  AS total_customers,
            COALESCE(AVG(revenue), 0)                    AS avg_order_value
        FROM "Order"
        WHERE "userId" = :user_id
        """,
        {"user_id": user_id}
    )

    return {
        "total_revenue":    round(float(result["total_revenue"]), 2),
        "total_orders":     result["total_orders"],
        "total_customers":  result["total_customers"],
        "avg_order_value":  round(float(result["avg_order_value"]), 2),
    }


# ── Top Products ──────────────────────────────────────────
# Returns top 10 products ranked by total revenue
@router.get("/products")
async def get_top_products(user_id: str = Depends(get_current_user)):

    rows = await database.fetch_all(
        """
        SELECT
            p.name,
            p.category,
            SUM(o.revenue)   AS total_revenue,
            SUM(o.quantity)  AS total_units
        FROM "Order" o
        JOIN "Product" p ON o."productId" = p.id
        WHERE o."userId" = :user_id
        GROUP BY p.id, p.name, p.category
        ORDER BY total_revenue DESC
        LIMIT 10
        """,
        {"user_id": user_id}
    )

    return [
        {
            "name":          row["name"],
            "category":      row["category"],
            "total_revenue": round(float(row["total_revenue"]), 2),
            "total_units":   row["total_units"],
        }
        for row in rows
    ]


# ── Top Customers ─────────────────────────────────────────
# Returns top 10 customers ranked by total spend
@router.get("/customers")
async def get_top_customers(user_id: str = Depends(get_current_user)):

    rows = await database.fetch_all(
        """
        SELECT
            c.name,
            c.email,
            COUNT(o.id)      AS total_orders,
            SUM(o.revenue)   AS total_spend
        FROM "Order" o
        JOIN "Customer" c ON o."customerId" = c.id
        WHERE o."userId" = :user_id
        GROUP BY c.id, c.name, c.email
        ORDER BY total_spend DESC
        LIMIT 10
        """,
        {"user_id": user_id}
    )

    return [
        {
            "name":         row["name"],
            "email":        row["email"],
            "total_orders": row["total_orders"],
            "total_spend":  round(float(row["total_spend"]), 2),
        }
        for row in rows
    ]


# ── Revenue Trends ────────────────────────────────────────
# Returns revenue grouped by month — powers the line chart
@router.get("/trends")
async def get_trends(user_id: str = Depends(get_current_user)):

    rows = await database.fetch_all(
        """
        SELECT
            TO_CHAR(DATE_TRUNC('month', "orderDate"), 'Mon YYYY') AS month,
            DATE_TRUNC('month', "orderDate")                       AS month_date,
            COALESCE(SUM(revenue), 0)                             AS revenue,
            COUNT(*)                                               AS orders
        FROM "Order"
        WHERE "userId" = :user_id
        GROUP BY month_date
        ORDER BY month_date ASC
        """,
        {"user_id": user_id}
    )

    return [
        {
            "month":   row["month"],        # e.g. "Oct 2025"
            "revenue": round(float(row["revenue"]), 2),
            "orders":  row["orders"],
        }
        for row in rows
    ]