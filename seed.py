# seed.py
import asyncio
import uuid
import random
from datetime import datetime, timedelta
from database import database
from auth import hash_password
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────
TEST_EMAIL    = "test@shopsense.com"
TEST_PASSWORD = "password123"
TEST_STORE    = "Test Store"

PRODUCTS = [
    ("AirPods Pro",          "Electronics",   249.99, 120),
    ("Mechanical Keyboard",  "Electronics",    89.99, 200),
    ("USB-C Hub",            "Electronics",    49.99, 350),
    ("Webcam HD",            "Electronics",    79.99, 180),
    ("Monitor Stand",        "Accessories",    39.99, 220),
    ("Desk Mat XL",          "Accessories",    29.99, 400),
    ("Cable Management Kit", "Accessories",    19.99, 500),
    ("Ergonomic Chair",      "Furniture",     399.99,  40),
    ("Standing Desk",        "Furniture",     599.99,  25),
    ("Desk Lamp LED",        "Furniture",      44.99, 160),
    ("Python Crash Course",  "Books",          29.99, 300),
    ("Clean Code",           "Books",          34.99, 280),
    ("The Lean Startup",     "Books",          24.99, 320),
    ("Wireless Mouse",       "Electronics",    39.99, 250),
    ("Laptop Stand",         "Accessories",    49.99, 190),
    ("Blue Light Glasses",   "Accessories",    24.99, 310),
    ("Noise Cancelling Headphones", "Electronics", 199.99, 90),
    ("Smart Plug",           "Electronics",    19.99, 450),
    ("Whiteboard",           "Furniture",      89.99,  70),
    ("Sticky Notes Pack",    "Accessories",     9.99, 600),
]

CUSTOMER_NAMES = [
    ("Alice Johnson",  "alice@example.com"),
    ("Bob Smith",      "bob@example.com"),
    ("Carol White",    "carol@example.com"),
    ("David Brown",    "david@example.com"),
    ("Eva Martinez",   "eva@example.com"),
    ("Frank Lee",      "frank@example.com"),
    ("Grace Kim",      "grace@example.com"),
    ("Henry Wilson",   "henry@example.com"),
    ("Iris Chen",      "iris@example.com"),
    ("Jack Davis",     "jack@example.com"),
]

# ── Helpers ───────────────────────────────────────────────
def random_date_last_6_months() -> datetime:
    days_ago = random.randint(0, 180)
    return datetime.utcnow() - timedelta(days=days_ago)

# ── Main seed function ────────────────────────────────────
async def seed():
    await database.connect()
    print("✅ Connected to database")

    # ── 1. Get or create test user ────────────────────────
    existing_user = await database.fetch_one(
        'SELECT id FROM "User" WHERE email = :email',
        {"email": TEST_EMAIL}
    )

    if existing_user:
        user_id = str(existing_user["id"])
        print(f"👤 Using existing user: {TEST_EMAIL}")
    else:
        user_id = str(uuid.uuid4())
        await database.execute(
            """
            INSERT INTO "User" (id, email, "passwordHash", "storeName", "createdAt")
            VALUES (:id, :email, :password_hash, :store_name, NOW())
            """,
            {
                "id":            user_id,
                "email":         TEST_EMAIL,
                "password_hash": hash_password(TEST_PASSWORD),
                "store_name":    TEST_STORE,
            }
        )
        print(f"👤 Created new user: {TEST_EMAIL}")

    # ── 2. Clear existing seed data for this user ─────────
    await database.execute('DELETE FROM "Order"   WHERE "userId" = :uid', {"uid": user_id})
    await database.execute('DELETE FROM "Product" WHERE "userId" = :uid', {"uid": user_id})
    await database.execute('DELETE FROM "Customer" WHERE "userId" = :uid', {"uid": user_id})
    print("🧹 Cleared existing data")

    # ── 3. Insert customers ───────────────────────────────
    customer_ids = []
    for name, email in CUSTOMER_NAMES:
        cid = str(uuid.uuid4())
        customer_ids.append(cid)
        await database.execute(
            """
            INSERT INTO "Customer" (id, "userId", name, email, "createdAt")
            VALUES (:id, :user_id, :name, :email, NOW())
            """,
            {
                "id":      cid,
                "user_id": user_id,
                "name":    name,
                "email":   email,
            }
        )
    print(f"👥 Inserted {len(customer_ids)} customers")

    # ── 4. Insert products ────────────────────────────────
    product_ids = []
    for name, category, price, stock in PRODUCTS:
        pid = str(uuid.uuid4())
        product_ids.append((pid, price))
        await database.execute(
            """
            INSERT INTO "Product" (id, "userId", name, category, price, stock, "createdAt")
            VALUES (:id, :user_id, :name, :category, :price, :stock, NOW())
            """,
            {
                "id":       pid,
                "user_id":  user_id,
                "name":     name,
                "category": category,
                "price":    price,
                "stock":    stock,
            }
        )
    print(f"📦 Inserted {len(product_ids)} products")

    # ── 5. Insert orders ──────────────────────────────────
    order_count = 0
    for _ in range(200):
        pid, price     = random.choice(product_ids)
        cid            = random.choice(customer_ids)
        quantity       = random.randint(1, 5)
        revenue        = round(price * quantity, 2)
        order_date     = random_date_last_6_months()

        await database.execute(
            """
            INSERT INTO "Order" (id, "userId", "productId", "customerId", quantity, revenue, "orderDate", "createdAt")
            VALUES (:id, :user_id, :product_id, :customer_id, :quantity, :revenue, :order_date, NOW())
            """,
            {
                "id":          str(uuid.uuid4()),
                "user_id":     user_id,
                "product_id":  pid,
                "customer_id": cid,
                "quantity":    quantity,
                "revenue":     revenue,
                "order_date":  order_date,
            }
        )
        order_count += 1

    print(f"🛒 Inserted {order_count} orders")

    # ── 6. Print summary ──────────────────────────────────
    total_revenue = await database.fetch_one(
        'SELECT SUM(revenue) as total FROM "Order" WHERE "userId" = :uid',
        {"uid": user_id}
    )
    print(f"\n🎉 Seed complete!")
    print(f"   User:      {TEST_EMAIL}")
    print(f"   Customers: {len(customer_ids)}")
    print(f"   Products:  {len(product_ids)}")
    print(f"   Orders:    {order_count}")
    print(f"   Revenue:   ${float(total_revenue['total']):.2f}")

    await database.disconnect()

# ── Run ───────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(seed())