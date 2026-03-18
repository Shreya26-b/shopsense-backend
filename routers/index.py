# routers/index.py
from fastapi import APIRouter, Depends
from auth import get_current_user
from services.faiss_index import build_user_index

router = APIRouter(prefix="/index", tags=["Index"])

@router.post("/build")
async def build_index(user_id: str = Depends(get_current_user)):
    """
    Builds the FAISS vector index for the authenticated user.
    Fetches all their products and orders, embeds them,
    and saves the index to disk.
    """
    result = await build_user_index(user_id)
    return result