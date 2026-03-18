# services/rag.py
from services.faiss_index import search_index
from dotenv import load_dotenv
from groq import AsyncGroq
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ── Prompt Builder ────────────────────────────────────────

def build_prompt(
    question:             str,
    chunks:               list[str],
    conversation_history: list[dict] = []
) -> str:
    """
    Assembles the complete prompt from:
    - Retrieved data chunks (the context)
    - Conversation history (for follow-up questions)
    - The current question

    Passed to the LLM as the user message.
    """

    # Format retrieved chunks as a numbered list
    context = "\n".join([
        f"[{i+1}] {chunk}"
        for i, chunk in enumerate(chunks)
    ])

    # Include last 4 messages of conversation history
    # Sliding window — prevents context window overflow
    history_text = ""
    if conversation_history:
        history_text = "\n\nPrevious conversation:\n"
        for msg in conversation_history[-4:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    # Complete prompt — structure determines answer quality
    prompt = f"""You are a helpful analytics assistant for an e-commerce store owner.
Your job is to answer questions about their store performance using only the data below.

Rules:
- Use ONLY the store data provided — never make up numbers or facts
- Be specific — mention actual product names, amounts, and dates from the data
- Keep answers concise and actionable
- If the data doesn't contain enough information say so clearly

Store data:
{context}
{history_text}
Question: {question}

Answer:"""

    return prompt


# ── LLM Call ──────────────────────────────────────────────

async def call_llm(prompt: str) -> str:
    """
    Calls Llama 3.1 8B via Groq's API.
    Groq uses LPU hardware — responses typically under 1 second.
    Free tier: 14,400 requests/day — plenty for portfolio use.
    """
    client = AsyncGroq(api_key=GROQ_API_KEY)

    try:
        print("🤖 Calling Llama 3.1 8B via Groq...")

        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful e-commerce analytics assistant. Answer questions based only on the store data provided. Never make up numbers or facts."
                },
                {
                    "role":    "user",
                    "content": prompt
                }
            ],
            max_tokens=  512,
            temperature= 0.3,
        )

        answer = response.choices[0].message.content.strip()
        print(f"✅ Got answer ({len(answer)} chars)")
        return answer

    except Exception as e:
        print(f"❌ Groq error: {e}")
        return f"LLM temporarily unavailable: {str(e)}"


# ── RAG Pipeline ──────────────────────────────────────────

async def run_rag_query(
    user_id:              str,
    question:             str,
    conversation_history: list[dict] = []
) -> dict:
    """
    The complete RAG pipeline:
    1. Retrieve relevant chunks from FAISS
    2. Build the prompt
    3. Call the LLM
    4. Return the answer with metadata
    """

    # ── Step 1: Retrieve ──────────────────────────────────
    print(f"🔍 Searching index for: '{question[:50]}...'")
    results = search_index(user_id, question, top_k=5)

    if not results:
        return {
            "answer":  "No data found. Please build your index first using POST /index/build.",
            "chunks":  [],
            "sources": 0
        }

    chunks = [r["chunk"] for r in results]
    print(f"📚 Retrieved {len(chunks)} relevant chunks")

    # ── Step 2: Build prompt ──────────────────────────────
    prompt = build_prompt(question, chunks, conversation_history)
    print(f"📝 Prompt assembled ({len(prompt)} characters)")

    # ── Step 3: Call LLM ──────────────────────────────────
    answer = await call_llm(prompt)

    return {
        "answer":  answer,
        "chunks":  chunks,
        "sources": len(chunks)
    }