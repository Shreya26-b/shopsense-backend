# routers/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth import get_current_user
from services.rag import run_rag_query
from database import database

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Request/Response models ───────────────────────────────

class ChatMessage(BaseModel):
    role:    str   # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    question:             str
    conversation_history: list[ChatMessage] = []


# ── Chat endpoint ─────────────────────────────────────────

@router.post("/query")
async def chat_query(
    body:    ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Main RAG chatbot endpoint.
    Retrieves relevant data, builds prompt, calls LLM,
    saves conversation to database, returns answer.
    """

    # Run the complete RAG pipeline
    result = await run_rag_query(
        user_id=user_id,
        question=body.question,
        conversation_history=[
            m.dict() for m in body.conversation_history
        ]
    )

    # Save the Q&A to chat history in database
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
async def get_chat_history(user_id: str = Depends(get_current_user)):
    """
    Returns all past Q&A pairs for the authenticated user.
    Used to populate the chat history panel in the UI.
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