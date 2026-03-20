# routers/importer.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from auth import get_current_user
from services.importer import import_products, import_orders
from services.faiss_index import build_user_index

router = APIRouter(prefix="/import", tags=["Import"])


@router.post("/csv")
async def import_csv(
    file:    UploadFile = File(...),
    type:    str        = "products",   # "products" or "orders"
    user_id: str        = Depends(get_current_user)
):
    """
    Upload a CSV file to import products or orders.
    Automatically rebuilds the FAISS index after import.

    Query params:
    - type: "products" or "orders"
    """

    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted"
        )

    # Validate import type
    if type not in ["products", "orders"]:
        raise HTTPException(
            status_code=400,
            detail="type must be 'products' or 'orders'"
        )

    # Read file content
    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    # Run the appropriate importer
    if type == "products":
        result = await import_products(content, user_id)
    else:
        result = await import_orders(content, user_id)

    # Re-index FAISS automatically after import
    # This ensures the AI chatbot uses the latest data
    print(f"Re-indexing FAISS for user {user_id[:8]}...")
    index_result = await build_user_index(user_id)

    return {
        "import":  result,
        "reindex": index_result,
        "message": f"Successfully imported {result['imported']} {type} and rebuilt AI index"
    }