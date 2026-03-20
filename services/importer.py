# services/importer.py
import csv
import uuid
import io
from datetime import datetime
from pydantic import BaseModel, validator
from database import database
from services.faiss_index import build_user_index


# ── Pydantic models for CSV validation ───────────────────

class ProductRow(BaseModel):
    name:     str
    category: str = "Uncategorized"
    price:    float
    stock:    int = 0

    @validator("price")
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return round(v, 2)

    @validator("stock")
    def stock_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError("Stock cannot be negative")
        return v

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip()


class OrderRow(BaseModel):
    product_name:   str
    customer_name:  str
    customer_email: str
    quantity:       int
    revenue:        float
    order_date:     str

    @validator("quantity")
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @validator("revenue")
    def revenue_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Revenue must be greater than 0")
        return round(v, 2)

    @validator("order_date")
    def parse_date(cls, v):
        # Accept multiple date formats
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                datetime.strptime(v.strip(), fmt)
                return v.strip()
            except ValueError:
                continue
        raise ValueError(f"Invalid date format: {v}. Use YYYY-MM-DD")


# ── Products import ───────────────────────────────────────

async def import_products(
    content: bytes,
    user_id: str
) -> dict:
    """
    Parses a products CSV file and bulk inserts into PostgreSQL.
    Returns summary of imported, skipped, and error rows.
    """
    text     = content.decode("utf-8-sig")  # utf-8-sig handles Excel BOM
    reader   = csv.DictReader(io.StringIO(text))

    imported = 0
    errors   = []

    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        try:
            # Strip whitespace from all values
            clean_row = {k.strip(): v.strip() for k, v in row.items()}

            # Validate with Pydantic
            product = ProductRow(**clean_row)

            # Insert into database
            await database.execute(
                """
                INSERT INTO "Product"
                    (id, "userId", name, category, price, stock, "createdAt")
                VALUES
                    (:id, :user_id, :name, :category, :price, :stock, NOW())
                """,
                {
                    "id":       str(uuid.uuid4()),
                    "user_id":  user_id,
                    "name":     product.name,
                    "category": product.category,
                    "price":    product.price,
                    "stock":    product.stock,
                }
            )
            imported += 1

        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    return {
        "imported": imported,
        "errors":   errors,
        "type":     "products"
    }


# ── Orders import ─────────────────────────────────────────

async def import_orders(
    content: bytes,
    user_id: str
) -> dict:
    """
    Parses an orders CSV file.
    Creates customers if they don't exist, then inserts orders.
    """
    text   = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    errors   = []

    # Cache customer and product IDs to avoid repeated DB lookups
    customer_cache = {}
    product_cache  = {}

    for i, row in enumerate(reader, start=2):
        try:
            clean_row = {k.strip(): v.strip() for k, v in row.items()}
            order     = OrderRow(**clean_row)

            # ── Get or create customer ────────────────────
            customer_key = order.customer_email.lower()
            if customer_key not in customer_cache:
                existing = await database.fetch_one(
                    """
                    SELECT id FROM "Customer"
                    WHERE "userId" = :user_id AND email = :email
                    """,
                    {"user_id": user_id, "email": customer_key}
                )
                if existing:
                    customer_cache[customer_key] = str(existing["id"])
                else:
                    cid = str(uuid.uuid4())
                    await database.execute(
                        """
                        INSERT INTO "Customer"
                            (id, "userId", name, email, "createdAt")
                        VALUES
                            (:id, :user_id, :name, :email, NOW())
                        """,
                        {
                            "id":      cid,
                            "user_id": user_id,
                            "name":    order.customer_name,
                            "email":   customer_key,
                        }
                    )
                    customer_cache[customer_key] = cid

            # ── Get product ID ────────────────────────────
            product_key = order.product_name.lower().strip()
            if product_key not in product_cache:
                product = await database.fetch_one(
                    """
                    SELECT id FROM "Product"
                    WHERE "userId" = :user_id
                    AND LOWER(name) = :name
                    """,
                    {"user_id": user_id, "name": product_key}
                )
                if not product:
                    errors.append({
                        "row":   i,
                        "error": f"Product '{order.product_name}' not found. Import products first."
                    })
                    continue
                product_cache[product_key] = str(product["id"])

            # ── Insert order ──────────────────────────────
            order_date = datetime.strptime(
                order.order_date,
                "%Y-%m-%d" if "-" in order.order_date else "%d/%m/%Y"
            )

            await database.execute(
                """
                INSERT INTO "Order"
                    (id, "userId", "productId", "customerId",
                     quantity, revenue, "orderDate", "createdAt")
                VALUES
                    (:id, :user_id, :product_id, :customer_id,
                     :quantity, :revenue, :order_date, NOW())
                """,
                {
                    "id":          str(uuid.uuid4()),
                    "user_id":     user_id,
                    "product_id":  product_cache[product_key],
                    "customer_id": customer_cache[customer_key],
                    "quantity":    order.quantity,
                    "revenue":     order.revenue,
                    "order_date":  order_date,
                }
            )
            imported += 1

        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    return {
        "imported": imported,
        "errors":   errors,
        "type":     "orders"
    }