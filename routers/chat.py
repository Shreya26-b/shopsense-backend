# routers/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth import get_current_user
from services.rag import run_rag_query
from database import database

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Request models ────────────────────────────────────────

class ChatMessage(BaseModel):
    role:    str
    content: str

class ChatRequest(BaseModel):
    question:             str
    conversation_history: list[ChatMessage] = []


# ── Chat query endpoint ───────────────────────────────────

@router.post("/query")
async def chat_query(
    body:    ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Main RAG chatbot endpoint.
    Retrieves relevant chunks, builds prompt,
    calls Groq LLM, saves to DB, returns answer.
    """
    result = await run_rag_query(
        user_id=user_id,
        question=body.question,
        conversation_history=[
            m.dict() for m in body.conversation_history
        ]
    )

    # Save Q&A to database for chat history
    await database.execute(
        """
        INSERT INTO "ChatHistory"
            (id, "userId", question, answer, "createdAt")
        VALUES
            (gen_random_uuid(), :user_id, :question, :answer, NOW())
        """,
        {
            "user_id":  user_id,
            "question": body.question,
            "answer":   result["answer"],
        }
    )

    return {
        "question": body.question,
        "answer":   result["answer"],
        "sources":  result["sources"],
    }


# ── Chat history endpoint ─────────────────────────────────

@router.get("/history")
async def get_chat_history(
    user_id: str = Depends(get_current_user)
):
    """
    Returns last 50 Q&A pairs for the authenticated user.
    """
    rows = await database.fetch_all(
        """
        SELECT question, answer, "createdAt"
        FROM "ChatHistory"
        WHERE "userId" = :user_id
        ORDER BY "createdAt" DESC
        LIMIT 50
        """,
        {"user_id": user_id}
    )

    return [
        {
            "question":   row["question"],
            "answer":     row["answer"],
            "created_at": str(row["createdAt"]),
        }
        for row in rows
    ]